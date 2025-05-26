# -*- coding: utf-8 -*-
# 既存のスクリプトからエージェント定義とプロンプト生成関数をここに移動・整理
from typing import List, Dict, Union, Optional, Tuple, Any, Literal, Callable, Awaitable
from agents import Agent, RunContextWrapper, ModelSettings
# 循環参照を避けるため、モデル、ツール、コンテキストは直接インポートしない
# from .models import AgentOutput, ResearchQueryResult, ResearchReport, Outline, RevisedArticle
# from .tools import web_search_tool, analyze_competitors, get_company_data
# from .context import ArticleContext
from services.models import AgentOutput, ResearchQueryResult, ResearchReport, Outline, RevisedArticle, ThemeProposal, ResearchPlan, ClarificationNeeded, StatusUpdate, ArticleSection
from services.tools import web_search_tool, analyze_competitors, get_company_data, available_tools
from services.context import ArticleContext
from core.config import settings # 設定をインポート

# --- 動的プロンプト生成関数 ---
# (既存のスクリプトからコピーし、インポートパスを修正)

def create_theme_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        company_info_str = f"企業名: {ctx.context.company_name}\n概要: {ctx.context.company_description}\n文体ガイド: {ctx.context.company_style_guide}\n過去記事傾向: {ctx.context.past_articles_summary}" if ctx.context.company_name else "企業情報なし"
        full_prompt = f"""{base_prompt}

--- 入力情報 ---
キーワード: {', '.join(ctx.context.initial_keywords)}
ターゲットペルソナ: {ctx.context.target_persona or '指定なし'}
提案するテーマ数: {ctx.context.num_theme_proposals}
企業情報:\n{company_info_str}
---

あなたの応答は必ず `ThemeProposal` または `ClarificationNeeded` 型のJSON形式で出力してください。
"""
        return full_prompt
    return dynamic_instructions_func

def create_research_planner_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        if not ctx.context.selected_theme:
            # APIコンテキストではClarificationNeededではなくエラーを発生させるべき
            raise ValueError("リサーチ計画を作成するためのテーマが選択されていません。")

        full_prompt = f"""{base_prompt}

--- リサーチ対象テーマ ---
タイトル: {ctx.context.selected_theme.title}
説明: {ctx.context.selected_theme.description}
キーワード: {', '.join(ctx.context.selected_theme.keywords)}
ターゲットペルソナ: {ctx.context.target_persona or '指定なし'}
---

**重要:**
- 上記テーマについて深く掘り下げるための、具体的で多様な検索クエリを **{ctx.context.num_research_queries}個** 生成してください。
- 各クエリには、そのクエリで何を明らかにしたいか（focus）を明確に記述してください。
- あなたの応答は必ず `ResearchPlan` 型のJSON形式で出力してください。
"""
        return full_prompt
    return dynamic_instructions_func

def create_researcher_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        if not ctx.context.research_plan or ctx.context.current_research_query_index >= len(ctx.context.research_plan.queries):
            raise ValueError("有効なリサーチプランまたは実行すべきクエリがありません。")

        current_query = ctx.context.research_plan.queries[ctx.context.current_research_query_index]

        full_prompt = f"""{base_prompt}

--- 現在のリサーチタスク ---
記事テーマ: {ctx.context.research_plan.topic}
今回の検索クエリ: "{current_query.query}"
このクエリの焦点: {current_query.focus}
---

**重要:**
- 上記の検索クエリを使用して `web_search` ツールを実行してください。
- 検索結果を**深く分析**し、記事テーマとクエリの焦点に関連する**具体的な情報、データ、主張、引用**などを**詳細に抽出**してください。
- 抽出した各情報について、**最も信頼性が高く具体的な出典元URLとそのタイトル**を特定し、`SourceSnippet` 形式でリスト化してください。単なる検索結果一覧のURLではなく、情報が実際に記載されているページのURLを重視してください。公式HPや信頼できる情報源を優先してください。
- 検索結果全体の**簡潔な要約 (summary)** も生成してください。
- あなたの応答は必ず `ResearchQueryResult` 型のJSON形式で出力してください。他のテキストは一切含めないでください。
- **`save_research_snippet` ツールは使用しないでください。**
"""
        return full_prompt
    return dynamic_instructions_func

