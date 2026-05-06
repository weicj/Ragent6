from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from ragent6.models import CaseSpec


TOOL_TAG_RE = re.compile(r"<tool>\s*(\{[\s\S]*?\})\s*</tool>", re.IGNORECASE)
TOP_LEVEL_TOOL_ARG_KEYS = {
    "path", "file", "filename", "command", "cmd", "shell",
    "content", "text", "value", "edits", "oldText", "newText",
    "old_string", "new_string", "search", "replace", "old", "new",
}


def _clean_text(text: str) -> str:
    cleaned = str(text or "").strip()
    for token in ("<|im_end|>", "<|endoftext|>", "<eos>"):
        cleaned = cleaned.replace(token, "")
    cleaned = re.sub(r"(?is)<think>\s*</think>", "", cleaned)
    cleaned = cleaned.replace("</think>", "")
    return cleaned.strip()


def _is_zh(case: CaseSpec) -> bool:
    return str(getattr(case, "locale", "") or "").lower().startswith("zh")


def _system_prompt(case: CaseSpec) -> str:
    if _is_zh(case):
        return _system_prompt_zh(case)
    return _system_prompt_en(case)


def _system_prompt_en(case: CaseSpec) -> str:
    lines = ["You are running inside the Ragent6 native harness."]
    if case.allowed_tools:
        allowed = ", ".join(case.allowed_tools)
        lines.extend(
            [
                "When you need a tool, call exactly one tool at a time and output only: <tool>{...}</tool>.",
                "The tool name must be one of the allowed tools for this case: " + allowed + ".",
                "Do not write the literal string \"read|exec|write|edit\" as the tool name.",
                "Do not output any extra text outside <tool>...</tool> when calling a tool.",
                "If you can answer, output the final answer directly: no markdown wrapper, no explanation, no extra label.",
                "Do not output labels such as assistant: or final-answer:.",
                "Do not use exec only to print or echo the final answer; final answers must be returned as assistant text.",
                "Tool arguments must use the correct fields. If a tool result means you need another step, output another <tool>{...}</tool>.",
                "All paths are relative to the workspace root. A reference like docs/a.md inside fixtures should be read as fixtures/docs/a.md.",
                "Use exact file paths from the prompt or the WORKSPACE_FILES list. If read returns ENOENT, do not repeat the same missing path.",
                "When a verification command succeeds or prints OK/PASS, stop using tools and return the requested final answer.",
                "Allowed tools: " + allowed + ".",
            ]
        )
        if "read" in case.allowed_tools and "exec" in case.allowed_tools and any(tool in case.allowed_tools for tool in ("write", "edit")):
            lines.append("If the prompt names a local verifier such as fixtures/check.py or fixtures/check.sh, read that verifier before writing whenever the required file schema is ambiguous.")
        if case.expected.get("search_command_any") and "exec" in case.allowed_tools:
            lines.append("This case requires a local search step. Use exec with rg, grep, or find before reading the matching files.")
        if "read" in case.allowed_tools:
            lines.append("read example: <tool>{\"name\":\"read\",\"arguments\":{\"path\":\"fixtures/a.txt\"}}</tool>")
        if "exec" in case.allowed_tools:
            lines.append("exec example: <tool>{\"name\":\"exec\",\"arguments\":{\"command\":\"sh fixtures/check.sh\"}}</tool>")
        if "write" in case.allowed_tools:
            lines.append("write example: <tool>{\"name\":\"write\",\"arguments\":{\"path\":\"fixtures/out.json\",\"content\":\"{}\"}}</tool>")
        if "edit" in case.allowed_tools:
            lines.append("edit example: <tool>{\"name\":\"edit\",\"arguments\":{\"path\":\"fixtures/a.txt\",\"edits\":[{\"oldText\":\"old\",\"newText\":\"new\"}]}}</tool>")
    else:
        lines.extend(
            [
                "No tools are allowed for this case.",
                "Do not output <tool>...</tool>.",
                "Do not answer with only the tool names `read`, `exec`, `write`, or `edit`.",
                "If the prompt asks for commands or a plan, output the plain-text commands or plan directly.",
                "If the prompt asks for a result, output only the result itself.",
                "Do not wrap the answer in markdown, explain, or add labels unless the prompt explicitly asks for fixed labels.",
            ]
        )
    if case.max_tool_calls is not None:
        lines.append(f"Do not exceed {case.max_tool_calls} total tool calls.")
    if case.max_turns:
        lines.append(f"Do not exceed {case.max_turns} assistant turns.")
    if case.allowed_tools:
        lines.extend(
            [
                "Multi-turn example 1:",
                "<tool>{\"name\":\"read\",\"arguments\":{\"path\":\"fixtures/a.txt\"}}</tool>",
                "After receiving TOOL_RESULT, output the final answer directly if you have it.",
                "Multi-turn example 2:",
                "<tool>{\"name\":\"exec\",\"arguments\":{\"command\":\"sh fixtures/check.sh\"}}</tool>",
                "After receiving TOOL_RESULT, output PASS directly if the check succeeded.",
            ]
        )
    return "\n".join(lines)


