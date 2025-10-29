# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "openai>=1.53.0",
#   "openai-agents>=0.2.6",
#   "openai-agents[litellm]>=0.2.6",
#   "pydantic>=2.8.0",
#   "httpx>=0.27.2",
#   "python-dotenv>=1.0.1",
#   "rich>=13.7.1",
#   "typing-extensions>=4.12.2",
#   "ujson>=5.10.0",
#   "orjson>=3.10.7",
#   "tqdm>=4.66.5",
#   "tenacity>=9.0.0"
# ]
# ///

"""
SEO執筆エージェント・パイプライン（OpenAI Agents SDK + SerpAPI + WebSearchTool + Handoffs + HITL）

要件:
- 入口は "リーチしたいキーワードのリスト"
- 最初のエージェント(KeywordAnalysisAgent)が必ず SERP API ツールを使ってデータを取得
- その後、Web Search Tool を ReAct ループで使い競合/見出し/構成/キーワード分析を深掘り
- ペルソナ生成 → 人間承認（ツール） → テーマ生成 → 人間承認（ツール）
- アウトライン生成（Web検索は任意）
- リサーチエージェントが検索とレポートを一括で実施
- 執筆エージェントにハンドオフして Markdown で記事完成
- すべて GPT-5 を使用（Writer は LiteLLM で外部モデルも可）
- uv run seo_pipeline.py だけで完了

設計のポイント:
- ハンドオフ（transfer_to_xxx）は Agents SDK の推奨設計。RECOMMENDED_PROMPT_PREFIX を付与。
- SERP は function_tool で実装。最初のターンで tool_choice に "serp_batch_search" を指定し強制実行、
  ツール呼び出し後は SDK により tool_choice は auto に戻る仕様（ループ無限化防止）。
- HITL は JSON 壊れ対策として単一文字列引数版 user_select_block を主体に。
- ラン全体は“ハンドオフ連鎖の単一 Runner.run”で行い、to_input_list の重複合成を避ける。
- Hooks（RunHooks/AgentHooks）で段階ログを綺麗に表示。

ドキュメント出典（代表）:
- Handoffs: https://openai.github.io/openai-agents-python/handoffs/ 
- Handoff prompt 推奨: https://openai.github.io/openai-agents-python/ref/extensions/handoff_prompt/
- Tools（WebSearchTool / function_tool）: https://openai.github.io/openai-agents-python/tools/
- Agents（ModelSettings.tool_choice / Tool Use Behavior）:
  https://openai.github.io/openai-agents-python/agents/
"""

from __future__ import annotations

import asyncio
import os
import sys
import json
import re
import textwrap
import argparse
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict, Sequence, Tuple

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from pydantic import BaseModel, Field, ValidationError
from typing_extensions import Annotated

from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import IntPrompt

from agents import (
    Agent,
    Runner,
    WebSearchTool,
    function_tool,
    ModelSettings,
    RunContextWrapper,
    RunHooks,
    AgentHooks,
    handoff,
)
from agents.agent import StopAtTools
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents.extensions.models.litellm_model import LitellmModel

import dotenv

dotenv.load_dotenv()
console = Console()


# =============================================================================
#                               型定義（Pydantic）
# =============================================================================

class Competitor(BaseModel):
    url: str
    title: str
    serp_position: int | None = None
    headings: List[str] = Field(default_factory=list)
    notes: str = ""

class KeywordAnalysisOutput(BaseModel):
    target_intent: str
    primary_keywords: List[str]
    secondary_keywords: List[str]
    long_tail_keywords: List[str]
    competitors: List[Competitor]
    insights: str

class PersonaOption(BaseModel):
    id: str
    name: str
    description: str
    tone: str
    reading_level: str
    pains: List[str]
    search_intent: str

class PersonaOptions(BaseModel):
    options: List[PersonaOption]
    recommended_id: str

class ThemeOption(BaseModel):
    id: str
    label: str
    angle: str
    rationale: str

class ThemeOptions(BaseModel):
    options: List[ThemeOption]
    recommended_id: str

class OutlineSection(BaseModel):
    id: str
    heading: str
    objective: str
    target_keywords: List[str] = Field(default_factory=list)
    length_target_words: int = 300
    bullets: List[str] = Field(default_factory=list)

