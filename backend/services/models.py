# -*- coding: utf-8 -*-
# 既存のスクリプトからPydanticモデル定義をここに移動・整理
from pydantic import BaseModel, Field
from typing import List, Dict, Union, Optional, Tuple, Any, Literal

# --- Pydanticモデル定義 (Agentの出力型) ---
class ThemeIdea(BaseModel):
    """単一のテーマ案"""
    title: str = Field(description="記事のタイトル案")
    description: str = Field(description="テーマの簡単な説明とSEO的な狙い")
    keywords: List[str] = Field(description="関連するSEOキーワード")

class ThemeProposal(BaseModel):
    """テーマ提案のリスト"""
    status: Literal["theme_proposal"] = Field(description="出力タイプ: テーマ提案")
    themes: List[ThemeIdea] = Field(description="提案するテーマのリスト")

class OutlineSection(BaseModel):
    """アウトラインの単一セクション（見出し）"""
    heading: str = Field(description="セクションの見出し (例: H2, H3)")
    estimated_chars: Optional[int] = Field(default=None, description="このセクションの推定文字数")
    subsections: Optional[List['OutlineSection']] = Field(default=None, description="サブセクションのリスト（ネスト構造）")

class Outline(BaseModel):
    """記事のアウトライン"""
    status: Literal["outline"] = Field(description="出力タイプ: アウトライン")
    title: str = Field(description="記事の最終タイトル")
    suggested_tone: str = Field(description="提案する記事のトーン（例: 丁寧な解説調、フレンドリー、専門的）")
    sections: List[OutlineSection] = Field(description="記事のセクション（見出し）リスト")

class ArticleSection(BaseModel):
    """生成された記事の単一セクション (内部処理用)"""
    status: Literal["article_section"] = Field(default="article_section", description="出力タイプ: 記事セクション")
    section_index: int = Field(description="生成対象のセクションインデックス（Outline.sectionsのインデックス、0ベース）")
    heading: str = Field(description="生成されたセクションの見出し")
    html_content: str = Field(description="生成されたセクションのHTMLコンテンツ")

class RevisedArticle(BaseModel):
    """推敲・編集後の完成記事"""
    status: Literal["revised_article"] = Field(description="出力タイプ: 完成記事")
    title: str = Field(description="最終的な記事タイトル")
    final_html_content: str = Field(description="推敲・編集後の完全なHTMLコンテンツ")

class ClarificationNeeded(BaseModel):
    """ユーザーへの確認・質問 (APIでは通常エラーとして処理)"""
    status: Literal["clarification_needed"] = Field(description="出力タイプ: 要確認")
    message: str = Field(description="ユーザーへの具体的な質問や確認事項")

class StatusUpdate(BaseModel):
    """処理状況のアップデート (内部処理用)"""
    status: Literal["status_update"] = Field(description="出力タイプ: 状況更新")
    message: str = Field(description="現在の処理状況や次のステップに関するメッセージ")

# --- リサーチ関連モデル (強化版) ---
class ResearchQuery(BaseModel):
    """リサーチプラン内の単一検索クエリ"""
    query: str = Field(description="実行する具体的な検索クエリ")
    focus: str = Field(description="このクエリで特に調査したい点")

class ResearchPlan(BaseModel):
    """リサーチ計画"""
    status: Literal["research_plan"] = Field(description="出力タイプ: リサーチ計画")
    topic: str = Field(description="リサーチ対象のトピック（記事テーマ）")
    queries: List[ResearchQuery] = Field(description="実行する検索クエリのリスト")

class SourceSnippet(BaseModel):
    """リサーチ結果からの詳細な抜粋と出典情報"""
    snippet_text: str = Field(description="記事作成に役立つ具体的な情報やデータの抜粋")
    source_url: str = Field(description="この抜粋の出典元URL（可能な限り、最も具体的なページ）")
    source_title: Optional[str] = Field(default=None, description="出典元ページのタイトル")

class ResearchQueryResult(BaseModel):
    """単一クエリのリサーチ結果（詳細版）"""
    status: Literal["research_query_result"] = Field(description="出力タイプ: リサーチクエリ結果")
    query: str = Field(description="実行された検索クエリ")
    summary: str = Field(description="検索結果の主要な情報の要約（簡潔に）")
    detailed_findings: List[SourceSnippet] = Field(description="記事作成に役立つ詳細な情報抜粋と出典URLのリスト")

class KeyPoint(BaseModel):
    """リサーチレポートのキーポイントと関連情報源"""
    point: str = Field(description="記事に含めるべき重要なポイントや事実")
    supporting_sources: List[str] = Field(description="このポイントを裏付ける情報源URLのリスト")

