"""Observability-grade injection detection — see root README for rationale."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class InjectionPattern:
    name: str
    pattern: re.Pattern[str]
    description: str


def _compile(src: str) -> re.Pattern[str]:
    return re.compile(src, re.IGNORECASE | re.DOTALL)


PATTERNS: tuple[InjectionPattern, ...] = (
    InjectionPattern(
        name="ignore_previous_instructions",
        pattern=_compile(r"\bignore\s+(?:all\s+)?(?:previous|prior|above|the above)\b.*\binstructions?\b"),
        description="Classic 'ignore previous instructions' variants",
    ),
    InjectionPattern(
        name="disregard_instructions",
        pattern=_compile(r"\b(?:disregard|forget|skip)\s+(?:all\s+)?(?:previous|prior|your|the)\s+(?:instructions?|rules?|prompt|directives?)\b"),
        description="Disregard/forget/skip instructions",
    ),
    InjectionPattern(
        name="new_instructions_header",
        pattern=_compile(r"^\s*(?:new\s+instructions?|updated\s+instructions?|system\s*:)\s*[:\-]"),
        description="Fake instruction header",
    ),
    InjectionPattern(
        name="role_override_you_are",
        pattern=_compile(r"\byou\s+are\s+(?:now|actually)\s+(?:a\s+|an\s+)?"),
        description="Role override: 'you are now ...'",
    ),
    InjectionPattern(
        name="role_override_act_as",
        pattern=_compile(r"\b(?:act|behave|pretend|roleplay)\s+as\s+(?:a\s+|an\s+|if\s+you)"),
        description="Role override: 'act as', 'pretend to be'",
    ),
    InjectionPattern(
        name="reveal_system_prompt",
        pattern=_compile(r"\b(?:reveal|show|print|output|repeat|display|tell\s+me)\s+(?:your|the)\s+(?:system\s+)?(?:prompt|instructions?|rules?|directives?)\b"),
        description="Attempts to extract the system prompt",
    ),
    InjectionPattern(
        name="initial_prompt_leak",
        pattern=_compile(r"\b(?:initial|original|first|hidden)\s+(?:prompt|instructions?|message|directive)\b"),
        description="References to 'initial/original/hidden' prompts",
    ),
    InjectionPattern(
        name="fake_system_role",
        pattern=_compile(r"<\s*(?:system|/?\s*instruction|/?\s*prompt)\s*>"),
        description="Pseudo-XML system/instruction tags",
    ),
    InjectionPattern(
        name="jailbreak_keywords",
        pattern=_compile(r"\b(?:jailbreak|DAN|do\s+anything\s+now|developer\s+mode)\b"),
        description="Known jailbreak terminology",
    ),
    InjectionPattern(
        name="override_safety",
        pattern=_compile(r"\b(?:bypass|override|ignore)\s+(?:safety|content|moderation)\s+(?:filters?|policy|guidelines?)\b"),
        description="Explicit requests to bypass safety",
    ),
    InjectionPattern(
        name="repeat_above",
        pattern=_compile(r"\brepeat\s+(?:everything|the\s+text|what(?:'s| is)\s+above|word\s+for\s+word)"),
        description="Attempts to extract prior context verbatim",
    ),
    InjectionPattern(
        name="base64_indicator",
        pattern=_compile(r"\b(?:decode|base64|rot13|hex)\s*(?:this|the\s+following|:)"),
        description="Encoding-based obfuscation hints",
    ),
    InjectionPattern(
        name="end_of_context_marker",
        pattern=_compile(r"(?:###|---|```)\s*(?:end|begin)\s+(?:of\s+)?(?:instructions?|prompt|context|system)"),
        description="Fake context-boundary markers",
    ),
    InjectionPattern(
        name="instruction_nullification",
        pattern=_compile(r"\b(?:above|previous)\s+(?:rules?|instructions?)\s+(?:do\s+not\s+apply|are\s+(?:void|cancelled|ignored))\b"),
        description="Nullifying prior instructions",
    ),
    InjectionPattern(
        name="prompt_end_injection",
        pattern=_compile(r"\bend\s+(?:of\s+)?(?:user|human)\s+(?:input|message|turn)\b"),
        description="Fake end-of-turn markers",
    ),
)


@dataclass(frozen=True)
class InjectionMatch:
    pattern_name: str
    description: str
    matched_text: str


def detect(text: str) -> list[InjectionMatch]:
    matches: list[InjectionMatch] = []
    for p in PATTERNS:
        m = p.pattern.search(text)
        if m is not None:
            matches.append(
                InjectionMatch(
                    pattern_name=p.name,
                    description=p.description,
                    matched_text=_truncate(m.group(0)),
                )
            )
    return matches


def _truncate(s: str, limit: int = 120) -> str:
    s = " ".join(s.split())
    return s if len(s) <= limit else s[: limit - 1] + "…"
