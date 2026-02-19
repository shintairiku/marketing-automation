"""
Codex-compatible apply_patch parser and applier utilities.

This module centralizes the Codex-style patch parsing and hunk application
logic so that both CLI tools and the web article editor share identical,
robust behaviour.  It enforces a strict interpretation by default, matching
Codex's own ApplyPatch tool while still permitting an optional lenient mode
for future extensions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

__all__ = [
    "ApplyPatch",
    "FileSection",
    "Hunk",
    "PatchError",
    "HunkApplyError",
    "strip_patch_wrappers",
    "parse_apply_patch",
    "apply_hunk",
]


class PatchError(Exception):
    """Base exception raised when a patch cannot be parsed or applied."""


@dataclass(slots=True)
class Hunk:
    """Represents a single @@ hunk block."""

    header: str
    lines: List[str]
    old_start: Optional[int] = None
    old_count: Optional[int] = None
    new_start: Optional[int] = None
    new_count: Optional[int] = None
    anchor_eof: bool = False

    def __post_init__(self) -> None:
        if self.header and self.header.strip().startswith("@@"):
            m = _HUNK_HEADER_RE.match(self.header.strip())
            if m:
                self.old_start = int(m.group(1))
                self.old_count = int(m.group(2) or "1")
                self.new_start = int(m.group(3))
                self.new_count = int(m.group(4) or "1")

    @property
    def context_lines(self) -> List[str]:
        return [_strip_prefix(l) for l in self.lines if l and l[0] == " "]

    @property
    def old_block(self) -> List[str]:
        return [_strip_prefix(l) for l in self.lines if (not l) or l[0] in (" ", "-")]

    @property
    def new_block(self) -> List[str]:
        return [_strip_prefix(l) for l in self.lines if (not l) or l[0] in (" ", "+")]

    @property
    def removed_lines(self) -> List[str]:
        return [_strip_prefix(l) for l in self.lines if l and l.startswith("-")]

    @property
    def added_lines(self) -> List[str]:
        return [_strip_prefix(l) for l in self.lines if l and l.startswith("+")]


@dataclass(slots=True)
class FileSection:
    """One file section within a patch."""

    action: str  # "Add" | "Update" | "Delete" | "Move"
    src_path: str
    dst_path: Optional[str]
    hunks: List[Hunk] = field(default_factory=list)
    add_content: List[str] = field(default_factory=list)


@dataclass(slots=True)
class ApplyPatch:
    sections: List[FileSection]


class HunkApplyError(PatchError):
    """Raised when a hunk cannot be located or applied."""

    def __init__(
        self,
        *,
        file_path: Optional[str],
        header: str,
        context_lines: Sequence[str],
        reason: str,
    ) -> None:
        self.file_path = file_path
        self.header = header
        self.context_lines = list(context_lines)
        super().__init__(reason)


_BEGIN = re.compile(r"^\s*\*\*\*\s+Begin\s+Patch\s*$")
_END = re.compile(r"^\s*\*\*\*\s+End\s+Patch\s*$")
_ADD = re.compile(r"^\s*\*\*\*\s+Add\s+File:\s*(.+?)\s*$")
_UPDATE = re.compile(r"^\s*\*\*\*\s+Update\s+File:\s*(.+?)\s*$")
_DELETE = re.compile(r"^\s*\*\*\*\s+Delete\s+File:\s*(.+?)\s*$")
_MOVE_FILE = re.compile(r"^\s*\*\*\*\s+Move\s+File:\s*(.+?)\s*$")
_MOVE_TO = re.compile(r"^\s*\*\*\*\s+(?:To|Move\s+to):\s*(.+?)\s*$")
_EOF_ANCHOR = re.compile(r"^\s*\*\*\*\s+End\s+of\s+File\s*$")
_HUNK_HEADER_RE = re.compile(r"^@@\s*-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s*@@")
_HUNK_HDR = re.compile(r"^\s*@@.*$")


def strip_patch_wrappers(text: str) -> str:
    """
    Remove common heredoc / fenced code wrappers surrounding a patch string.
    """
    stripped = text.strip()
    # Heredoc form: <<'PATCH' ... PATCH
    heredoc = re.match(r"<<[-~]?['\"]?PATCH['\"]?\s*\n(.*)\nPATCH\s*$", stripped, re.S)
    if heredoc:
        return heredoc.group(1)
    # Triple backtick fences
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 2:
            # drop opening fence and closing fence
            return "\n".join(lines[1:-1])
    return text


def parse_apply_patch(text: str, *, strict: bool = True) -> ApplyPatch:
    """
    Parse a Codex-style apply_patch string into structured sections.
    """
    normalized = strip_patch_wrappers(text).replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")

    try:
        start = next(i for i, line in enumerate(lines) if _BEGIN.match(line))
        end = max(i for i, line in enumerate(lines) if _END.match(line))
    except StopIteration:
        raise PatchError("apply_patch verification failed: Missing *** Begin Patch / *** End Patch")

    cursor = start + 1
    sections: List[FileSection] = []

    def read_add_body(idx: int) -> Tuple[List[str], int]:
        buf: List[str] = []
        while idx < end:
            line = lines[idx]
            if line.startswith("*** "):
                break
            if line.startswith("+"):
                buf.append(line[1:])
            else:
                buf.append(line)
            idx += 1
        return buf, idx

    while cursor < end:
        line = lines[cursor]

        if not line.strip():
            cursor += 1
            continue

        # *** End of File anchors outside of Update blocks are invalid
        if _EOF_ANCHOR.match(line):
            raise PatchError("apply_patch verification failed: *** End of File is only valid inside an Update section")

        m_add = _ADD.match(line)
        if m_add:
            path = m_add.group(1).strip()
            content, cursor = read_add_body(cursor + 1)
            sections.append(FileSection("Add", path, None, [], content))
            continue

        m_del = _DELETE.match(line)
        if m_del:
            path = m_del.group(1).strip()
            sections.append(FileSection("Delete", path, None, [], []))
            cursor += 1
            continue

        m_move = _MOVE_FILE.match(line)
        if m_move:
            src = m_move.group(1).strip()
            idx = cursor + 1
            if idx >= end or not _MOVE_TO.match(lines[idx]):
                raise PatchError("apply_patch verification failed: Move File directive missing destination")
            dst = _MOVE_TO.match(lines[idx]).group(1).strip()  # type: ignore
            sections.append(FileSection("Move", src, dst, [], []))
            cursor = idx + 1
            continue

        m_update = _UPDATE.match(line)
        if m_update:
            path = m_update.group(1).strip()
            idx = cursor + 1
            dst: Optional[str] = None
            hunks: List[Hunk] = []

            if idx < end and _MOVE_TO.match(lines[idx] or ""):
                dst = _MOVE_TO.match(lines[idx]).group(1).strip()  # type: ignore
                idx += 1

            while idx < end:
                current = lines[idx]

                if _EOF_ANCHOR.match(current):
                    if not hunks:
                        raise PatchError("apply_patch verification failed: *** End of File must follow a hunk")
                    hunks[-1].anchor_eof = True
                    idx += 1
                    continue

                if current.startswith("*** "):
                    break
                if not current.strip():
                    idx += 1
                    continue

                if not _HUNK_HDR.match(current):
                    if strict:
                        raise PatchError(
                            f"apply_patch verification failed: Missing @@ header in update for {path} near line {idx + 1}"
                        )
                    # lenient fallback: treat as context-only hunk
                    header = "@@"
                else:
                    header = current.strip()
                    idx += 1

                if header == "@@" and strict:
                    raise PatchError(
                        f"apply_patch verification failed: Missing @@ header in update for {path} near line {idx}"
                    )

                body: List[str] = []
                while idx < end:
                    ln = lines[idx]
                    if _HUNK_HDR.match(ln) or ln.startswith("*** ") or _EOF_ANCHOR.match(ln):
                        break
                    if not ln:
                        body.append(" ")
                    elif ln[0] in (" ", "+", "-"):
                        body.append(ln)
                    else:
                        # treat unexpected prefix as context to remain compatible
                        body.append(" " + ln)
                    idx += 1

                if not body:
                    raise PatchError("apply_patch verification failed: Empty hunk body encountered")

                hunks.append(Hunk(header=header, lines=body))
                continue

            if not hunks:
                raise PatchError(f"apply_patch verification failed: Update section for {path} missing hunks")

            sections.append(FileSection("Update", path, dst, hunks, []))
            cursor = idx
            continue

        raise PatchError(f"apply_patch verification failed: Unknown patch directive: {line.strip()}")

    return ApplyPatch(sections)


def apply_hunk(
    original: List[str],
    hunk: Hunk,
    *,
    strict: bool = True,
    file_path: Optional[str] = None,
) -> Tuple[List[str], int, int]:
    """
    Apply a single hunk to the given list of lines.
    Returns the new lines and (added_count, deleted_count).
    """
    old_block = hunk.old_block
    new_block = hunk.new_block

    if hunk.anchor_eof:
        pos = _match_eof(original, old_block, hunk, file_path)
    else:
        pos = _locate_hunk_position(original, old_block, hunk, strict=strict)
        if pos is None:
            context = hunk.context_lines or old_block
            raise HunkApplyError(
                file_path=file_path,
                header=hunk.header,
                context_lines=context,
                reason="Failed to locate hunk context",
            )

    end = pos + len(old_block)
    new_lines = original[:pos] + new_block + original[end:]
    added = len(hunk.added_lines)
    deleted = len(hunk.removed_lines)
    return new_lines, added, deleted


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _strip_prefix(line: str) -> str:
    if not line:
        return ""
    if line[0] in (" ", "+", "-"):
        return line[1:]
    return line


def _iter_subseq_positions(
    source: Sequence[str],
    needle: Sequence[str],
    *,
    start: int = 0,
    end: Optional[int] = None,
) -> Iterable[int]:
    if end is None:
        end = len(source)
    if not needle:
        return []
    length = len(needle)
    if length > (end - start):
        return []
    for idx in range(start, end - length + 1):
        if all(source[idx + offset] == needle[offset] for offset in range(length)):
            yield idx


def _locate_hunk_position(
    source: List[str],
    block: List[str],
    hunk: Hunk,
    *,
    strict: bool,
) -> Optional[int]:
    if not block:
        return len(source)

    expected = (hunk.old_start - 1) if hunk.old_start else None
    search_window = None
    if expected is not None and hunk.old_count is not None:
        radius = max(hunk.old_count + 4, 32)
        search_window = (max(0, expected - radius), min(len(source), expected + radius))

    candidates: List[int] = []

    if search_window:
        start, end = search_window
        candidates.extend(_iter_subseq_positions(source, block, start=start, end=end))

    if not candidates:
        candidates.extend(_iter_subseq_positions(source, block))

    if not candidates:
        if strict:
            return None
        context = hunk.context_lines
        if context:
            ctx_candidates = list(_iter_subseq_positions(source, context))
            if len(ctx_candidates) == 1:
                return ctx_candidates[0]
        return None

    if len(candidates) == 1:
        return candidates[0]

    if expected is not None:
        closest = min(candidates, key=lambda idx: abs(idx - expected))
    else:
        closest = candidates[0]

    # If multiple candidates remain equally close, consider this ambiguous.
    ties = [idx for idx in candidates if idx == closest]
    if len(ties) > 1 and strict:
        return None
    return closest


def _match_eof(source: List[str], block: List[str], hunk: Hunk, file_path: Optional[str]) -> int:
    if not block:
        return len(source)
    pos = len(source) - len(block)
    if pos < 0 or source[pos:] != block:
        raise HunkApplyError(
            file_path=file_path,
            header=hunk.header,
            context_lines=block[-8:],
            reason="Failed to match *** End of File hunk",
        )
    return pos
