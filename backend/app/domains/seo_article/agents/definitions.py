# -*- coding: utf-8 -*-
# 既存のスクリプトからエージェント定義とプロンプト生成関数をここに移動・整理
from typing import Callable, Awaitable, Union
from agents import Agent, RunContextWrapper, ModelSettings
from datetime import datetime, timezone
# 循環参照を避けるため、モデル、ツール、コンテキストは直接インポートしない
# from .models import AgentOutput, ResearchQueryResult, ResearchReport, Outline, RevisedArticle
# from .tools import web_search_tool, analyze_competitors, get_company_data
# from .context import ArticleContext
from app.domains.seo_article.schemas import (
    ResearchQueryResult, ResearchReport, RevisedArticle, 
    GeneratedPersonasResponse, SerpKeywordAnalysisReport, 
    ArticleSectionWithImages, ThemeProposal, ClarificationNeeded,
    ResearchPlan, Outline
)
from app.domains.seo_article.agents.tools import web_search_tool
from app.domains.seo_article.context import ArticleContext
from app.core.config import settings # 設定をインポート
from app.domains.seo_article.schemas import PersonaType

# --- ヘルパー関数 ---

def get_current_date_context() -> str:
    """現在の日付コンテキストを取得"""
    try:
        now = datetime.now(timezone.utc)
        japan_time = now.astimezone()
        return f"現在の日時: {japan_time.strftime('%Y年%m月%d日')}"
    except Exception:
        return f"現在の日時: {datetime.now().strftime('%Y年%m月%d日')}"

def build_style_context(ctx: ArticleContext) -> str:
    """スタイルガイドコンテキストを構築（カスタムテンプレート優先）"""
    if hasattr(ctx, 'style_template_settings') and ctx.style_template_settings:
        # カスタムスタイルテンプレートが設定されている場合
        style_parts = ["=== カスタムスタイルガイド ==="]
        
        if ctx.style_template_settings.get('tone'):
            style_parts.append(f"トーン・調子: {ctx.style_template_settings['tone']}")
        
        if ctx.style_template_settings.get('style'):
            style_parts.append(f"文体: {ctx.style_template_settings['style']}")
        
        if ctx.style_template_settings.get('approach'):
            style_parts.append(f"アプローチ・方針: {ctx.style_template_settings['approach']}")
        
        if ctx.style_template_settings.get('vocabulary'):
            style_parts.append(f"語彙・表現の指針: {ctx.style_template_settings['vocabulary']}")
        
        if ctx.style_template_settings.get('structure'):
            style_parts.append(f"記事構成の指針: {ctx.style_template_settings['structure']}")
        
        if ctx.style_template_settings.get('special_instructions'):
            style_parts.append(f"特別な指示: {ctx.style_template_settings['special_instructions']}")
        
        style_parts.append("")
        style_parts.append("**重要: 上記のカスタムスタイルガイドに従って執筆してください。従来のデフォルトスタイルは適用せず、このカスタム設定を優先してください。**")
        
        return "\n".join(style_parts)
    
    elif hasattr(ctx, 'company_style_guide') and ctx.company_style_guide:
        # 従来の会社スタイルガイドがある場合
        return f"=== 会社スタイルガイド ===\n文体・トンマナ: {ctx.company_style_guide}"
    
    else:
        # デフォルトスタイル
        return "=== デフォルトスタイルガイド ===\n親しみやすく分かりやすい文章で、読者に寄り添うトーン。専門用語を避け、日本の一般的なブログやコラムのような自然で人間味あふれる表現を使用。"