class Outline(BaseModel):
    title: str
    slug: str
    sections: List[OutlineSection]

class ResearchBundle(BaseModel):
    notes: str
    quotes: List[str]
    sources: List[str]

class ChosenID(BaseModel):
    """HITL後に返す選択結果（id のみ）"""
    id: str


# =============================================================================
#                               ユーティリティ
# =============================================================================

def require_env(var: str) -> str:
    val = os.getenv(var, "")
    if not val:
        console.print(f"[yellow]警告: 環境変数 {var} が未設定です。[/yellow]")
    return val

def pretty_json(data: Any) -> str:
    try:
        import orjson
        return orjson.dumps(
            data,
            option=orjson.OPT_INDENT_2 | orjson.OPT_NON_STR_KEYS | orjson.OPT_SORT_KEYS
        ).decode("utf-8")
    except Exception:
        return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)

def parse_keywords(args: argparse.Namespace) -> List[str]:
    kws: List[str] = []
    if args.keywords:
        for part in args.keywords.split(","):
            kw = part.strip()
            if kw:
                kws.append(kw)
    if args.keywords_file:
        with open(args.keywords_file, "r", encoding="utf-8") as f:
            for line in f:
                kw = line.strip()
                if kw:
                    kws.append(kw)
    unique: List[str] = []
    seen = set()
    for k in kws:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    if not unique:
        console.print("[red]キーワードがありません。--keywords か --keywords-file を指定してください。[/red]")
        sys.exit(1)
    return unique

def make_slug(text: str) -> str:
    t = re.sub(r"[^\w\-ぁ-んァ-ヴー一-龠]+", "-", text.strip())
    t = re.sub(r"-{2,}", "-", t).strip("-")
    return t[:120] if len(t) > 120 else t

def clamp(s: str, max_len: int) -> str:
    s = s.strip()
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


# =============================================================================
#                           実行コンテキスト（依存注入）
# =============================================================================

@dataclass
class AppContext:
    """Runner.run に渡す context。ツールやハンドオフ間で共有される。"""
    gl: str
    hl: str
    keywords: List[str]
    serp_cache: Dict[Tuple[str, str, str, int, str, str], Dict[str, Any]] = field(default_factory=dict)
    flags: Dict[str, Any] = field(default_factory=dict)
    user_selection_store: Dict[str, str] = field(default_factory=dict)  # "persona"->id, "theme"->id


# =============================================================================
#                           関数ツール（SerpAPI / fetch / HITL）
# =============================================================================

@function_tool
@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
def fetch_url(url: str, max_chars: int = 50000) -> str:
    """
    指定URLの本文（HTML）を取得するシンプルなフェッチャ。LLM 側で見出し抽出などを行う前提。
    max_chars で返却サイズを制限。
    """
    headers = {"User-Agent": "Mozilla/5.0 (compatible; SEOAgents/1.0)"}
    r = httpx.get(url, headers=headers, timeout=40.0, follow_redirects=True)
    r.raise_for_status()
    txt = r.text
    return txt[:max_chars] if len(txt) > max_chars else txt


@function_tool
def user_select(label: str, options: List[str]) -> str:
    """
    [HITL] 人間の承認を取得する選択ツール（従来の List[str] 版）。
    - options は短い ASCII ラベル（id を含む "id: label..." 形式）で渡すこと。
    - 返り値: 選ばれたオプションの「そのままの文字列」（先頭に idを含む）。
    """
    console.print(Panel.fit(f"[bold cyan]{label}[/bold cyan] を選択してください"))
    table = Table(title=label)
    table.add_column("No.", justify="right", width=4)
    table.add_column("Option")
    for i, opt in enumerate(options, start=1):
        table.add_row(str(i), opt)
    console.print(table)
    idx = IntPrompt.ask("番号を入力", choices=[str(i) for i in range(1, len(options) + 1)])
    chosen = options[int(idx) - 1]
    console.print(Panel.fit(f"[green]選択:[/green] {chosen}"))
    return chosen


