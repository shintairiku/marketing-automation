# -*- coding: utf-8 -*-
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from app.common.schemas import BasePayload

# --- Request Models ---

class AgeGroup(str, Enum):
    TEENS = "10代"
    TWENTIES = "20代"
    THIRTIES = "30代"
    FORTIES = "40代"
    FIFTIES = "50代"
    SIXTIES = "60代"
    SEVENTIES_OR_OLDER = "70代以上"

class PersonaType(str, Enum):
    HOUSEWIFE = "主婦"
    STUDENT = "学生"
    OFFICE_WORKER = "社会人"
    SELF_EMPLOYED = "自営業"
    EXECUTIVE = "経営者・役員"
    RETIREE = "退職者"
    OTHER = "その他" # ユーザーが独自に設定する場合

class GenerateArticleRequest(BaseModel):
    """記事生成APIリクエストモデル"""
    initial_keywords: List[str] = Field(..., description="記事生成の元となるキーワードリスト", examples=[["札幌", "注文住宅", "自然素材", "子育て"]])
    target_age_group: Optional[AgeGroup] = Field(None, description="ターゲット年代層")
    persona_type: Optional[PersonaType] = Field(None, description="ペルソナ属性")
    custom_persona: Optional[str] = Field(None, description="独自に設定したペルソナ（persona_typeがOTHERの場合に利用）", examples=["札幌近郊で自然素材を使った家づくりに関心がある、小さな子供を持つ30代夫婦"])
    target_length: Optional[int] = Field(None, description="目標文字数（目安）", examples=[3000])
    num_theme_proposals: int = Field(3, description="生成するテーマ案の数", ge=1)
    num_research_queries: int = Field(3, description="リサーチで使用する検索クエリ数", ge=1) # デフォルト値を3に設定
    num_persona_examples: int = Field(3, description="生成する具体的なペルソナの数", ge=1) # 新パラメータ、デフォルト3
    company_name: Optional[str] = Field(None, description="クライアント企業名（指定があれば）", examples=["株式会社ナチュラルホームズ札幌"])
    company_description: Optional[str] = Field(None, description="クライアント企業概要（指定があれば）")
    company_style_guide: Optional[str] = Field(None, description="クライアント企業の文体・トンマナガイド（指定があれば）")
    
    # --- 画像モード関連 (新規追加) ---
    image_mode: bool = Field(False, description="画像プレースホルダー機能を使用するかどうか")
    image_settings: Optional[dict] = Field(None, description="画像生成設定")
    
    # --- スタイルテンプレート関連 (新規追加) ---
    style_template_id: Optional[str] = Field(None, description="使用するスタイルテンプレートのID")

    class Config:
        json_schema_extra = {
            "example": {
                "initial_keywords": ["札幌", "注文住宅", "自然素材", "子育て"],
                "target_age_group": AgeGroup.THIRTIES,
                "persona_type": PersonaType.HOUSEWIFE,
                "custom_persona": "札幌近郊で自然素材を使った家づくりに関心がある、小さな子供を持つ30代夫婦",
                "target_length": 3000,
                "num_theme_proposals": 3,
                "num_research_queries": 3,
                "num_persona_examples": 3,
                "company_name": "株式会社ナチュラルホームズ札幌",
                "company_description": "札幌を拠点に、自然素材を活かした健康で快適な注文住宅を提供しています。",
                "image_mode": False,
                "image_settings": {},
                "company_style_guide": "専門用語を避け、温かみのある丁寧語（ですます調）で。子育て世代の読者に寄り添い、安心感を与えるようなトーンを心がける。"
            }
        }

# --- Response Models (SEO Article specific parts from response.py) ---

class StatusUpdatePayload(BasePayload):
    """ステータス更新ペイロード"""
    step: str = Field(description="現在の処理ステップ名")
    message: str = Field(description="処理状況に関するメッセージ")
    image_mode: Optional[bool] = Field(None, description="画像モードが有効かどうか")

class ThemeProposalData(BaseModel):
    title: str
    description: str
    keywords: List[str]

class ThemeProposalPayload(BasePayload):
    """テーマ提案ペイロード (選択要求時に使用)"""
    themes: List[ThemeProposalData] = Field(description="提案されたテーマ案")

class ResearchPlanQueryData(BaseModel):
    query: str
    focus: str

class ResearchPlanData(BaseModel):
    topic: str
    queries: List[ResearchPlanQueryData]

