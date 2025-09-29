# -*- coding: utf-8 -*-
# 既存のスクリプトからエージェント定義とプロンプト生成関数をここに移動・整理
from typing import Callable, Awaitable, Union, Any, List, Dict
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
    """会社情報コンテキストを構築（テーマ関連性を重視した簡潔版）"""
    if not hasattr(ctx, 'company_name') or not ctx.company_name:
        return "企業情報: 未設定（一般的な記事として作成）"

    company_parts = []

    # 基本情報（簡潔に）
    company_parts.append(f"企業名: {ctx.company_name}")
    company_parts.append("\n※ 以下の企業情報は、テーマに直接関連し企業の専門分野に該当する場合のみ参考としてください※")
    
    # 最重要な情報のみ簡潔に表示
    if hasattr(ctx, 'company_description') and ctx.company_description:
        company_parts.append(f"概要: {ctx.company_description[:100]}...")  # 文字数制限

    if hasattr(ctx, 'company_usp') and ctx.company_usp:
        company_parts.append(f"専門分野: {ctx.company_usp[:80]}...")  # USPではなく専門分野として表現

    # 避けるべき表現のみ表示（重要）
    if hasattr(ctx, 'company_avoid_terms') and ctx.company_avoid_terms:
        company_parts.append(f"避けるべき表現: {ctx.company_avoid_terms}")
    
    company_parts.append("\n※重要: 上記企業情報はテーマに直接関連する場合のみ参考とし、テーマと無関係な内容は一切反映しないでください※")

    return "\n".join(company_parts)

# --- 動的プロンプト生成関数 ---
# (既存のスクリプトからコピーし、インポートパスを修正)

def create_theme_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        if not ctx.context.selected_detailed_persona:
            raise ValueError("テーマ提案のための詳細なペルソナが選択されていません。")
        persona_description = ctx.context.selected_detailed_persona
        outline_top_level = getattr(ctx.context, 'outline_top_level_heading', 2) or 2
        if outline_top_level not in (2, 3):
            outline_top_level = 2
        child_heading_level = min(outline_top_level + 1, 6)
        advanced_outline_mode = getattr(ctx.context, 'advanced_outline_mode', False)
        
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
想定読者の詳細:\n{persona_description}
提案するテーマ数: {ctx.context.num_theme_proposals}

{seo_analysis_str}

=== 企業情報（参考用） ===
{company_info_str}
---

**重要なバランス指針:**
- **検索意図を最優先（重要度85%）**: キーワードと読者ニーズに厳密に合致した実用的なテーマを提案
- **企業情報は最小限の参考（重要度15%）**: テーマに直接関連し自然に組み込める場合のみ軽く反映
- 日付情報を考慮し、季節やタイミングに適したコンテンツを提案してください
- **厳格な制限事項**: 提供されたキーワードとSerpAPI分析結果に含まれない概念・用語は一切追加しない

**テーマ提案の優先順位:**
1. 検索ユーザーが求める実用的な情報価値（最重要）
2. キーワードとSerpAPI分析結果との厳密な関連性
3. ターゲット読者の具体的な悩み・関心事
4. 企業の専門分野に該当する場合のみ、軽微な関連性の反映

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

        # 企業情報（拡張）
        company_info_str = build_enhanced_company_context(ctx.context)

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
想定読者の詳細:\n{persona_description}

{seo_guidance_str}

=== 企業情報（参考用・制限的使用） ===
{company_info_str}
---

**リサーチ計画の厳格な指針:**
- **テーマ完全一致原則（最優先）**: 選択されたテーマのタイトル、説明、キーワードに厳密に一致する情報のみをリサーチ対象とする
- **検索意図専念（90%）**: 読者がそのキーワードで求める情報のみを収集
- **企業情報は最小限（10%）**: テーマに直接的に関連し、かつ企業の専門領域に該当する場合のみ考慮
- **絶対禁止事項**: テーマ、キーワード、SerpAPI分析結果に含まれないいかなる概念や用語もリサーチクエリに含めない