def _system_prompt_zh(case: CaseSpec) -> str:
    lines = ["你正在 Ragent6 native harness 中运行。"]
    if case.allowed_tools:
        allowed = "、".join(case.allowed_tools)
        lines.extend(
            [
                "需要使用工具时，一次只调用一个工具，并且只输出：<tool>{...}</tool>。",
                "工具名只能是本题允许的工具：" + allowed + "。",
                "不要把字面字符串 \"read|exec|write|edit\" 当作工具名输出。",
                "调用工具时，不要在 <tool>...</tool> 外输出任何额外文字。",
                "如果已经可以回答，直接输出最终答案：不要 markdown 包裹，不要解释，不要额外标签。",
                "不要输出 assistant: 或 final-answer: 这类标签。",
                "不要只为了打印最终答案而使用 exec 或 echo；最终答案必须作为 assistant 文本返回。",
                "工具参数必须使用正确字段。如果工具结果表示还需要下一步，就继续输出另一个 <tool>{...}</tool>。",
                "所有路径都相对工作区根目录；fixtures 内文档引用的 docs/a.md 应按 fixtures/docs/a.md 读取。",
                "优先使用题目或 WORKSPACE_FILES 中出现的精确路径。如果 read 返回 ENOENT，不要重复读取同一个不存在路径。",
                "如果验证命令成功或输出 OK/PASS，立即停止调用工具并返回题目要求的最终答案。",
                "允许的工具：" + "、".join(case.allowed_tools) + "。",
            ]
        )
        if "read" in case.allowed_tools and "exec" in case.allowed_tools and any(tool in case.allowed_tools for tool in ("write", "edit")):
            lines.append("如果题目提到本地验证脚本（如 fixtures/check.py 或 fixtures/check.sh），且文件 schema 不完全明确，应先 read 验证脚本，再写入文件。")
        if case.expected.get("search_command_any") and "exec" in case.allowed_tools:
            lines.append("本题要求本地搜索步骤。读取匹配文件前，先用 exec 调用 rg、grep 或 find。")
        if "read" in case.allowed_tools:
            lines.append("read 示例：<tool>{\"name\":\"read\",\"arguments\":{\"path\":\"fixtures/a.txt\"}}</tool>")
        if "exec" in case.allowed_tools:
            lines.append("exec 示例：<tool>{\"name\":\"exec\",\"arguments\":{\"command\":\"sh fixtures/check.sh\"}}</tool>")
        if "write" in case.allowed_tools:
            lines.append("write 示例：<tool>{\"name\":\"write\",\"arguments\":{\"path\":\"fixtures/out.json\",\"content\":\"{}\"}}</tool>")
        if "edit" in case.allowed_tools:
            lines.append("edit 示例：<tool>{\"name\":\"edit\",\"arguments\":{\"path\":\"fixtures/a.txt\",\"edits\":[{\"oldText\":\"old\",\"newText\":\"new\"}]}}</tool>")
    else:
        lines.extend(
            [
                "本题不允许使用工具。",
                "不要输出 <tool>...</tool>。",
                "不要只回答工具名 `read`、`exec`、`write` 或 `edit`。",
                "如果题目要求输出命令或计划，直接输出纯文本命令或计划。",
                "如果题目要求输出结果，只输出结果本身。",
                "除非题目明确要求固定标签，否则不要用 markdown、解释或额外标签包裹答案。",
            ]
        )
    if case.max_tool_calls is not None:
        lines.append(f"总工具调用次数不要超过 {case.max_tool_calls} 次。")
    if case.max_turns:
        lines.append(f"assistant 回合数不要超过 {case.max_turns} 轮。")
    if case.allowed_tools:
        lines.extend(
            [
                "多轮示例 1：",
                "<tool>{\"name\":\"read\",\"arguments\":{\"path\":\"fixtures/a.txt\"}}</tool>",
                "收到 TOOL_RESULT 后，如果已经有答案，就直接输出最终答案。",
                "多轮示例 2：",
                "<tool>{\"name\":\"exec\",\"arguments\":{\"command\":\"sh fixtures/check.sh\"}}</tool>",
                "收到 TOOL_RESULT 后，如果检查成功，就直接输出 PASS。",
            ]
        )
    return "\n".join(lines)