class ResearchPlanPayload(BasePayload):
    """リサーチ計画ペイロード (承認要求時に使用)"""
    plan: ResearchPlanData = Field(description="生成されたリサーチ計画")

class ResearchProgressPayload(BasePayload):
    """リサーチ進捗ペイロード"""
    query_index: int = Field(description="現在実行中のクエリインデックス (0ベース)")
    total_queries: int = Field(description="総クエリ数")
    query: str = Field(description="実行中のクエリ文字列")

class KeyPointData(BaseModel):
    point: str
    supporting_sources: List[str]

class ResearchReportData(BaseModel):
    topic: str
    overall_summary: str
    key_points: List[KeyPointData]
    interesting_angles: List[str]
    all_sources: List[str]

class ResearchCompletePayload(BasePayload):
    """リサーチ完了ペイロード (情報提供用)"""
    report: ResearchReportData = Field(description="生成されたリサーチレポート")

class OutlineSectionData(BaseModel):
    heading: str
    estimated_chars: Optional[int] = None
    subsections: Optional[List['OutlineSectionData']] = None # 再帰的な型ヒント

class OutlineData(BaseModel):
    title: str
    suggested_tone: str
    sections: List[OutlineSectionData]

class OutlinePayload(BasePayload):
    """アウトラインペイロード (承認要求時に使用)"""
    outline: OutlineData = Field(description="生成されたアウトライン")

class ImagePlaceholderData(BaseModel):
    """画像プレースホルダー情報（WebSocket用）"""
    placeholder_id: str = Field(description="プレースホルダーの一意ID")
    description_jp: str = Field(description="画像の説明（日本語）")
    prompt_en: str = Field(description="画像生成用の英語プロンプト")
    alt_text: str = Field(description="画像のalt属性テキスト")

class SectionChunkPayload(BasePayload):
    """セクションHTMLチャンクペイロード (ストリーミング用)"""
    section_index: int = Field(description="生成中のセクションインデックス (0ベース)")
    heading: str = Field(description="生成中のセクションの見出し")
    html_content_chunk: str = Field(description="生成されたHTMLコンテンツの断片")
    is_complete: bool = Field(False, description="このセクションの生成が完了したか")
    # 画像モード対応: セクション完了時の追加情報
    section_complete_content: Optional[str] = Field(None, description="セクション完了時の完全なHTMLコンテンツ（画像モード用）")
    image_placeholders: Optional[List[ImagePlaceholderData]] = Field(None, description="このセクション内の画像プレースホルダー（画像モード用）")
    is_image_mode: bool = Field(False, description="画像モードかどうか")

class EditingStartPayload(BasePayload):
    """編集開始ペイロード"""
    message: str = "最終編集を開始します..."

class FinalResultPayload(BasePayload):
    """最終結果ペイロード"""
    title: str = Field(description="最終的な記事タイトル")
    final_html_content: str = Field(description="完成した記事のHTMLコンテンツ")
    # 新規追加: DBに保存された記事ID (フロントエンドで編集ページへ遷移する際に使用)
    article_id: Optional[str] = Field(default=None, description="生成された記事の一意ID")

# SerpAPIキーワード分析結果
class SerpAnalysisArticleData(BaseModel):
    """SerpAPI分析記事データ"""
    url: str
    title: str
    headings: List[str]
    content_preview: str
    char_count: int
    image_count: int
    source_type: str
    position: Optional[int] = None
    question: Optional[str] = None

class SerpKeywordAnalysisPayload(BasePayload):
    """SerpAPIキーワード分析結果ペイロード"""
    search_query: str = Field(description="実行した検索クエリ")
    total_results: int = Field(description="検索結果の総数")
    analyzed_articles: List[SerpAnalysisArticleData] = Field(description="分析対象記事のリスト")
    average_article_length: int = Field(description="分析した記事の平均文字数")
    recommended_target_length: int = Field(description="推奨記事文字数")
    main_themes: List[str] = Field(description="上位記事で頻出する主要テーマ")
    common_headings: List[str] = Field(description="上位記事で共通して使用される見出しパターン")
    content_gaps: List[str] = Field(description="上位記事で不足している可能性のあるコンテンツ")
    competitive_advantages: List[str] = Field(description="差別化できる可能性のあるポイント")
    user_intent_analysis: str = Field(description="検索ユーザーの意図分析")
    content_strategy_recommendations: List[str] = Field(description="コンテンツ戦略の推奨事項")