**検索クエリ生成の厳密な基準:**
1. テーマタイトルとキーワードに直結する基礎情報・定義
2. 読者がそのキーワードで求める具体的な疑問・悩みへの答え
3. テーマに完全一致する実践的なノウハウ・手順
4. テーマキーワードに直接関連する統計データ・事例のみ
5. テーマ範囲内での比較・選択肢のみ

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

        # 企業情報（拡張）
        company_info_str = build_enhanced_company_context(ctx.context)

        full_prompt = f"""{base_prompt}

--- 現在のリサーチタスク ---
記事テーマ: {ctx.context.research_plan.topic}
今回の検索クエリ: "{current_query.query}"
このクエリの焦点: {current_query.focus}
\n
=== 企業情報 ===
{company_info_str}
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

def create_research_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        if not ctx.context.selected_theme:
            raise ValueError("リサーチ計画を作成するためのテーマが選択されていません。")
        if not ctx.context.selected_detailed_persona:
            raise ValueError("リサーチ計画のための詳細なペルソナが選択されていません。")
        persona_description = ctx.context.selected_detailed_persona

        # 企業情報（拡張）
        company_info_str = build_enhanced_company_context(ctx.context)

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
想定読者の詳細:\n{persona_description}

{seo_guidance_str}

=== 企業情報（参考用・制限的使用） ===
{company_info_str}
---

**検索クエリ生成の厳密な基準:**
1. テーマタイトルとキーワードに直結する基礎情報・定義
2. 読者がそのキーワードで求める具体的な疑問・悩みへの答え
3. テーマに完全一致する実践的なノウハウ・手順
4. テーマキーワードに直接関連する統計データ・事例のみ
5. テーマ範囲内での比較・選択肢のみ

**重要:**
- 上記テーマについて深く掘り下げるための、具体的で多様な検索クエリを **{ctx.context.num_research_queries}個** 生成してください。
- 各クエリには、そのクエリで何を明らかにしたいか（focus）を明確に記述してください。

**重要なリサーチ指針:**
- 生成した検索クエリを使用して `web_search` ツールを実行してください。
- **権威ある情報源を最優先で活用してください**：
  * **Wikipedia（ja.wikipedia.org）**: 基礎情報、定義、概要
  * **政府機関・自治体サイト（.go.jp）**: 統計データ、公式見解、制度情報
  * **学術機関（.ac.jp）**: 研究データ、専門知識
  * **業界団体・公的機関**: 業界統計、ガイドライン
  * **大手メディア・新聞社**: ニュース、トレンド情報
  * **企業公式サイト**: 製品情報、サービス詳細
- 検索結果を**深く分析**し、記事テーマとクエリの焦点に関連する**具体的な情報、データ、主張、引用**などを**詳細に抽出**してください。
- 個人ブログやまとめサイト、広告的なコンテンツよりも、**公的機関、学術機関、業界の権威、著名メディア**からの情報を優先して選択してください。
- 検索結果全体の**簡潔な要約 (summary)** も生成してください。
- **`save_research_snippet` ツールは使用しないでください。**

**重要なリサーチ結果要約指針:**
- 上記の詳細なリサーチ結果全体を分析し、記事執筆に役立つように情報を統合・要約してください。
- 以下の要素を含む**実用的で詳細なリサーチレポート**を作成してください:
    - `overall_summary`: リサーチ全体から得られた主要な洞察やポイントの要約。
    - `key_points`: 記事に含めるべき重要なポイントや事実をリスト形式で記述し、各ポイントについて**それを裏付ける情報源URL (`supporting_sources`)** を `KeyPoint` 形式で明確に紐付けてください。
    - `interesting_angles`: 記事を面白くするための切り口や視点のアイデアのリスト形式。
    - `all_sources`: 参照した全ての情報源URLのリスト（重複削除済み、可能であれば重要度順）。
- レポートは論文調ではなく、記事作成者がすぐに使えるような分かりやすい言葉で記述してください。
- あなたの応答は必ず `ResearchReport` 型のJSON形式で出力してください。

検索クエリの作成、リサーチの実行はすべて上記の指針に従って厳格に行い、内部で実行してください。
出力は必ず `ResearchReport` 型のJSON形式のみで行ってください。リサーチ計画や実行は内部で完結させ、他のテキストは一切含めないでください。

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
        outline_top_level = getattr(ctx.context, 'outline_top_level_heading', 2) or 2
        if outline_top_level not in (2, 3):
            outline_top_level = 2
        child_heading_level = min(outline_top_level + 1, 6)
        advanced_outline_mode = getattr(ctx.context, 'advanced_outline_mode', False)

        research_summary = ctx.context.research_report.overall_summary
        # 企業情報（拡張）
        company_info_block = f"""

=== 企業情報 ===
{build_enhanced_company_context(ctx.context)}
"""

        # SerpAPI分析結果を含める
        seo_structure_guidance = ""
        if ctx.context.serp_analysis_report:
            # 上位記事の具体的な見出し一覧を取得
            specific_headings_list = ""
            if hasattr(ctx.context.serp_analysis_report, 'analyzed_articles') and ctx.context.serp_analysis_report.analyzed_articles:
                specific_headings_list = "\n=== 上位記事の具体的な見出し一覧（参考用） ===\n"
                for i, article_data in enumerate(ctx.context.serp_analysis_report.analyzed_articles[:3]):  # 上位3記事
                    if isinstance(article_data, dict) and 'headings' in article_data:
                        specific_headings_list += f"\n【記事{i+1}】{article_data.get('title', 'N/A')}\n"
                        for heading in article_data['headings'][:10]:  # 各記事の上位10見出し
                            specific_headings_list += f"  • {heading}\n"
                specific_headings_list += "\n上記見出しを参考に、独自性を保ちながら効果的な構成を設計してください。\n"
            
            seo_structure_guidance = f"""