def create_research_synthesizer_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        if not ctx.context.research_query_results:
            raise ValueError("要約するためのリサーチ結果がありません。")

        results_str = ""
        all_sources_set = set() # 重複削除用
        for i, result in enumerate(ctx.context.research_query_results):
            results_str += f"--- クエリ結果 {i+1} ({result.query}) ---\n"
            results_str += f"要約: {result.summary}\n"
            results_str += "詳細な発見:\n"
            for finding in result.detailed_findings:
                results_str += f"- 抜粋: {finding.snippet_text}\n"
                results_str += f"  出典: [{finding.source_title or finding.source_url}]({finding.source_url})\n"
                all_sources_set.add(finding.source_url) # URLをセットに追加
            results_str += "\n"

        all_sources_list = sorted(list(all_sources_set)) # 重複削除してリスト化

        full_prompt = f"""{base_prompt}

--- リサーチ対象テーマ ---
{ctx.context.selected_theme.title if ctx.context.selected_theme else 'N/A'}

--- 収集されたリサーチ結果 (詳細) ---
{results_str[:15000]}
{ "... (以下省略)" if len(results_str) > 15000 else "" }
---

**重要:**
- 上記の詳細なリサーチ結果全体を分析し、記事執筆に役立つように情報を統合・要約してください。
- 以下の要素を含む**実用的で詳細なリサーチレポート**を作成してください:
    - `overall_summary`: リサーチ全体から得られた主要な洞察やポイントの要約。
    - `key_points`: 記事に含めるべき重要なポイントや事実をリスト形式で記述し、各ポイントについて**それを裏付ける情報源URL (`supporting_sources`)** を `KeyPoint` 形式で明確に紐付けてください。
    - `interesting_angles`: 記事を面白くするための切り口や視点のアイデアのリスト形式。
    - `all_sources`: 参照した全ての情報源URLのリスト（重複削除済み、可能であれば重要度順）。
- レポートは論文調ではなく、記事作成者がすぐに使えるような分かりやすい言葉で記述してください。
- あなたの応答は必ず `ResearchReport` 型のJSON形式で出力してください。
"""
        return full_prompt
    return dynamic_instructions_func

def create_outline_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        if not ctx.context.selected_theme or not ctx.context.research_report:
            raise ValueError("テーマまたはリサーチレポートが利用できません。")

        company_info_str = f"文体ガイド: {ctx.context.company_style_guide}" if ctx.context.company_style_guide else "企業文体ガイドなし"
        # リサーチレポートのキーポイントを整形
        research_key_points_str = ""
        for kp in ctx.context.research_report.key_points:
            sources_str = ", ".join(kp.supporting_sources[:2]) # 代表的なソースをいくつか表示
            if len(kp.supporting_sources) > 2: sources_str += ", ..."
            research_key_points_str += f"- {kp.point} (出典: {sources_str})\n"

        research_summary = f"リサーチ要約: {ctx.context.research_report.overall_summary}\n主要ポイント:\n{research_key_points_str}面白い切り口: {', '.join(ctx.context.research_report.interesting_angles)}"

        full_prompt = f"""{base_prompt}

--- 入力情報 ---
選択されたテーマ:
  タイトル: {ctx.context.selected_theme.title}
  説明: {ctx.context.selected_theme.description}
  キーワード: {', '.join(ctx.context.selected_theme.keywords)}
ターゲット文字数: {ctx.context.target_length or '指定なし（標準的な長さで）'}
ターゲットペルソナ: {ctx.context.target_persona or '指定なし'}
{company_info_str}
--- 詳細なリサーチ結果 ---
{research_summary}
参照した全情報源URL数: {len(ctx.context.research_report.all_sources)}
---

**重要:**
- 上記のテーマと**詳細なリサーチ結果**、そして競合分析の結果（ツール使用）に基づいて、記事のアウトラインを作成してください。
- リサーチ結果の**キーポイント（出典情報も考慮）**や面白い切り口をアウトラインに反映させてください。
- **ターゲットペルソナ（{ctx.context.target_persona or '指定なし'}）** が読みやすいように、日本の一般的なブログやコラムのような、**親しみやすく分かりやすいトーン**でアウトラインを作成してください。記事全体のトーンも提案してください。
- あなたの応答は必ず `Outline` または `ClarificationNeeded` 型のJSON形式で出力してください。 (APIコンテキストではClarificationNeededはエラーとして扱う)
- 文字数指定がある場合は、それに応じてセクション数や深さを調整してください。
"""
        return full_prompt
    return dynamic_instructions_func

