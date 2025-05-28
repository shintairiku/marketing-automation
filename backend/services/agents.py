# -*- coding: utf-8 -*-
# 既存のスクリプトからエージェント定義とプロンプト生成関数をここに移動・整理
from typing import List, Dict, Union, Optional, Tuple, Any, Literal, Callable, Awaitable
from agents import Agent, RunContextWrapper, ModelSettings
# 循環参照を避けるため、モデル、ツール、コンテキストは直接インポートしない
# from .models import AgentOutput, ResearchQueryResult, ResearchReport, Outline, RevisedArticle
# from .tools import web_search_tool, analyze_competitors, get_company_data
# from .context import ArticleContext
from services.models import AgentOutput, ResearchQueryResult, ResearchReport, Outline, RevisedArticle, ThemeProposal, ResearchPlan, ClarificationNeeded, StatusUpdate, ArticleSection, GeneratedPersonasResponse, GeneratedPersonaItem
from services.tools import web_search_tool, analyze_competitors, get_company_data, available_tools
from services.context import ArticleContext
from core.config import settings # 設定をインポート
from schemas.request import PersonaType # 修正

# --- 動的プロンプト生成関数 ---
# (既存のスクリプトからコピーし、インポートパスを修正)

def create_theme_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        if not ctx.context.selected_detailed_persona:
            raise ValueError("テーマ提案のための詳細なペルソナが選択されていません。")
        persona_description = ctx.context.selected_detailed_persona
        company_info_str = f"企業名: {ctx.context.company_name}\n概要: {ctx.context.company_description}\n文体ガイド: {ctx.context.company_style_guide}\n過去記事傾向: {ctx.context.past_articles_summary}" if ctx.context.company_name else "企業情報なし"
        full_prompt = f"""{base_prompt}

--- 入力情報 ---
キーワード: {', '.join(ctx.context.initial_keywords)}
ターゲットペルソナ詳細:\n{persona_description}
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
            raise ValueError("リサーチ計画を作成するためのテーマが選択されていません。")
        if not ctx.context.selected_detailed_persona:
            raise ValueError("リサーチ計画のための詳細なペルソナが選択されていません。")
        persona_description = ctx.context.selected_detailed_persona

        full_prompt = f"""{base_prompt}