=== SerpAPI構成戦略ガイダンス ===
競合共通見出しパターン: {', '.join(ctx.context.serp_analysis_report.common_headings)}
推奨文字数: {ctx.context.serp_analysis_report.recommended_target_length}文字
コンテンツギャップ（新規追加推奨）: {', '.join(ctx.context.serp_analysis_report.content_gaps)}
差別化ポイント: {', '.join(ctx.context.serp_analysis_report.competitive_advantages)}
コンテンツ戦略: {', '.join(ctx.context.serp_analysis_report.content_strategy_recommendations)}
{specific_headings_list}
上記の競合分析を参考に、競合記事を上回る価値を提供できる独自の構成を設計してください。
競合見出しの模倣ではなく、差別化要素を強く反映したアウトラインを作成してください。
"""

        if advanced_outline_mode:
            subheading_requirement = (
                f"- 各トップレベル見出し（`level` = {outline_top_level}）には、H{child_heading_level} に相当する `subsections` を1つ以上追加し、論点を段階的に展開してください。"
            )
        else:
            subheading_requirement = (
                f"- 必要に応じて `subsections` フィールドで小見出し（`level` >= {child_heading_level}）を追加できます。"
            )

        full_prompt = f"""{base_prompt}

--- 入力情報 ---
選択されたテーマ:
  タイトル: {ctx.context.selected_theme.title}
  説明: {ctx.context.selected_theme.description}
  キーワード: {', '.join(ctx.context.selected_theme.keywords)}
ターゲット文字数: {ctx.context.target_length or '指定なし（標準的な長さで）'}
想定読者の詳細:\n{persona_description}
アウトラインのトップレベル見出し指定: H{outline_top_level}
{company_info_block}
{seo_structure_guidance}
--- 詳細なリサーチ結果 ---
{research_summary}
参照した全情報源URL数: {len(ctx.context.research_report.all_sources)}
---

--- アウトライン構造の要件 ---
- トップレベル見出しは `level`: {outline_top_level}（HTMLでは <h{outline_top_level}>）として出力し、`heading` に見出しテキストを設定してください。
{subheading_requirement}
- 各見出しには `estimated_chars`（推定文字数）を必ず設定し、必要に応じて `description` で補足を加えてください。
- ルートのJSONには `top_level_heading` フィールドを含め、値を {outline_top_level} としてください。
- 返却形式の例:
```json
{{
  "title": "サンプル記事タイトル",
  "suggested_tone": "丁寧で読みやすい解説調",
  "top_level_heading": {outline_top_level},
  "sections": [
    {{
      "heading": "メイン見出し例",
      "level": {outline_top_level},
      "description": "このセクションで伝える核となるメッセージ",
      "estimated_chars": 400,
      "subsections": [
        {{
          "heading": "小見出し例",
          "level": {child_heading_level},
          "description": "詳細トピックや補足説明",
          "estimated_chars": 200
        }}
      ]
    }}
  ]
}}
```

**重要な構成指針:**
- **リサーチ結果を絶対優先（重要度90%）**: テーマとキーワード、SerpAPI分析、リサーチ結果に厳密に基づく構成
- **企業情報は最小限の参考（重要度10%）**: テーマに直接的に関連し企業の専門領域に該当する場合のみ軽微に反映
- **テーマ完全一致原則**: 選択されたテーマのタイトル、説明、キーワードから一切逸脱しない
- **厳格な制限事項**: テーマ、キーワード、リサーチ結果に含まれないいかなる概念や用語も構成に含めない

**アウトライン作成の厳密な基準:**
1. テーマキーワードとリサーチ結果の**キーポイント**に完全一致する構成のみ作成
2. **想定読者「{persona_description}」**がそのキーワードで求める情報のみを構成に含める
3. スタイルガイドに従いつつ、テーマに集中したトーン設定
4. SerpAPI分析結果とテーマに完全一致する差別化要素のみ反映
5. 文字数指定に応じたセクション構成（テーマの範囲内で）

