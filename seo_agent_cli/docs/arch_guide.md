自律型SEO記事生成エージェントシステム 設計書1. はじめに1.1. プロジェクトの目的と背景本プロジェクトの目的は、従来の静的なパイプライン方式によるSEO記事生成フローを、より高度で自律的なマルチエージェントシステムへと進化させることである。Gemini CLIやClaude Codeに見られるような、ReAct（Reasoning + Acting）フレームワークを中核に据え、各生成プロセスが自己修正的に動作し、高品質な成果物を安定して生み出すことを目指す。現状のフローは各ステップが決められた順序で実行されるが、本システムでは各責務を持つ専門エージェントが協調し、状況に応じて自律的に思考・行動・観察のループを実行することで、より柔軟かつインテリジェントな記事生成を実現する。1.2. 解決すべき課題柔軟性の欠如: 固定化されたパイプラインでは、予期せぬAPIの出力や外部情報の変化に対応しきれない。エラーハンドリングの複雑さ: ステップの途中でエラーが発生した場合、フロー全体が停止し、手動での介入が必要となる。品質のばらつき: LLMの出力の揺らぎにより、各ステップの成果物の品質が安定しない。保守性と拡張性の課題: フロー全体のロジックが密結合になりがちで、新しい機能の追加や変更が困難。1.3. 設計思想エージェント中心設計: 各タスクを独立した「専門家エージェント」として定義し、自律的な動作を促す。関心の分離: ビジネスロジック、外部API連携、アプリケーションフレームワークを明確に分離し、テスト容易性と再利用性を高める（DDD、オニオンアーキテクチャの思想を参考）。構造化された入出力: エージェント間の連携は、厳密に型定義されたPydanticモデル（スキーマ）を通じて行い、安定性を確保する。宣言的なワークフロー: ワークフローの進行を状態（State）で管理し、各状態に応じて適切なエージェントを起動させる。2. システムアーキテクチャ2.1. 全体構成図本システムは、ワークフローを管理するオーケストレーター、自律的に思考・行動するエージェント群、外部機能を提供するツール群、そして外部APIクライアントを実装するインフラストラクチャ層から構成される。graph TD
    subgraph CLI / API Layer
        A[CLI Entrypoint] --> B[WorkflowManager]
    end

    subgraph Application Core
        B -- Manages --> C{ArticleGenerationContext}
        B -- Invokes --> D[Agent Runner]

        D -- Executes --> E1[KeywordAnalyzerAgent]
        D -- Executes --> E2[PersonaGeneratorAgent]
        D -- Executes --> E3[...]
        D -- Executes --> E4[SectionWriterAgent]

        E1 -- Uses --> T1[SerpAPI Tool]
        E2 -- Uses --> T2[CompanyInfo Tool]
        E4 -- Uses --> T3[StyleTemplate Tool]
    end

    subgraph Infrastructure
        T1 -- Calls --> I1[SerpAPI Client]
        T2 -- Calls --> I2[Database Client]
        T3 -- Calls --> I2
    end

    C -- Shared State --> D
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#f9f,stroke:#333,stroke-width:2px
2.2. ディレクトリ構造ドメイン駆動設計（DDD）とオニオンアーキテクチャの思想を取り入れ、関心の分離を徹底する。seo_agent_cli/
├── app/
│   ├── workflow_manager.py      # ワークフロー全体の進行管理とエージェントの呼び出し
│   └── state_machine.py         # 状態遷移の定義
│
├── core/
│   ├── agents/                  # エージェントの定義 (思考と行動のロジック)
│   │   ├── keyword_analyzer_agent.py
│   │   ├── persona_generator_agent.py
│   │   ├── theme_generator_agent.py
│   │   ├── research_planner_agent.py
│   │   ├── researcher_agent.py
│   │   ├── research_synthesizer_agent.py
│   │   ├── outline_generator_agent.py
│   │   ├── section_writer_agent.py
│   │   └── editor_agent.py
│   │
│   ├── tools/                   # ツールの定義 (外部機能へのインターフェース)
│   │   ├── serpapi_tool.py
│   │   ├── company_info_tool.py
│   │   └── style_template_tool.py
│   │
│   ├── schemas.py               # Pydanticモデル (構造化データ) の定義
│   └── context.py               # ワークフロー全体で共有されるコンテキスト
│
├── infrastructure/
│   └── services/                # 外部APIクライアントの実装
│       └── serpapi_client.py    # (DBクライアントは既存のものを想定)
│
├── cli/
│   └── main.py                  # Typerを使ったCLIのエントリーポイント
│
├── prompts/                     # プロンプトテンプレート (Markdown形式)
│   ├── keyword_analyzer.md
│   └── ... (各エージェントのプロンプト)
│
└── .env                         # APIキーなどの環境変数
2.3. 主要コンポーネントの役割コンポーネント役割WorkflowManager (app)ワークフロー全体の進行を管理するオーケストレーター。ArticleGenerationContextの状態に基づき、次に実行すべきエージェントを決定し、Runnerを介して呼び出す。ArticleGenerationContext (core)ワークフロー全体の状態を保持するPydanticモデル。エージェント間の情報共有の場（黒板）として機能する。Agents (core/agents)各々が特定の責務を持つ自律的な思考・行動単位。openai-agentsのAgentクラスを継承して定義される。ReActループを実行し、ツールを呼び出し、構造化された成果物を出力する。Tools (core/tools)外部システムへのアクセスを抽象化する関数。@function_toolデコレータで定義され、エージェントから呼び出される。Schemas (core/schemas)エージェント間の入出力やツールの戻り値を定義するPydanticモデル。システムの安定性と信頼性を担保する。Infrastructure (infrastructure)外部API（SerpAPI, DBなど）との具体的な通信ロジックを実装する層。ツールから呼び出される。CLI (cli)ユーザーからの初期入力を受け付け、ワークフローを開始し、ユーザーの選択が必要な場面で対話を行うインターフェース。3. データモデル (Schemas)core/schemas.pyにて、エージェントとツールが扱うすべての構造化データをPydanticモデルとして厳密に定義する。3.1. 共有コンテキスト (core/context.py)from pydantic import BaseModel, Field
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
3.2. 主要なスキーマ定義 (core/schemas.py)from pydantic import BaseModel, Field
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