--- リサーチ対象テーマ ---
タイトル: {ctx.context.selected_theme.title}
説明: {ctx.context.selected_theme.description}
キーワード: {', '.join(ctx.context.selected_theme.keywords)}
ターゲットペルソナ詳細:\n{persona_description}
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
            raise ValueError("アウトライン作成に必要なテーマまたはリサーチレポートがありません。")
        if not ctx.context.selected_detailed_persona:
            raise ValueError("アウトライン作成のための詳細なペルソナが選択されていません。")
        persona_description = ctx.context.selected_detailed_persona

        research_summary = ctx.context.research_report.overall_summary
        company_info_str = ""
        if ctx.context.company_name or ctx.context.company_description:
            company_info_str = f"\nクライアント情報:\n  企業名: {ctx.context.company_name or '未設定'}\n  企業概要: {ctx.context.company_description or '未設定'}\n"

        full_prompt = f"""{base_prompt}

--- 入力情報 ---
選択されたテーマ:
  タイトル: {ctx.context.selected_theme.title}
  説明: {ctx.context.selected_theme.description}
  キーワード: {', '.join(ctx.context.selected_theme.keywords)}
ターゲット文字数: {ctx.context.target_length or '指定なし（標準的な長さで）'}
ターゲットペルソナ詳細:\n{persona_description}
{company_info_str}
--- 詳細なリサーチ結果 ---
{research_summary}
参照した全情報源URL数: {len(ctx.context.research_report.all_sources)}
---

**重要:**
- 上記のテーマと**詳細なリサーチ結果**、そして競合分析の結果（ツール使用）に基づいて、記事のアウトラインを作成してください。
- リサーチ結果の**キーポイント（出典情報も考慮）**や面白い切り口をアウトラインに反映させてください。
- **ターゲットペルソナ「{persona_description}」** が読みやすいように、日本の一般的なブログやコラムのような、**親しみやすく分かりやすいトーン**でアウトラインを作成してください。記事全体のトーンも提案してください。
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
        if not ctx.context.selected_detailed_persona:
            raise ValueError("セクション執筆のための詳細なペルソナが選択されていません。")
        persona_description = ctx.context.selected_detailed_persona

        target_section = ctx.context.generated_outline.sections[ctx.context.current_section_index]
        target_index = ctx.context.current_section_index
        target_heading = target_section.heading
        
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
ターゲットペルソナ詳細:\n{persona_description}
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
あなたの役割は、単に情報をHTMLにするだけでなく、**まるで経験豊富な友人が以下のペルソナ「{persona_description}」に語りかけるように**、親しみやすく、分かりやすい文章でセクションを執筆することです。
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
        if not ctx.context.selected_detailed_persona:
            raise ValueError("編集のための詳細なペルソナが選択されていません。")
        persona_description = ctx.context.selected_detailed_persona

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
ターゲットペルソナ詳細:\n{persona_description}
目標文字数: {ctx.context.target_length or '指定なし'}
トーン: {ctx.context.generated_outline.suggested_tone if ctx.context.generated_outline else 'N/A'}
企業スタイルガイド: {ctx.context.company_style_guide or '指定なし'}
--- 詳細なリサーチ情報 ---
{research_context_str[:10000]}
{ "... (以下省略)" if len(research_context_str) > 10000 else "" }
---

**重要:**
- 上記のドラフトHTMLをレビューし、記事の要件と**詳細なリサーチ情報**に基づいて推敲・編集してください。
- **特に、文章全体がターゲットペルソナ「{persona_description}」にとって自然で、親しみやすく、分かりやすい言葉遣いになっているか** を重点的に確認してください。機械的な表現や硬い言い回しがあれば、より人間味のある表現に修正してください。
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

# 新しいエージェント: ペルソナ生成エージェント
PERSONA_GENERATOR_AGENT_BASE_PROMPT = """
あなたはターゲット顧客の具体的なペルソナ像を鮮明に描き出すプロフェッショナルです。
与えられたSEOキーワード、ターゲット年代、ペルソナ属性、およびクライアント企業情報（あれば）を基に、その顧客がどのような人物で、どのようなニーズや悩みを抱えているのか、具体的な背景情報（家族構成、ライフスタイル、価値観など）を含めて詳細なペルソナ像を複数案作成してください。
あなたの応答は必ず `GeneratedPersonasResponse` 型のJSON形式で、`personas` リストの中に指定された数のペルソナ詳細を `GeneratedPersonaItem` として含めてください。
各ペルソナの `description` は、ユーザーが提供した例のような形式で、具体的かつ簡潔に記述してください。

例:
ユーザー入力: 50代 主婦 キーワード「二重窓 デメリット」
あなたの出力内のペルソナdescriptionの一例:
「築30年の戸建てに暮らす50代後半の女性。家族構成は夫婦（子どもは独立）。年々寒さがこたえるようになり、家の暖かさには窓の性能が大きく関わっていることを知った。内窓を設置して家の断熱性を高めたいと考えている。補助金も気になっている。」
"""

def create_persona_generator_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        # 初期入力からのペルソナ情報の組み立て (これは大まかな指定)
        initial_persona_description = "指定なし"
        if ctx.context.persona_type == PersonaType.OTHER and ctx.context.custom_persona:
            initial_persona_description = ctx.context.custom_persona
        elif ctx.context.target_age_group and ctx.context.persona_type:
            initial_persona_description = f"{ctx.context.target_age_group.value}の{ctx.context.persona_type.value}"
        elif ctx.context.custom_persona: # 移行措置
            initial_persona_description = ctx.context.custom_persona
        
        company_info_str = ""
        if ctx.context.company_name or ctx.context.company_description:
            company_info_str = f"\nクライアント企業名: {ctx.context.company_name or '未設定'}\nクライアント企業概要: {ctx.context.company_description or '未設定'}"

        full_prompt = f"""{base_prompt}

--- 入力情報 ---
SEOキーワード: {', '.join(ctx.context.initial_keywords)}
ターゲット年代: {ctx.context.target_age_group.value if ctx.context.target_age_group else '指定なし'}
ペルソナ属性（大分類）: {ctx.context.persona_type.value if ctx.context.persona_type else '指定なし'}
（上記属性が「その他」の場合のユーザー指定ペルソナ: {ctx.context.custom_persona if ctx.context.persona_type == PersonaType.OTHER else '該当なし'}）
生成する具体的なペルソナの数: {ctx.context.num_persona_examples}
{company_info_str}
---