class UserSelectBlockArgs(BaseModel):
    label: str
    options_block: str
    """
    options_block の書式（例）:
    1) opt_a: 20代キャリアチェンジ / pains=...
    2) opt_b: 年収UP志向 / pains=...
    3) opt_c: 企業人事 / pains=...
    （1〜9の番号で選べるように並べる）
    """


@function_tool(name_override="user_select_block")
def user_select_block(ctx: RunContextWrapper[AppContext], label: str, options_block: str) -> str:
    """
    [HITL・堅牢版] 単一文字列引数の選択ツール。
    - LLM 側で JSON が壊れにくいよう、options は1本のテキストブロックにして渡す。
    - 返り値: "opt_xxx"（行頭の id または "id:" の左側を抽出）
    """
    console.print(Panel.fit(f"[bold cyan]{label}[/bold cyan]"))
    console.print(options_block)
    # 末尾の "番号を入力" プロンプト
    # options_block から行数と (1)〜(9) の範囲を推定
    lines = [ln for ln in options_block.splitlines() if ln.strip()]
    max_n = 0
    ids: Dict[int, str] = {}
    for ln in lines:
        m = re.match(r"^\s*(\d+)\)\s*([^:\s]+)", ln)
        if m:
            n = int(m.group(1))
            max_n = max(max_n, n)
            ids[n] = m.group(2).strip()
    if max_n == 0:
        # フォールバック：番号が見つからなければ1行目のみ
        console.print("[yellow]警告: options_block に番号行が見つかりませんでした。1番固定で処理します。[/yellow]")
        ids[1] = "opt_1"
        max_n = 1
    idx = IntPrompt.ask("番号を入力", choices=[str(i) for i in range(1, max_n + 1)])
    chosen_id = ids[int(idx)]
    console.print(Panel.fit(f"[green]選択:[/green] {chosen_id}"))
    return chosen_id


@function_tool
def serp_batch_search(
    ctx: RunContextWrapper[AppContext],
    keywords: List[str],
    gl: str = "jp",
    hl: str = "ja",
    num: int = 10,
    device: str = "desktop",
    safe: str = "off"
) -> str:
    """
    Google SERP を SerpAPI で取得するバッチ検索ツール。
    - **キーワード分析エージェントは最初に必ずこのツールを "一度だけ" 呼び出すこと**。
    - キャッシュキー=(tuple(keywords), gl, hl, num, device, safe)
    - 返り値: {keyword: raw_serp_json} を pretty JSON 文字列化
    """
    api_key = require_env("SERPAPI_API_KEY")
    if not api_key:
        return json.dumps({"error": "SERPAPI_API_KEY is missing. Cannot fetch SERP."}, ensure_ascii=False)

    # 二重呼び出し防止（同一パラメータで既に取得済みならキャッシュ返し）
    key = (tuple(keywords), gl, hl, num, device, safe)
    if key in ctx.context.serp_cache:
        return pretty_json(ctx.context.serp_cache[key])

    base = "https://serpapi.com/search.json"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; SEOAgents/1.0)"}
    out: Dict[str, Any] = {}
    with httpx.Client(timeout=50.0, headers=headers) as client:
        for kw in keywords:
            params = {
                "q": kw,
                "hl": hl,
                "gl": gl,
                "num": num,
                "device": device,
                "safe": safe,
                "api_key": api_key,
                "engine": "google",
            }
            resp = client.get(base, params=params)
            resp.raise_for_status()
            out[kw] = resp.json()

    ctx.context.serp_cache[key] = out
    # フラグも立てておく（LLM 側に説明用のヒントとなることがある）
    ctx.context.flags["serp_executed"] = True
    return pretty_json(out)


# =============================================================================
#                               Hooks（ログ表示）
# =============================================================================