def build_enhanced_company_context(ctx: ArticleContext) -> str:
    """拡張された会社情報コンテキストを構築"""
    if not hasattr(ctx, 'company_name') or not ctx.company_name:
        return "企業情報: 未設定（一般的な記事として作成）"
    
    company_parts = []
    
    # 基本情報
    company_parts.append(f"企業名: {ctx.company_name}")
    
    if hasattr(ctx, 'company_description') and ctx.company_description:
        company_parts.append(f"概要: {ctx.company_description}")
    
    if hasattr(ctx, 'company_usp') and ctx.company_usp:
        company_parts.append(f"USP・強み: {ctx.company_usp}")
    
    if hasattr(ctx, 'company_website_url') and ctx.company_website_url:
        company_parts.append(f"ウェブサイト: {ctx.company_website_url}")
    
    if hasattr(ctx, 'company_target_persona') and ctx.company_target_persona:
        company_parts.append(f"主要ターゲット: {ctx.company_target_persona}")
    
    # ブランディング情報
    if hasattr(ctx, 'company_brand_slogan') and ctx.company_brand_slogan:
        company_parts.append(f"ブランドスローガン: {ctx.company_brand_slogan}")
    
    # SEO・コンテンツ戦略
    if hasattr(ctx, 'company_target_keywords') and ctx.company_target_keywords:
        company_parts.append(f"重要キーワード: {ctx.company_target_keywords}")
    
    if hasattr(ctx, 'company_industry_terms') and ctx.company_industry_terms:
        company_parts.append(f"業界専門用語: {ctx.company_industry_terms}")
    
    if hasattr(ctx, 'company_avoid_terms') and ctx.company_avoid_terms:
        company_parts.append(f"避けるべき表現: {ctx.company_avoid_terms}")
    
    # コンテンツ参考情報
    if hasattr(ctx, 'company_popular_articles') and ctx.company_popular_articles:
        company_parts.append(f"人気記事参考: {ctx.company_popular_articles}")
    
    if hasattr(ctx, 'company_target_area') and ctx.company_target_area:
        company_parts.append(f"対象エリア: {ctx.company_target_area}")
    
    if hasattr(ctx, 'past_articles_summary') and ctx.past_articles_summary:
        company_parts.append(f"過去記事傾向: {ctx.past_articles_summary}")
    
    return "\n".join(company_parts)

# --- 動的プロンプト生成関数 ---
# (既存のスクリプトからコピーし、インポートパスを修正)

def create_theme_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        if not ctx.context.selected_detailed_persona:
            raise ValueError("テーマ提案のための詳細なペルソナが選択されていません。")
        persona_description = ctx.context.selected_detailed_persona
        
        # 拡張された会社情報コンテキストを使用
        company_info_str = build_enhanced_company_context(ctx.context)
        
        # 日付コンテキストを追加
        date_context = get_current_date_context()
        
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

{date_context}

--- 入力情報 ---
キーワード: {', '.join(ctx.context.initial_keywords)}
ターゲットペルソナ詳細:\n{persona_description}
提案するテーマ数: {ctx.context.num_theme_proposals}

=== 企業情報 ===
{company_info_str}

{seo_analysis_str}
---

**重要な注意事項:**
- 企業情報を活用して、その企業らしさが出るテーマを提案してください
- 日付情報を考慮し、季節やタイミングに適したコンテンツを提案してください
- 企業のターゲット顧客や強みを反映した独自性のあるアプローチを心がけてください

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

**重要なリサーチ指針:**
- 上記の検索クエリを使用して `web_search` ツールを実行してください。
- **権威ある情報源を最優先で活用してください**：
  * **Wikipedia（ja.wikipedia.org）**: 基礎情報、定義、概要
  * **政府機関・自治体サイト（.go.jp）**: 統計データ、公式見解、制度情報
  * **学術機関（.ac.jp）**: 研究データ、専門知識
  * **業界団体・公的機関**: 業界統計、ガイドライン
  * **大手メディア・新聞社**: ニュース、トレンド情報
  * **企業公式サイト**: 製品情報、サービス詳細
- 検索結果を**深く分析**し、記事テーマとクエリの焦点に関連する**具体的な情報、データ、主張、引用**などを**詳細に抽出**してください。
- 抽出した各情報について、**最も信頼性が高く具体的な出典元URLとそのタイトル**を特定し、`SourceSnippet` 形式でリスト化してください。上記の権威ある情報源からの情報を特に重視してください。
- 個人ブログやまとめサイト、広告的なコンテンツよりも、**公的機関、学術機関、業界の権威、著名メディア**からの情報を優先して選択してください。
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
            for finding in result.results:
                results_str += f"- 抜粋: {finding.snippet}\n"
                results_str += f"  出典: [{finding.title or finding.url}]({finding.url})\n"
                all_sources_set.add(finding.url) # URLをセットに追加
            results_str += "\n"

        sorted(list(all_sources_set)) # 重複削除してリスト化

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
        if ctx.context.company_name or ctx.context.company_description or ctx.context.company_style_guide:
            company_info_str = f"\nクライアント情報:\n  企業名: {ctx.context.company_name or '未設定'}\n  企業概要: {ctx.context.company_description or '未設定'}\n"
            if ctx.context.company_style_guide:
                company_info_str += f"  スタイルガイド（トンマナ）: {ctx.context.company_style_guide}\n"

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
- 上記のテーマと**詳細なリサーチ結果**、SerpAPI分析結果に基づいて、記事のアウトラインを作成してください。
- リサーチ結果の**キーポイント（出典情報も考慮）**や面白い切り口をアウトラインに反映させてください。
- **ターゲットペルソナ「{persona_description}」** が読みやすいように、記事全体のトーンを提案してください。{f'**クライアントのスタイルガイド（{ctx.context.company_style_guide}）に従って**' if ctx.context.company_style_guide else '日本の一般的なブログやコラムのような、**親しみやすく分かりやすいトーン**で'}トーンを決定してください。
- SerpAPI分析で判明した競合の弱点を補強し、差別化要素を強調した構成にしてください。
- あなたの応答は必ず `Outline` または `ClarificationNeeded` 型のJSON形式で出力してください。 (APIコンテキストではClarificationNeededはエラーとして処理)
- 文字数指定がある場合は、それに応じてセクション数や深さを調整してください。
"""
        return full_prompt
    return dynamic_instructions_func

def create_section_writer_with_images_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
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

        # スタイルガイドコンテキストを構築
        style_guide_context = build_style_context(ctx.context)

        full_prompt = f"""{base_prompt}