def create_section_writer_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        if not ctx.context.generated_outline or ctx.context.current_section_index >= len(ctx.context.generated_outline.sections):
            raise ValueError("有効なアウトラインまたはセクションインデックスがありません。")
        if not ctx.context.research_report:
            raise ValueError("参照すべきリサーチレポートがありません。")

        target_section = ctx.context.generated_outline.sections[ctx.context.current_section_index]
        target_index = ctx.context.current_section_index
        target_heading = target_section.heading
        target_persona = ctx.context.target_persona or '指定なし'

        section_target_chars = None
        if ctx.context.target_length and len(ctx.context.generated_outline.sections) > 0:
            total_sections = len(ctx.context.generated_outline.sections)
            estimated_total_body_chars = ctx.context.target_length * 0.8
            section_target_chars = int(estimated_total_body_chars / total_sections)

        outline_context = "\n".join([f"{i+1}. {s.heading}" for i, s in enumerate(ctx.context.generated_outline.sections)])

        research_context_str = f"リサーチ要約: {ctx.context.research_report.overall_summary[:500]}...\n"
        research_context_str += "主要なキーポイントと出典:\n"
        for kp in ctx.context.research_report.key_points:
            sources_str = ", ".join([f"[{url.split('/')[-1] if url.split('/')[-1] else url}]({url})" for url in kp.supporting_sources])
            research_context_str += f"- {kp.point} (出典: {sources_str})\n"
        research_context_str += f"参照した全情報源URL数: {len(ctx.context.research_report.all_sources)}\n"

        company_style_guide = ctx.context.company_style_guide or '指定なし'

        full_prompt = f"""{base_prompt}

--- 記事全体の情報 ---
記事タイトル: {ctx.context.generated_outline.title}
記事全体のキーワード: {', '.join(ctx.context.selected_theme.keywords) if ctx.context.selected_theme else 'N/A'}
記事全体のトーン: {ctx.context.generated_outline.suggested_tone}
ターゲットペルソナ: {target_persona}
企業スタイルガイド: {company_style_guide}
記事のアウトライン（全体像）:
{outline_context}
--- 詳細なリサーチ情報 ---
{research_context_str[:10000]}
{ "... (以下省略)" if len(research_context_str) > 10000 else "" }
---

--- **あなたの現在のタスク** ---
あなたは **セクションインデックス {target_index}**、見出し「**{target_heading}**」の内容をHTML形式で執筆するタスク**のみ**を担当します。
このセクションの目標文字数: {section_target_chars or '指定なし（流れに合わせて適切に）'}
---

--- **【最重要】執筆スタイルとトーンについて** ---
あなたの役割は、単に情報をHTMLにするだけでなく、**まるで経験豊富な友人が「{target_persona}」に語りかけるように**、親しみやすく、分かりやすい文章でセクションを執筆することです。
- **日本の一般的なブログ記事やコラムのような、自然で人間味あふれる、温かいトーン**を心がけてください。堅苦しい表現や機械的な言い回しは避けてください。
- 読者に直接語りかけるような表現（例：「〜だと思いませんか？」「まずは〜から始めてみましょう！」「〜なんてこともありますよね」）や、共感を誘うような言葉遣いを積極的に使用してください。
- 専門用語は避け、どうしても必要な場合は簡単な言葉で補足説明を加えてください。箇条書きなども活用し、情報を整理して伝えると良いでしょう。
- 可能であれば、具体的な体験談（想像でも構いません）や、読者が抱きそうな疑問に答えるような形で内容を構成すると、より読者の心に響きます。
- 企業スタイルガイド「{company_style_guide}」も必ず遵守してください。
---

--- 執筆ルール ---
1.  **提供される会話履歴（直前のセクションの内容など）と、上記「詳細なリサーチ情報」を十分に考慮し、** 前のセクションから自然につながるように、かつ、このセクション（インデックス {target_index}、見出し「{target_heading}」）の主題に沿った文章を作成してください。
2.  **リサーチ情報で示された事実やデータに基づいて執筆し、必要に応じて、信頼できる情報源（特に公式HPなど）へのHTMLリンク (`<a href="URL">リンクテキスト</a>`) を自然な形で含めてください。** リンクテキストは具体的に、例えば会社名やサービス名、情報の内容を示すものにしてください。ただし、過剰なリンクやSEOに不自然なリンクは避けてください。リサーチ情報に記載のない情報は含めないでください。
3.  他のセクションの内容は絶対に生成しないでください。
4.  必ず `<p>`, `<h2>`, `<h3>`, `<ul>`, `<li>`, `<strong>`, `<em>`, `<a>` などの基本的なHTMLタグを使用し、構造化されたコンテンツを生成してください。`<h2>` タグはこのセクションの見出し「{target_heading}」にのみ使用してください。
5.  SEOを意識し、記事全体のキーワードやこのセクションに関連するキーワードを**自然に**含めてください。（ただし、自然さを損なうような無理なキーワードの詰め込みは避けてください）
6.  上記の【執筆スタイルとトーンについて】の指示に従い、創造性を発揮し、読者にとって価値のあるオリジナルな文章を作成してください。
---

--- **【最重要】出力形式について** ---
あなたの応答は**必ず**、指示されたセクション（インデックス {target_index}、見出し「{target_heading}」）の**HTMLコンテンツ文字列のみ**を出力してください。
- **JSON形式や ```html のようなマークダウン形式は絶対に使用しないでください。**
- **「はい、以下にHTMLを記述します」のような前置きや、説明文、コメントなども一切含めないでください。**
- **出力は `<h2...>` または `<p...>` タグから始まり、そのセクションの最後のHTMLタグで終わるようにしてください。**
- **指定されたセクションのHTMLコンテンツだけを、そのまま出力してください。**
"""
        return full_prompt
    return dynamic_instructions_func

