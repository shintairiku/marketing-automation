#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Codex-compatible patch agent (single file, full apply_patch compatibility)
- OpenAI Agents SDK + function tools
- Fully implements Codex-style apply_patch: Add / Update / Delete / Move (+ optional Move in Update)
- Multiple file sections & hunks, @@ headers, +/-/space lines, strict relative paths, safe rename
- Robust matching: exact old-block match → fallback to context-only match

Requirements:
  pip install openai-agents
Env:
  export OPENAI_API_KEY=sk-...

Run:
  python codex_patch_agent.py --file ./README.md --model gpt-5-codex
"""

from __future__ import annotations
import argparse
import asyncio
import dataclasses
import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional, Tuple, Dict

from agents import Agent, Runner, function_tool, ModelSettings, SQLiteSession
from agents.run_context import RunContextWrapper
import dotenv

dotenv.load_dotenv()

# =========================
# Context
# =========================
@dataclass
class AppContext:
    root: Path          # workspace root (target file's parent)
    target_path: Path   # current target file (single-file agent)
    # If moved, we update target_path in-place to follow the new location


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
# Tools
# =========================
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

# =========================
# Simple TUI loop using Agents SDK
# =========================
async def main():
    parser = argparse.ArgumentParser(description="Codex-compatible Patch Agent (Agents SDK, single-file)")
    parser.add_argument("--file", required=True, help="Editable file path")
    parser.add_argument("--model", default=os.environ.get("AGENT_MODEL", "gpt-5-mini"),
                        help="Model name (default: gpt-5-mini)")
    parser.add_argument("--session", default="codex-patch-session", help="Session id for SQLiteSession")
    parser.add_argument("--force-tools", action="store_true",
                        help="Force tool use via ModelSettings(tool_choice='required')")
    args = parser.parse_args()

    target = Path(args.file).expanduser().resolve()
    root = target.parent
    ctx = AppContext(root=root, target_path=target)

    # Print banner
    print("╭────────────────────────────────────────────────────╮")
    print("│  Codex-compatible Patch Agent (OpenAI Agents SDK)  │")
    print(f"│  model : {args.model:<40s}│")
    print(f"│  file  : {rel_to(root, target):<40s}│")
    print("╰────────────────────────────────────────────────────╯")
    print("ヒント: 例) read_file(offset=1, limit_lines=100) と指示すると読みます。")
    print("      編集は apply_patch で差分を生成してください。終了は Ctrl+C。")

    ms = ModelSettings(tool_choice="required" if args.force_tools else "auto")

    agent = Agent[AppContext](
        name="Codex-like Patch Agent",
        instructions=CODEX_STYLE_INSTRUCTIONS,
        model=args.model,
        model_settings=ms,
        tools=[read_file, apply_patch],
    )

    session = SQLiteSession(args.session)

    while True:
        try:
            user = input("\n› ").strip()
            if not user:
                continue
            if user.lower() in {"exit", "quit"}:
                print("bye.")
                break
            result = await Runner.run(agent, input=user, context=ctx, session=session)
            if result.final_output:
                print(result.final_output if isinstance(result.final_output, str) else str(result.final_output))
        except KeyboardInterrupt:
            print("\nbye.")
            break
        except EOFError:
            print("\nbye.")
            break
        except Exception as e:
            print(f"[error] {e}")

if __name__ == "__main__":
    asyncio.run(main())