--- 記事全体の情報 ---
記事タイトル: {ctx.context.generated_outline.title}
記事全体のキーワード: {', '.join(ctx.context.selected_theme.keywords) if ctx.context.selected_theme else 'N/A'}
記事全体のトーン: {ctx.context.generated_outline.suggested_tone}
ターゲットペルソナ詳細:\n{persona_description}

{style_guide_context}
記事のアウトライン（全体像）:
{outline_context}
--- 詳細なリサーチ情報 ---
{research_context_str[:10000]}
{ "... (以下省略)" if len(research_context_str) > 10000 else "" }
---

--- **あなたの現在のタスク** ---
あなたは **セクションインデックス {target_index}**、見出し「**{target_heading}**」の内容をHTML形式で執筆するタスク**のみ**を担当します。
このセクションの目標文字数: {section_target_chars or '指定なし（流れに合わせて適切に）'}

**📌 重要: この記事は画像モードで生成されています。可能であれば画像プレースホルダーを含めてください。**
---

--- **【最重要】執筆スタイルとトーンについて** ---
あなたの役割は、単に情報をHTMLにするだけでなく、**まるで経験豊富な友人が以下のペルソナ「{persona_description}」に語りかけるように**、親しみやすく、分かりやすい文章でセクションを執筆することです。
- **日本の一般的なブログ記事やコラムのような、自然で人間味あふれる、温かいトーン**を心がけてください。堅苦しい表現や機械的な言い回しは避けてください。
- 読者に直接語りかけるような表現（例：「〜だと思いませんか？」「まずは〜から始めてみましょう！」「〜なんてこともありますよね」）や、共感を誘うような言葉遣いを積極的に使用してください。
- 専門用語は避け、どうしても必要な場合は簡単な言葉で補足説明を加えてください。箇条書きなども活用し、情報を整理して伝えると良いでしょう。
- 可能であれば、具体的な体験談（想像でも構いません）や、読者が抱きそうな疑問に答えるような形で内容を構成すると、より読者の心に響きます。
- 企業情報に記載された文体・トンマナ要件も必ず遵守してください。
---

--- **【画像プレースホルダーについて】** ---
このセクションでは、内容に応じて画像プレースホルダーを適切に配置してください。
画像プレースホルダーは以下の形式で記述してください:

```html
<!-- IMAGE_PLACEHOLDER: placeholder_id|日本語での画像説明|英語での画像生成プロンプト -->
```

例:
```html
<!-- IMAGE_PLACEHOLDER: living_room_01|札幌の住宅内装の写真。カラマツ無垢材の床や家具が暖かさを演出し、珪藻土の壁が柔らかな質感を醸し出している。薪ストーブが置かれ、冬も快適に過ごせる工夫が見られるリビングの様子。|A photo of a residential interior in Sapporo. The solid larch wood flooring and furniture create a warm atmosphere, while the diatomaceous earth walls add a soft texture. A wood-burning stove is placed in the living room, providing comfort and warmth during the winter months. -->
```

**具体例2：**
```html
<!-- IMAGE_PLACEHOLDER: section{target_index + 1}_img01|記事内容に関連する高品質で魅力的な写真の説明を日本語で記述|Detailed English prompt for generating a high-quality, professional image that directly relates to the section content, including specific details about colors, lighting, composition, and style -->
```