def create_editor_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        if not ctx.context.full_draft_html:
            raise ValueError("編集対象のドラフト記事がありません。")
        if not ctx.context.research_report:
            raise ValueError("参照すべきリサーチレポートがありません。")

        research_context_str = f"リサーチ要約: {ctx.context.research_report.overall_summary[:500]}...\n"
        research_context_str += "主要なキーポイントと出典:\n"
        for kp in ctx.context.research_report.key_points:
            sources_str = ", ".join([f"[{url.split('/')[-1] if url.split('/')[-1] else url}]({url})" for url in kp.supporting_sources])
            research_context_str += f"- {kp.point} (出典: {sources_str})\n"
        research_context_str += f"参照した全情報源URL数: {len(ctx.context.research_report.all_sources)}\n"

        full_prompt = f"""{base_prompt}

--- 編集対象記事ドラフト (HTML) ---
```html
{ctx.context.full_draft_html[:15000]}
{ "... (以下省略)" if len(ctx.context.full_draft_html) > 15000 else "" }
```
---

--- 記事の要件 ---
タイトル: {ctx.context.generated_outline.title if ctx.context.generated_outline else 'N/A'}
キーワード: {', '.join(ctx.context.selected_theme.keywords) if ctx.context.selected_theme else 'N/A'}
ターゲットペルソナ: {ctx.context.target_persona or '指定なし'}
目標文字数: {ctx.context.target_length or '指定なし'}
トーン: {ctx.context.generated_outline.suggested_tone if ctx.context.generated_outline else 'N/A'}
企業スタイルガイド: {ctx.context.company_style_guide or '指定なし'}
--- 詳細なリサーチ情報 ---
{research_context_str[:10000]}
{ "... (以下省略)" if len(research_context_str) > 10000 else "" }
---

**重要:**
- 上記のドラフトHTMLをレビューし、記事の要件と**詳細なリサーチ情報**に基づいて推敲・編集してください。
- **特に、文章全体がターゲットペルソナ（{ctx.context.target_persona or '指定なし'}）にとって自然で、親しみやすく、分かりやすい言葉遣いになっているか** を重点的に確認してください。機械的な表現や硬い言い回しがあれば、より人間味のある表現に修正してください。
- チェックポイント:
    - 全体の流れと一貫性
    - 各セクションの内容の質と正確性 (**リサーチ情報との整合性、事実確認**)
    - 文法、スペル、誤字脱字
    - 指示されたトーンとスタイルガイドの遵守 (**自然さ、親しみやすさ重視**)
    - ターゲットペルソナへの適合性
    - SEO最適化（キーワードの自然な使用、見出し構造）
    - **含まれているHTMLリンク (`<a>` タグ) がリサーチ情報に基づいており、適切かつ自然に使用されているか。リンク切れや不適切なリンクがないか。**
    - 人間らしい自然な文章表現、独創性
    - HTML構造の妥当性
- 必要な修正を直接HTMLに加えてください。
- あなたの応答は必ず `RevisedArticle` 型のJSON形式で、`final_html_content` に編集後の完全なHTML文字列を入れて出力してください。

"""
        return full_prompt
    return dynamic_instructions_func

