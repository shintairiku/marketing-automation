#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Codex-compatible text edit agent + fact-check → edit multi-agent orchestration.

This module copies the standalone Codex-style patch agent and extends it with
an OpenAI Agents SDK multi-agent workflow:

1. Fact-check agent
   - Reads a user-specified HTML article via local tool access
   - Executes a *mandatory* web search (OpenAI hosted WebSearch tool)
   - Emits a structured FactCheckReport (Pydantic) with issues & citations
2. Conditional text-edit agent handoff
   - Reuses the Codex-style apply_patch workflow for precise edits when
     the fact-check report requires corrections.

Usage (examples):
  python fact_check_multi_agent.py fact-check --article ./docs/post.html --edit-file ./docs/post.html
  python fact_check_multi_agent.py patch --file ./README.md

Requirements:
  pip install openai-agents beautifulsoup4 lxml rich
Env:
  export OPENAI_API_KEY=sk-...
"""

from __future__ import annotations
import argparse
import asyncio
import dataclasses
import importlib
import json
import os
import re
import shutil
import textwrap
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from agents import Agent, ModelSettings, Runner, RunConfig, SQLiteSession, function_tool
from agents import tracing as agent_tracing
from agents.lifecycle import RunHooks
from agents.run_context import RunContextWrapper
from agents.tool import WebSearchTool
import dotenv

dotenv.load_dotenv()

# =========================
# Context
# =========================
@dataclass
class AppContext:
    root: Path               # workspace root (target file's parent)
    target_path: Path        # editable file path (Codex-style agent target)
    article_path: Path       # HTML article path for fact-checking
    session_id: str = "fact-check-text-edit"
    web_search_count: int = 0
    last_fact_report: Optional["FactCheckReport"] = None
    current_phase: Optional[str] = None
    lxml_available: bool = field(default_factory=lambda: importlib.util.find_spec("lxml") is not None)
    # If moved by apply_patch, we update target_path in-place to follow the new location


# =========================
# IO helpers
# =========================
def read_text_lines(p: Path) -> List[str]:
    if not p.exists():
        return []
    # Preserve LF/CRLF detection in write back
    data = p.read_text(encoding="utf-8", errors="replace")
    # Normalize to '\n' internally
    return data.splitlines()

def write_text_lines(p: Path, lines: List[str], prefer_crlf: Optional[bool] = None) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    # Determine newline style
    if prefer_crlf is None:
        prefer_crlf = False
        try:
            raw = p.read_bytes()
            if b"\r\n" in raw and b"\n" in raw:
                prefer_crlf = True
        except Exception:
            pass
    sep = "\r\n" if prefer_crlf else "\n"
    text = sep.join(lines)
    p.write_text(text, encoding="utf-8", errors="ignore")

def rel_to(root: Path, p: Path) -> str:
    try:
        return str(p.relative_to(root))
    except Exception:
        return p.name

def is_within(root: Path, p: Path) -> bool:
    try:
        p.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


# =========================
# Patch model
# =========================
class PatchError(Exception):
    pass

@dataclass
class Hunk:
    header: str               # raw "@@ ...." line
    lines: List[str]          # lines starting with ' ', '+', '-' (empty ok → treated as context)

@dataclass
class FileSection:
    action: str               # "Add" | "Update" | "Delete" | "Move"
    src_path: str             # path in header (relative)
    dst_path: Optional[str]   # for Move or Update+Move
    hunks: List[Hunk]         # for Update
    add_content: List[str]    # for Add (content lines)
    # Delete: no content

@dataclass
class ApplyPatch:
    sections: List[FileSection]


# =========================
# Parser (fully compatible with Codex-style apply_patch)
#  Grammar accepted:
#   *** Begin Patch
#     *** Add File: path
#       [+]content lines... (either '+'-prefixed or raw; we'll accept both)
#     *** Update File: path
#       (optional) *** Move to: newpath
#       @@ optional header
#        [ ' ' context | '-' old | '+' new ]*
#       (repeat hunks)
#     *** Delete File: path
#     *** Move File: oldpath
#       *** To: newpath
#   *** End Patch
# =========================
_BEGIN = re.compile(r"^\s*\*\*\*\s+Begin\s+Patch\s*$")
_END   = re.compile(r"^\s*\*\*\*\s+End\s+Patch\s*$")
_ADD   = re.compile(r"^\s*\*\*\*\s+Add\s+File:\s*(.+?)\s*$")
_UPDATE= re.compile(r"^\s*\*\*\*\s+Update\s+File:\s*(.+?)\s*$")
_DELETE= re.compile(r"^\s*\*\*\*\s+Delete\s+File:\s*(.+?)\s*$")
_MOVE_FILE = re.compile(r"^\s*\*\*\*\s+Move\s+File:\s*(.+?)\s*$")   # alternative form
_MOVE_TO   = re.compile(r"^\s*\*\*\*\s+(?:To|Move\s+to):\s*(.+?)\s*$")
_HUNK_HDR  = re.compile(r"^\s*@@.*$")

def parse_apply_patch(text: str) -> ApplyPatch:
    # normalize newlines
    lines = text.replace("\r\n","\n").replace("\r","\n").split("\n")
    # trim outer lines to Begin..End region
    try:
        start = next(i for i,l in enumerate(lines) if _BEGIN.match(l))
        end   = max(i for i,l in enumerate(lines) if _END.match(l))
    except StopIteration:
        raise PatchError("Missing *** Begin Patch / *** End Patch")

    cursor = start + 1
    sections: List[FileSection] = []

    def read_until_next_marker(idx: int) -> Tuple[List[str], int]:
        """Collect raw lines until next *** Marker or *** End Patch (exclusive)."""
        buf: List[str] = []
        while idx < end:
            l = lines[idx]
            if l.startswith("*** "):  # next section
                break
            buf.append(l)
            idx += 1
        return buf, idx

    while cursor < end:
        line = lines[cursor]
        # skip blanks between sections
        if not line.strip():
            cursor += 1
            continue

        m_add = _ADD.match(line)
        m_upd = _UPDATE.match(line)
        m_del = _DELETE.match(line)
        m_mov = _MOVE_FILE.match(line)

        if m_add:
            path = m_add.group(1).strip()
            raw, cursor2 = read_until_next_marker(cursor + 1)
            # Accept both "+content" and raw lines
            content: List[str] = []
            for r in raw:
                if r.startswith("+"):
                    content.append(r[1:])
                elif _HUNK_HDR.match(r) or r.startswith("- "):
                    # unlikely in Add; treat header as literal content
                    content.append(r.lstrip())
                else:
                    content.append(r)
            sections.append(FileSection("Add", path, None, [], content))
            cursor = cursor2
            continue

        if m_upd:
            path = m_upd.group(1).strip()
            dst: Optional[str] = None
            hunks: List[Hunk] = []
            idx = cursor + 1
            # optional Move to:
            if idx < end and _MOVE_TO.match(lines[idx] or ""):
                dst = _MOVE_TO.match(lines[idx]).group(1).strip()  # type: ignore
                idx += 1

            # gather hunks
            while idx < end:
                if lines[idx].startswith("*** "):
                    break
                if not lines[idx].strip():
                    idx += 1
                    continue
                if _HUNK_HDR.match(lines[idx]):
                    header = lines[idx]
                    idx += 1
                    body: List[str] = []
                    while idx < end:
                        ln = lines[idx]
                        if _HUNK_HDR.match(ln) or ln.startswith("*** "):
                            break
                        # Accept only ' ', '+', '-' as first char; treat empty line as ' ' context
                        if not ln:
                            body.append(" ")
                        elif ln[0] in (" ", "+", "-"):
                            body.append(ln)
                        else:
                            # treat as context
                            body.append(" " + ln)
                        idx += 1
                    hunks.append(Hunk(header=header, lines=body))
                    continue
                # Lines between hunks without @@: treat as context-only hunk
                temp: List[str] = []
                while idx < end and not (lines[idx].startswith("*** ") or _HUNK_HDR.match(lines[idx])):
                    ln = lines[idx]
                    if not ln:
                        temp.append(" ")
                    elif ln[0] in (" ", "+", "-"):
                        temp.append(ln)
                    else:
                        temp.append(" " + ln)
                    idx += 1
                if temp:
                    hunks.append(Hunk(header="@@", lines=temp))
            sections.append(FileSection("Update", path, dst, hunks, []))
            cursor = idx
            continue

        if m_del:
            path = m_del.group(1).strip()
            sections.append(FileSection("Delete", path, None, [], []))
            cursor += 1
            continue

        if m_mov:
            src = m_mov.group(1).strip()
            idx = cursor + 1
            if idx >= end or not _MOVE_TO.match(lines[idx]):
                raise PatchError("Move File without *** To: destination")
            dst = _MOVE_TO.match(lines[idx]).group(1).strip()  # type: ignore
            sections.append(FileSection("Move", src, dst, [], []))
            cursor = idx + 1
            continue

        # Unrecognized marker
        if line.startswith("*** "):
            raise PatchError(f"Unknown patch directive: {line}")
        cursor += 1

    return ApplyPatch(sections)


# =========================
# Hunk application (robust)
# =========================
def _strip_prefix(line: str) -> str:
    if not line:
        return ""
    if line[0] in (" ", "+", "-"):
        return line[1:]
    return line

def _find_subseq(source: List[str], needle: List[str]) -> int:
    if not needle:
        return 0
    Ls, Ln = len(source), len(needle)
    if Ln > Ls:
        return -1
    # naive O(n*m) is fine for typical hunk sizes
    for i in range(Ls - Ln + 1):
        if source[i:i+Ln] == needle:
            return i
    return -1

def apply_hunk(orig: List[str], hunk: Hunk) -> Tuple[List[str], int, int]:
    """
    Replace old_block with new_block:
      old_block = [context + removed]
      new_block = [context + added]
    On failure, try context-only match.
    """
    old_block = [_strip_prefix(l) for l in hunk.lines if (not l) or l[0] in (" ", "-")]
    new_block = [_strip_prefix(l) for l in hunk.lines if (not l) or l[0] in (" ", "+")]

    pos = _find_subseq(orig, old_block)
    if pos < 0:
        # fallback: context-only
        ctx = [_strip_prefix(l) for l in hunk.lines if l and l[0] == " "]
        if ctx:
            pos = _find_subseq(orig, ctx)
            if pos >= 0:
                end = pos + len(ctx)
                new_lines = orig[:pos] + new_block + orig[end:]
                return new_lines, max(0, len(ctx)-len(new_block)), max(0, len(new_block)-len(ctx))
        raise PatchError(f"Hunk context not found: {hunk.header}")

    end = pos + len(old_block)
    new_lines = orig[:pos] + new_block + orig[end:]
    del_cnt = max(0, len(old_block) - len(new_block))
    add_cnt = max(0, len(new_block) - len(old_block))
    return new_lines, add_cnt, del_cnt


# =========================
# Filesystem applier with single-file policy
# =========================
@dataclass
class ApplyResult:
    added: List[str]
    updated: List[str]
    deleted: List[str]
    moved: List[Tuple[str,str]]

def enforce_rel_path(root: Path, raw: str) -> Path:
    p = (root / raw).resolve()
    if raw.strip().startswith("/") or not is_within(root, p):
        raise PatchError(f"Absolute or out-of-root path is not allowed: {raw}")
    return p

def apply_patch_to_fs(ctx: AppContext, ap: ApplyPatch) -> ApplyResult:
    res = ApplyResult([], [], [], [])
    root = ctx.root

    # single-file policy: allowed paths are either current target or its basename,
    # plus the destination when moving/renaming.
    allowed_srcs = {rel_to(root, ctx.target_path), ctx.target_path.name}

    for sec in ap.sections:
        action = sec.action
        src_raw = sec.src_path
        dst_raw = sec.dst_path

        # Normalize and enforce
        src_path = enforce_rel_path(root, src_raw)
        dst_path = enforce_rel_path(root, dst_raw) if dst_raw else None

        # Enforce single-file policy
        if action in ("Add", "Update", "Delete", "Move"):
            # Allow src == current target OR (Add when target does not exist yet and path equals target)
            target_rel = rel_to(root, ctx.target_path)
            if action == "Add":
                if rel_to(root, src_path) not in (target_rel, ctx.target_path.name):
                    raise PatchError(f"Add target is not the configured single file: {src_raw}")
            elif action in ("Update", "Delete", "Move"):
                if rel_to(root, src_path) not in allowed_srcs:
                    raise PatchError(f"{action} target must be the configured single file: {src_raw}")

        if action == "Add":
            if src_path.exists():
                # overwrite to match Codex behavior (it often re-creates files)
                pass
            # Accept '+'-prefixed or raw lines
            content = sec.add_content
            write_text_lines(src_path, content)
            res.added.append(rel_to(root, src_path))
            # If Add equals our target file path, keep target_path as is.

        elif action == "Delete":
            if src_path.exists():
                if src_path.is_dir():
                    raise PatchError(f"Refusing to delete directory: {src_raw}")
                src_path.unlink()
            res.deleted.append(rel_to(root, src_path))
            # If deleted our target, keep path but file is gone.

        elif action == "Move":
            if not dst_path:
                raise PatchError("Move requires destination path")
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            if src_path.exists():
                shutil.move(str(src_path), str(dst_path))
            else:
                # Still record the move (Codex sometimes plans then moves)
                dst_path.touch()
            res.moved.append((rel_to(root, src_path), rel_to(root, dst_path)))
            # If moving our target, update context
            if src_path == ctx.target_path:
                ctx.target_path = dst_path

        elif action == "Update":
            # Update with optional Move to:
            prefer_crlf = None
            orig_lines = read_text_lines(src_path)
            # Apply hunks sequentially
            acc = orig_lines[:]
            added, deleted = 0, 0
            for h in sec.hunks:
                acc, a, d = apply_hunk(acc, h)
                added += a
                deleted += d
            write_text_lines(src_path, acc, prefer_crlf=prefer_crlf)
            res.updated.append(rel_to(root, src_path))
            # If there is a Move to:, rename after update
            if sec.dst_path:
                dst = enforce_rel_path(root, sec.dst_path)
                dst.parent.mkdir(parents=True, exist_ok=True)
                if src_path.exists():
                    shutil.move(str(src_path), str(dst))
                res.moved.append((rel_to(root, src_path), rel_to(root, dst)))
                if src_path == ctx.target_path:
                    ctx.target_path = dst
        else:
            raise PatchError(f"Unsupported action: {action}")

    return res


# =========================
# Fact-check data structures and helpers
# =========================

FACT_EXTRACTION_TAGS = ("title", "h1", "h2", "h3", "h4", "h5", "p", "li", "blockquote", "figcaption")


def _normalize_ws(text: str) -> str:
    return " ".join(text.strip().split())


def _stream_log(*parts: Any) -> None:
    msg = " ".join(str(p) for p in parts)
    print(f"[agents] {msg}")


def _build_soup(html: str, prefer_lxml: bool = True) -> Tuple[Optional[BeautifulSoup], Optional[str]]:
    parsers = ["lxml", "html.parser", "html5lib"] if prefer_lxml else ["html.parser", "lxml", "html5lib"]
    for parser in parsers:
        try:
            soup = BeautifulSoup(html, parser)
            if soup is not None:
                return soup, parser
        except Exception:
            continue
    return None, None


def extract_article_sections(path: Path, max_sections: int = 160) -> Tuple[List[Dict[str, Any]], str]:
    if not path.exists():
        raise FileNotFoundError(f"Article not found: {path}")
    html = path.read_text(encoding="utf-8", errors="ignore")
    soup, parser_name = _build_soup(html)
    sections: List[Dict[str, Any]] = []
    parser_used = parser_name or "plain-text"
    if soup is not None:
        for idx, node in enumerate(soup.find_all(FACT_EXTRACTION_TAGS)):
            raw = node.get_text(separator=" ", strip=True)
            clean = _normalize_ws(raw)
            if not clean:
                continue
            sections.append({
                "index": idx,
                "tag": node.name or "p",
                "text": clean,
            })
            if len(sections) >= max_sections:
                break
    else:
        # Parser fallback: plain text lines
        for idx, line in enumerate(html.splitlines()):
            clean = _normalize_ws(line)
            if not clean:
                continue
            sections.append({"index": idx, "tag": "p", "text": clean})
            if len(sections) >= max_sections:
                break
    return sections, parser_used


class FactCitation(BaseModel):
    claim: str = Field(..., description="Claim text or paraphrase that was checked")
    verdict: Literal["supported", "contradicted", "uncertain"] = Field(..., description="Result of the check")
    url: str = Field(..., description="Source URL used as evidence")
    source: str = Field(..., description="Publisher / site name")
    published_at: Optional[str] = Field(None, description="Publication date if known (ISO or textual)")
    snippet: Optional[str] = Field(None, description="Short summary of the evidence from the source")


class FactIssue(BaseModel):
    claim: str = Field(..., description="Original claim or sentence excerpt from the article")
    severity: Literal["critical", "major", "minor"] = Field(..., description="Impact if incorrect")
    verdict: Literal["needs_revision", "needs_citation", "supported", "uncertain"] = Field(...)
    recommendation: str = Field(..., description="Specific guidance for the fix, referencing article lines")
    supporting_citations: List[str] = Field(default_factory=list, description="URLs or citation IDs backing the recommendation")
    target_hint: Optional[str] = Field(None, description="Line numbers or section hints for the edit agent")


class FactCheckReport(BaseModel):
    needs_edit: bool = Field(..., description="True if edits are required before publishing")
    overall_verdict: Literal["pass", "needs_revision", "incomplete"]
    summary: str = Field(..., description="High-level summary of fact-check results")
    checked_claims: List[str] = Field(default_factory=list, description="List of primary claims that were evaluated")
    issues: List[FactIssue] = Field(default_factory=list)
    citations: List[FactCitation] = Field(default_factory=list)
    search_queries: List[str] = Field(default_factory=list, description="Queries issued during web search phase")
    notes: Optional[str] = Field(None, description="Additional reviewer comments")


def build_fact_report_digest(report: FactCheckReport) -> str:
    lines = ["# FactCheckReport", f"overall_verdict: {report.overall_verdict}", f"needs_edit: {report.needs_edit}"]
    lines.append("summary: " + report.summary.strip())
    if report.checked_claims:
        lines.append("checked_claims:")
        for claim in report.checked_claims:
            lines.append(f"  - {claim}")
    if report.issues:
        lines.append("issues:")
        for issue in report.issues:
            cite_str = ", ".join(issue.supporting_citations) if issue.supporting_citations else "(no citations)"
            target_hint = f" [{issue.target_hint}]" if issue.target_hint else ""
            lines.append(
                f"  - [{issue.severity}/{issue.verdict}] {issue.claim}{target_hint}\n    recommendation: {issue.recommendation}\n    citations: {cite_str}"
            )
    if report.citations:
        lines.append("citations:")
        for idx, citation in enumerate(report.citations, start=1):
            details = f"{citation.source} ({citation.verdict}) - {citation.url}"
            if citation.published_at:
                details += f" [{citation.published_at}]"
            if citation.snippet:
                details += f" :: {citation.snippet}"
            lines.append(f"  {idx}. {details}")
    if report.search_queries:
        lines.append("search_queries: " + "; ".join(report.search_queries))
    if report.notes:
        lines.append("notes: " + report.notes)
    return "\n".join(lines)


@function_tool
def read_article(context: RunContextWrapper[AppContext],
                 max_sections: int = 160,
                 include_headings: bool = True,
                 include_summary: bool = True) -> str:
    """Read and normalize the HTML article configured in the context.

    Args:
        max_sections: Max number of block elements to surface.
        include_headings: Include heading tags (h1-h5) in output.
        include_summary: Append a gist paragraph for quick reference.
    """
    app = context.context
    sections, parser_used = extract_article_sections(app.article_path, max_sections=max_sections)
    lines: List[str] = []
    rel_article = rel_to(app.root, app.article_path)
    lines.append(f"# Article: {rel_article}")
    lines.append(f"# Returned sections: {len(sections)} (max {max_sections})")
    lines.append(f"# Parser: {parser_used}")
    for sec in sections:
        tag = sec["tag"].upper()
        if not include_headings and tag.lower().startswith("H"):
            continue
        lines.append(f"[{sec['index']:03d}]<{tag}> {sec['text']}")
    if include_summary:
        summary = textwrap.shorten(" ".join(sec["text"] for sec in sections[:30]), width=550, placeholder="…")
        lines.append("")
        lines.append(f"# Summary: {summary}")
    return "\n".join(lines)


class FactCheckRunHooks(RunHooks[AppContext]):
    """Lifecycle hooks to track tool usage with readable streaming logs."""

    def __init__(self) -> None:
        super().__init__()
        self.last_web_search_agent: Optional[str] = None

    def _phase(self, context: RunContextWrapper[AppContext]) -> str:
        return context.context.current_phase or "n/a"

    async def on_tool_start(self, context: RunContextWrapper[AppContext], agent: Agent[AppContext], tool) -> None:  # type: ignore[override]
        name = getattr(tool, "name", str(tool))
        if name == "web_search":
            context.context.web_search_count += 1
            self.last_web_search_agent = agent.name
        _stream_log(f"tool:{name}", f"agent={agent.name}", f"phase={self._phase(context)}")

    async def on_agent_end(self, context: RunContextWrapper[AppContext], agent: Agent[AppContext], output: Any) -> None:  # type: ignore[override]
        if isinstance(output, FactCheckReport):
            context.context.last_fact_report = output
        _stream_log(f"agent_end:{agent.name}", f"phase={self._phase(context)}")

    async def on_llm_start(self, context: RunContextWrapper[AppContext], agent: Agent[AppContext], system_prompt: Optional[str], input_items: List[Any]) -> None:  # type: ignore[override]
        _stream_log(f"llm_start:{agent.name}", f"phase={self._phase(context)}")

    async def on_llm_end(self, context: RunContextWrapper[AppContext], agent: Agent[AppContext], response) -> None:  # type: ignore[override]
        _stream_log(f"llm_end:{agent.name}", f"phase={self._phase(context)}")


def create_web_search_tool(country: Optional[str] = None,
                           subdivision: Optional[str] = None) -> WebSearchTool:
    """Create a hosted web search tool with optional approximate location."""
    user_location: Optional[Dict[str, Any]] = None
    if country:
        user_location = {"type": "approximate", "country": country}
        if subdivision:
            user_location["subdivision"] = subdivision
    return WebSearchTool(user_location=user_location)


def build_model_settings(*,
                         tool_choice: Optional[str] = None,
                         temperature: Optional[float] = None,
                         parallel_tool_calls: Optional[bool] = None) -> ModelSettings:
    kwargs: Dict[str, Any] = {}
    if tool_choice is not None:
        kwargs["tool_choice"] = tool_choice
    if temperature is not None:
        kwargs["temperature"] = temperature
    if parallel_tool_calls is not None:
        kwargs["parallel_tool_calls"] = parallel_tool_calls
    return ModelSettings(**kwargs)


FACT_CHECK_INSTRUCTIONS = """
あなたはローカルHTML記事のファクトチェック専用エージェントです。
Context.article_path にある記事を対象に、以下の手順を厳守してください。