**📌 画像プレースホルダーは記事全体で最低1つ必要です。このセクションには必須ではありませんが、内容に合わせて適切に配置してください。**

画像プレースホルダーの配置ガイドライン:
1. **📌 推奨事項**: **画像モードでは、このセクションの内容に適した画像プレースホルダーを配置することを推奨します。ただし、記事全体で最低1つあれば十分です。**  
2. **適切なタイミング**: 長い文章の途中や、新しい概念を説明する前後に配置
3. **内容との関連性**: セクションの内容と直接関連する画像を想定
4. **ユーザー体験**: 読者の理解を助け、視覚的に魅力的になるような画像を想定
5. **placeholder_id**: セクション名と連番で一意になるように（例: section{target_index + 1}_img01, section{target_index + 1}_img02）
6. **英語プロンプト**: 具体的で詳細な描写を含む（色、材質、雰囲気、場所、人物、アクション、ライティングなど）
7. **数量**: セクションの長さに応じて1-3個程度が適切（ただし、必ず最低1つは含める）
8. **品質基準**: 説得力のある、プロフェッショナルで美しい画像を生成するための詳細なプロンプトを作成

---

--- 執筆ルール ---
1.  **提供される会話履歴（直前のセクションの内容など）と、上記「詳細なリサーチ情報」を十分に考慮し、** 前のセクションから自然につながるように、かつ、このセクション（インデックス {target_index}、見出し「{target_heading}」）の主題に沿った文章を作成してください。
2.  **リサーチ情報で示された事実やデータに基づいて執筆し、必要に応じて、信頼できる情報源（特に公式HPなど）へのHTMLリンク (`<a href="URL">リンクテキスト</a>`) を自然な形で含めてください。** リンクテキストは具体的に、例えば会社名やサービス名、情報の内容を示すものにしてください。ただし、過剰なリンクやSEOに不自然なリンクは避けてください。リサーチ情報に記載のない情報は含めないでください。
3.  他のセクションの内容は絶対に生成しないでください。
4.  必ず `<p>`, `<h2>`, `<h3>`, `<ul>`, `<li>`, `<strong>`, `<em>`, `<a>` などの基本的なHTMLタグを使用し、構造化されたコンテンツを生成してください。`<h2>` タグはこのセクションの見出し「{target_heading}」にのみ使用してください。
5.  SEOを意識し、記事全体のキーワードやこのセクションに関連するキーワードを**自然に**含めてください。（ただし、自然さを損なうような無理なキーワードの詰め込みは避けてください）
6.  上記の【執筆スタイルとトーンについて】の指示に従い、創造性を発揮し、読者にとって価値のあるオリジナルな文章を作成してください。
7.  **【📌 推奨事項】適切であれば画像プレースホルダーを配置してください。** 文章の流れを考慮し、読者の理解を助ける位置に配置することが重要です。記事全体で最低1つの画像プレースホルダーがあれば十分です。
---

--- **【最重要】出力形式について** ---
あなたの応答は**必ず** `ArticleSectionWithImages` 型のJSON形式で出力してください。
以下のフィールドを含む必要があります:
- `section_index`: {target_index}
- `heading`: "{target_heading}"
- `html_content`: 画像プレースホルダーを含むHTMLコンテンツ
- `image_placeholders`: 配置した画像プレースホルダーの詳細リスト

各画像プレースホルダーについて、以下の情報を `ImagePlaceholder` 形式で提供してください:
- `placeholder_id`: プレースホルダーの一意ID
- `description_jp`: 日本語での画像説明
- `prompt_en`: 英語での画像生成プロンプト
- `alt_text`: 画像のalt属性用テキスト
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

        # 拡張された会社情報コンテキストを使用
        company_info_str = build_enhanced_company_context(ctx.context)
        
        # スタイルガイドコンテキストを構築
        style_guide_context = build_style_context(ctx.context)
        
        # 日付コンテキストを追加
        date_context = get_current_date_context()

        full_prompt = f"""{base_prompt}

{date_context}

--- 記事全体の情報 ---
記事タイトル: {ctx.context.generated_outline.title}
記事全体のキーワード: {', '.join(ctx.context.selected_theme.keywords) if ctx.context.selected_theme else 'N/A'}
記事全体のトーン: {ctx.context.generated_outline.suggested_tone}
ターゲットペルソナ詳細:\n{persona_description}

=== 企業情報 ===
{company_info_str}

{style_guide_context}
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
- 企業情報に記載された文体・トンマナ要件も必ず遵守してください。
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

        # 拡張された会社情報コンテキストを使用
        company_info_str = build_enhanced_company_context(ctx.context)
        
        # スタイルガイドコンテキストを構築
        style_guide_context = build_style_context(ctx.context)
        
        # 日付コンテキストを追加
        date_context = get_current_date_context()

        full_prompt = f"""{base_prompt}