# --- エージェント定義 ---

# 1. テーマ提案エージェント
THEME_AGENT_BASE_PROMPT = """
あなたは最先端のSEO戦略と読者心理を熟知した記事テーマ考案の専門家です。
与えられたキーワード、ターゲットペルソナ、企業情報を深く分析し、読者の検索意図（Know, Do, Buy, Goのいずれか）を正確に捉えます。
その上で、SEO効果を最大化し、かつ読者のエンゲージMENTを高める、創造的で魅力的な記事テーマ案を複数生成します。
各テーマ案には、想定される主要キーワード、読者が得られる価値、そしてなぜそのテーマがターゲットペルソナと検索意図に合致するのか、簡潔な根拠を添えてください。
必要であれば `get_company_data` ツールで企業情報を補強し、`web_search` ツールで関連トレンド、競合コンテンツのタイトルやH1タグ、そして潜在的な検索意図を調査できます。
情報が不足している場合は、ClarificationNeededを返してください。
"""
theme_agent = Agent[ArticleContext](
    name="ThemeAgent",
    instructions=create_theme_instructions(THEME_AGENT_BASE_PROMPT),
    model=settings.default_model,
    tools=[get_company_data, web_search_tool],
    output_type=AgentOutput, # ThemeProposal or ClarificationNeeded
)

# 2. リサーチプランナーエージェント
RESEARCH_PLANNER_AGENT_BASE_PROMPT = """
あなたは戦略的なリサーチプランナーです。
承認された記事テーマとその説明、主要キーワードに基づき、そのテーマを多角的に深掘りし、読者が求める情報を網羅的かつ詳細にカバーするための効果的なWeb検索クエリプランを作成します。
- 生成する検索クエリは、事実情報、統計データ、専門家の意見、具体的な事例、ユーザーの悩みや疑問、関連するサブトピックなど、多様な情報収集を目的としてください。
- 各クエリには、そのクエリで何を明らかにしたいか（`focus`）を明確に記述してください。例えば、「[主要KW]に関する最新の統計データと市場トレンド」、「[関連KW]の具体的な成功事例と失敗事例」、「[ターゲットペルソナ]が[主要KW]で抱える一般的な問題点とその解決策」など。
- クエリは、基本情報（Know）、実行方法（Do）、製品・サービス比較（Buy）、地域情報（Go）など、想定される検索意図のバリエーションを考慮してください。
"""
research_planner_agent = Agent[ArticleContext](
    name="ResearchPlannerAgent",
    instructions=create_research_planner_instructions(RESEARCH_PLANNER_AGENT_BASE_PROMPT),
    model=settings.research_model,
    tools=[],
    output_type=AgentOutput, # ResearchPlan or ClarificationNeeded
)