1. 必ず最初に read_article(...) ツールで本文を読み込み、主要な主張・統計・固有名詞を箇条書きで整理する。
2. 続けて必ず web_search ツールを1回以上呼び出し、信頼性の高いソースで各主張を検証する。
   - 可能であれば複数のクエリをまとめて1回の検索にし、複数の候補を評価する。
   - 出典URL、媒体、発行日、該当抜粋を収集する。
3. FactCheckReport 型で最終結論を返し、needs_edit を正しく設定する。
   - needs_edit=True の場合は issues[].recommendation に apply_patch が書きやすい修正指示を含める。
   - search_queries と citations には使用した検索キーワードと根拠URLを列挙する。
4. 不確実な情報は「uncertain」と明記し、推測による補完を行わない。
"""

FACTCHECK_RUN_PROMPT_TEMPLATE = """
対象記事: `{article_rel}`
- Context の read_article ツールで本文を取得し、主張リストを作成。
- 必ず web_search ツールを最低1回実行し、主要ファクトを検証。
- すべての結果を FactCheckReport 型で出力。
"""


def format_edit_handoff_prompt(ctx: AppContext, report: FactCheckReport) -> str:
    rel_file = rel_to(ctx.root, ctx.target_path)
    rel_article = rel_to(ctx.root, ctx.article_path)
    digest = build_fact_report_digest(report)
    instructions = textwrap.dedent(
        f"""
        ファクトチェック結果に基づき、ファイル `{rel_file}` を apply_patch で修正してください。
        - 対象HTML: `{rel_article}` （編集対象と同一の場合あり）
        - 変更は最小限にし、事実誤認の訂正・出典追記・表現の調整に留めてください。
        - 修正方針は FactCheckReport の issues/recommendation に従い、引用URLを本文に反映させてください。
        - 不確実な主張は削除または文言を弱め、必要に応じて注記を追記します。
        - 必ず apply_patch（*** Begin Patch～*** End Patch）フォーマットを使用します。
        """
    ).strip()
    return instructions + "\n\n" + digest

# =========================
# Tools
# =========================
def ensure_session_trace(
    workflow_name: str,
    trace_id: Optional[str],
    group_id: Optional[str],
    metadata: Optional[Dict[str, Any]],
    disabled: bool,
) -> Tuple[Optional[agent_tracing.Trace], bool]:
    """
    Ensure a single trace stays active for the CLI session.
    Returns the active trace (if any) and whether it was created here.
    """
    if disabled:
        return None, False

    existing = agent_tracing.get_current_trace()
    if existing:
        if trace_id and existing.trace_id != trace_id:
            print(
                f"[trace] Existing trace {existing.trace_id} differs from requested {trace_id}; "
                "continuing with existing trace."
            )
        return existing, False

    trace_obj = agent_tracing.trace(
        workflow_name=workflow_name,
        trace_id=trace_id or agent_tracing.gen_trace_id(),
        group_id=group_id,
        metadata=metadata,
        disabled=False,
    )
    trace_obj.start(mark_as_current=True)
    return trace_obj, True


def make_run_config(*,
                    workflow_name: str,
                    trace_id: Optional[str],
                    group_id: Optional[str],
                    trace_metadata: Optional[Dict[str, Any]],
                    tracing_disabled: bool,
                    model_settings: Optional[ModelSettings] = None) -> RunConfig:
    return RunConfig(
        workflow_name=workflow_name,
        trace_id=trace_id,
        group_id=group_id,
        trace_metadata=trace_metadata,
        tracing_disabled=tracing_disabled,
        model_settings=model_settings,
    )


@function_tool
def read_file(context: RunContextWrapper[AppContext],
              offset: int = 1,
              limit_lines: int = 400,
              with_line_numbers: bool = True) -> str:
    """
    単一ファイルの内容を読み出します（1始まり）。
    - offset: 開始行（1-based）
    - limit_lines: 取得行数
    - with_line_numbers: 行番号付き
    """
    app: AppContext = context.context
    target = app.target_path
    lines = read_text_lines(target)
    if not lines:
        header = f"# File: {rel_to(app.root, target)} (empty or missing)\n"
        return header

    start = max(1, int(offset))
    end = min(len(lines), start - 1 + max(1, int(limit_lines)))
    view = lines[start-1:end]
    if with_line_numbers:
        view = [f"{i+start:>6}: {ln}" for i, ln in enumerate(view)]
    header = f"# File: {rel_to(app.root, target)}\n# Showing lines {start}..{end} of {len(lines)}\n"
    return header + "\n".join(view)

@function_tool
def apply_patch(context: RunContextWrapper[AppContext], patch: str) -> str:
    """
    Codex 互換 apply_patch を適用します（Add/Update/Delete/Move, @@ 対応）。
    - すべて root 配下の相対パスのみ許可
    - このエージェントは「単一ファイル」ポリシー：ターゲット以外の編集は拒否（Move の宛先は例外）
    - 成功時は JSON サマリを返します
    """
    app: AppContext = context.context
    ap = parse_apply_patch(patch)
    result = apply_patch_to_fs(app, ap)
    return "APPLIED " + json.dumps(dataclasses.asdict(result), ensure_ascii=False)


# =========================
# System Instructions (Codex風・日本語)
# =========================
CODEX_STYLE_INSTRUCTIONS = """
あなたはローカルの単一ファイルを編集するコーディングエージェントです。
必ず以下に従ってください。