{date_context}

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

=== 企業情報 ===
{company_info_str}

{style_guide_context}
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
        if ctx.context.persona_type == PersonaType.OTHER and ctx.context.custom_persona:
            pass
        elif ctx.context.target_age_group and ctx.context.persona_type:
            pass
        elif ctx.context.custom_persona: # 移行措置
            pass
        
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

# 新しいエージェント: SerpAPIキーワード分析エージェント
SERP_KEYWORD_ANALYSIS_AGENT_BASE_PROMPT = """
あなたはSEOとキーワード分析の専門家です。
SerpAPIで取得されたGoogle検索結果と、上位記事のスクレイピング結果を詳細に分析し、以下を含む包括的なSEO戦略レポートを作成します：

1. 上位記事で頻出する主要テーマ・トピック
2. 共通して使用される見出しパターン・構成
3. 上位記事で不足している可能性のあるコンテンツ（コンテンツギャップ）
4. 差別化できる可能性のあるポイント
5. 検索ユーザーの意図分析（情報収集、比較検討、購入検討など）
6. コンテンツ戦略の推奨事項

あなたの分析結果は、後続の記事生成プロセス（ペルソナ生成、テーマ提案、アウトライン作成、執筆）において重要な参考資料として活用されます。
特に、ターゲットキーワードで上位表示を狙うために必要な要素を明確に特定し、実用的な戦略を提案してください。

あなたの応答は必ず `SerpKeywordAnalysisReport` 型のJSON形式で出力してください。
"""

def create_serp_keyword_analysis_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        # キーワードからSerpAPI分析を実行（この時点で実行）
        keywords = ctx.context.initial_keywords
        
        # SerpAPIサービスのインポートと実行
        from app.infrastructure.external_apis.serpapi_service import get_serpapi_service
        serpapi_service = get_serpapi_service()
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

serp_keyword_analysis_agent = Agent[ArticleContext](
    name="SerpKeywordAnalysisAgent",
    instructions=create_serp_keyword_analysis_instructions(SERP_KEYWORD_ANALYSIS_AGENT_BASE_PROMPT),
    model=settings.research_model,  # 分析タスクに適したモデル
    tools=[],  # SerpAPIサービスを直接使用するため、ツールは不要
    output_type=SerpKeywordAnalysisReport,
)

# --- エージェント定義 ---

