from __future__ import annotations

import json
from typing import Any

from .models import CaseResult, CaseSpec

INFRA_TOOL_NAMES = {
    "process",
}

TOOLISH_TOP_LEVEL_KEYS = {
    "path", "file", "filename", "command", "cmd", "shell",
    "content", "text", "value", "edits", "oldText", "newText",
    "old_string", "new_string", "search", "replace", "old", "new",
}


def _result(case: CaseSpec, status: str, score: int | None, reason_code: str, message: str, **evidence: Any) -> CaseResult:
    return CaseResult(
        case_id=case.case_id,
        dimension_id=case.dimension_id,
        status=status,
        score=score,
        checker="common_constraints",
        reason_code=reason_code,
        message=message,
        evidence=evidence,
    )


def assistant_turn_count(trace: dict[str, Any]) -> int:
    texts = trace.get("assistant_texts") or []
    if isinstance(texts, list):
        visible_texts = [str(item).strip() for item in texts if str(item).strip()]
        if visible_texts:
            return len(visible_texts)
    raw = trace.get("assistant_message_count")
    if isinstance(raw, int) and raw >= 0:
        return raw
    if str(trace.get("final_answer", "")).strip():
        return 1
    return 0


def _strip_runtime_artifacts(text: str) -> str:
    cleaned = str(text or "")
    for token in ("<|im_end|>", "<|endoftext|>", "<eos>"):
        cleaned = cleaned.replace(token, "")
    if "<|im_start|>" in cleaned:
        cleaned = cleaned.split("<|im_start|>", 1)[0]
    return cleaned.strip()


def _json_head(text: str) -> Any | None:
    raw = _strip_runtime_artifacts(text).strip()
    if not raw:
        return None
    decoder = json.JSONDecoder()
    try:
        obj, _idx = decoder.raw_decode(raw)
        return obj
    except json.JSONDecodeError:
        return None


def _looks_like_tool_dict(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    name = obj.get("name")
    if not isinstance(name, str) or not name.strip():
        return False
    if isinstance(obj.get("arguments"), dict):
        return True
    return any(key in obj for key in TOOLISH_TOP_LEVEL_KEYS)


def _trace_has_native_parse_artifact(trace: dict[str, Any]) -> bool:
    if str(trace.get("final_answer", "")).strip():
        return False
    assistant_texts = [str(item).strip() for item in trace.get("assistant_texts", []) if str(item).strip()]
    if assistant_texts:
        return False
    tool_results = trace.get("tool_results") or []
    if not tool_results:
        return False
    unsupported = []
    for item in tool_results:
        text = str(item.get("text", ""))
        details = item.get("details") or {}
        error = str(details.get("error", ""))
        combined = f"{text}\n{error}"
        if "unsupported tool:" not in combined.lower():
            return False
        unsupported.append(combined)
    if not unsupported:
        return False
    turn_runs = trace.get("turn_runs") or []
    if not turn_runs:
        return False
    candidate = _strip_runtime_artifacts(str(turn_runs[-1].get("cleaned_response") or turn_runs[-1].get("raw_response") or ""))
    if not candidate or "<tool>" in candidate.lower():
        return False
    obj = _json_head(candidate)
    return isinstance(obj, dict) and not _looks_like_tool_dict(obj) and isinstance(obj.get("name"), str)


def _trace_transport_error(trace: dict[str, Any]) -> str | None:
    adapter_error = trace.get("adapter_error")
    if isinstance(adapter_error, dict):
        message = str(adapter_error.get("message") or "").strip()
        if message:
            return message
    final_answer = str(trace.get("final_answer", "")).strip()
    transport_markers = (
        "urlopen error",
        "connection refused",
        "connection reset",
        "remote end closed connection",
        "timed out",
        "http 5",
        "cuda error",
    )
    lowered = final_answer.lower()
    if trace.get("aborted") and any(marker in lowered for marker in transport_markers):
        return final_answer
    return None


def common_constraint_verdict(case: CaseSpec, trace: dict[str, Any]) -> CaseResult | None:
    tool_calls = trace.get("tool_calls") or []
    used_tools = [
        str(call.get("name", "")).strip()
        for call in tool_calls
        if str(call.get("name", "")).strip() and str(call.get("name", "")).strip() not in INFRA_TOOL_NAMES
    ]
    if used_tools and _trace_has_native_parse_artifact(trace):
        used_tools = []
    allowed_tools = [tool for tool in case.allowed_tools if tool]

    if allowed_tools:
        disallowed_tools = sorted({tool for tool in used_tools if tool not in allowed_tools})
        if disallowed_tools:
            return _result(
                case,
                "fail",
                0,
                "disallowed_tool_used",
                "trace used tools outside case allowlist",
                allowed_tools=allowed_tools,
                used_tools=used_tools,
                disallowed_tools=disallowed_tools,
            )
    elif used_tools:
        return _result(
            case,
            "fail",
            0,
            "disallowed_tool_used",
            "case does not allow tool usage",
            used_tools=used_tools,
        )

    if case.max_tool_calls is not None and len(used_tools) > case.max_tool_calls:
        return _result(
            case,
            "fail",
            0,
            "too_many_tool_calls",
            "tool call count exceeded case limit",
            max_tool_calls=case.max_tool_calls,
            actual_tool_calls=len(used_tools),
            used_tools=used_tools,
        )

    turns = assistant_turn_count(trace)
    if case.max_turns and turns > case.max_turns:
        return _result(
            case,
            "fail",
            0,
            "too_many_turns",
            "assistant turn count exceeded case limit",
            max_turns=case.max_turns,
            actual_turns=turns,
        )

    transport_error = _trace_transport_error(trace)
    if transport_error:
        return _result(
            case,
            "invalid",
            None,
            "adapter_transport_error",
            "adapter/server transport failed before a usable model answer",
            error=transport_error[:400],
            returncode=trace.get("returncode"),
        )

    if trace.get("aborted") and not trace.get("assistant_texts") and not used_tools:
        stderr = str(trace.get("stderr", "")).strip()
        if len(stderr) > 400:
            stderr = stderr[:400] + "..."
        return _result(
            case,
            "fail",
            0,
            "agent_aborted_before_answer",
            "agent aborted before producing a usable answer",
            returncode=trace.get("returncode"),
            stderr=stderr,
        )

    return None
