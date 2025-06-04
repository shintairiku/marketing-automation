# -*- coding: utf-8 -*-
from typing import Callable, Awaitable
from agents import Agent, RunContextWrapper
from services.context import ArticleContext
from schemas.request import PersonaType


def create_theme_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        if not ctx.context.selected_detailed_persona:
            raise ValueError("テーマ提案のための詳細なペルソナが選択されていません。")
        persona_description = ctx.context.selected_detailed_persona
        company_info_str = f"企業名: {ctx.context.company_name}\n概要: {ctx.context.company_description}\n文体ガイド: {ctx.context.company_style_guide}\n過去記事傾向: {ctx.context.past_articles_summary}" if ctx.context.company_name else "企業情報なし"
        
        # SerpAPI分析結果を含める
        seo_analysis_str = ""
        if ctx.context.serp_analysis_report:
            seo_analysis_str = f"""

=== SerpAPI競合分析結果 ===
検索クエリ: {ctx.context.serp_analysis_report.search_query}
競合記事数: {len(ctx.context.serp_analysis_report.analyzed_articles)}
推奨文字数: {ctx.context.serp_analysis_report.recommended_target_length}文字

主要テーマ（競合頻出）: {', '.join(ctx.context.serp_analysis_report.main_themes)}
共通見出し: {', '.join(ctx.context.serp_analysis_report.common_headings[:8])}
コンテンツギャップ: {', '.join(ctx.context.serp_analysis_report.content_gaps)}
差別化ポイント: {', '.join(ctx.context.serp_analysis_report.competitive_advantages)}
検索意図: {ctx.context.serp_analysis_report.user_intent_analysis}

戦略推奨: {', '.join(ctx.context.serp_analysis_report.content_strategy_recommendations[:5])}

上記の競合分析を活用し、検索上位を狙える差別化されたテーマを提案してください。
"""
        
        full_prompt = f"""{base_prompt}

--- 入力情報 ---
キーワード: {', '.join(ctx.context.initial_keywords)}
ターゲットペルソナ詳細:\n{persona_description}
提案するテーマ数: {ctx.context.num_theme_proposals}
企業情報:\n{company_info_str}
{seo_analysis_str}
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

        # SerpAPI分析結果を含める
        seo_guidance_str = ""
        if ctx.context.serp_analysis_report:
            seo_guidance_str = f"""

=== SerpAPI分析ガイダンス ===
競合記事の主要テーマ: {', '.join(ctx.context.serp_analysis_report.main_themes)}
コンテンツギャップ（調査すべき領域）: {', '.join(ctx.context.serp_analysis_report.content_gaps)}
差別化ポイント: {', '.join(ctx.context.serp_analysis_report.competitive_advantages)}
検索ユーザーの意図: {ctx.context.serp_analysis_report.user_intent_analysis}

上記の分析結果を踏まえ、競合が扱っていない角度や、より深く掘り下げるべき領域を重点的にリサーチしてください。
"""

        full_prompt = f"""{base_prompt}

--- リサーチ対象テーマ ---
タイトル: {ctx.context.selected_theme.title}
説明: {ctx.context.selected_theme.description}
キーワード: {', '.join(ctx.context.selected_theme.keywords)}
ターゲットペルソナ詳細:\n{persona_description}
{seo_guidance_str}
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

        # SerpAPI分析結果を含める
        seo_structure_guidance = ""
        if ctx.context.serp_analysis_report:
            seo_structure_guidance = f"""

=== SerpAPI構成戦略ガイダンス ===
競合共通見出しパターン: {', '.join(ctx.context.serp_analysis_report.common_headings)}
推奨文字数: {ctx.context.serp_analysis_report.recommended_target_length}文字
コンテンツギャップ（新規追加推奨）: {', '.join(ctx.context.serp_analysis_report.content_gaps)}
差別化ポイント: {', '.join(ctx.context.serp_analysis_report.competitive_advantages)}
コンテンツ戦略: {', '.join(ctx.context.serp_analysis_report.content_strategy_recommendations)}

上記を参考に、競合に勝る構成を設計してください。共通見出しは参考程度に留め、差別化要素を強く反映したアウトラインを作成してください。
"""

        full_prompt = f"""{base_prompt}

--- 入力情報 ---
選択されたテーマ:
  タイトル: {ctx.context.selected_theme.title}
  説明: {ctx.context.selected_theme.description}
  キーワード: {', '.join(ctx.context.selected_theme.keywords)}
ターゲット文字数: {ctx.context.target_length or '指定なし（標準的な長さで）'}
ターゲットペルソナ詳細:\n{persona_description}
{company_info_str}
{seo_structure_guidance}
--- 詳細なリサーチ結果 ---
{research_summary}
参照した全情報源URL数: {len(ctx.context.research_report.all_sources)}
---

**重要:**
- 上記のテーマと**詳細なリサーチ結果**、そして競合分析の結果（ツール使用）に基づいて、記事のアウトラインを作成してください。
- リサーチ結果の**キーポイント（出典情報も考慮）**や面白い切り口をアウトラインに反映させてください。
- **ターゲットペルソナ「{persona_description}」** が読みやすいように、日本の一般的なブログやコラムのような、**親しみやすく分かりやすいトーン**でアウトラインを作成してください。記事全体のトーンも提案してください。
- SerpAPI分析で判明した競合の弱点を補強し、差別化要素を強調した構成にしてください。
- あなたの応答は必ず `Outline` または `ClarificationNeeded` 型のJSON形式で出力してください。 (APIコンテキストではClarificationNeededはエラーとして処理)
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

def create_persona_generator_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        initial_persona_description = "指定なし"
        if ctx.context.persona_type == PersonaType.OTHER and ctx.context.custom_persona:
            initial_persona_description = ctx.context.custom_persona
        elif ctx.context.target_age_group and ctx.context.persona_type:
            initial_persona_description = f"{ctx.context.target_age_group.value}の{ctx.context.persona_type.value}"
        elif ctx.context.custom_persona:
            initial_persona_description = ctx.context.custom_persona

        company_info_str = ""
        if ctx.context.company_name or ctx.context.company_description:
            company_info_str = f"\nクライアント企業名: {ctx.context.company_name or '未設定'}\nクライアント企業概要: {ctx.context.company_description or '未設定'}"

        full_prompt = f"""{base_prompt}