class ResearchReport(BaseModel):
    """リサーチ結果の要約レポート（詳細版）"""
    status: Literal["research_report"] = Field(description="出力タイプ: リサーチレポート")
    topic: str = Field(description="リサーチ対象のトピック")
    overall_summary: str = Field(description="リサーチ全体から得られた主要な洞察やポイントの要約")
    key_points: List[KeyPoint] = Field(description="記事に含めるべき重要なポイントや事実と、その情報源リスト")
    interesting_angles: List[str] = Field(description="記事を面白くするための切り口や視点のアイデア")
    all_sources: List[str] = Field(description="参照した全ての情報源URLのリスト（重複削除済み、重要度順推奨）")

# 新しいモデル: 具体的なペルソナ
class GeneratedPersonaItem(BaseModel):
    """生成された単一の具体的なペルソナ"""
    id: int = Field(description="ペルソナの一意なID (リスト内インデックス)")
    description: str = Field(description="生成された具体的なペルソナの説明文")
    # keywords: List[str] = Field(description="このペルソナ生成に使用されたキーワード") # 必要であれば追加
    # age_group: Optional[str] = Field(None, description="このペルソナの年代") # 必要であれば追加
    # persona_type: Optional[str] = Field(None, description="このペルソナの属性") # 必要であれば追加

class GeneratedPersonasResponse(BaseModel):
    """ペルソナ生成エージェントの応答 (具体的なペルソナのリスト)"""
    status: Literal["generated_personas_response"] = Field(description="出力タイプ: 生成済みペルソナリスト")
    personas: List[GeneratedPersonaItem] = Field(description="生成された具体的なペルソナのリスト")

# --- SerpAPI分析関連モデル (新規追加) ---
class SerpAnalysisArticle(BaseModel):
    """SerpAPI分析でスクレイピングした記事情報"""
    url: str = Field(description="記事のURL")
    title: str = Field(description="記事のタイトル")
    headings: List[str] = Field(description="記事で使用されている見出しのリスト")
    content_preview: str = Field(description="記事本文の要約またはプレビュー")
    char_count: int = Field(description="記事の文字数")
    image_count: int = Field(description="記事内の画像数")
    source_type: str = Field(description="取得元タイプ（related_question または organic_result）")
    position: Optional[int] = Field(default=None, description="検索結果での順位（organic_resultの場合）")
    question: Optional[str] = Field(default=None, description="関連質問（related_questionの場合）")

class SerpKeywordAnalysisReport(BaseModel):
    """キーワード分析エージェントの出力（SerpAPI分析結果とSEO戦略レポート）"""
    status: Literal["serp_keyword_analysis"] = Field(description="出力タイプ: SerpAPIキーワード分析")
    search_query: str = Field(description="実行した検索クエリ")
    total_results: int = Field(description="検索結果の総数")
    analyzed_articles: List[SerpAnalysisArticle] = Field(description="分析対象記事のリスト")
    average_article_length: int = Field(description="分析した記事の平均文字数")
    recommended_target_length: int = Field(description="推奨記事文字数")
    
    # SEO戦略分析結果
    main_themes: List[str] = Field(description="上位記事で頻出する主要テーマ")
    common_headings: List[str] = Field(description="上位記事で共通して使用される見出しパターン")
    content_gaps: List[str] = Field(description="上位記事で不足している可能性のあるコンテンツ")
    competitive_advantages: List[str] = Field(description="差別化できる可能性のあるポイント")
    user_intent_analysis: str = Field(description="検索ユーザーの意図分析")
    content_strategy_recommendations: List[str] = Field(description="コンテンツ戦略の推奨事項")

# --- 画像プレースホルダー関連モデル (新規追加) ---
class ImagePlaceholder(BaseModel):
    """画像プレースホルダー情報"""
    placeholder_id: str = Field(description="プレースホルダーの一意ID")
    description_jp: str = Field(description="画像の説明（日本語）")
    prompt_en: str = Field(description="画像生成用の英語プロンプト")
    alt_text: str = Field(description="画像のalt属性テキスト")

class ArticleSectionWithImages(BaseModel):
    """画像プレースホルダーを含む記事セクション"""
    status: Literal["article_section_with_images"] = Field(default="article_section_with_images", description="出力タイプ: 画像付き記事セクション")
    section_index: int = Field(description="生成対象のセクションインデックス（Outline.sectionsのインデックス、0ベース）")
    heading: str = Field(description="生成されたセクションの見出し")
    html_content: str = Field(description="画像プレースホルダーを含むHTMLコンテンツ")
    image_placeholders: List[ImagePlaceholder] = Field(description="このセクション内の画像プレースホルダーリスト")

# エージェントが出力しうる型のUnion (ArticleSection を削除)
AgentOutput = Union[
    ThemeProposal, Outline, RevisedArticle, ClarificationNeeded, StatusUpdate,
    ResearchPlan, ResearchQueryResult, ResearchReport, GeneratedPersonasResponse,
    SerpKeywordAnalysisReport, ArticleSectionWithImages
]