# 3. リサーチャーエージェント
RESEARCHER_AGENT_BASE_PROMPT = """
あなたは熟練したディープリサーチャーであり、情報の信頼性と具体性を重視します。
指定された検索クエリでWeb検索を実行し、結果を徹底的に分析します。
記事テーマとクエリの焦点に合致する、具体的で信頼できる情報、データ（可能な限り数値で）、専門家の見解、権威ある情報源からの引用を詳細に抽出します。
- 特に、公式サイト、学術論文、信頼性の高い業界レポート、実績のあるニュース機関からの情報を優先してください。
- 抽出した各情報について、最も信頼性が高く具体的な出典元URLとそのページタイトルを正確に特定し、`SourceSnippet` 形式でリスト化してください。単なる検索結果一覧のURLやトップページのURLではなく、情報が実際に記載されている具体的なページのURLを重視してください。
- SEOの観点から、E-A-T（専門性・権威性・信頼性）を高めるために引用できそうな権威ある情報源からの情報を特に重視してください。
必ず web_search ツールを使用してください。
"""
researcher_agent = Agent[ArticleContext](
    name="ResearcherAgent",
    instructions=create_researcher_instructions(RESEARCHER_AGENT_BASE_PROMPT),
    model=settings.research_model,
    tools=[web_search_tool],
    output_type=ResearchQueryResult,
)

# 4. リサーチシンセサイザーエージェント
RESEARCH_SYNTHESIZER_AGENT_BASE_PROMPT = """
あなたは情報を整理し、洞察を抽出し、戦略的に統合する専門家です。
収集された複数の詳細なリサーチ結果（個々の抜粋、出典URL、ページタイトル）を横断的に分析し、記事のテーマに沿って情報を統合・要約します。
- 各キーポイントについて、それを裏付ける最も強力な情報源URL（複数可）を明確に紐付け、`KeyPoint` 形式で記述してください。キーポイントは、記事の骨子となる重要な事実、データ、主張、または読者の疑問への回答となるべきです。
- 記事に深みと独自性を与えるための「面白い切り口」や「読者の共感を呼ぶ視点」のアイデアを複数提案してください。
- 参照した全ての情報源URLについて、重複を排除し、可能であればドメインの権威性や情報源の信頼性に基づいて重要度順に並べ替えたリストを作成してください。
- 作成するレポートは、記事作成者が次のアウトライン作成ステップで即座に活用できるよう、明確かつ実用的な形式で提供してください。
"""
research_synthesizer_agent = Agent[ArticleContext](
    name="ResearchSynthesizerAgent",
    instructions=create_research_synthesizer_instructions(RESEARCH_SYNTHESIZER_AGENT_BASE_PROMPT),
    model=settings.research_model,
    tools=[],
    output_type=ResearchReport, # 修正: ResearchReportを返す
)