あなたのタスクは、上記入力情報に基づいて、より具体的で詳細なペルソナ像を **{ctx.context.num_persona_examples}個** 生成することです。
各ペルソナは、`GeneratedPersonaItem` の形式で、`id` (0から始まるインデックス) と `description` を含めてください。
"""
        return full_prompt
    return dynamic_instructions_func

persona_generator_agent = Agent[ArticleContext](
    name="PersonaGeneratorAgent",
    instructions=create_persona_generator_instructions(PERSONA_GENERATOR_AGENT_BASE_PROMPT),
    model=settings.default_model, # ペルソナ生成に適したモデルを選択 (例: default_model や writing_model)
    tools=[], # 基本的にはツール不要だが、必要に応じてweb_searchなどを追加検討
    output_type=GeneratedPersonasResponse, # 新しく定義したモデル
)

# --- エージェント定義 ---

# 1. テーマ提案エージェント
THEME_AGENT_BASE_PROMPT = """
あなたはSEO記事のテーマを考案する専門家です。
与えられたキーワード、ターゲットペルソナ、企業情報を分析し、読者の検索意図とSEO効果を考慮した上で、創造的で魅力的な記事テーマ案を複数生成します。
必要であれば `get_company_data` ツールで企業情報を補強し、`web_search` ツールで関連トレンドや競合を調査できます。
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
あなたは優秀なリサーチプランナーです。
与えられた記事テーマに基づき、そのテーマを深く掘り下げ、読者が知りたいであろう情報を網羅するための効果的なWeb検索クエリプランを作成します。
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
あなたは熟練したディープリサーチャーです。
指定された検索クエリでWeb検索を実行し、結果を深く分析します。
記事テーマに関連する具体的で信頼できる情報、データ、主張、引用を詳細に抽出し、最も適切な出典元URLとタイトルを特定して、指定された形式で返します。
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
あなたは情報を整理し、要点を抽出し、統合する専門家です。
収集された詳細なリサーチ結果（抜粋と出典）を分析し、記事のテーマに沿って統合・要約します。
各キーポイントについて、それを裏付ける情報源URLを明確に紐付け、記事作成者がすぐに活用できる実用的で詳細なリサーチレポートを作成します。
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
あなたはSEO記事のアウトライン（構成案）を作成する専門家です。
選択されたテーマ、目標文字数、企業のスタイルガイド、ターゲットペルソナ、そして詳細なリサーチレポート（キーポイントと出典情報を含む）に基づいて、論理的で網羅的、かつ読者の興味を引く記事のアウトラインを生成します。
`analyze_competitors` ツールで競合記事の構成を調査し、差別化できる構成を考案します。
`get_company_data` ツールでスタイルガイドを確認します。
文字数指定に応じて、見出しの数や階層構造を適切に調整します。
ターゲットペルソナが読みやすいように、親しみやすく分かりやすいトーンで記事全体のトーンも提案してください。
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
あなたは指定された記事のセクション（見出し）に関する内容を執筆するプロのライターです。
あなたの役割は、日本の一般的なブログやコラムのように、自然で人間味あふれる、親しみやすい文章で、割り当てられた特定のセクションの内容をHTML形式で執筆することです。
記事全体のテーマ、アウトライン、キーワード、トーン、会話履歴（前のセクションを含む完全な文脈）、そして詳細なリサーチレポート（出典情報付き）に基づき、創造的かつSEOを意識して執筆してください。
リサーチ情報に基づき、必要に応じて信頼できる情報源へのHTMLリンクを自然に含めてください。
必要に応じて `web_search` ツールで最新情報や詳細情報を調査し、内容を充実させます。
あなたのタスクは、指示された1つのセクションのHTMLコンテンツを生成することだけです。読者を引きつけ、価値を提供するオリジナルな文章を作成してください。
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
あなたはプロの編集者兼SEOスペシャリストです。
与えられた記事ドラフト（HTML形式）を、記事の要件（テーマ、キーワード、ペルソナ、文字数、トーン、スタイルガイド）と詳細なリサーチレポート（出典情報付き）を照らし合わせながら、徹底的にレビューし、推敲・編集します。
特に、文章全体がターゲットペルソナにとって自然で、親しみやすく、分かりやすい言葉遣いになっているか を重点的に確認し、機械的な表現があれば人間味のある表現に修正してください。
リサーチ情報との整合性、事実確認、含まれるHTMLリンクの適切性も厳しくチェックします。
文章の流れ、一貫性、正確性、文法、読みやすさ、独創性、そしてSEO最適化の観点から、最高品質の記事に仕上げることを目指します。
必要であれば `web_search` ツールでファクトチェックや追加情報を調査します。
最終的な成果物として、編集済みの完全なHTMLコンテンツを出力します。
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