**重要:**
- あなたの応答は必ず `Outline` または `ClarificationNeeded` 型のJSON形式で出力してください。 (APIコンテキストではClarificationNeededはエラーとして処理)
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

        def get_value(item: Any, key: str, default: Any = None) -> Any:
            if isinstance(item, dict):
                return item.get(key, default)
            return getattr(item, key, default)

        target_heading = get_value(target_section, 'heading', '')
        outline_top_level = getattr(ctx.context.generated_outline, 'top_level_heading', 2) or 2
        target_level = get_value(target_section, 'level', outline_top_level)
        if not isinstance(target_level, int):
            target_level = outline_top_level
        target_level = max(2, min(target_level, 6))
        
        section_target_chars = None
        if ctx.context.target_length and len(ctx.context.generated_outline.sections) > 0:
            total_sections = len(ctx.context.generated_outline.sections)
            estimated_total_body_chars = ctx.context.target_length * 0.8
            section_target_chars = int(estimated_total_body_chars / total_sections)

        default_child_level = min(target_level + 1, 6)

        raw_subsections = get_value(target_section, 'subsections', []) or []
        target_subsections: List[Dict[str, Any]] = []
        for sub in raw_subsections:
            sub_heading = get_value(sub, 'heading', '').strip()
            if not sub_heading:
                continue
            sub_level = get_value(sub, 'level', default_child_level)
            if not isinstance(sub_level, int):
                sub_level = default_child_level
            sub_level = max(target_level + 1, min(sub_level, 6))
            sub_description = get_value(sub, 'description', '') or ''
            target_subsections.append({
                'heading': sub_heading,
                'level': sub_level,
                'description': sub_description
            })

        subsection_heading_tags = {f"h{sub['level']}" for sub in target_subsections}
        subheading_plan_lines = [
            f"- H{sub['level']} {sub['heading']}" + (f"：{sub['description']}" if sub['description'] else '')
            for sub in target_subsections
        ]
        if subheading_plan_lines:
            subheading_prompt_block = (
                "\n--- このセクションで必ず使用する小見出し ---\n"
                "下記の順序で小見出しを組み込み、それぞれの見出しに対応する内容を十分に書いてください。\n"
                + "\n".join(subheading_plan_lines)
                + "\n---\n\n"
            )
        else:
            subheading_prompt_block = "\n"

        def format_outline_sections(sections: Any, prefix: str = "") -> List[str]:
            lines: List[str] = []
            for idx, section in enumerate(sections or []):
                heading = get_value(section, 'heading', '').strip()
                if not heading:
                    continue
                level = get_value(section, 'level', outline_top_level)
                if not isinstance(level, int):
                    level = outline_top_level
                level = max(2, min(level, 6))
                label = f"{prefix}{idx + 1}"
                lines.append(f"{label}. H{level} {heading}")
                children = get_value(section, 'subsections', []) or []
                for child_idx, child in enumerate(children):
                    child_heading = get_value(child, 'heading', '').strip()
                    if not child_heading:
                        continue
                    child_level = get_value(child, 'level', min(level + 1, 6))
                    if not isinstance(child_level, int):
                        child_level = min(level + 1, 6)
                    child_level = max(level + 1, min(child_level, 6))
                    lines.append(f"{label}.{child_idx + 1}. H{child_level} {child_heading}")
            return lines

        outline_context = "\n".join(format_outline_sections(ctx.context.generated_outline.sections))

        research_context_str = f"リサーチ要約: {ctx.context.research_report.overall_summary[:500]}...\n"
        research_context_str += "主要なキーポイント:\n"
        for kp in ctx.context.research_report.key_points:
            research_context_str += f"- {kp.point}\n"

        # 企業情報（拡張）とスタイルガイドコンテキスト
        company_info_str = build_enhanced_company_context(ctx.context)
        # スタイルガイドコンテキストを構築
        style_guide_context = build_style_context(ctx.context)

        main_heading_tag = f"h{target_level}"
        sorted_subheading_tags = sorted(subsection_heading_tags)
        if sorted_subheading_tags:
            child_heading_instruction_text = (
                "指定された小見出しには "
                + ", ".join(f"`<{tag}>`" for tag in sorted_subheading_tags)
                + " を使用し、提示された順序で配置し、追加の見出しレベルは作成しないでください。"
            )
        else:
            child_heading_instruction_text = (
                f"必要に応じて `<h{default_child_level}>` で論点を整理できますが、不要な見出しは追加しないでください。"
            )

        full_prompt = f"""{base_prompt}

--- 記事全体の情報 ---
記事タイトル: {ctx.context.generated_outline.title}
記事全体のキーワード: {', '.join(ctx.context.selected_theme.keywords) if ctx.context.selected_theme else 'N/A'}
記事全体のトーン: {ctx.context.generated_outline.suggested_tone}
想定読者の詳細:\n{persona_description}

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
使用するメイン見出しタグ: <{main_heading_tag}>
このセクションの目標文字数: {section_target_chars or '指定なし（流れに合わせて適切に）'}
{subheading_prompt_block}

**📌 重要: この記事は画像モードで生成されています。可能であれば画像プレースホルダーを含めてください。**
---

--- **【最重要】執筆スタイルとトーンについて** ---
あなたの役割は、単に情報をHTMLにするだけでなく、**まるで経験豊富な友人が以下の読者像の方に語りかけるように**、親しみやすく、分かりやすい文章でセクションを執筆することです：
「{persona_description}」

- **日本の一般的なブログ記事やコラムのような、自然で人間味あふれる、温かいトーン**を心がけてください。堅苦しい表現や機械的な言い回しは避けてください。
- 読者に直接語りかけるような表現（例：「〜だと思いませんか？」「まずは〜から始めてみましょう！」「〜なんてこともありますよね」）や、共感を誘うような言葉遣いを積極的に使用してください。
- 専門用語は避け、どうしても必要な場合は簡単な言葉で補足説明を加えてください。箇条書きなども活用し、情報を整理して伝えると良いでしょう。
- 可能であれば、具体的な体験談（想像でも構いません）や、読者が抱きそうな疑問に答えるような形で内容を構成すると、より読者の心に響きます。
- 企業情報に記載された文体・トンマナ要件も必ず遵守してください。

**重要な注意事項:**
- 記事内では「ペルソナ」という用語を一切使用しないでください
- 読者を指す場合は「皆さん」「読者の方」「お客様」「ご家庭」「ご家族」など自然な表現を使用してください
- システム用語（ペルソナ、ターゲット、SEO等）は記事本文に含めないでください
---

--- **【画像プレースホルダーについて】** ---
このセクションでは、内容に応じて画像プレースホルダーを必ず適切に配置してください。
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
1. **📌 必須事項**: **画像モードでは、このセクションの内容に適した画像プレースホルダーを配置することを推奨します。**  
2. **適切なタイミング**: 長い文章の途中や、新しい概念を説明する前後に配置
3. **内容との関連性**: セクションの内容と直接関連する画像を想定
4. **ユーザー体験**: 読者の理解を助け、視覚的に魅力的になるような画像を想定
5. **placeholder_id**: セクション名と連番で一意になるように（例: section{target_index + 1}_img01, section{target_index + 1}_img02）
6. **英語プロンプト**: 具体的で詳細な描写を含む（色、材質、雰囲気、場所、人物、アクション、ライティングなど）
7. **品質基準**: 説得力のある、プロフェッショナルで美しい画像を生成するための詳細なプロンプトを作成

---

--- 執筆ルール ---
1.  **記事の一貫性と構造:** 上記の3段階構造（結論→詳細→ポイント再確認）に従って執筆し、前のセクションから自然につながるよう配慮する
2.  **厳格な情報源・リンク管理:**
    - リサーチ情報に含まれる事実やデータのみを使用し、憶測や一般論の域を出ない情報は含めない
    - **記事内にはURLリンクを一切含めないでください**
    - 個別企業名やサービス名を情報源として明記することは禁止（例：「○○がスーモに書いていました」等）
    - 情報は一般的な事実として記述し、特定のメディアや企業への直接的言及は避ける
3.  **セクションスコープの厳守:** このセクション（インデックス {target_index}、見出し「{target_heading}」）の内容のみを生成し、他のセクションの内容は絶対に含めない
4.  **HTML構造:** `<p>`, `<ul>`, `<li>`, `<strong>` などの基本HTMLタグを適切に使用し、メイン見出しには必ず `<{main_heading_tag}>` を使用してください。{child_heading_instruction_text} **重要：`<em>`タグ（斜体）は一切使用しないでください**
5.  **SEO最適化:** 記事のキーワードやセクション関連キーワードを自然に含める（過度な詰め込みは避ける）
6.  **読者価値の提供:** 上記の執筆スタイル指針に従い、読者にとって実用的で価値のあるオリジナルコンテンツを作成
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

        def get_value(item: Any, key: str, default: Any = None) -> Any:
            if isinstance(item, dict):
                return item.get(key, default)
            return getattr(item, key, default)

        target_heading = get_value(target_section, 'heading', '')
        outline_top_level = getattr(ctx.context.generated_outline, 'top_level_heading', 2) or 2
        target_level = get_value(target_section, 'level', outline_top_level)
        if not isinstance(target_level, int):
            target_level = outline_top_level
        target_level = max(2, min(target_level, 6))
        
        section_target_chars = None
        if ctx.context.target_length and len(ctx.context.generated_outline.sections) > 0:
            total_sections = len(ctx.context.generated_outline.sections)
            estimated_total_body_chars = ctx.context.target_length * 0.8
            section_target_chars = int(estimated_total_body_chars / total_sections)

        default_child_level = min(target_level + 1, 6)

        raw_subsections = get_value(target_section, 'subsections', []) or []
        target_subsections: List[Dict[str, Any]] = []
        for sub in raw_subsections:
            sub_heading = get_value(sub, 'heading', '').strip()
            if not sub_heading:
                continue
            sub_level = get_value(sub, 'level', default_child_level)
            if not isinstance(sub_level, int):
                sub_level = default_child_level
            sub_level = max(target_level + 1, min(sub_level, 6))
            sub_description = get_value(sub, 'description', '') or ''
            target_subsections.append({
                'heading': sub_heading,
                'level': sub_level,
                'description': sub_description
            })

        subsection_heading_tags = {f"h{sub['level']}" for sub in target_subsections}
        subheading_plan_lines = [
            f"- H{sub['level']} {sub['heading']}" + (f"：{sub['description']}" if sub['description'] else '')
            for sub in target_subsections
        ]
        if subheading_plan_lines:
            subheading_prompt_block = (
                "\n--- このセクションで必ず使用する小見出し ---\n"
                "下記の順序で小見出しを組み込み、それぞれの見出しに対応する内容を十分に書いてください。\n"
                + "\n".join(subheading_plan_lines)
                + "\n---\n\n"
            )
        else:
            subheading_prompt_block = "\n"

        def format_outline_sections(sections: Any, prefix: str = "") -> List[str]:
            lines: List[str] = []
            for idx, section in enumerate(sections or []):
                heading = get_value(section, 'heading', '').strip()
                if not heading:
                    continue
                level = get_value(section, 'level', outline_top_level)
                if not isinstance(level, int):
                    level = outline_top_level
                level = max(2, min(level, 6))
                label = f"{prefix}{idx + 1}"
                lines.append(f"{label}. H{level} {heading}")
                children = get_value(section, 'subsections', []) or []
                for child_idx, child in enumerate(children):
                    child_heading = get_value(child, 'heading', '').strip()
                    if not child_heading:
                        continue
                    child_level = get_value(child, 'level', min(level + 1, 6))
                    if not isinstance(child_level, int):
                        child_level = min(level + 1, 6)
                    child_level = max(level + 1, min(child_level, 6))
                    lines.append(f"{label}.{child_idx + 1}. H{child_level} {child_heading}")
            return lines

        outline_context = "\n".join(format_outline_sections(ctx.context.generated_outline.sections))

        research_context_str = f"リサーチ要約: {ctx.context.research_report.overall_summary[:500]}...\n"
        research_context_str += "主要なキーポイント:\n"
        for kp in ctx.context.research_report.key_points:
            research_context_str += f"- {kp.point}\n"

        # 拡張された会社情報コンテキストを使用
        company_info_str = build_enhanced_company_context(ctx.context)
        
        # スタイルガイドコンテキストを構築
        style_guide_context = build_style_context(ctx.context)
        
        # 日付コンテキストを追加
        date_context = get_current_date_context()

        main_heading_tag = f"h{target_level}"
        sorted_subheading_tags = sorted(subsection_heading_tags)
        if sorted_subheading_tags:
            child_heading_instruction_text = (
                "指定された小見出しには "
                + ", ".join(f"`<{tag}>`" for tag in sorted_subheading_tags)
                + " を使用し、提示された順序で配置し、追加の見出しレベルは作成しないでください。"
            )
        else:
            child_heading_instruction_text = (
                f"必要に応じて `<h{default_child_level}>` で論点を整理できますが、不要な見出しは追加しないでください。"
            )

        full_prompt = f"""{base_prompt}