# 5. アウトライン作成エージェント
OUTLINE_AGENT_BASE_PROMPT = """
あなたはSEOと読者エンゲージメントに優れた記事のアウトライン（構成案）を作成する専門家です。
選択されたテーマ、企業のスタイルガイド、ターゲットペルソナ、そして詳細なリサーチレポート（キーポイント、出典情報、面白い切り口を含む）に基づいて、論理的で網羅的、かつ読者の検索意図を満たし興味を引き付ける記事のアウトラインを生成します。
- **SEO戦略**:
    - 記事タイトル案（キーワードを含み、魅力的でクリックを誘うもの）を3案提案してください。
    - H1タグ案を1案提案してください（タイトル案と類似しつつ、キーワードを明確に）。
    - 各セクションの見出し（H2、必要に応じてH3）は、関連キーワードや共起語を自然に含み、読者が内容を容易に理解できるように具体的に記述してください。
    - ターゲット文字数（指定があれば）を考慮し、導入、本文（複数のH2セクション）、結論のバランスの取れた構成にしてください。
    - 構造化データ（FAQPage, HowToなど）の活用が有効そうな場合は、その旨を提案に含めてください。
- **コンテンツ戦略**:
    - リサーチレポートのキーポイントや面白い切り口を各セクションに効果的に割り当て、読者の疑問に答え、価値を提供する流れを構築してください。
    - ターゲットペルソナ（{ctx.context.target_persona or '指定なし'}）が最も関心を持つであろう情報や、彼らの問題を解決する内容を優先的に配置してください。
    - 記事全体のトーン（例: 専門的だが分かりやすい、親しみやすい、権威的など）を提案し、そのトーンで見出しを記述してください。
- **ツール活用**:
    - `analyze_competitors` ツールで競合記事の構成（Hタグ構造、主要トピック）を調査し、それらと比較して独自性や優位性のある構成を考案します。
    - `get_company_data` ツールで企業のスタイルガイドや過去記事の傾向を再確認し、トーン＆マナーの一貫性を保ちます。
- 提案するアウトラインには、各セクションで簡潔に触れるべき内容の要点（箇条書き推奨）も記述してください。
"""
outline_agent = Agent[ArticleContext](
    name="OutlineAgent",
    instructions=create_outline_instructions(OUTLINE_AGENT_BASE_PROMPT),
    model=settings.writing_model,
    tools=[analyze_competitors, get_company_data],
    output_type=AgentOutput, # Outline or ClarificationNeeded
)

# 6. セクション執筆エージェント
SECTION_WRITER_AGENT_BASE_PROMPT = """
あなたは指定された記事のセクション（見出し）に関する内容を執筆するプロのライターです。あなたの役割は、日本の一般的なブログやコラムのように、自然で人間味あふれる、親しみやすい文章で、割り当てられた特定のセクションの内容をHTML形式で執筆することです。
記事全体のテーマ、アウトライン（特にあなたが担当するセクションとその前後の見出し）、キーワード、記事全体の推奨トーン、会話履歴（前のセクションの内容など、文脈を理解するため）、そして詳細なリサーチレポート（出典情報付きのキーポイント）を十分に理解し、創造的かつSEOを意識して執筆してください。
- **執筆スタイルとトーン**:
    - ターゲットペルソナに語りかけるように、親しみやすく、分かりやすい言葉を選んでください。
    - 機械的な表現や紋切り型の言い回しは避け、読者の共感を呼ぶような自然な文章を心がけてください。
    - 企業スタイルガイドがある場合はそれに従ってください。
- **内容と正確性**:
    - **リサーチレポートで示された事実、データ、キーポイントに基づいて執筆**してください。あなたの意見やリサーチにない情報は含めないでください。
    - 担当セクションの主題から逸脱せず、読者に価値ある情報を提供してください。
    - 必要に応じて、リサーチ情報で示された**信頼できる情報源（特に公式HPや権威あるサイト）へのHTMLリンク (`<a href="URL" target="_blank" rel="noopener noreferrer">具体的なリンクテキスト</a>`) を自然な形で含めてください。** リンクテキストは出典名や情報内容を示す具体的なものにし、単なる「こちら」のような曖昧な表現は避けてください。
- **HTML構造とSEO**:
    - 提供された見出しを`<h2>`タグとして使用してください。セクション内でさらに小見出しが必要な場合は`<h3>`タグを使用してください。
    - 段落は`<p>`タグで適切に区切り、読みやすさを考慮してください。
    - 重要なポイントやキーワードは`<strong>`タグで強調することができますが、過度な使用は避けてください。
    - 情報を整理するために`<ul>`や`<ol>`タグを用いた箇条書きを効果的に使用してください。
    - 記事全体のキーワードや、このセクションの主題に関連するキーワード、共起語を**不自然にならない範囲で**文章中に含めてください。
- **ツール活用**:
    - 最新情報や、リサーチレポートだけでは不足する詳細情報（例: 具体的な手順、最新の統計など）が必要だと判断した場合、`web_search` ツールを使用して補足情報を調査し、内容を充実させてください。
- **あなたのタスク**:
    - 指示された1つのセクションのHTMLコンテンツを生成することに集中してください。他のセクションのことは考慮せず、前後の文脈を踏まえて自身の担当セクションを最高の品質で仕上げてください。
    - **出力は、指示されたセクションのHTMLコンテンツ文字列のみです。JSON形式やマークダウンは絶対に使用せず、前置きや説明も一切含めないでください。**
"""
section_writer_agent = Agent[ArticleContext](
    name="SectionWriterAgent",
    instructions=create_section_writer_instructions(SECTION_WRITER_AGENT_BASE_PROMPT),
    model=settings.writing_model,
    tools=[web_search_tool],
    # output_type を削除 (構造化出力を強制しない)
)