# 1. テーマ提案エージェント
THEME_AGENT_BASE_PROMPT = """
あなたはSEO記事のテーマを考案する専門家です。
与えられたキーワード、ターゲットペルソナ、企業情報を分析し、読者の検索意図とSEO効果を考慮した上で、創造的で魅力的な記事テーマ案を複数生成します。
`web_search` ツールで関連トレンドや競合を調査できます。
情報が不足している場合は、ClarificationNeededを返してください。
"""
theme_agent = Agent[ArticleContext](
    name="ThemeAgent",
    instructions=create_theme_instructions(THEME_AGENT_BASE_PROMPT),
    model=settings.default_model,
    tools=[web_search_tool],
    output_type=Union[ThemeProposal, ClarificationNeeded],
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
    output_type=Union[ResearchPlan, ClarificationNeeded],
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
`web_search` ツールで競合記事の構成を調査し、差別化できる構成を考案します。
文字数指定に応じて、見出しの数や階層構造を適切に調整します。
ターゲットペルソナが読みやすいように、親しみやすく分かりやすいトーンで記事全体のトーンも提案してください。
"""
outline_agent = Agent[ArticleContext](
    name="OutlineAgent",
    instructions=create_outline_instructions(OUTLINE_AGENT_BASE_PROMPT),
    model=settings.writing_model,
    tools=[web_search_tool],
    output_type=Union[Outline, ClarificationNeeded],
)

# 6. セクション執筆エージェント
SECTION_WRITER_AGENT_BASE_PROMPT = """
あなたは指定された記事のセクション（見出し）に関する内容を執筆するプロのライターです。
あなたの役割は、日本の一般的なブログやコラムのように、自然で人間味あふれる、親しみやすい文章で、割り当てられた特定のセクションの内容をHTML形式で執筆することです。
記事全体のテーマ、アウトライン、キーワード、トーン、会話履歴（前のセクションを含む完全な文脈）、そして詳細なリサーチレポート（出典情報付き）に基づき、創造的かつSEOを意識して執筆してください。
リサーチ情報に基づき、必要に応じて信頼できる情報源へのHTMLリンクを自然に含めてください。
あなたのタスクは、指示された1つのセクションのHTMLコンテンツを生成することだけです。読者を引きつけ、価値を提供するオリジナルな文章を作成してください。
"""
section_writer_agent = Agent[ArticleContext](
    name="SectionWriterAgent",
    instructions=create_section_writer_instructions(SECTION_WRITER_AGENT_BASE_PROMPT),
    model=settings.writing_model,
    model_settings=ModelSettings(max_tokens=32768),  # 最大出力トークン数設定
    # output_type を削除 (構造化出力を強制しない)
)

# 6-2. 画像プレースホルダー対応セクション執筆エージェント
SECTION_WRITER_WITH_IMAGES_AGENT_BASE_PROMPT = """
あなたは指定された記事のセクション（見出し）に関する内容を執筆するプロのライターです。
あなたの役割は、日本の一般的なブログやコラムのように、自然で人間味あふれる、親しみやすい文章で、割り当てられた特定のセクションの内容をHTML形式で執筆することです。
**この記事は画像プレースホルダー機能を使用しており、記事全体で最低1つの画像プレースホルダーが必要です。このセクションでは内容に応じて適切に配置してください。**
記事全体のテーマ、アウトライン、キーワード、トーン、会話履歴（前のセクションを含む完全な文脈）、そして詳細なリサーチレポート（出典情報付き）に基づき、創造的かつSEOを意識して執筆してください。
リサーチ情報に基づき、必要に応じて信頼できる情報源へのHTMLリンクを自然に含めてください。
画像プレースホルダーは読者の理解を助け、視覚的に魅力的な記事にするために重要な要素です。
あなたのタスクは、指示された1つのセクションのHTMLコンテンツと画像プレースホルダー情報を生成することです。読者を引きつけ、価値を提供するオリジナルな文章を作成してください。
"""
section_writer_with_images_agent = Agent[ArticleContext](
    name="SectionWriterWithImagesAgent",
    instructions=create_section_writer_with_images_instructions(SECTION_WRITER_WITH_IMAGES_AGENT_BASE_PROMPT),
    model=settings.writing_model,
    model_settings=ModelSettings(max_tokens=32768),  # 最大出力トークン数設定
    output_type=ArticleSectionWithImages,
)

# 7. 推敲・編集エージェント
EDITOR_AGENT_BASE_PROMPT = """
あなたはプロの編集者兼SEOスペシャリストです。
与えられた記事ドラフト（HTML形式）を、記事の要件（テーマ、キーワード、ペルソナ、文字数、トーン、スタイルガイド）と詳細なリサーチレポート（出典情報付き）を照らし合わせながら、徹底的にレビューし、推敲・編集します。
特に、文章全体がターゲットペルソナにとって自然で、親しみやすく、分かりやすい言葉遣いになっているか を重点的に確認し、機械的な表現があれば人間味のある表現に修正してください。
リサーチ情報との整合性、事実確認、含まれるHTMLリンクの適切性も厳しくチェックします。
文章の流れ、一貫性、正確性、文法、読みやすさ、独創性、そしてSEO最適化の観点から、最高品質の記事に仕上げることを目指します。
必要であれば `web_search` ツールでファクトチェックや追加情報を調査します。

**重要な制約事項:**
- JSON出力時は、HTMLコンテンツ内のダブルクォート（"）をエスケープし、改行は\\nで表現する
- 完全で有効なJSONフォーマットで出力することを厳守する

最終的な成果物として、編集済みの完全なHTMLコンテンツを出力します。
"""
editor_agent = Agent[ArticleContext](
    name="EditorAgent",
    instructions=create_editor_instructions(EDITOR_AGENT_BASE_PROMPT),
    model=settings.editing_model,
    model_settings=ModelSettings(max_tokens=32768),  # 最大出力トークン数設定
    tools=[web_search_tool],
    output_type=RevisedArticle, # 修正: RevisedArticleを返す
)

# LiteLLMエージェント生成関数 (APIでは直接使わないかもしれないが、念のため残す)
# 必要に応じてAPIキーの取得方法などを修正する必要がある
# def get_litellm_agent(...) -> Optional[Agent]: ... (実装は省略)