# 目的
- ユーザーの依頼に基づき、対象ファイルの必要箇所のみを編集します。
- 編集は必ず apply_patch を使い、差分パッチで行います（ファイル全体の上書きは禁止）。

# 使えるツール
- read_file(offset, limit_lines, with_line_numbers): ファイルの一部を読みます。
- apply_patch(patch): Codex 互換の apply_patch を適用します（*** Begin Patch〜*** End Patch）。

# パッチ仕様（厳守）
- 全体を `*** Begin Patch` と `*** End Patch` で囲む。
- ファイルごとに 1 セクション：
  - 追加:    `*** Add File: <path>` の後に内容（`+` で始まる行、または素の行も可）。
  - 更新:    `*** Update File: <path>`。必要なら直後に `*** Move to: <newpath>`。
             1個以上のハンクを `@@` 行で開始し、変更行を続ける：
               * 先頭` `（空白）= 文脈、`-`=削除、`+`=追加
  - 削除:    `*** Delete File: <path>`
  - 移動:    `*** Move File: <old>` の次行で `*** To: <new>`
- 曖昧さ回避のため、関数名/見出しなどを含む `@@` 見出しや十分な文脈行を付与すること。

# ワークフロー
1) まず read_file で必要範囲を確認し、編集位置と方針を決める。
2) apply_patch で差分を適用する。
3) 必要なら短く変更点と確認方法を説明する。