# 生成されたペルソナリスト (クライアント送信用)
class GeneratedPersonaData(BaseModel):
    id: int
    description: str

class GeneratedPersonasPayload(BasePayload):
    """生成されたペルソナリストペイロード (選択要求時に使用)"""
    personas: List[GeneratedPersonaData] = Field(description="生成された具体的なペルソナのリスト")

# --- クライアント -> サーバー 応答ペイロード ---
class SelectPersonaPayload(BasePayload):
    """ペルソナ選択応答ペイロード"""
    selected_id: int = Field(description="ユーザーが選択したペルソナのID (0ベース)", ge=0)

class SelectThemePayload(BasePayload):
    """テーマ選択応答ペイロード"""
    selected_index: int = Field(description="ユーザーが選択したテーマのインデックス (0ベース)", ge=0)

class ApprovePayload(BasePayload):
    """承認/拒否応答ペイロード"""
    approved: bool = Field(description="承認したかどうか")

class RegeneratePayload(BasePayload):
    """再生成要求ペイロード (特定のステップの再生成を意図)"""
    pass # シンプルにするため、一旦フィールドなし

class EditAndProceedPayload(BasePayload):
    """編集して進行要求ペイロード"""
    edited_content: Dict[str, Any] = Field(description="ユーザーによって編集された内容")

# 個別編集用ペイロード
class EditPersonaPayload(BasePayload):
    """ペルソナ編集ペイロード"""
    edited_persona: Dict[str, Any] = Field(description="編集されたペルソナ")

class EditThemePayload(BasePayload):
    """テーマ編集ペイロード"""
    edited_theme: Dict[str, Any] = Field(description="編集されたテーマ")

class EditPlanPayload(BasePayload):
    """計画編集ペイロード"""
    edited_plan: Dict[str, Any] = Field(description="編集された計画")

class EditOutlinePayload(BasePayload):
    """アウトライン編集ペイロード"""
    edited_outline: Dict[str, Any] = Field(description="編集されたアウトライン")

# サーバーから送信されるイベントペイロードのUnion型
ServerEventPayload = Union[
    StatusUpdatePayload,
    SerpKeywordAnalysisPayload,
    GeneratedPersonasPayload,
    ThemeProposalPayload, # 選択要求時に使用
    ResearchPlanPayload,  # 承認要求時に使用
    ResearchProgressPayload,
    ResearchCompletePayload,
    OutlinePayload,       # 承認要求時に使用
    SectionChunkPayload,
    EditingStartPayload,
    FinalResultPayload,
    # ErrorPayload,  # 共通スキーマから参照
    # UserInputRequestPayload, # 共通スキーマから参照
]

# クライアントから送信される応答ペイロードのUnion型
ClientResponsePayload = Union[
    SelectPersonaPayload,
    SelectThemePayload,
    ApprovePayload,
    RegeneratePayload,
    EditAndProceedPayload,
    EditPersonaPayload,
    EditThemePayload,
    EditPlanPayload,
    EditOutlinePayload,
]

# UserActionPayload は ClientResponsePayload の型ヒントとして使用
UserActionPayload = ClientResponsePayload

# --- 不足しているモデルクラス（移行時に失われたもの）---

class SourceSnippet(BaseModel):
    """リサーチで抽出された情報の出典スニペット"""
    title: str = Field(description="出典タイトル")
    url: str = Field(description="出典URL")
    snippet: str = Field(description="抽出された情報・データ・主張")
    
class ResearchQueryResult(BaseModel):
    """リサーチクエリ結果"""
    query: str = Field(description="検索クエリ")
    results: List[SourceSnippet] = Field(default_factory=list, description="検索結果から抽出された情報")
    summary: Optional[str] = Field(None, description="結果サマリー")

class ArticleSection(BaseModel):
    """記事セクション"""
    title: str = Field(description="セクションタイトル")
    content: str = Field(description="セクション内容")
    order: int = Field(description="セクション順序")

class ArticleSectionWithImages(BaseModel):
    """画像付き記事セクション"""
    title: str = Field(description="セクションタイトル")
    content: str = Field(description="セクション内容")
    order: int = Field(description="セクション順序")
    images: List[ImagePlaceholderData] = Field(default_factory=list, description="画像プレースホルダー")

class RevisedArticle(BaseModel):
    """修正済み記事"""
    title: str = Field(description="記事タイトル")
    content: str = Field(description="記事本文")
    sections: List[ArticleSection] = Field(default_factory=list, description="セクション")
    revision_notes: Optional[str] = Field(None, description="修正メモ")