--- 入力情報 ---
SEOキーワード: {', '.join(ctx.context.initial_keywords)}
ターゲット年代: {ctx.context.target_age_group.value if ctx.context.target_age_group else '指定なし'}
ペルソナ属性（大分類）: {ctx.context.persona_type.value if ctx.context.persona_type else '指定なし'}
(上記属性が「その他」の場合のユーザー指定ペルソナ: {ctx.context.custom_persona if ctx.context.persona_type == PersonaType.OTHER else '該当なし'})
生成する具体的なペルソナの数: {ctx.context.num_persona_examples}
{company_info_str}
---

あなたのタスクは、上記入力情報に基づいて、より具体的で詳細なペルソナ像を **{ctx.context.num_persona_examples}個** 生成することです。
各ペルソナは、`GeneratedPersonaItem` の形式で、`id` (0から始まるインデックス) と `description` を含めてください。
"""
        return full_prompt
    return dynamic_instructions_func


# 新しいエージェント: ペルソナ生成エージェント
def create_serp_keyword_analysis_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        # キーワードからSerpAPI分析を実行（この時点で実行）
        keywords = ctx.context.initial_keywords
        
        # SerpAPIサービスのインポートと実行
        from services.serpapi_service import serpapi_service
        analysis_result = await serpapi_service.analyze_keywords(keywords, num_articles_to_scrape=5)
        
        # 分析データを文字列に整理
        articles_summary = ""
        for i, article in enumerate(analysis_result.scraped_articles):
            articles_summary += f"""
記事 {i+1}:
- タイトル: {article.title}
- URL: {article.url}
- 文字数: {article.char_count}
- 画像数: {article.image_count}
- 取得元: {article.source_type}
{f"- 検索順位: {article.position}" if article.position else ""}
{f"- 関連質問: {article.question}" if article.question else ""}
- 見出し構成:
{chr(10).join(f"  * {heading}" for heading in article.headings)}
- 本文プレビュー: {article.content[:200]}...

"""
        
        related_questions_str = ""
        if analysis_result.related_questions:
            related_questions_str = "関連質問:\n"
            for i, q in enumerate(analysis_result.related_questions):
                related_questions_str += f"  {i+1}. {q.get('question', 'N/A')}\n"
        
        full_prompt = f"""{base_prompt}

--- SerpAPI分析データ ---
検索クエリ: {analysis_result.search_query}
検索結果総数: {analysis_result.total_results:,}
分析対象記事数: {len(analysis_result.scraped_articles)}
平均文字数: {analysis_result.average_char_count}
推奨目標文字数: {analysis_result.suggested_target_length}

{related_questions_str}

--- 上位記事詳細分析データ ---
{articles_summary}

--- あなたのタスク ---
上記のSerpAPI分析結果を基に、以下の項目を含む包括的なSEO戦略レポートを作成してください：

1. main_themes: 上位記事で頻出する主要テーマ・トピック（5-8個程度）
2. common_headings: 共通して使用される見出しパターン（5-10個程度）
3. content_gaps: 上位記事で不足している可能性のあるコンテンツ（3-5個程度）
4. competitive_advantages: 差別化できる可能性のあるポイント（3-5個程度）
5. user_intent_analysis: 検索ユーザーの意図分析（詳細な文章で）
6. content_strategy_recommendations: コンテンツ戦略の推奨事項（5-8個程度）

**必須フィールド**: あなたの応答には以下の情報を必ず含めてください：
- search_query: "{analysis_result.search_query}"
- total_results: {analysis_result.total_results}
- average_article_length: {analysis_result.average_char_count}
- recommended_target_length: {analysis_result.suggested_target_length}
- analyzed_articles: 分析した記事のリスト（以下の形式で各記事を記述）
  [
    {{
      "url": "記事URL",
      "title": "記事タイトル", 
      "headings": ["見出し1", "見出し2", ...],
      "content_preview": "記事内容のプレビュー",
      "char_count": 文字数,
      "image_count": 画像数,
      "source_type": "organic_result" または "related_question",
      "position": 順位（該当する場合）,
      "question": "関連質問"（該当する場合）
    }}, ...
  ]

特に、分析した記事の見出し構成、文字数、扱っているトピックの傾向を詳しく分析し、競合に勝るコンテンツを作成するための戦略を提案してください。
"""
        return full_prompt
    return dynamic_instructions_func
