from pydantic import BaseModel, Field
from typing import List, Optional

# KeywordAnalyzerAgentの出力
class KeywordAnalysisReport(BaseModel):
    search_intent: str = Field(description="推定されるユーザーの検索意図")
    main_topics: List[str] = Field(description="競合記事で共通して扱われる主要トピック")
    content_gaps: List[str] = Field(description="競合記事であまり触れられていない、差別化可能なトピック")
    recommended_length_chars: int = Field(description="推奨される記事の文字数")
    user_pain_points: List[str] = Field(description="検索ユーザーが抱えているであろう悩みや課題")

# PersonaGeneratorAgentの出力
class GeneratedPersona(BaseModel):
    id: int
    name: str = Field(description="ペルソナの仮名")
    description: str = Field(description="ペルソナの背景、ニーズ、悩みを詳細に記述した文章")
    related_keywords: List[str] = Field(description="このペルソナが検索しそうな関連キーワード")

class GeneratedPersonasResponse(BaseModel):
    personas: List[GeneratedPersona]

# ThemeGeneratorAgentの出力
class Theme(BaseModel):
    id: int
    title: str = Field(description="記事のテーマ・タイトル案")
    reason: str = Field(description="なぜこのテーマがSEOに有効と考えられるかの根拠")
    target_audience: str = Field(description="このテーマが特に響くターゲット層")

# ResearchPlannerAgentの出力
class ResearchQuery(BaseModel):
    query: str = Field(description="実行する検索クエリ")
    source: str = Field(description="情報源（例: Google Search, 専門家のブログ）")

class ResearchPlan(BaseModel):
    queries: List[ResearchQuery] = Field(description="実行する調査クエリのリスト")

# ResearcherAgentの出力
class ResearchReport(BaseModel):
    query: str
    summary: str = Field(description="検索結果の要約")
    key_findings: List[str] = Field(description="主要な発見やデータポイント")
    sources: List[str] = Field(description="参照したURLリスト")

# OutlineGeneratorAgentの出力
class Section(BaseModel):
    title: str = Field(description="セクションのタイトル")
    description: str = Field(description="このセクションで記述すべき内容の要約")
    keywords: List[str] = Field(description="含めるべきキーワード")
    subsections: List['Section'] = Field(default_factory=list, description="サブセクション")

class ArticleOutline(BaseModel):
    title: str = Field(description="記事全体のタイトル")
    introduction: str = Field(description="導入部分で記述すべき内容")
    sections: List[Section] = Field(description="記事の主要なセクション")
    conclusion: str = Field(description="結論部分で記述すべき内容")

# FinalArticle (EditorAgentの出力)
class FinalArticle(BaseModel):
    title: str
    content_html: str
    summary: str = Field(description="記事の要約")