# ... 他のエージェントの出力スキーマも同様に定義 ...

# FinalArticle (EditorAgentの出力)
class FinalArticle(BaseModel):
    title: str
    content_html: str
    summary: str = Field(description="記事の要約")
4. エージェント設計各エージェントは core/agents/ ディレクトリに個別のファイルとして定義される。エージェント名責務入力 (Contextから)使用ツール出力 (Contextへ)KeywordAnalyzerAgentキーワードの競合分析と検索意図の特定initial_keywordssearch_google_and_scrapeKeywordAnalysisReportPersonaGeneratorAgent具体的なペルソナ像を複数生成initial_persona_prompt, keyword_analysis_reportget_company_infoGeneratedPersonasResponseThemeGeneratorAgentSEOに最適化された記事テーマを複数提案selected_persona, keyword_analysis_reportget_style_templateList[Theme]ResearchPlannerAgent選択されたテーマに基づき、調査計画（検索クエリ群）を立案selected_theme-ResearchPlanResearcherAgent計画に基づき、検索クエリを一つずつ実行し、情報を収集・要約research_plan (各クエリ)search_google_and_scrapeList[ResearchReport]ResearchSynthesizerAgent全ての調査結果を統合し、包括的なレポートを作成research_reports-SynthesizedResearchReportOutlineGeneratorAgent調査レポートに基づき、記事のアウトラインを作成synthesized_research_report, selected_theme-ArticleOutlineSectionWriterAgentアウトラインの各セクションを一つずつ執筆article_outline (各セクション), synthesized_research_reportget_style_templateList[str] (HTML)EditorAgent全セクションを統合し、推敲・校正して最終的な記事を完成させるwritten_sections-FinalArticle5. ツール設計各ツールは core/tools/ ディレクトリに個別のファイルとして定義される。ツール名機能入力パラメータ戻り値備考search_google_and_scrapeSerpAPIで検索し、指定された数の上位記事をスクレイピング・解析するkeywords: List[str], num_articles_to_scrape: intDict (SerpAnalysisResult)ワークフロー中で複数回呼び出される可能性があるため、キャッシュ機構を検討get_company_infoDBから指定されたIDの会社情報を取得するcompany_id: strDictget_style_templateDBから指定されたIDのスタイルテンプレートを取得するstyle_template_id: strDict6. ワークフロー設計ワークフローは app/workflow_manager.py で管理されるステートマシンとして実装する。6.1. 状態遷移図stateDiagram-v2
    [*] --> START
    START --> KEYWORD_ANALYSIS_RUNNING : run
    KEYWORD_ANALYSIS_RUNNING --> PERSONA_GENERATION_RUNNING : success
    PERSONA_GENERATION_RUNNING --> AWAITING_PERSONA_SELECTION : success
    AWAITING_PERSONA_SELECTION --> THEME_GENERATION_RUNNING : user_selects
    THEME_GENERATION_RUNNING --> AWAITING_THEME_SELECTION : success
    AWAITING_THEME_SELECTION --> RESEARCH_PLANNING_RUNNING : user_selects
    RESEARCH_PLANNING_RUNNING --> AWAITING_RESEARCH_PLAN_APPROVAL : success
    AWAITING_RESEARCH_PLAN_APPROVAL --> RESEARCH_EXECUTION_RUNNING : user_approves
    RESEARCH_EXECUTION_RUNNING --> RESEARCH_SYNTHESIS_RUNNING : success
    RESEARCH_SYNTHESIS_RUNNING --> OUTLINE_GENERATION_RUNNING : success
    OUTLINE_GENERATION_RUNNING --> AWAITING_OUTLINE_APPROVAL : success
    AWAITING_OUTLINE_APPROVAL --> SECTION_WRITING_RUNNING : user_approves
    SECTION_WRITING_RUNNING --> EDITING_RUNNING : all_sections_written
    EDITING_RUNNING --> COMPLETED : success
    
    KEYWORD_ANALYSIS_RUNNING --> ERROR : failure
    PERSONA_GENERATION_RUNNING --> ERROR : failure
    AWAITING_PERSONA_SELECTION --> ERROR : user_cancels
    --> ERROR