class SEOGlobalRunHooks(RunHooks[AppContext]):
    """ラン全体にかかるフック（各エージェント/ツールの動作を見やすく）"""

    async def on_agent_start(self, context: RunContextWrapper[AppContext], agent: Agent[AppContext]) -> None:
        console.rule(f"[bold]RUN ▶ {agent.name}[/bold]")

    async def on_handoff(self, context: RunContextWrapper[AppContext], agent: Agent[AppContext], source_agent: Agent[AppContext]) -> None:
        console.print(Panel.fit(f"🤝 Handoff: [bold]{source_agent.name}[/bold] → [bold]{agent.name}[/bold]"))

    async def on_tool_start(self, context: RunContextWrapper[AppContext], agent: Agent[AppContext], tool) -> None:
        console.print(f"[dim]🛠 {agent.name} ツール開始: {getattr(tool, 'name', type(tool).__name__)}[/dim]")

    async def on_tool_end(self, context: RunContextWrapper[AppContext], agent: Agent[AppContext], tool, result: str) -> None:
        console.print(f"[dim]🛠 {agent.name} ツール終了: {getattr(tool, 'name', type(tool).__name__)}[/dim]")


# =============================================================================
#                               エージェント定義
# =============================================================================

# 1) キーワード分析（最初に SERP 実行→WebSearchTool/fetch_url で裏取り）
def make_keyword_analysis_agent() -> Agent[AppContext]:
    return Agent[AppContext](
        name="Keyword Analysis Agent",
        instructions=(
            f"""{RECOMMENDED_PROMPT_PREFIX}
あなたは高度なSEOアナリストです。以下を厳守してください：

[強制手順]
1) 会話の最初のターンで、必ず一度だけ serp_batch_search を呼び出し、ユーザーから受け取った keywords（配列）・hl・gl を使って SERP スナップショットを取得します。
   - これは必ず最初に実行します。2回以上呼び出さないでください（同一パラメータならツール側でキャッシュされます）。
2) その後、WebSearchTool と fetch_url を必要な回数だけ使って、競合記事の本文・見出し(H1/H2/H3)・構成・キーワードの使い方などを裏取りします（ReActループ）。
3) 以下の構造化スキーマ（KeywordAnalysisOutput）に厳密に従い、検索意図、主要/副次/ロングテールKW、競合一覧（URL, title, headings 概要, notes）、要点（insights）を日本語で返します。
4) 完了したら Persona Generator へのハンドオフを**必ず**呼び出してください（transfer_to_persona_generator）。

注意:
- 妄想や推測で埋めず、SERP/実ページ裏取りを行ってから記載します。
- 競合は SERP 上位から現実的な範囲（例: 5〜10件）を候補に。
- 日本語で簡潔かつ意思決定に足る深さでまとめること。
"""
        ),
        tools=[
            serp_batch_search,
            WebSearchTool(),
            fetch_url,
        ],
        # 最初に serp_batch_search を強制。ツール実行後はSDK仕様で auto に戻る。
        model_settings=ModelSettings(tool_choice="serp_batch_search"),
        model="gpt-5",
        output_type=KeywordAnalysisOutput,
        # 次エージェントへのハンドオフ
        handoffs=[
            handoff(
                agent=Agent(name="Persona Generator"),  # プレースホルダ。実体は後で clone で上書き
                tool_name_override="transfer_to_persona_generator",
                tool_description_override="分析結果をもとに、読者ペルソナ案を生成するエージェントへ移譲します。"
            )
        ],
    )


# 2) ペルソナ生成
def make_persona_generator_agent() -> Agent[AppContext]:
    return Agent[AppContext](
        name="Persona Generator",
        instructions=(
            f"""{RECOMMENDED_PROMPT_PREFIX}
あなたはマーケティング戦略プランナーです。直前までの分析結果を踏まえて、到達したい読者像（ペルソナ）を3〜5案、以下のスキーマ（PersonaOptions）で生成してください。
- 各案は id, name, description, tone, reading_level, pains[], search_intent を含むこと。
- 推奨 id を一つ選び、recommended_id に設定してください。
- 出力は必ずスキーマに厳密に従って構造化。
- 生成が終わったら Persona Approval エージェントへハンドオフ（transfer_to_persona_approval）を呼び出してください。
"""
        ),
        model="gpt-5",
        output_type=PersonaOptions,
        handoffs=[
            handoff(
                agent=Agent(name="Persona Approval"),
                tool_name_override="transfer_to_persona_approval",
                tool_description_override="ペルソナ案を人間に提示し、HITLで最終選択を取得します。"
            )
        ],
    )