def _localized_prompt_path(case_dir: Path, prompt_file: str, locale: str) -> Path:
    base = case_dir / prompt_file
    if locale:
        localized = base.with_name(f"{base.stem}.{locale}{base.suffix}")
        if localized.is_file():
            return localized
    return base


def _parse_first_json_object(text: str) -> dict[str, Any] | None:
    raw = _clean_text(text)
    start = raw.find("{")
    if start < 0:
        return None
    decoder = json.JSONDecoder()
    try:
        obj, _idx = decoder.raw_decode(raw[start:])
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _parse_first_json_object_loose(text: str) -> dict[str, Any] | None:
    parsed = _parse_first_json_object(text)
    if parsed is not None:
        return parsed
    raw = _clean_text(text)
    start = raw.find("{")
    if start < 0:
        return None
    candidate = raw[start:]
    decoder = json.JSONDecoder()
    for missing in range(0, 5):
        try:
            obj, _idx = decoder.raw_decode(candidate + ("}" * missing))
        except json.JSONDecodeError:
            continue
        return obj if isinstance(obj, dict) else None
    return None


def _request_chat(base_url: str, model_id: str, messages: list[dict[str, str]], max_tokens: int, timeout_seconds: int) -> tuple[str, dict[str, Any]]:
    payload = {
        "model": model_id,
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    headers = {"Content-Type": "application/json"}
    auth_bearer = os.environ.get("RAGENT6_AUTH_BEARER", "").strip()
    auth_header = os.environ.get("RAGENT6_AUTH_HEADER", "Authorization").strip() or "Authorization"
    if auth_bearer:
        headers[auth_header] = f"Bearer {auth_bearer}"
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    elapsed_ms = int((time.time() - started) * 1000)
    data = json.loads(raw)
    content = data["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "".join(item.get("text", "") for item in content if isinstance(item, dict))
    return str(content), {"elapsed_ms": elapsed_ms, "response": data}


def _extract_tool_call(text: str) -> dict[str, Any] | None:
    tool_open = re.search(r"<tool>", text, re.IGNORECASE)
    tool_close = re.search(r"</tool>", text, re.IGNORECASE)
    has_tool_tag = tool_open is not None
    match = TOOL_TAG_RE.search(text)
    parsed = None
    if match:
        try:
            parsed = json.loads(match.group(1))
        except json.JSONDecodeError:
            parsed = None
    if parsed is None and has_tool_tag:
        start = tool_open.end() if tool_open else 0
        end = tool_close.start() if tool_close else len(text)
        parsed = _parse_first_json_object_loose(text[start:end])
    if parsed is None:
        parsed = _parse_first_json_object_loose(text)
    if not isinstance(parsed, dict):
        return None
    if not has_tool_tag:
        name = parsed.get("name")
        looks_like_tool = isinstance(name, str) and name.strip() and (
            isinstance(parsed.get("arguments"), dict) or any(key in parsed for key in TOP_LEVEL_TOOL_ARG_KEYS)
        )
        if not looks_like_tool:
            return None
    normalized = _normalize_tool_call(text, parsed)
    name = str(normalized.get("name", "")).strip()
    if not name and not has_tool_tag:
        return None
    if not name:
        return None
    return normalized


def _normalize_tool_call(raw_text: str, call: dict[str, Any]) -> dict[str, Any]:
    name = str(call.get("name", "")).strip()
    if not name:
        tag_match = re.search(r"<tool>\s*([a-zA-Z_]+)\s*</tool>", raw_text)
        if tag_match:
            name = tag_match.group(1).strip()
    args = dict(call.get("arguments") or {})
    if not args:
        for key in TOP_LEVEL_TOOL_ARG_KEYS:
            if key in call:
                args[key] = call[key]
    if name == "read":
        path = args.get("path") or args.get("file") or args.get("filename")
        if path is not None:
            args["path"] = path
    elif name == "write":
        path = args.get("path") or args.get("file") or args.get("filename")
        content = args.get("content")
        if content is None:
            content = args.get("text")
        if content is None:
            content = args.get("value")
        if path is not None:
            args["path"] = path
        if content is not None:
            args["content"] = content
    elif name == "edit":
        path = args.get("path") or args.get("file") or args.get("filename")
        if path is not None:
            args["path"] = path
        if isinstance(args.get("edits"), list):
            normalized_edits = []
            for edit in args["edits"]:
                if not isinstance(edit, dict):
                    continue
                old_text = edit.get("oldText")
                if old_text is None:
                    old_text = edit.get("oldtext")
                if old_text is None:
                    old_text = edit.get("old_string")
                if old_text is None:
                    old_text = edit.get("search")
                if old_text is None:
                    old_text = edit.get("old")
                new_text = edit.get("newText")
                if new_text is None:
                    new_text = edit.get("newtext")
                if new_text is None:
                    new_text = edit.get("new_string")
                if new_text is None:
                    new_text = edit.get("replace")
                if new_text is None:
                    new_text = edit.get("new")
                normalized_edits.append({"oldText": str(old_text or ""), "newText": str(new_text or "")})
            args["edits"] = normalized_edits
        else:
            old_text = args.get("oldText")
            if old_text is None:
                old_text = args.get("oldtext")
            if old_text is None:
                old_text = args.get("old_string")
            if old_text is None:
                old_text = args.get("search")
            if old_text is None:
                old_text = args.get("old")
            new_text = args.get("newText")
            if new_text is None:
                new_text = args.get("newtext")
            if new_text is None:
                new_text = args.get("new_string")
            if new_text is None:
                new_text = args.get("replace")
            if new_text is None:
                new_text = args.get("new")
            if old_text is not None or new_text is not None:
                args["edits"] = [{"oldText": str(old_text or ""), "newText": str(new_text or "")}]
    elif name == "exec":
        command = args.get("command") or args.get("cmd") or args.get("shell")
        if command is not None:
            args["command"] = command
    return {"name": name, "arguments": args}


def _read_tool(path: Path) -> tuple[str, dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
        return text, {}
    except FileNotFoundError:
        return (
            json.dumps(
                {
                    "status": "error",
                    "tool": "read",
                    "error": f"ENOENT: no such file or directory, access '{path}'",
                },
                ensure_ascii=False,
                indent=2,
            ),
            {"status": "error", "tool": "read", "error": f"ENOENT: no such file or directory, access '{path}'"},
        )
    except IsADirectoryError:
        return (
            json.dumps(
                {
                    "status": "error",
                    "tool": "read",
                    "error": "EISDIR: illegal operation on a directory, read",
                },
                ensure_ascii=False,
                indent=2,
            ),
            {"status": "error", "tool": "read", "error": "EISDIR: illegal operation on a directory, read"},
        )


def _workspace_file_list(workspace_main: Path) -> list[str]:
    files: list[str] = []
    for path in sorted(workspace_main.rglob("*")):
        if path.is_file():
            files.append(path.relative_to(workspace_main).as_posix())
    return files


def _format_workspace_files(workspace_main: Path) -> str:
    files = _workspace_file_list(workspace_main)
    if not files:
        return "WORKSPACE_FILES: (none)"
    return "WORKSPACE_FILES:\n" + "\n".join(f"- {path}" for path in files)


def _similar_fixture_paths(requested: str, available: list[str]) -> list[str]:
    normalized = str(requested or "").strip().replace("\\", "/")
    basename = Path(normalized).name
    matches = []
    if basename:
        matches.extend(path for path in available if Path(path).name == basename)
    if normalized and not normalized.startswith("fixtures/"):
        prefixed = "fixtures/" + normalized.lstrip("/")
        matches.extend(path for path in available if path == prefixed)
    if normalized.startswith("fixtures/"):
        unprefixed = normalized[len("fixtures/"):]
        matches.extend(path for path in available if path.endswith("/" + unprefixed))
    seen = set()
    out = []
    for path in matches:
        if path in seen:
            continue
        seen.add(path)
        out.append(path)
    return out[:8]


def _augment_tool_feedback(
    tool_output: str,
    details: dict[str, Any],
    call: dict[str, Any],
    workspace_main: Path,
    tool_calls: list[dict[str, Any]],
    case: CaseSpec,
) -> tuple[str, dict[str, Any]]:
    name = str(call.get("name", "")).strip()
    arguments = call.get("arguments") or {}
    augmented = str(tool_output)
    extras: dict[str, Any] = {}
    available = _workspace_file_list(workspace_main)

    if name == "read" and (details or {}).get("status") == "error":
        requested = str(arguments.get("path", "")).strip()
        similar = _similar_fixture_paths(requested, available)
        extras["available_files"] = available
        if similar:
            extras["similar_files"] = similar
        guidance = {
            "available_files": available,
            "similar_files": similar,
            "guidance": "Do not repeat the same missing path. Use one of the available_files paths exactly, or return the best final answer if enough evidence is already available.",
        }
        augmented += "\n" + json.dumps(guidance, ensure_ascii=False, indent=2)

    if case.max_tool_calls is not None:
        remaining_after = int(case.max_tool_calls) - len(tool_calls)
        extras["remaining_tool_calls"] = max(0, remaining_after)
        if remaining_after <= 1:
            augmented += "\n" + json.dumps(
                {
                    "remaining_tool_calls": max(0, remaining_after),
                    "guidance": "Tool budget is nearly exhausted. If you have enough evidence, return the final answer now instead of calling another tool.",
                },
                ensure_ascii=False,
                indent=2,
            )

    if extras:
        details = dict(details or {})
        details.update(extras)
    return augmented, details


def _final_answer_nudge(case: CaseSpec, last_tool_output: str = "") -> str:
    prompt = "Tool budget is exhausted. Output only the requested final answer now. Do not call another tool."
    if _is_zh(case):
        prompt = "工具调用预算已经用完。现在只输出题目要求的最终答案，不要再调用工具。"
    if last_tool_output:
        prompt += "\nLast TOOL_RESULT:\n" + last_tool_output[-2000:]
    return prompt


def _write_tool(path: Path, content: str) -> tuple[str, dict[str, Any]]:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return "written", {}
    except IsADirectoryError:
        return (
            json.dumps(
                {
                    "status": "error",
                    "tool": "write",
                    "error": "EISDIR: illegal operation on a directory, write",
                },
                ensure_ascii=False,
                indent=2,
            ),
            {"status": "error", "tool": "write", "error": "EISDIR: illegal operation on a directory, write"},
        )


def _edit_tool(path: Path, arguments: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    try:
        original = path.read_text(encoding="utf-8")
        updated = original
        if isinstance(arguments.get("edits"), list):
            for edit in arguments["edits"]:
                old = str(edit.get("oldText", ""))
                new = str(edit.get("newText", ""))
                updated = updated.replace(old, new, 1)
        else:
            old = str(arguments.get("oldText", ""))
            new = str(arguments.get("newText", ""))
            updated = updated.replace(old, new, 1)
        path.write_text(updated, encoding="utf-8")
        return "applied", {}
    except IsADirectoryError:
        return (
            json.dumps(
                {
                    "status": "error",
                    "tool": "edit",
                    "error": "EISDIR: illegal operation on a directory, edit",
                },
                ensure_ascii=False,
                indent=2,
            ),
            {"status": "error", "tool": "edit", "error": "EISDIR: illegal operation on a directory, edit"},
        )
    except FileNotFoundError:
        return (
            json.dumps(
                {
                    "status": "error",
                    "tool": "edit",
                    "error": f"ENOENT: no such file or directory, access '{path}'",
                },
                ensure_ascii=False,
                indent=2,
            ),
            {"status": "error", "tool": "edit", "error": f"ENOENT: no such file or directory, access '{path}'"},
        )


def _exec_tool(command: str, cwd: Path, timeout_seconds: int = 30) -> tuple[str, dict[str, Any]]:
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
        text = proc.stdout.strip() or "(no output)"
        return text, {"exitCode": proc.returncode}
    except subprocess.TimeoutExpired as exc:
        stdout = (exc.stdout or "").strip() if isinstance(exc.stdout, str) else ""
        text = stdout or f"TIMEOUT after {timeout_seconds}s"
        return (
            text,
            {
                "exitCode": None,
                "error": "TIMEOUT",
                "timeoutSeconds": timeout_seconds,
                "command": command,
            },
        )


def _run_tool(call: dict[str, Any], workspace_main: Path) -> tuple[str, dict[str, Any]]:
    name = str(call.get("name", "")).strip()
    arguments = call.get("arguments") or {}
    if name == "read":
        path = workspace_main / str(arguments.get("path", ""))
        return _read_tool(path)
    if name == "write":
        path = workspace_main / str(arguments.get("path", ""))
        return _write_tool(path, str(arguments.get("content", "")))
    if name == "edit":
        path = workspace_main / str(arguments.get("path", ""))
        return _edit_tool(path, arguments)
    if name == "exec":
        return _exec_tool(str(arguments.get("command", "")), workspace_main)
    return json.dumps({"status": "error", "tool": name, "error": f"unsupported tool: {name}"}, ensure_ascii=False), {"status": "error", "tool": name, "error": f"unsupported tool: {name}"}


def _snapshot_workspace_fixtures(workspace_main: Path, max_chars: int = 200_000) -> dict[str, str]:
    fixtures_root = workspace_main / "fixtures"
    if not fixtures_root.exists():
        return {}
    snapshot: dict[str, str] = {}
    used_chars = 0
    for path in sorted(fixtures_root.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(workspace_main).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        remaining = max_chars - used_chars
        if remaining <= 0:
            break
        if len(text) > remaining:
            snapshot[rel_path] = text[:remaining]
            break
        snapshot[rel_path] = text
        used_chars += len(text)
    return snapshot


def run_case(case: CaseSpec, case_dir: Path, suite_context: Any = None) -> dict[str, Any]:
    base_url = os.environ.get("RAGENT6_BASE_URL")
    model_id = os.environ.get("RAGENT6_MODEL_ID")
    if not base_url or not model_id:
        raise RuntimeError("RAGENT6_BASE_URL and RAGENT6_MODEL_ID are required for native_local adapter")
    max_tokens = int(os.environ.get("RAGENT6_MAX_TOKENS", "2048"))
    timeout_seconds = int(os.environ.get("RAGENT6_AGENT_TIMEOUT", str(case.timeout_seconds)))

    temp_dir = Path(tempfile.mkdtemp(prefix=f"ragent6-native-{case.case_id}-"))
    workspace_main = temp_dir / "workspace-main"
    workspace_main.mkdir(parents=True, exist_ok=True)
    src_fixtures = case_dir / "fixtures"
    if src_fixtures.exists():
        shutil.copytree(src_fixtures, workspace_main / "fixtures", dirs_exist_ok=True)

    prompt_paths = [_localized_prompt_path(case_dir, case.prompt_file, case.locale)]
    prompt_paths.extend(_localized_prompt_path(case_dir, followup, case.locale) for followup in case.followup_prompt_files)
    prompts = [path.read_text(encoding="utf-8") for path in prompt_paths]

    tool_calls: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    assistant_texts: list[str] = []
    turn_runs: list[dict[str, Any]] = []
    aborted = False
    final_answer = ""
    request_error: dict[str, str] | None = None
    started = time.time()

    system_content = _system_prompt(case)
    if case.allowed_tools:
        system_content += "\n\n" + _format_workspace_files(workspace_main)
    messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]
    try:
        for prompt in prompts:
            messages.append({"role": "user", "content": prompt})
            nudged_final = False
            last_tool_output = ""
            internal_turn_budget = max(1, case.max_turns, (case.max_tool_calls or 0) + 1)
            for _turn in range(internal_turn_budget):
                remaining = max(5, int(timeout_seconds - (time.time() - started)))
                if remaining <= 0:
                    aborted = True
                    break
                if case.max_tool_calls is not None and len(tool_calls) >= case.max_tool_calls and not nudged_final:
                    messages.append({"role": "user", "content": _final_answer_nudge(case, last_tool_output)})
                    nudged_final = True
                try:
                    response_text, meta = _request_chat(base_url, model_id, messages, max_tokens, remaining)
                except Exception as exc:  # noqa: BLE001
                    aborted = True
                    final_answer = str(exc)
                    request_error = {
                        "type": exc.__class__.__name__,
                        "message": str(exc),
                    }
                    break
                cleaned = _clean_text(response_text)
                turn_runs.append({"prompt": prompt, "raw_response": response_text, "cleaned_response": cleaned, "elapsed_ms": meta["elapsed_ms"]})
                tool_call = _extract_tool_call(response_text)
                if tool_call is not None:
                    if case.max_tool_calls is not None and len(tool_calls) >= case.max_tool_calls:
                        messages.append({"role": "assistant", "content": response_text})
                        if not nudged_final:
                            messages.append({"role": "user", "content": _final_answer_nudge(case, last_tool_output)})
                            nudged_final = True
                            continue
                        break
                    tool_calls.append(tool_call)
                    tool_output, details = _run_tool(tool_call, workspace_main)
                    tool_output, details = _augment_tool_feedback(tool_output, details, tool_call, workspace_main, tool_calls, case)
                    last_tool_output = tool_output
                    tool_results.append(
                        {
                            "tool_name": tool_call.get("name"),
                            "is_error": bool((details or {}).get("status") == "error"),
                            "text": tool_output,
                            "details": details,
                        }
                    )
                    messages.append({"role": "assistant", "content": response_text})
                    observation = (
                        "TOOL_RESULT\n"
                        + json.dumps(
                            {
                                "name": tool_call.get("name"),
                                "arguments": tool_call.get("arguments") or {},
                                "output": tool_output,
                            },
                            ensure_ascii=False,
                            indent=2,
                        )
                    )
                    messages.append({"role": "user", "content": observation})
                    continue
                if not cleaned and not nudged_final:
                    messages.append({"role": "user", "content": "You did not output a valid answer. Now output only the final answer itself, with no </think> and no labels."})
                    nudged_final = True
                    continue
                assistant_texts.append(cleaned)
                final_answer = cleaned
                messages.append({"role": "assistant", "content": response_text})
                break
            if aborted:
                break
        return {
            "case_id": case.case_id,
            "locale": case.locale,
            "config_path": base_url,
            "returncode": 0 if not aborted else None,
            "stdout": "",
            "stderr": "",
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "assistant_texts": assistant_texts,
            "events_count": len(messages),
            "assistant_message_count": len(assistant_texts),
            "user_message_count": len(prompts),
            "final_answer": final_answer,
            "session_path": "",
            "aborted": aborted,
            "adapter_error": request_error,
            "turn_runs": turn_runs,
            "workspace_files": _snapshot_workspace_fixtures(workspace_main),
            "prompt_files": [path.name for path in prompt_paths],
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
