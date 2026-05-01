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


def _system_prompt(case: CaseSpec) -> str:
    lines = ["你运行在 Ragent6 native harness 中。"]
    if case.allowed_tools:
        lines.extend(
            [
                "如果需要使用工具，只能一次调用一个工具，并且必须严格输出：<tool>{...}</tool>",
                "tool name 只能是以下四个之一：read、exec、write、edit。",
                "不要把 \"read|exec|write|edit\" 当成字面字符串写进 name。",
                "read 示例：<tool>{\"name\":\"read\",\"arguments\":{\"path\":\"fixtures/a.txt\"}}</tool>",
                "exec 示例：<tool>{\"name\":\"exec\",\"arguments\":{\"command\":\"sh fixtures/check.sh\"}}</tool>",
                "write 示例：<tool>{\"name\":\"write\",\"arguments\":{\"path\":\"fixtures/out.json\",\"content\":\"{}\"}}</tool>",
                "edit 示例：<tool>{\"name\":\"edit\",\"arguments\":{\"path\":\"fixtures/a.txt\",\"edits\":[{\"oldText\":\"old\",\"newText\":\"new\"}]}}</tool>",
                "除 <tool>...</tool> 以外不要输出任何多余文字。",
                "如果已经可以回答，就直接输出最终答案本身，不要包裹 markdown，不要解释，不要加标签。",
                "不要输出 assistant:、final-answer: 这类标签。",
                "不要用 exec 只是为了打印或 echo 最终答案；最终答案必须直接作为 assistant 文本返回。",
                "read/write/edit/exec 的 arguments 必须使用正确字段；如果收到工具结果后还需要继续，就再次输出新的 <tool>{...}</tool>。",
                "可用工具仅限: " + ", ".join(case.allowed_tools) + "。",
            ]
        )
    else:
        lines.extend(
            [
                "本题不允许使用任何工具。",
                "不要输出 <tool>...</tool>。",
                "不要只回答 `read`、`exec`、`write`、`edit` 这些工具名。",
                "如果题目要求命令或方案，就直接输出给用户可执行的纯文本命令；如果题目要求结果，就直接输出结果本身。",
                "不要包裹 markdown，不要解释，不要加标签，除非题面明确要求固定标签格式。",
            ]
        )
    if case.max_tool_calls is not None:
        lines.append(f"工具调用总数不得超过 {case.max_tool_calls} 次。")
    if case.max_turns:
        lines.append(f"最多回复 {case.max_turns} 次。")
    if case.allowed_tools:
        lines.extend(
            [
                "多轮示例1：",
                "<tool>{\"name\":\"read\",\"arguments\":{\"path\":\"fixtures/a.txt\"}}</tool>",
                "收到 TOOL_RESULT 后，如果已得到答案，直接输出 final-answer",
                "多轮示例2：",
                "<tool>{\"name\":\"exec\",\"arguments\":{\"command\":\"sh fixtures/check.sh\"}}</tool>",
                "收到 TOOL_RESULT 后，如果成功，直接输出 PASS",
            ]
        )
    return "\n".join(lines)


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

    prompts = [(case_dir / case.prompt_file).read_text(encoding="utf-8")]
    prompts.extend((case_dir / followup).read_text(encoding="utf-8") for followup in case.followup_prompt_files)

    tool_calls: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    assistant_texts: list[str] = []
    turn_runs: list[dict[str, Any]] = []
    aborted = False
    final_answer = ""
    request_error: dict[str, str] | None = None
    started = time.time()

    messages: list[dict[str, str]] = [{"role": "system", "content": _system_prompt(case)}]
    try:
        for prompt in prompts:
            messages.append({"role": "user", "content": prompt})
            nudged_final = False
            internal_turn_budget = max(1, case.max_turns, (case.max_tool_calls or 0) + 1)
            for _turn in range(internal_turn_budget):
                remaining = max(5, int(timeout_seconds - (time.time() - started)))
                if remaining <= 0:
                    aborted = True
                    break
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
                    tool_calls.append(tool_call)
                    tool_output, details = _run_tool(tool_call, workspace_main)
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
                    messages.append({"role": "user", "content": "你刚才没有输出有效答案。现在只输出最终答案本身，不要输出 </think> 或任何标签。"})
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
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