# 3) ペルソナ承認（HITL：user_select_block を使う / 構造化で id のみ返す）
def make_persona_approval_agent() -> Agent[AppContext]:
    return Agent[AppContext](
        name="Persona Approval",
        instructions=(
            f"""{RECOMMENDED_PROMPT_PREFIX}
あなたはファシリテーターです。前段で生成された PersonaOptions を受け取り、人間に分かりやすく提示して選択を得ます。
- 各案は短いASCIIラベル化した「id: name / tone / pains要約(<=60字)」へ整形し、"1) ... 2) ... 3) ..." 形式の options_block を作成してください。
- user_select_block ツールを必ず1回だけ呼び出し、返ってきた id（例: "opt_a"）を ChosenID のスキーマで最終出力してください。
- その後 Theme Generator へハンドオフ（transfer_to_theme_generator）を呼び出します。
"""
        ),
        tools=[user_select_block],
        model_settings=ModelSettings(tool_choice="user_select_block"),
        model="gpt-5",
        output_type=ChosenID,
        handoffs=[
            handoff(
                agent=Agent(name="Theme Generator"),
                tool_name_override="transfer_to_theme_generator",
                tool_description_override="承認されたペルソナに基づいて記事テーマ案を生成します。"
            )
        ],
    )


# 4) テーマ生成
def make_theme_generator_agent() -> Agent[AppContext]:
    return Agent[AppContext](
        name="Theme Generator",
        instructions=(
            f"""{RECOMMENDED_PROMPT_PREFIX}
あなたはコンテンツストラテジストです。承認済みのペルソナと検索意図/キーワードを踏まえ、記事のテーマ（角度・切り口）を3〜5案、ThemeOptions で生成してください。
- 各案は id, label, angle, rationale を含むこと。
- 最も妥当なテーマの recommended_id を一つ選ぶこと。
- 完了後、Theme Approval エージェントにハンドオフ（transfer_to_theme_approval）。
"""
        ),
        model="gpt-5",
        output_type=ThemeOptions,
        handoffs=[
            handoff(
                agent=Agent(name="Theme Approval"),
                tool_name_override="transfer_to_theme_approval",
                tool_description_override="テーマ案から人間に最終選択をいただきます。"
            )
        ],
    )


# 5) テーマ承認（HITL）
def make_theme_approval_agent() -> Agent[AppContext]:
    return Agent[AppContext](
        name="Theme Approval",
        instructions=(
            f"""{RECOMMENDED_PROMPT_PREFIX}
あなたはファシリテーターです。ThemeOptions を短いASCIIラベルに整形し、options_block を作成して user_select_block を呼びます。
- 戻り値の id を ChosenID で出力。
- 完了後、Outline Builder へハンドオフ（transfer_to_outline_builder）。
"""
        ),
        tools=[user_select_block],
        model_settings=ModelSettings(tool_choice="user_select_block"),
        model="gpt-5",
        output_type=ChosenID,
        handoffs=[
            handoff(
                agent=Agent(name="Outline Builder"),
                tool_name_override="transfer_to_outline_builder",
                tool_description_override="承認済みテーマと分析結果を基に、SEO記事のアウトラインを設計します。"
            )
        ],
    )


# 6) アウトライン
def make_outline_builder_agent() -> Agent[AppContext]:
    return Agent[AppContext](
        name="Outline Builder",
        instructions=(
            f"""{RECOMMENDED_PROMPT_PREFIX}
あなたはSEO記事の構成作成者です。承認済みペルソナ/テーマ/キーワード/競合傾向を踏まえ、差別化されたアウトライン（Outline）を日本語で設計します。
- title/slug/sections[] を厳密スキーマで返すこと。
- WebSearchTool の使用は任意ですが、主要上位記事の見出し傾向に大きな違いがある場合は裏取りしてください。
- 完了後、Research Agent にハンドオフ（transfer_to_research_agent）。
"""
        ),
        tools=[WebSearchTool()],
        model="gpt-5",
        output_type=Outline,
        handoffs=[
            handoff(
                agent=Agent(name="Research Agent"),
                tool_name_override="transfer_to_research_agent",
                tool_description_override="アウトラインに必要な情報・統計・出典URL等を収集・要約します。"
            )
        ],
    )


