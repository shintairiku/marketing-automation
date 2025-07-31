from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from .schemas import (
    KeywordAnalysisReport, GeneratedPersona, Theme, ResearchPlan,
    ResearchReport, ArticleOutline, FinalArticle
)

class WorkflowState(str, Enum):
    START = "START"
    KEYWORD_ANALYSIS_RUNNING = "KEYWORD_ANALYSIS_RUNNING"
    PERSONA_GENERATION_RUNNING = "PERSONA_GENERATION_RUNNING"
    AWAITING_PERSONA_SELECTION = "AWAITING_PERSONA_SELECTION"
    THEME_GENERATION_RUNNING = "THEME_GENERATION_RUNNING"
    AWAITING_THEME_SELECTION = "AWAITING_THEME_SELECTION"
    RESEARCH_PLANNING_RUNNING = "RESEARCH_PLANNING_RUNNING"
    AWAITING_RESEARCH_PLAN_APPROVAL = "AWAITING_RESEARCH_PLAN_APPROVAL"
    RESEARCH_EXECUTION_RUNNING = "RESEARCH_EXECUTION_RUNNING"
    RESEARCH_SYNTHESIS_RUNNING = "RESEARCH_SYNTHESIS_RUNNING"
    OUTLINE_GENERATION_RUNNING = "OUTLINE_GENERATION_RUNNING"
    AWAITING_OUTLINE_APPROVAL = "AWAITING_OUTLINE_APPROVAL"
    SECTION_WRITING_RUNNING = "SECTION_WRITING_RUNNING"
    EDITING_RUNNING = "EDITING_RUNNING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"

class ArticleGenerationContext(BaseModel):
    # 初期入力
    initial_keywords: List[str]
    initial_persona_prompt: str
    num_persona_to_generate: int = 3
    company_id: Optional[str] = None
    style_template_id: Optional[str] = None

    # ワークフローの状態
    state: WorkflowState = Field(default=WorkflowState.START)
    error_message: Optional[str] = None

    # 各エージェントの成果物
    keyword_analysis_report: Optional[KeywordAnalysisReport] = None
    generated_personas: List[GeneratedPersona] = Field(default_factory=list)
    selected_persona: Optional[GeneratedPersona] = None
    generated_themes: List[Theme] = Field(default_factory=list)
    selected_theme: Optional[Theme] = None
    research_plan: Optional[ResearchPlan] = None
    research_reports: List[ResearchReport] = Field(default_factory=list)
    synthesized_research_report: Optional[ResearchReport] = None
    article_outline: Optional[ArticleOutline] = None
    written_sections: List[str] = Field(default_factory=list) # HTML
    final_article: Optional[FinalArticle] = None

    class Config:
        arbitrary_types_allowed = True
        validate_assignment = True