{date_context}

--- 記事全体の情報 ---
記事タイトル: {ctx.context.generated_outline.title}
記事全体のキーワード: {', '.join(ctx.context.selected_theme.keywords) if ctx.context.selected_theme else 'N/A'}
記事全体のトーン: {ctx.context.generated_outline.suggested_tone}
想定読者の詳細:\n{persona_description}

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
使用するメイン見出しタグ: <{main_heading_tag}>
このセクションの目標文字数: {section_target_chars or '指定なし（流れに合わせて適切に）'}
{subheading_prompt_block}--- **【最重要】執筆スタイルとトーンについて** ---
あなたは専門知識を持つプロのライターとして、以下のターゲット読者に向けて執筆します：
「{persona_description}」

**執筆の基本姿勢:**
- あなたは「情報を提供する執筆者」、読者は「その情報を求める人」という関係性を明確に保つ
- 読者の知識レベルや関心に合わせて、分かりやすく実用的な情報を提供する
- 企業のスタイルガイドが設定されている場合は、そのトンマナに従う

**重要な注意事項:**
- 記事内では「ペルソナ」という用語を一切使用しないでください
- 読者を指す場合は「皆さん」「読者の方」「お客様」「ご家庭」「ご家族」など自然な表現を使用してください
- システム用語（ペルソナ、ターゲット、SEO等）は記事本文に含めないでください