# 7) リサーチ（検索・要約を一括）
def make_research_agent() -> Agent[AppContext]:
    return Agent[AppContext](
        name="Research Agent",
        instructions=(
            f"""{RECOMMENDED_PROMPT_PREFIX}
あなたは熟練リサーチャーです。アウトラインの各セクションに必要な情報・統計・引用・一次情報URLを WebSearchTool と fetch_url で収集し、ResearchBundle（notes/quotes/sources）で返します。
- notes は自由記述の要点メモ（セクションごとに見出しを付けてもよい）。
- quotes には直接引用候補（文引用）を収集、sources にはURLを列挙（最低でも各セクションに1つ以上の信頼できる出典）。
- 完了後、Writer Agent にハンドオフ（transfer_to_writer_agent）。
"""
        ),
        tools=[WebSearchTool(), fetch_url],
        model_settings=ModelSettings(tool_choice="required"),  # 少なくとも一度はツールを使わせる
        model="gpt-5",
        output_type=ResearchBundle,
        handoffs=[
            handoff(
                agent=Agent(name="Writer Agent"),
                tool_name_override="transfer_to_writer_agent",
                tool_description_override="収集ノートとアウトラインから SEO 記事を Markdown で執筆します。"
            )
        ],
    )


# 8) 執筆（LiteLLM も可）
def make_writer_agent(writing_model: Optional[str], writer_api_key: Optional[str]) -> Agent[AppContext]:
    model_obj: Any
    if writing_model:
        # ライターだけ外部モデルで書かせる場合（例: anthropic/claude-3-5-sonnet 他）
        model_obj = LitellmModel(model=writing_model, api_key=writer_api_key or "")
    else:
        model_obj = "gpt-5"

    return Agent[AppContext](
        name="Writer Agent",
        instructions=(
            f"""{RECOMMENDED_PROMPT_PREFIX}
あなたはプロのSEOライターです。これまでの分析/ペルソナ/テーマ/アウトライン/リサーチノートを統合し、完成した日本語のSEO記事を Markdown で執筆します。
要件:
- セクションごとに見出し(H2/H3)＋本文。冗長さを避け、固有名詞や数値は出典（sources）を脚注や括弧で明記。
- E-E-A-T を意識し、読者の課題解決と次アクション（CTA）を明確に。
- 可能なら内部リンク/外部リンクの提案（URLはダミーでもよい）。
- 最終出力は Markdown 文字列のみ。余計な説明は不要。
"""
        ),
        model=model_obj,
        # 出力はプレーン文字列（記事本文）
    )


# =============================================================================
#                          エージェント群の“実体”を組み立てる
# =============================================================================

def build_agents(writing_model: Optional[str], writer_api_key: Optional[str]) -> Dict[str, Agent[AppContext]]:
    # まず実体を作る
    keyword_agent = make_keyword_analysis_agent()
    persona_gen = make_persona_generator_agent()
    persona_approval = make_persona_approval_agent()
    theme_gen = make_theme_generator_agent()
    theme_approval = make_theme_approval_agent()
    outline_builder = make_outline_builder_agent()
    research_agent = make_research_agent()
    writer_agent = make_writer_agent(writing_model, writer_api_key)

    # 上で placeholder を使った handoff ターゲットを、実体エージェントに置き換える
    # （SDKの Agent は clone 可能だが、ここでは handoffs を作り直すより agents をまとめて使う）
    keyword_agent.handoffs = [
        handoff(agent=persona_gen, tool_name_override="transfer_to_persona_generator", tool_description_override="分析結果をもとに、読者ペルソナ案を生成するエージェントへ移譲します。")
    ]
    persona_gen.handoffs = [
        handoff(agent=persona_approval, tool_name_override="transfer_to_persona_approval", tool_description_override="ペルソナ案を人間に提示し、HITLで最終選択を取得します。")
    ]
    persona_approval.handoffs = [
        handoff(agent=theme_gen, tool_name_override="transfer_to_theme_generator", tool_description_override="承認されたペルソナに基づいて記事テーマ案を生成します。")
    ]
    theme_gen.handoffs = [
        handoff(agent=theme_approval, tool_name_override="transfer_to_theme_approval", tool_description_override="テーマ案から人間に最終選択をいただきます。")
    ]
    theme_approval.handoffs = [
        handoff(agent=outline_builder, tool_name_override="transfer_to_outline_builder", tool_description_override="承認済みテーマと分析結果を基に、SEO記事のアウトラインを設計します。")
    ]
    outline_builder.handoffs = [
        handoff(agent=research_agent, tool_name_override="transfer_to_research_agent", tool_description_override="アウトラインに必要な情報・統計・出典URL等を収集・要約します。")
    ]
    research_agent.handoffs = [
        handoff(agent=writer_agent, tool_name_override="transfer_to_writer_agent", tool_description_override="収集ノートとアウトラインから SEO 記事を Markdown で執筆します。")
    ]

    return {
        "keyword": keyword_agent,
        "persona_gen": persona_gen,
        "persona_approval": persona_approval,
        "theme_gen": theme_gen,
        "theme_approval": theme_approval,
        "outline": outline_builder,
        "research": research_agent,
        "writer": writer_agent,
    }