# 出力
- 冗長な説明は避け、要点のみ伝える。
- 新規テキストをそのまま出力せず、必ず apply_patch を生成する。
"""


def build_text_edit_agent(model: str,
                          *,
                          tool_choice: str = "auto",
                          temperature: Optional[float] = None,
                          instructions: Optional[str] = None,
                          include_web_search: bool = False,
                          web_search_tool: Optional[WebSearchTool] = None) -> Agent[AppContext]:
    settings = build_model_settings(tool_choice=tool_choice, temperature=temperature)
    tools = [read_file, apply_patch]
    if include_web_search:
        search_tool = web_search_tool or create_web_search_tool()
        tools.insert(0, search_tool)
    return Agent[AppContext](
        name="Codex-like Patch Agent",
        instructions=instructions or CODEX_STYLE_INSTRUCTIONS,
        model=model,
        model_settings=settings,
        tools=tools,
    )


def build_fact_check_agent(model: str,
                           web_tool: WebSearchTool,
                           *,
                           temperature: Optional[float] = None,
                           handoffs: Optional[List[Agent[AppContext]]] = None) -> Agent[AppContext]:
    settings = build_model_settings(tool_choice="auto", temperature=temperature, parallel_tool_calls=False)
    tools = [read_article, web_tool, read_file]
    agent = Agent[AppContext](
        name="FactCheck Agent",
        instructions=FACT_CHECK_INSTRUCTIONS,
        model=model,
        model_settings=settings,
        tools=tools,
        output_type=FactCheckReport,
    )
    if handoffs:
        agent.handoffs = handoffs
    return agent


# =========================
# Multi-agent orchestration helpers
# =========================

def _print_banner(lines: List[str]) -> None:
    print("╭" + "─" * 54 + "╮")
    for line in lines:
        body = line[:54]
        print(f"│ {body:<54}│")
    print("╰" + "─" * 54 + "╯")


async def run_fact_check_cli(args: argparse.Namespace) -> None:
    article = Path(args.article).expanduser().resolve()
    edit_path = Path(args.edit_file).expanduser().resolve() if args.edit_file else article
    if not article.exists():
        raise FileNotFoundError(f"Article not found: {article}")
    root = (args.root and Path(args.root).expanduser().resolve()) or edit_path.parent
    ctx = AppContext(root=root, target_path=edit_path, article_path=article, session_id=args.session)

    workflow_name = args.trace_workflow_name or "fact-check-text-edit"
    trace_group_id = args.trace_group_id or args.session
    trace_md = {
        "article": rel_to(root, article),
        "edit_target": rel_to(root, edit_path),
        "mode": "fact-check",
    }
    session_trace, trace_created = ensure_session_trace(
        workflow_name=workflow_name,
        trace_id=args.trace_id,
        group_id=trace_group_id,
        metadata=trace_md,
        disabled=args.disable_tracing,
    )
    active_trace_id = session_trace.trace_id if session_trace else args.trace_id

    base_run_config = make_run_config(
        workflow_name=workflow_name,
        trace_id=active_trace_id,
        group_id=trace_group_id,
        trace_metadata=trace_md,
        tracing_disabled=args.disable_tracing,
    )

    session = SQLiteSession(args.session)
    text_agent = build_text_edit_agent(
        args.edit_model,
        tool_choice="required" if args.force_text_tools else "auto",
        temperature=args.edit_temperature,
    )
    web_tool = create_web_search_tool(args.web_search_country, args.web_search_subdivision)
    fact_agent = build_fact_check_agent(
        args.fact_model,
        web_tool,
        temperature=args.fact_temperature,
        handoffs=[text_agent] if args.allow_agent_handoff else None,
    )

    ctx.web_search_count = 0
    ctx.last_fact_report = None
    hooks = FactCheckRunHooks()
    fact_prompt = textwrap.dedent(FACTCHECK_RUN_PROMPT_TEMPLATE.format(article_rel=rel_to(root, article))).strip()
    ctx.current_phase = "fact-check"
    _stream_log("fact_check_start", f"article={rel_to(root, article)}")
    fact_ms = build_model_settings(tool_choice="auto", temperature=args.fact_temperature, parallel_tool_calls=False)
    fact_run_config = replace(base_run_config, model_settings=fact_ms)
    fact_result = await Runner.run(
        fact_agent,
        input=fact_prompt,
        context=ctx,
        session=session,
        hooks=hooks,
        run_config=fact_run_config,
        max_turns=args.fact_max_turns,
    )
    ctx.current_phase = None

    candidate = ctx.last_fact_report if isinstance(ctx.last_fact_report, FactCheckReport) else fact_result.final_output
    if not isinstance(candidate, FactCheckReport):
        raise RuntimeError("Fact-check agent did not return a structured FactCheckReport.")
    report = candidate

    digest = build_fact_report_digest(report)
    _print_banner([
        "Fact-Check completed",
        f"web_search_count: {ctx.web_search_count}",
        f"needs_edit: {report.needs_edit}",
    ])
    print(digest)

    if report.needs_edit:
        ctx.current_phase = "text-edit"
        edit_prompt = format_edit_handoff_prompt(ctx, report)
        edit_ms = build_model_settings(
            tool_choice="required" if args.force_text_tools else "auto",
            temperature=args.edit_temperature,
        )
        edit_run_config = replace(base_run_config, model_settings=edit_ms)
        _stream_log("text_edit_start", f"target={rel_to(root, edit_path)}")
        edit_result = await Runner.run(
            text_agent,
            input=edit_prompt,
            context=ctx,
            session=session,
            run_config=edit_run_config,
            max_turns=args.edit_max_turns,
        )
        print("\n=== Text-Edit Agent Final Output ===")
        if edit_result.final_output:
            print(edit_result.final_output if isinstance(edit_result.final_output, str) else str(edit_result.final_output))
        _stream_log("text_edit_done")
    else:
        print("\n修正は不要です。FactCheckReport を上記に出力しました。")
    ctx.current_phase = None

    if trace_created and session_trace:
        session_trace.finish(reset_current=True)


async def run_patch_cli(args: argparse.Namespace) -> None:
    target = Path(args.file).expanduser().resolve()
    root = target.parent
    article = Path(args.article).expanduser().resolve() if args.article else target
    ctx = AppContext(root=root, target_path=target, article_path=article, session_id=args.session)

    workflow_name = args.trace_workflow_name or "text-edit-agent"
    trace_group_id = args.trace_group_id or args.session
    trace_md = {"target_file": rel_to(root, target), "mode": "patch"}
    session_trace, trace_created = ensure_session_trace(
        workflow_name=workflow_name,
        trace_id=args.trace_id,
        group_id=trace_group_id,
        metadata=trace_md,
        disabled=args.disable_tracing,
    )
    active_trace_id = session_trace.trace_id if session_trace else args.trace_id

    patch_tool_choice = "required" if args.force_tools else "auto"
    model_settings = build_model_settings(tool_choice=patch_tool_choice, temperature=args.temperature)
    run_config = make_run_config(
        workflow_name=workflow_name,
        trace_id=active_trace_id,
        group_id=trace_group_id,
        trace_metadata=trace_md,
        tracing_disabled=args.disable_tracing,
        model_settings=model_settings,
    )

    agent = build_text_edit_agent(args.model, tool_choice=patch_tool_choice, temperature=args.temperature)
    session = SQLiteSession(args.session)

    banner = [
        "Codex-compatible Patch Agent (OpenAI Agents SDK)",
        f"model : {args.model}",
        f"file  : {rel_to(root, target)}",
    ]
    if active_trace_id:
        banner.append(f"trace : {active_trace_id}")
    _print_banner(banner)
    print("ヒント: read_file(offset=1, limit_lines=100) で内容を確認。apply_patch で差分を適用。")
    print("終了は Ctrl+C または exit/quit。")

    try:
        existing_items = await session.get_items(limit=1)
    except Exception as exc:
        existing_items = None
        print(f"[warn] Failed to inspect session history: {exc}")

    if not existing_items:
        preload_prompt = (
            f"事前に対象ファイル {rel_to(root, target)} の内容を確認するため、"
            "read_file(offset=1, limit_lines=400, with_line_numbers=True) を実行してください。"
        )
        try:
            preload_result = await Runner.run(
                agent,
                input=preload_prompt,
                context=ctx,
                session=session,
                run_config=run_config,
            )
            if preload_result.final_output is not None:
                print(preload_result.final_output if isinstance(preload_result.final_output, str) else str(preload_result.final_output))
        except Exception as exc:
            print(f"[warn] 初回の read_file 呼び出しに失敗しました: {exc}")

    try:
        while True:
            try:
                user = input("\n› ").strip()
                if not user:
                    continue
                if user.lower() in {"exit", "quit"}:
                    print("bye.")
                    break
                result = await Runner.run(
                    agent,
                    input=user,
                    context=ctx,
                    session=session,
                    run_config=run_config,
                )
                if result.final_output:
                    print(result.final_output if isinstance(result.final_output, str) else str(result.final_output))
            except KeyboardInterrupt:
                print("\nbye.")
                break
            except EOFError:
                print("\nbye.")
                break
            except Exception as exc:
                print(f"[error] {exc}")
    finally:
        if trace_created and session_trace:
            session_trace.finish(reset_current=True)

# =========================
# CLI Entrypoint
# =========================

def _add_trace_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--trace-workflow-name", default=None, help="Workflow name used for OpenAI trace logging")
    p.add_argument("--trace-group-id", default=None, help="Trace group identifier (defaults to session id)")
    p.add_argument("--trace-id", default=None, help="Explicit trace id to reuse across runs")
    p.add_argument("--disable-tracing", action="store_true", help="Disable OpenAI trace export for this run")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fact-check → text-edit multi-agent toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    patch = sub.add_parser("patch", help="Interactive Codex-style text edit agent")
    patch.add_argument("--file", required=True, help="Editable file path")
    patch.add_argument("--model", default=os.environ.get("AGENT_MODEL", "gpt-5-mini"), help="Model name for text edits")
    patch.add_argument("--session", default="codex-patch-session", help="SQLite session id")
    patch.add_argument("--article", default=None, help="HTML article path (defaults to --file)")
    patch.add_argument("--force-tools", action="store_true", help="Force tool use (tool_choice='required')")
    patch.add_argument("--temperature", type=float, default=None, help="Model temperature for edit agent (omit for model defaults)")
    _add_trace_args(patch)

    fact = sub.add_parser("fact-check", help="Run fact-check → conditional text edit workflow")
    fact.add_argument("--article", required=True, help="HTML article file path")
    fact.add_argument("--edit-file", default=None, help="Editable file path (defaults to --article)")
    fact.add_argument("--root", default=None, help="Workspace root (defaults to edit file parent)")
    fact.add_argument("--session", default="fact-check-session", help="SQLite session id")
    fact.add_argument("--fact-model", default=os.environ.get("FACT_MODEL", "gpt-5-mini"), help="Model name for fact-check agent")
    fact.add_argument("--fact-temperature", type=float, default=None, help="Temperature for fact-check agent (omit if unsupported)")
    fact.add_argument("--fact-max-turns", type=int, default=12, help="Max turns per fact-check phase")
    fact.add_argument("--edit-model", default=os.environ.get("AGENT_MODEL", "gpt-5-mini"), help="Model for text edit agent")
    fact.add_argument("--edit-temperature", type=float, default=None, help="Temperature for text edit agent (omit if unsupported)")
    fact.add_argument("--edit-max-turns", type=int, default=12, help="Max turns for text edit agent")
    fact.add_argument("--force-text-tools", action="store_true", help="Force tool usage for text edit agent")
    fact.add_argument("--web-search-country", default="JP", help="Web search country code (ISO alpha-2)")
    fact.add_argument("--web-search-subdivision", default=None, help="Web search subdivision (optional)")
    fact.add_argument("--allow-agent-handoff", action="store_true", help="Expose text edit agent as handoff target (LLM-driven)")
    _add_trace_args(fact)

    return parser


async def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "patch":
        await run_patch_cli(args)
    elif args.command == "fact-check":
        await run_fact_check_cli(args)
    else:
        raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    asyncio.run(main())