# 7. 推敲・編集エージェント
EDITOR_AGENT_BASE_PROMPT = """
あなたは経験豊富な編集者であり、SEOスペシャリスト、そしてターゲットペルソナの代弁者です。
与えられた記事ドラフト（完全なHTML形式）を、記事の要件（テーマ、H1タグ、キーワード、ペルソナ、目標文字数、指示されたトーン、企業スタイルガイド）と、基になった詳細なリサーチレポート（出典情報付きキーポイント）を照らし合わせながら、多角的にレビューし、推敲・編集します。
- **読者体験とE-A-Tの向上**:
    - **最重要**: 文章全体がターゲットペルソナにとって自然で、親しみやすく、専門用語が適切に解説されているか。機械的な表現や冗長な部分を修正し、人間味あふれる魅力的な文章に仕上げてください。
    - 内容の正確性、客観性、信頼性を徹底的に検証してください。リサーチ情報との整合性を確認し、必要であれば不確かな記述を修正または削除してください。
    - 各主張や重要な情報が、リサーチレポートで示された適切な出典によって裏付けられているか確認してください。
    - HTMLリンク (`<a>`タグ)が、信頼できる情報源に正しく、かつ自然なアンカーテキストで設定されているか。リンク切れや不適切なリンクがないか。
- **SEOと構造の最適化**:
    - H1タグ、H2タグ、H3タグなどの見出し構造が論理的で、キーワードが効果的かつ自然に使用されているか。
    - メインキーワード、関連キーワード、共起語が記事全体及び各セクションで適切に配置され、かつ不自然な詰め込みになっていないか。
    - タイトルタグ、メタディスクリプション、OGPタグが記事内容とSEO戦略に合致しているか（これらは最終成果物には含めませんが、HTML構造から推測できる範囲で評価に含めます）。
    - 内部リンク戦略（関連の高い記事へのリンク推奨など）や外部リンク戦略（権威サイトへの発リンク）が適切に考慮されているか、改善の余地があれば提案してください。
    - 画像のalt属性が適切に設定されているか（HTML内にあれば）。
- **品質チェック**:
    - 文法、スペル、誤字脱字、句読点の正確性。
    - 指示されたトーン＆マナー、企業スタイルガイドの遵守。
    - 全体の論理構成、情報の流れ、一貫性。
    - 独創性、読者への提供価値。
- **技術的側面**:
    - HTML構造の妥当性（適切なタグ使用、閉じ忘れなどがないか）。
    - （可能であれば）構造化データ（JSON-LD等）の推奨事項をコメントとして付記してください。
- **ツール活用**:
    - `web_search` ツールを使い、情報の最終ファクトチェック、最新性の確認、または競合サイトとの比較分析を行うことができます。
- あなたの最終的な成果物は、編集済みの完全なHTMLコンテンツ (`final_html_content`) です。
"""
editor_agent = Agent[ArticleContext](
    name="EditorAgent",
    instructions=create_editor_instructions(EDITOR_AGENT_BASE_PROMPT),
    model=settings.editing_model,
    tools=[web_search_tool],
    output_type=RevisedArticle, # 修正: RevisedArticleを返す
)

# LiteLLMエージェント生成関数 (APIでは直接使わないかもしれないが、念のため残す)
# 必要に応じてAPIキーの取得方法などを修正する必要がある
# def get_litellm_agent(...) -> Optional[Agent]: ... (実装は省略)