**文章構成の原則（必須）:**
各セクションは以下の3段階構造で執筆してください：
1. **結論・主張**: このセクションで伝えたい核心的な内容を最初に明確に述べる
2. **詳細・根拠**: 具体例、手順、データなどで詳しく説明・補強する  
3. **ポイント再確認**: 読者が押さえるべき要点を簡潔にまとめ直す

**文体・表現の指針:**
- 断言調は避け、「〜と考えられます」「〜が効果的です」等の丁寧で説得力のある表現を使用
- 過度な感嘆符や語りかけ（「〜ですよね！」「〜しましょう！」）は控えめに
- 専門用語は必要に応じて使用し、読者に分かりやすく説明を加える
---

--- 執筆ルール ---
1.  **記事の一貫性と構造:** 上記の3段階構造（結論→詳細→ポイント再確認）に従って執筆し、前のセクションから自然につながるよう配慮する
2.  **厳格な情報源・リンク管理:**
    - リサーチ情報に含まれる事実やデータのみを使用し、憶測や一般論の域を出ない情報は含めない
    - **記事内にはURLリンクを一切含めないでください**
    - 個別企業名やサービス名を情報源として明記することは禁止（例：「○○がスーモに書いていました」等）
    - 情報は一般的な事実として記述し、特定のメディアや企業への直接的言及は避ける