# =============================================================================
#                           CLI / ランナー
# =============================================================================

def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="SEO 執筆エージェント（OpenAI Agents SDK x SERPAPI x WebSearch x Handoffs x LiteLLM）")
    p.add_argument("--keywords", type=str, help="カンマ区切りのキーワード")
    p.add_argument("--keywords-file", type=str, help="1行1キーワードのテキストファイル")
    p.add_argument("--gl", type=str, default="jp", help="SERP の地域（gl）例: jp/us/de")
    p.add_argument("--hl", type=str, default="ja", help="SERP の言語（hl）例: ja/en/de")
    p.add_argument("--out", type=str, default="article.md", help="出力Markdownファイルパス")
    p.add_argument("--writer-model", type=str, default=os.getenv("WRITER_MODEL", ""), help="LiteLLM で使う他社モデル指定（例: anthropic/claude-3-5-sonnet-20240620）")
    p.add_argument("--writer-api-key", type=str, default=os.getenv("WRITER_API_KEY", ""), help="ライター用モデルのAPIキー（プロバイダに応じて）")
    return p


async def run_pipeline_single_run(ctx: AppContext, agents: Dict[str, Agent[AppContext]]) -> str:
    """
    ハンドオフ連鎖の**単一 Runner.run**で、Keyword Analysis から Writer まで駆け抜ける。
    途中の HITL は user_select_block が同期的に待ち、ユーザーが番号選択。
    """
    # 起点：Keyword Analysis Agent
    starting_agent = agents["keyword"]
    prompt = (
        "次の keywords を対象に、必ず最初に serp_batch_search を一度だけ実行してSERPスナップショットを取得してください。"
        "続いて WebSearchTool / fetch_url で競合の見出し・本文を裏取りし、KeywordAnalysisOutput を返し、"
        "完了したらペルソナ生成エージェントにハンドオフしてください。\n"
        f"keywords={ctx.keywords}\n"
        f"gl={ctx.gl}, hl={ctx.hl}\n"
    )

    # Hooks を差し込んで進捗を可視化
    hooks = SEOGlobalRunHooks()
    result = await Runner.run(
        starting_agent,
        input=prompt,
        context=ctx,
        max_turns=40,  # 全工程を1ランで実施するため余裕を持たせる
        hooks=hooks,
    )

    final_output = str(result.final_output)
    return final_output


async def main_async():
    parser = build_argparser()
    args = parser.parse_args()
    keywords = parse_keywords(args)

    if not require_env("OPENAI_API_KEY"):
        console.print("[red]OPENAI_API_KEY が未設定です。[/red]")
        sys.exit(1)

    ctx = AppContext(gl=args.gl, hl=args.hl, keywords=keywords)
    agents = build_agents(writing_model=(args.writer_model or None), writer_api_key=(args.writer_api_key or None))

    try:
        article_md = await run_pipeline_single_run(ctx, agents)
    except KeyboardInterrupt:
        console.print("\n[red]中断されました。[/red]")
        sys.exit(1)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(article_md)
        console.print(Panel.fit(f"[green]記事を保存しました:[/green] {args.out}"))

    console.rule("[bold]PREVIEW (先頭1,000字)[/bold]")
    print(article_md[:1000])


if __name__ == "__main__":
    asyncio.run(main_async())
