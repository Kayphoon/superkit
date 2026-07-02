#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MAX_ENTRIES = int(os.environ.get("SUPERWIKI_HOOK_MAX_ENTRIES", "4"))
MAX_CONTEXT_CHARS = int(os.environ.get("SUPERWIKI_HOOK_MAX_CHARS", "6000"))
MAX_SOURCE_CHARS = int(os.environ.get("SUPERWIKI_HOOK_MAX_SOURCE_CHARS", "9000"))
MAX_TRANSCRIPT_CHARS = int(os.environ.get("SUPERWIKI_HOOK_MAX_TRANSCRIPT_CHARS", "12000"))
FRONTMATTER_RE = re.compile(r"^---\n(?P<frontmatter>.*?)\n---\n(?P<body>.*)$", re.DOTALL)
TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]{2,}|[\u4e00-\u9fff]{2,}")
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "what",
    "when",
    "where",
    "怎么",
    "什么",
    "这个",
    "那个",
    "可以",
    "需要",
    "项目",
    "一下",
    "进行",
}


@dataclass(frozen=True)
class WikiEntry:
    name: str
    path: Path
    description: str
    body: str
    score: int


def main() -> int:
    if os.environ.get("SUPERWIKI_HOOK_DISABLE") == "1":
        return 0

    payload = read_payload()
    if payload.get("hook_event_name") != "UserPromptSubmit":
        return 0

    prompt = str(payload.get("prompt") or "")
    cwd = Path(str(payload.get("cwd") or os.getcwd())).resolve()
    project_root = find_project_root(cwd)
    if project_root is None:
        return 0

    query_text = build_query_text(prompt, payload.get("transcript_path"))
    entries = rank_wikis(project_root, query_text)
    if not entries:
        return 0

    packet = render_packet(project_root, prompt, entries)
    if not packet:
        return 0

    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": packet,
                }
            },
            ensure_ascii=False,
        )
    )
    return 0


def read_payload() -> dict[str, Any]:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return {}
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def find_project_root(cwd: Path) -> Path | None:
    for directory in [cwd, *cwd.parents]:
        if (directory / ".wiki" / "skills").is_dir():
            return directory
        if (directory / ".git").exists() and (directory / ".wiki" / "skills").is_dir():
            return directory
    return None


def build_query_text(prompt: str, transcript_path: Any) -> str:
    fragments = [prompt]
    if isinstance(transcript_path, str) and transcript_path:
        path = Path(transcript_path)
        if path.is_file():
            fragments.append(read_recent_transcript_text(path))
    return "\n".join(fragment for fragment in fragments if fragment)


def read_recent_transcript_text(path: Path) -> str:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - MAX_TRANSCRIPT_CHARS))
            raw = handle.read().decode("utf-8", errors="replace")
    except Exception:
        return ""

    texts: list[str] = []
    for line in raw.splitlines()[-80:]:
        try:
            item = json.loads(line)
        except Exception:
            continue
        texts.extend(extract_strings(item)[:4])
    return "\n".join(texts)[-MAX_TRANSCRIPT_CHARS:]


def extract_strings(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, str):
        if len(value) > 20:
            found.append(value)
    elif isinstance(value, list):
        for item in value:
            found.extend(extract_strings(item))
    elif isinstance(value, dict):
        for key in ("content", "text", "message", "prompt", "additionalContext"):
            if key in value:
                found.extend(extract_strings(value[key]))
    return found


def rank_wikis(project_root: Path, query_text: str) -> list[WikiEntry]:
    wiki_root = project_root / ".wiki" / "skills"
    query_terms = tokenize(query_text)
    if not query_terms:
        return []

    entries: list[WikiEntry] = []
    for skill_file in sorted(wiki_root.glob("wiki-*/SKILL.md")) + sorted(wiki_root.glob("wiki_*/SKILL.md")):
        parsed = parse_skill(skill_file)
        if parsed is None:
            continue
        name, description, body = parsed
        searchable = f"{skill_file.parent.name}\n{name}\n{description}\n{body[:MAX_SOURCE_CHARS]}".lower()
        score = score_text(searchable, query_terms)
        if score > 0:
            entries.append(WikiEntry(name, skill_file, description, body, score))

    return sorted(entries, key=lambda item: (-item.score, str(item.path)))[:MAX_ENTRIES]


def parse_skill(path: Path) -> tuple[str, str, str] | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    match = FRONTMATTER_RE.match(text)
    if not match:
        return path.parent.name, "", text

    frontmatter = match.group("frontmatter")
    body = match.group("body")
    name = path.parent.name
    description_lines: list[str] = []
    in_description = False

    for raw_line in frontmatter.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("name:"):
            name = stripped.split(":", 1)[1].strip().strip('"')
            in_description = False
        elif stripped.startswith("description:"):
            value = stripped.split(":", 1)[1].strip()
            in_description = value in {"|", ">"} or value == ""
            if value not in {"|", ">", ""}:
                description_lines.append(value.strip('"'))
        elif in_description:
            if line.startswith(" ") or line.startswith("\t") or stripped.startswith("-"):
                description_lines.append(stripped)
            else:
                in_description = False

    return name, "\n".join(description_lines).strip(), body


def tokenize(text: str) -> set[str]:
    terms = {match.group(0).lower() for match in TOKEN_RE.finditer(text)}
    return {
        term
        for term in terms
        if term not in STOPWORDS and len(term) >= 2 and not term.startswith("/var/")
    }


def score_text(text: str, query_terms: set[str]) -> int:
    score = 0
    for term in query_terms:
        count = text.count(term)
        if count:
            score += min(count, 5)
            if term in text[:2000]:
                score += 2
    return score


def render_packet(project_root: Path, prompt: str, entries: list[WikiEntry]) -> str:
    lines = [
        "<superwiki-memory-packet>",
        "The following project-memory entries were selected by the SuperWiki UserPromptSubmit hook.",
        "Treat them as retrieval hints. Current code remains the source of truth; verify code before edits.",
        "",
        f"Project root: {project_root}",
        f"User request: {one_line(prompt, 240)}",
        "",
        "Relevant knowledge:",
    ]

    for entry in entries:
        rel_path = safe_relative(entry.path, project_root)
        confidence = confidence_for_score(entry.score)
        summary = summarize(entry.description or entry.body)
        lines.extend(
            [
                "",
                f"- {entry.name} ({confidence}, score={entry.score})",
                f"  path: {rel_path}",
                f"  summary: {summary}",
            ]
        )

    lines.extend(
        [
            "",
            "If this packet is insufficient or the task is high-risk, spawn the `memory-librarian` subagent for deeper retrieval before changing files.",
            "</superwiki-memory-packet>",
        ]
    )

    packet = "\n".join(lines).strip()
    if len(packet) <= MAX_CONTEXT_CHARS:
        return packet
    return packet[: MAX_CONTEXT_CHARS - 120].rstrip() + "\n\n[SuperWiki memory packet truncated by hook budget.]"


def confidence_for_score(score: int) -> str:
    if score >= 12:
        return "high"
    if score >= 5:
        return "medium"
    return "low"


def summarize(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    return one_line(cleaned, 520) if cleaned else "No summary available; read the wiki file if this entry matters."


def one_line(text: str, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def safe_relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