6.2. ユーザーインタラクションAWAITING_... の状態になったとき、WorkflowManagerは処理を一時停止し、CLIに制御を返す。CLIはユーザーに入力を促し、その結果でContextを更新した後、WorkflowManagerの実行を再開する。7. CLIアプリケーション設計 (cli/main.py)Typerとrichライブラリを活用し、対話的で分かりやすいCLIを構築する。7.1. コマンドpython -m cli.main generate --keywords "キーワード1" --keywords "キーワード2" --persona "ペルソナの概要" --company-id "..." --style-template-id "..."
7.2. 実行例$ python -m cli.main generate -k "SEO記事" -k "自動生成" -p "中小企業のマーケティング担当者"

🚀 ワークフローを開始します...
✅ キーワード分析が完了しました。
✅ ペルソナ生成が完了しました。

👤 ペルソナを選択してください:
  [1] 田中さん (35歳、Webマーケティング担当) - 記事作成の時間短縮と品質向上に課題。
  [2] 鈴木さん (42歳、経営者兼マーケター) - 専門知識はないが、自社の認知度向上を目指す。
番号を選択してください: 1

✅ ペルソナを選択しました。テーマ生成を開始します...
...
8. 技術選定分類ライブラリ/ツール目的エージェントフレームワークopenai-agentsReActループ、ツール利用、構造化出力の実現CLITyper, rich高機能で使いやすいコマンドラインインターフェースの構築データ検証Pydantic厳密な型定義によるデータ整合性の確保非同期処理asyncio外部API呼び出しなどを非同期で効率的に実行プロンプト管理Markdownファイルプロンプトとコードを分離し、管理を容易にする環境変数管理python-dotenvAPIキーなどの機密情報を安全に管理9. 今後の拡張性FastAPIへの統合: WorkflowManagerとcoreロジックはそのままに、cli層をFastAPIのルーターに置き換えることで、容易にWeb API化が可能。WebSocketやSupabase Realtimeと連携し、リアルタイムな進捗通知を実現する。エージェントの動的追加: 新しい機能（例: 画像生成エージェント、SNS投稿エージェント）をcore/agentsに追加し、WorkflowManagerに状態を追加するだけで、容易にフローを拡張できる。学習・改善機能: 実行ログをデータベースに保存し、エージェントのパフォーマンスやプロンプトの効果を分析する。成功/失敗パターンからプロンプトを自動的に改善するような、自己学習ループの導入も視野に入れる。