3.  **セクションスコープの厳守:** このセクション（インデックス {target_index}、見出し「{target_heading}」）の内容のみを生成し、他のセクションの内容は絶対に含めない
4.  **HTML構造:** `<p>`, `<ul>`, `<li>`, `<strong>` などの基本HTMLタグを適切に使用し、メイン見出しには必ず `<{main_heading_tag}>` を使用してください。{child_heading_instruction_text} **重要：`<em>`タグ（斜体）は一切使用しないでください**
5.  **SEO最適化:** 記事のキーワードやセクション関連キーワードを自然に含める（過度な詰め込みは避ける）
6.  **読者価値の提供:** 上記の執筆スタイル指針に従い、読者にとって実用的で価値のあるオリジナルコンテンツを作成
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
        research_context_str += "主要なキーポイント:\n"
        for kp in ctx.context.research_report.key_points:
            research_context_str += f"- {kp.point}\n"

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
想定読者: {persona_description}
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
- **特に、文章全体が想定読者「{persona_description}」にとって自然で、親しみやすく、分かりやすい言葉遣いになっているか** を重点的に確認してください。機械的な表現や硬い言い回しがあれば、より人間味のある表現に修正してください。
- チェックポイント:
    - 全体の流れと一貫性
    - 各セクションの内容の質と正確性 (**リサーチ情報との整合性、事実確認**)
    - 文法、スペル、誤字脱字
    - 指示されたトーンとスタイルガイドの遵守 (**自然さ、親しみやすさ重視**)
    - 想定読者への適合性
    - SEO最適化（キーワードの自然な使用、見出し構造）
    - **記事内にURLリンク (`<a>` タグ) が含まれていないことを確認し、もし含まれている場合は削除してください。**
    - **記事内に斜体 (`<em>` タグ) が含まれていないことを確認し、もし含まれている場合は削除して通常のテキストに変更してください。**
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

        # 企業情報（拡張）
        company_info_block = f"""

=== 企業情報 ===
{build_enhanced_company_context(ctx.context)}
"""

        full_prompt = f"""{base_prompt}

--- 入力情報 ---
SEOキーワード: {', '.join(ctx.context.initial_keywords)}
ターゲット年代: {ctx.context.target_age_group.value if ctx.context.target_age_group else '指定なし'}
ペルソナ属性（大分類）: {ctx.context.persona_type.value if ctx.context.persona_type else '指定なし'}
（上記属性が「その他」の場合のユーザー指定ペルソナ: {ctx.context.custom_persona if ctx.context.persona_type == PersonaType.OTHER else '該当なし'}）
生成する具体的なペルソナの数: {ctx.context.num_persona_examples}
{company_info_block}
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
    def _flatten_headings(headings_list, prefix: str = ""):
        """見出し階層構造をフラット化して見出しテキストのリストを返す"""
        flat_headings = []
        for heading in headings_list:
            if isinstance(heading, dict) and "text" in heading:
                level = heading.get("level", 1)
                indent = "  " * (level - 1)  # レベルに応じてインデント
                flat_headings.append(f"{indent}H{level}: {heading['text']}")
                
                # 子見出しも再帰的に処理
                if "children" in heading and heading["children"]:
                    flat_headings.extend(_flatten_headings(heading["children"], prefix + "  "))
            elif isinstance(heading, str):  # 文字列の場合はそのまま追加
                flat_headings.append(f"  * {heading}")
        return flat_headings

    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        # キーワードからSerpAPI分析を実行（この時点で実行）
        keywords = ctx.context.initial_keywords
        
        # SerpAPIサービスのインポートと実行
        from app.infrastructure.external_apis.serpapi_service import get_serpapi_service
        serpapi_service = get_serpapi_service()
        analysis_result = await serpapi_service.analyze_keywords(keywords, num_articles_to_scrape=5)
        
        # 全記事の見出し一覧を収集
        all_headings_flat = []
        for article in analysis_result.scraped_articles:
            article_headings = _flatten_headings(article.headings)
            all_headings_flat.extend(article_headings)
        
        # 分析データを文字列に整理
        articles_summary = ""
        for i, article in enumerate(analysis_result.scraped_articles):
            article_headings = _flatten_headings(article.headings)
            headings_text = "\n".join(article_headings) if article_headings else "見出しが取得できませんでした"
            
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
{headings_text}
- 本文プレビュー: {article.content[:200]}...

"""
        
        related_questions_str = ""
        if analysis_result.related_questions:
            related_questions_str = "関連質問:\n"
            for i, q in enumerate(analysis_result.related_questions):
                related_questions_str += f"  {i+1}. {q.get('question', 'N/A')}\n"
        
        # 上位記事の見出し一覧をまとめる
        all_headings_summary = "=== 上位記事で使用されている全見出し一覧 ===\n"
        if all_headings_flat:
            all_headings_summary += "\n".join(all_headings_flat[:50])  # 上位50個の見出しに限定
            if len(all_headings_flat) > 50:
                all_headings_summary += f"\n... その他 {len(all_headings_flat) - 50} 個の見出し"
        else:
            all_headings_summary += "見出しが取得できませんでした"
        all_headings_summary += "\n\n"

        full_prompt = f"""{base_prompt}

--- SerpAPI分析データ ---
検索クエリ: {analysis_result.search_query}
検索結果総数: {analysis_result.total_results:,}
分析対象記事数: {len(analysis_result.scraped_articles)}
平均文字数: {analysis_result.average_char_count}
推奨目標文字数: {analysis_result.suggested_target_length}

{related_questions_str}

{all_headings_summary}

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
- analyzed_articles: 分析した記事のリスト（見出し情報を含む、以下の形式で各記事を記述）
  [
    {{
      "url": "記事URL",
      "title": "記事タイトル", 
      "headings": ["H1: メイン見出し", "H2: サブ見出し1", "H3: 詳細見出し1", ...],
      "content_preview": "記事内容のプレビュー",
      "char_count": 文字数,
      "image_count": 画像数,
      "source_type": "organic_result" または "related_question",
      "position": 順位（該当する場合）,
      "question": "関連質問"（該当する場合）
    }}, ...
  ]
  
**重要**: headingsフィールドには各記事の見出し階層情報を含めてください。
この情報は後続のアウトライン作成で重要な参考資料として活用されます。

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
収集された詳細なリサーチ結果を分析し、記事のテーマに沿って統合・要約します。
各キーポイントについて、記事作成者がすぐに活用できる実用的で詳細なリサーチレポートを作成します。
※ 出典情報は不要です。URLを含めないでください。
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
あなたは高品質なSEO記事のアウトライン（構成案）を作成する専門家です。

**アウトライン設計方針:**
1. **SEO上位表示を意識した構成**: 検索意図を満たし、競合サイトを上回る価値を提供する構造
2. **読者の知識段階に応じた論理的な流れ**: 基礎→応用→実践の自然な流れ
3. **各見出しの明確な目的**: 読者が各セクションで何を得られるかが明確
4. **結論ファースト構造の準備**: 各セクションが「結論→詳細→ポイント再確認」で書けるよう設計

**見出し構成の品質基準:**
- 見出しだけで記事の全体像が把握できる
- 重複や矛盾のない論理的な構成
- ターゲットキーワードが自然に組み込まれた見出し
- 読者の疑問や関心に直接的に答える見出し設定

**記事全体のトーン設定:**
企業のスタイルガイドが設定されている場合はそれに従い、未設定の場合は読者ペルソナに最適なトーンを提案します。
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
あなたは高品質なSEO記事を執筆するプロのライターです。
指定されたセクション（見出し）について、ターゲット読者にとって価値のある、読みやすく実用的な内容をHTML形式で執筆します。

**重要な執筆方針:**
- ターゲットペルソナは「記事を読む読者」であり、あなたは「専門知識を持つ執筆者」として読者に向けて書きます
- 記事全体の一貫性を保ち、断片的にならないよう前後のセクションとの繋がりを意識します
- 各セクションは「結論ファースト→詳細説明→ポイント再確認」の構造で書きます
- 過度な語りかけや冗長な表現は避け、簡潔で要点が明確な文章を心がけます

**参考情報・リンクに関する厳格なルール:**
- 記事内にはURLリンクを一切含めないでください
- 個別企業名やサービス名の直接的な言及は避ける（例：「○○がスーモに書いていました」等は禁止）
- 一般的な事実として記述し、特定のメディアや企業を情報源として明示しない
- 外部サイトへのリンクや参考URLは記載しないでください
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
あなたは高品質なSEO記事を執筆するプロのライターです。
指定されたセクション（見出し）について、画像プレースホルダーを含む視覚的に魅力的なコンテンツをHTML形式で執筆します。

**重要な執筆方針:**
- ターゲットペルソナは「記事を読む読者」であり、あなたは「専門知識を持つ執筆者」として読者に向けて書きます
- 記事全体の一貫性を保ち、断片的にならないよう前後のセクションとの繋がりを意識します
- 各セクションは「結論ファースト→詳細説明→ポイント再確認」の構造で書きます
- 過度な語りかけや冗長な表現は避け、簡潔で要点が明確な文章を心がけます

**画像プレースホルダー要件:**
- このセクションでは内容に応じて適切に画像プレースホルダーを配置する
- 画像は読者の理解を助け、視覚的に魅力的な記事にするための重要要素

**参考情報・リンクに関する厳格なルール:**
- 記事内にはURLリンクを一切含めないでください
- 個別企業名やサービス名の直接的な言及は避ける（例：「○○がスーモに書いていました」等は禁止）
- 一般的な事実として記述し、特定のメディアや企業を情報源として明示しない
- 外部サイトへのリンクや参考URLは記載しないでください
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

# リサーチエージェント（計画、実行、要約を一度に実行するエージェント）
RESEARCH_AGENT_BASE_PROMPT = """
あなたはリサーチエージェントです。与えられたテーマに基づいて、計画、実行、要約を一度に行います。
1. まず、テーマを深く掘り下げ、読者が知りたいであろう情報を網羅するための効果的なWeb検索クエリプランを作成します。
2. 次に、その検索クエリでWeb検索を実行し、結果を深く分析します。記事テーマに関連する具体的で信頼できる情報、デ
3. 最後に、収集された詳細なリサーチ結果を分析し、記事のテーマに沿って統合・要約します。各キーポイントについて、記事作成者がすぐに活用できる実用的で詳細なリサーチレポートを作成します。

"""
research_agent = Agent[ArticleContext](
    name="ResearchAgent",
    instructions=create_research_instructions(RESEARCH_AGENT_BASE_PROMPT),
    model=settings.research_model,
    model_settings=ModelSettings(max_tokens=32768),  # 最大出力トークン数設定
    tools=[web_search_tool],
    output_type=ResearchReport, 
)

# LiteLLMエージェント生成関数 (APIでは直接使わないかもしれないが、念のため残す)
# 必要に応じてAPIキーの取得方法などを修正する必要がある
# def get_litellm_agent(...) -> Optional[Agent]: ... (実装は省略)