class ClarificationNeeded(BaseModel):
    """追加確認が必要な事項"""
    message: str = Field(description="確認メッセージ")
    options: List[str] = Field(default_factory=list, description="選択肢")
    required: bool = Field(default=True, description="必須確認かどうか")

class GeneratedPersonaItem(BaseModel):
    """生成されたペルソナ項目"""
    name: str = Field(description="ペルソナ名")
    age: int = Field(description="年齢")
    occupation: str = Field(description="職業")
    interests: List[str] = Field(default_factory=list, description="興味関心")
    description: str = Field(description="詳細説明")

class GeneratedPersonasResponse(BaseModel):
    """生成されたペルソナレスポンス"""
    personas: List[GeneratedPersonaItem] = Field(description="ペルソナリスト")

class GeneratedThemesResponse(BaseModel):
    """生成されたテーマレスポンス (エージェントが返すもの)"""
    themes: List[ThemeProposalData] = Field(description="テーマリスト")
    
class SerpKeywordAnalysisReport(BaseModel):
    """SERP キーワード分析レポート"""
    search_query: str = Field(description="実行した検索クエリ")
    total_results: int = Field(default=0, description="検索結果の総数")
    analyzed_articles: List[SerpAnalysisArticleData] = Field(default_factory=list, description="分析対象記事のリスト")
    average_article_length: int = Field(default=0, description="分析した記事の平均文字数")
    recommended_target_length: int = Field(default=3000, description="推奨記事文字数")
    main_themes: List[str] = Field(default_factory=list, description="上位記事で頻出する主要テーマ")
    common_headings: List[str] = Field(default_factory=list, description="上位記事で共通して使用される見出しパターン")
    content_gaps: List[str] = Field(default_factory=list, description="上位記事で不足している可能性のあるコンテンツ")
    competitive_advantages: List[str] = Field(default_factory=list, description="差別化できる可能性のあるポイント")
    user_intent_analysis: str = Field(default="", description="検索ユーザーの意図分析")
    content_strategy_recommendations: List[str] = Field(default_factory=list, description="コンテンツ戦略の推奨事項")
    # 後方互換性のために既存フィールドも残す
    keyword: str = Field(description="分析キーワード")
    competition_level: str = Field(default="medium", description="競合レベル")
    search_volume: Optional[int] = Field(None, description="検索ボリューム")
    difficulty: Optional[str] = Field(None, description="難易度")
    recommendations: List[str] = Field(default_factory=list, description="推奨事項")
    
    def model_post_init(self, __context) -> None:
        """モデル初期化後の処理でkeywordとsearch_queryを同期"""
        # search_queryが設定されていてkeywordが空の場合
        if self.search_query and not getattr(self, '_keyword_set', False):
            object.__setattr__(self, 'keyword', self.search_query)
        # keywordが設定されていてsearch_queryが空の場合  
        elif self.keyword and not self.search_query:
            object.__setattr__(self, 'search_query', self.keyword)

class OutlineSection(BaseModel):
    """アウトラインセクション"""
    title: str = Field(description="セクションタイトル")
    content: str = Field(description="セクション内容")
    subsections: List[str] = Field(default_factory=list, description="サブセクション")

class KeyPoint(BaseModel):
    """キーポイント"""
    title: str = Field(description="ポイントタイトル")
    description: str = Field(description="ポイント説明")
    importance: int = Field(default=1, description="重要度（1-5）")

class ResearchQuery(BaseModel):
    """リサーチクエリ"""
    query: str = Field(description="検索クエリ")
    category: str = Field(description="カテゴリ")
    priority: int = Field(default=1, description="優先度")

# エイリアス定義（既存コードとの互換性のため）
StatusUpdate = StatusUpdatePayload
ThemeProposal = GeneratedThemesResponse
ResearchPlan = ResearchPlanData
ResearchReport = ResearchReportData
Outline = OutlineData
ImagePlaceholder = ImagePlaceholderData

# AgentOutput のインポート
try:
    from agents import AgentOutputSchema as AgentOutput  # type: ignore[attr-defined]
except ImportError:
    # Fallback: 簡易AgentOutputクラスを定義
    class AgentOutput(BaseModel):  # type: ignore[no-redef]
        """エージェント出力の基底クラス"""
        content: Any = Field(description="出力内容")
        metadata: Dict[str, Any] = Field(default_factory=dict, description="メタデータ")