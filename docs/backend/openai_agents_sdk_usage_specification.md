# OpenAI Agents SDKの利用仕様

## 概要

このドキュメントでは、SEO記事生成システムにおいて`openai-agents` SDKを活用したエージェント実行の仕様について詳細に解説します。OpenAI Agents SDKは、複雑な多段階AIワークフローを構築するための強力なフレームワークであり、本システムでは記事生成の各ステップで専門化されたエージェントを使用して高品質なコンテンツを生成しています。

## 技術概要

### OpenAI Agents SDK の特徴
- **構造化された会話管理**: 複雑な対話フローの管理
- **ツール統合**: Web検索、API呼び出し等の外部ツールとの連携
- **ストリーミング対応**: リアルタイムなレスポンス生成
- **トレーシング機能**: 実行ログと パフォーマンス分析
- **エラーハンドリング**: 堅牢なエラー処理と復旧機能

### システム内での役割
1. **記事生成プロセスの自動化**: 各段階での専門エージェント実行
2. **品質保証**: 構造化された出力と検証機能
3. **拡張性**: 新しいエージェントタイプの追加が容易
4. **監視性**: 詳細な実行ログとメトリクス

## SDK 設定とセットアップ

### 初期設定（core/config.py）

```python
from agents import (
    set_default_openai_key, 
    set_tracing_disabled,
    set_tracing_export_api_key,
    enable_verbose_stdout_logging
)

def setup_agents_sdk():
    """OpenAI Agents SDKのセットアップ"""
    try:
        # API キーが設定されていない場合はスキップ
        if not settings.openai_api_key:
            print("OpenAI API キーが設定されていません。SDK設定をスキップします。")
            return

        # OpenAI APIキーを設定
        set_default_openai_key(settings.openai_api_key)
        print(f"OpenAI API キーを設定しました: {settings.openai_api_key[:8]}...")
        
        # トレーシング設定
        if settings.enable_tracing:
            # トレーシング用のAPIキーを設定（同じキーを使用）
            set_tracing_export_api_key(settings.openai_api_key)
            print("OpenAI Agents SDK トレーシングAPIキーを設定しました")
            
            # 機密データログ設定を環境変数で制御
            if settings.trace_include_sensitive_data:
                # 機密データを含める場合は環境変数をクリア
                os.environ.pop("OPENAI_AGENTS_DONT_LOG_MODEL_DATA", None)
                os.environ.pop("OPENAI_AGENTS_DONT_LOG_TOOL_DATA", None)
                print("トレーシングで機密データを含めるように設定しました")
            else:
                # 機密データを除外する場合は環境変数を設定
                os.environ["OPENAI_AGENTS_DONT_LOG_MODEL_DATA"] = "1"
                os.environ["OPENAI_AGENTS_DONT_LOG_TOOL_DATA"] = "1"
                print("トレーシングで機密データを除外するように設定しました")
            
            print("OpenAI Agents SDK トレーシングが有効化されました")
        else:
            # トレーシングを無効化
            set_tracing_disabled(True)
            print("OpenAI Agents SDK トレーシングが無効化されました")
        
        # 詳細ログを有効化（デバッグ時のみ）
        if settings.debug:
            enable_verbose_stdout_logging()
            print("OpenAI Agents SDK デバッグログが有効化されました")
            
    except ImportError as e:
        print(f"OpenAI Agents SDKのインポートに失敗しました: {e}")
        print("pip install openai-agents を実行してください")
    except Exception as e:
        print(f"OpenAI Agents SDKのセットアップに失敗しました: {e}")
```

### 設定パラメータ

| パラメータ | 説明 | デフォルト値 | 環境変数 |
|-----------|------|-------------|----------|
| `model_for_agents` | エージェント実行に使用するモデル | `gpt-4o-mini` | `MODEL_FOR_AGENTS` |
| `serp_analysis_model` | SerpAPI分析エージェント用モデル | `RESEARCH_MODEL` の値 (`gpt-5-mini`) | `SERP_ANALYSIS_MODEL` |
| `persona_model` | ペルソナ生成エージェント用モデル | `WRITING_MODEL` の値 (`gpt-4o-mini`) | `PERSONA_MODEL` |
| `theme_model` | テーマ生成エージェント用モデル | `WRITING_MODEL` の値 (`gpt-4o-mini`) | `THEME_MODEL` |
| `max_turns_for_agents` | エージェントの最大ターン数 | `10` | `MAX_TURNS_FOR_AGENTS` |
| `enable_tracing` | トレーシング機能の有効化 | `true` | `OPENAI_AGENTS_ENABLE_TRACING` |
| `trace_include_sensitive_data` | 機密データのトレーシング含有 | `false` | `OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA` |

## エージェント定義と役割

### エージェント一覧

本システムでは、記事生成プロセスの各段階に特化した8つの専門エージェントを定義しています。

| エージェント名 | 役割 | 使用ステップ | 出力形式 |
|---------------|------|-------------|----------|
| `serp_keyword_analysis_agent` | SerpAPIによるキーワード分析 | `keyword_analyzing` | `SerpKeywordAnalysisReport` |
| `persona_generator_agent` | 具体的なペルソナ生成 | `persona_generating` | `GeneratedPersonasResponse` |
| `theme_agent` | SEOテーマ案生成 | `theme_generating` | `ThemeProposal` |
| `research_planner_agent` | リサーチ計画立案 | `research_planning` | `ResearchPlan` |
| `researcher_agent` | Web検索・情報収集 | `researching` | `ResearchQueryResult` |
| `research_synthesizer_agent` | リサーチ結果統合 | `research_synthesizing` | `ResearchReport` |
| `outline_agent` | 記事アウトライン生成 | `outline_generating` | `Outline` |
| `section_writer_agent` | セクション執筆 | `writing_sections` | `ArticleSection` |
| `section_writer_with_images_agent` | 画像付きセクション執筆 | `writing_sections` (画像モード) | `ArticleSectionWithImages` |
| `editor_agent` | 最終編集・校正 | `editing` | `RevisedArticle` |

### エージェント定義の構造

#### 基本的なエージェント定義
```python
from agents import Agent, ModelSettings

# 基本設定
model_settings = ModelSettings(
    model=settings.model_for_agents,
    temperature=0.7,
    max_tokens=4000
)

# テーマ生成エージェント
theme_agent = Agent(
    name="ThemeGenerationAgent",
    model=model_settings,
    instructions="""
    あなたは優秀なSEOライターです。提供されたキーワードとペルソナ情報に基づいて、
    検索エンジンで上位表示されやすく、ターゲット読者に刺さるテーマ案を生成してください。
    
    # 出力要件
    - 提案数: 指定された数のテーマ案を生成
    - SEO最適化: キーワードを適切に含む
    - 読者訴求: ペルソナの課題や関心に対応
    - 独自性: 競合との差別化を意識
    
    # 出力形式
    ThemeProposal 形式のJSONで出力してください。
    """,
    response_format=ThemeProposal
)
```

#### ツール統合エージェント
```python
from agents import Agent, ModelSettings
from .tools import web_search_tool, analyze_competitors

# Web検索機能付きリサーチエージェント
researcher_agent = Agent(
    name="ResearchAgent",
    model=model_settings,
    instructions="""
    あなたは詳細なWeb検索を行う調査員です。提供されたクエリに基づいて、
    信頼性が高く最新の情報を収集し、構造化された形で報告してください。
    
    # 検索方針
    - 複数の信頼できる情報源からデータを収集
    - 情報の正確性と鮮度を重視
    - 著作権に配慮した引用
    
    # 出力要件
    - 各情報にソースURLを明記
    - 情報の要約と原文の区別を明確化
    - 関連度の高い情報を優先
    """,
    tools=[web_search_tool, analyze_competitors],
    response_format=ResearchQueryResult
)
```

#### ストリーミング対応エージェント
```python
# セクション執筆エージェント（ストリーミング出力）
section_writer_agent = Agent(
    name="SectionWriterAgent",
    model=ModelSettings(
        model=settings.writing_model,
        temperature=0.8,
        max_tokens=2000,
        stream=True  # ストリーミング有効化
    ),
    instructions="""
    あなたは経験豊富なWebライターです。提供されたアウトラインに基づいて、
    読みやすく情報価値の高いセクションを執筆してください。
    
    # 執筆方針
    - HTML形式での出力
    - 適切な見出し構造（h2, h3タグ）
    - 読みやすい段落構成
    - SEOキーワードの自然な組み込み
    
    # スタイルガイド
    設定されたスタイルガイドに従い、一貫したトーンで執筆してください。
    """,
    response_format=ArticleSection
)
```

### コンテキスト情報の活用

各エージェントは、`ArticleContext`から関連する情報を動的に取得し、プロンプトに組み込みます。

#### コンテキスト構築関数
```python
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
    
    # ブランディング情報
    if hasattr(ctx, 'company_brand_slogan') and ctx.company_brand_slogan:
        company_parts.append(f"ブランドスローガン: {ctx.company_brand_slogan}")
    
    # SEO・コンテンツ戦略
    if hasattr(ctx, 'company_target_keywords') and ctx.company_target_keywords:
        company_parts.append(f"重要キーワード: {ctx.company_target_keywords}")
    
    return "\n".join(company_parts)

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
        
        style_parts.append("**重要: 上記のカスタムスタイルガイドに従って執筆してください。**")
        
        return "\n".join(style_parts)
    
    elif hasattr(ctx, 'company_style_guide') and ctx.company_style_guide:
        # 従来の会社スタイルガイドがある場合
        return f"=== 会社スタイルガイド ===\n文体・トンマナ: {ctx.company_style_guide}"
    
    else:
        # デフォルトスタイル
        return "=== デフォルトスタイルガイド ===\n親しみやすく分かりやすい文章で、読者に寄り添うトーン。"
```

## エージェント実行機能

### Runner による実行制御

#### 標準実行
```python
from agents import Runner, RunConfig, trace

async def run_agent(
    self, 
    agent: Agent, 
    agent_input: str, 
    context: ArticleContext, 
    run_config: RunConfig
) -> Any:
    """エージェントの標準実行"""
    
    workflow_name = f"article_generation_{context.process_id}"
    trace_id = f"{context.process_id}_{agent.name}_{int(time.time())}"
    group_id = context.process_id or "unknown"
    
    # トレーシング開始
    with safe_trace_context(workflow_name, trace_id, group_id):
        with safe_custom_span(f"agent_execution_{agent.name}"):
            try:
                async with Runner(agent=agent, run_config=run_config) as runner:
                    # エージェント実行
                    result = await runner.run(user_message=agent_input)
                    
                    # 結果の検証
                    if result and hasattr(result, 'content'):
                        logger.info(f"✅ Agent {agent.name} completed successfully")
                        return result.content
                    else:
                        logger.warning(f"⚠️ Agent {agent.name} returned empty result")
                        return None
                        
            except MaxTurnsExceeded as e:
                logger.error(f"❌ Agent {agent.name} exceeded max turns: {e}")
                raise
            except ModelBehaviorError as e:
                logger.error(f"❌ Agent {agent.name} model behavior error: {e}")
                raise
            except Exception as e:
                logger.error(f"❌ Agent {agent.name} execution failed: {e}")
                raise
```

#### ストリーミング実行
```python
async def run_agent_streaming(
    self, 
    agent: Agent, 
    agent_input: str, 
    context: ArticleContext, 
    run_config: RunConfig, 
    section_index: int
) -> Any:
    """エージェントのストリーミング実行（セクション執筆用）"""
    
    accumulated_content = ""
    
    try:
        async with Runner(agent=agent, run_config=run_config) as runner:
            # ストリーミング実行
            async for chunk in runner.run_stream(user_message=agent_input):
                if chunk.content:
                    accumulated_content += chunk.content
                    
                    # リアルタイムでHTMLチャンクを送信
                    chunk_payload = SectionChunkPayload(
                        section_index=section_index,
                        heading=context.generated_outline.sections[section_index].heading,
                        html_content_chunk=chunk.content,
                        is_complete=False,
                        is_image_mode=context.image_mode
                    )
                    await self.service.utils.send_server_event(context, chunk_payload)
            
            # 最終結果の処理
            final_result = runner.result
            if final_result and hasattr(final_result, 'content'):
                logger.info(f"✅ Streaming agent {agent.name} completed")
                
                # セクション完了通知
                final_payload = SectionChunkPayload(
                    section_index=section_index,
                    heading=context.generated_outline.sections[section_index].heading,
                    html_content_chunk="",
                    is_complete=True,
                    section_complete_content=final_result.content,
                    is_image_mode=context.image_mode
                )
                await self.service.utils.send_server_event(context, final_payload)
                
                return final_result.content
            else:
                logger.warning(f"⚠️ Streaming agent {agent.name} returned empty result")
                return None
                
    except Exception as e:
        logger.error(f"❌ Streaming agent {agent.name} execution failed: {e}")
        raise
```

### RunConfig 設定

```python
from agents import RunConfig, ModelSettings

def create_run_config(context: ArticleContext) -> RunConfig:
    """実行設定を作成"""
    
    return RunConfig(
        # モデル設定
        model=ModelSettings(
            model=settings.model_for_agents,
            temperature=0.7,
            max_tokens=4000
        ),
        
        # 実行制御
        max_turns=settings.max_turns_for_agents,
        
        # デバッグ設定
        debug=settings.debug,
        
        # タイムアウト設定
        timeout=300,  # 5分
        
        # レスポンス形式検証
        validate_response=True
    )
```

## 外部ツール連携

### Web検索ツール

```python
from agents.tools import web_search_tool

# Web検索ツールの設定例
web_search_tool = WebSearchTool(
    name="web_search",
    description="Webサイトから情報を検索・取得する",
    parameters={
        "query": "検索クエリ",
        "max_results": "最大結果数（デフォルト: 5）",
        "language": "検索言語（デフォルト: ja）"
    }
)

# エージェントでの使用例
research_agent = Agent(
    name="ResearchAgent",
    instructions="""
    Web検索ツールを使用して、指定されたトピックについて詳細な調査を行ってください。
    信頼できる情報源から最新の情報を収集し、適切に引用してください。
    """,
    tools=[web_search_tool],
    response_format=ResearchQueryResult
)
```

### 競合分析ツール

```python
from agents.tools import analyze_competitors

# 競合分析ツールの実装例
async def analyze_competitors(query: str, top_n: int = 10) -> List[Dict[str, Any]]:
    """SerpAPIを使用した競合記事分析"""
    
    try:
        # SerpAPI呼び出し
        search_params = {
            "q": query,
            "hl": "ja",
            "gl": "jp",
            "num": top_n
        }
        
        search = GoogleSearch(search_params)
        results = search.get_dict()
        
        # 結果の構造化
        competitor_analysis = []
        for result in results.get("organic_results", []):
            analysis = {
                "title": result.get("title", ""),
                "url": result.get("link", ""),
                "snippet": result.get("snippet", ""),
                "position": result.get("position", 0),
                "domain": extract_domain(result.get("link", "")),
                "estimated_length": estimate_content_length(result.get("snippet", ""))
            }
            competitor_analysis.append(analysis)
        
        return competitor_analysis
        
    except Exception as e:
        logger.error(f"競合分析エラー: {e}")
        return []

# エージェントでの使用
serp_analysis_agent = Agent(
    name="SerpAnalysisAgent",
    instructions="""
    指定されたキーワードでSERP分析を実行し、競合記事の詳細な分析レポートを作成してください。
    検索上位の記事の特徴、コンテンツギャップ、差別化のポイントを特定してください。
    """,
    tools=[analyze_competitors],
    response_format=SerpKeywordAnalysisReport
)
```

## トークン使用量と会話履歴の管理

### 使用量追跡

```python
class TokenUsageTracker:
    """トークン使用量の追跡"""
    
    def __init__(self):
        self.usage_log: List[Dict[str, Any]] = []
    
    async def track_agent_execution(
        self, 
        agent_name: str, 
        runner: Runner, 
        context: ArticleContext
    ):
        """エージェント実行のトークン使用量を記録"""
        
        if hasattr(runner, 'usage_info'):
            usage = runner.usage_info
            
            usage_record = {
                "agent_name": agent_name,
                "process_id": context.process_id,
                "step": context.current_step,
                "timestamp": datetime.now(timezone.utc),
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "model": usage.get("model", "unknown"),
                "cost_estimate": self.calculate_cost(usage)
            }
            
            self.usage_log.append(usage_record)
            
            # ログシステムに送信
            if context.process_id:
                await self.log_to_database(usage_record)
    
    def calculate_cost(self, usage: Dict[str, Any]) -> float:
        """トークン使用量からコストを概算"""
        model = usage.get("model", "gpt-4o-mini")
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        
        # モデル別料金設定（例：gpt-4o-mini）
        pricing = {
            "gpt-4o-mini": {
                "input": 0.000150 / 1000,   # $0.150 per 1K tokens
                "output": 0.000600 / 1000   # $0.600 per 1K tokens
            },
            "gpt-4o": {
                "input": 0.0025 / 1000,     # $2.50 per 1K tokens  
                "output": 0.0100 / 1000     # $10.00 per 1K tokens
            }
        }
        
        if model in pricing:
            cost = (input_tokens * pricing[model]["input"] + 
                   output_tokens * pricing[model]["output"])
            return round(cost, 6)
        
        return 0.0

# 使用例
token_tracker = TokenUsageTracker()

async with Runner(agent=agent, run_config=run_config) as runner:
    result = await runner.run(user_message=agent_input)
    
    # トークン使用量を記録
    await token_tracker.track_agent_execution(agent.name, runner, context)
```

### 会話履歴の抽出

```python
def extract_conversation_history(runner: Runner) -> List[Dict[str, Any]]:
    """Runnerから会話履歴を抽出"""
    
    conversation_history = []
    
    if hasattr(runner, 'messages'):
        for message in runner.messages:
            history_item = {
                "role": message.get("role", "unknown"),
                "content": message.get("content", ""),
                "timestamp": message.get("timestamp", datetime.now().isoformat()),
                "token_count": len(str(message.get("content", ""))) // 4  # 概算
            }
            conversation_history.append(history_item)
    
    return conversation_history

# セクション執筆での履歴管理例
def add_to_section_writer_history(context: ArticleContext, role: str, content: str):
    """セクション執筆エージェントの履歴を追加"""
    
    content_type = "output_text" if role == "assistant" else "input_text"
    if role in ["system", "developer"]:
        content_type = "input_text"
    
    message = {
        "role": role,
        "content": [{"type": content_type, "text": content}],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    context.section_writer_history.append(message)
    
    # 履歴サイズ制限（メモリ効率化）
    if len(context.section_writer_history) > 50:
        context.section_writer_history.pop(0)
```

## エラーハンドリングと復旧

### エージェント固有のエラー処理

```python
from agents.exceptions import MaxTurnsExceeded, ModelBehaviorError, UserError

async def handle_agent_error(
    agent_name: str, 
    error: Exception, 
    context: ArticleContext,
    retry_count: int = 0,
    max_retries: int = 3
) -> Optional[Any]:
    """エージェント実行エラーのハンドリング"""
    
    logger.error(f"Agent {agent_name} error (attempt {retry_count + 1}): {error}")
    
    if isinstance(error, MaxTurnsExceeded):
        # ターン数超過：より短い入力で再実行
        if retry_count < max_retries:
            logger.info(f"Retrying {agent_name} with reduced input length")
            return await retry_with_reduced_input(agent_name, context, retry_count + 1)
        else:
            raise Exception(f"Agent {agent_name} consistently exceeded max turns")
    
    elif isinstance(error, ModelBehaviorError):
        # モデル動作エラー：異なる設定で再実行
        if retry_count < max_retries:
            logger.info(f"Retrying {agent_name} with different model settings")
            return await retry_with_different_settings(agent_name, context, retry_count + 1)
        else:
            raise Exception(f"Agent {agent_name} model behavior consistently problematic")
    
    elif isinstance(error, UserError):
        # ユーザーエラー：入力を修正して再実行
        logger.info(f"Fixing user input for agent {agent_name}")
        return await retry_with_fixed_input(agent_name, error, context)
    
    else:
        # その他のエラー：基本的なリトライ
        if retry_count < max_retries:
            logger.info(f"Basic retry for agent {agent_name} (attempt {retry_count + 1})")
            await asyncio.sleep(2 ** retry_count)  # 指数バックオフ
            return await retry_agent_execution(agent_name, context, retry_count + 1)
        else:
            raise Exception(f"Agent {agent_name} failed after {max_retries} retries: {error}")

async def retry_with_reduced_input(agent_name: str, context: ArticleContext, retry_count: int) -> Any:
    """入力を短縮してエージェントを再実行"""
    
    # 入力テキストを段階的に短縮
    reduction_factor = 0.8 ** retry_count
    
    # エージェント固有の入力短縮ロジック
    if agent_name == "ThemeGenerationAgent":
        # テーマ生成：ペルソナ情報を簡略化
        simplified_persona = simplify_persona_description(context.selected_detailed_persona, reduction_factor)
        agent_input = create_simplified_theme_input(context, simplified_persona)
    elif agent_name == "SectionWriterAgent":
        # セクション執筆：参考情報を削減
        reduced_research = reduce_research_context(context.research_report, reduction_factor)
        agent_input = create_section_input_with_reduced_context(context, reduced_research)
    else:
        # 汎用的な短縮
        agent_input = create_generic_reduced_input(context, reduction_factor)
    
    # 短縮された入力で再実行
    agent = get_agent_by_name(agent_name)
    run_config = create_run_config(context)
    
    return await run_agent(agent, agent_input, context, run_config)
```

### トレーシングとデバッグ支援

```python
def safe_trace_context(workflow_name: str, trace_id: str, group_id: str):
    """トレーシングエラーを安全にハンドリングするコンテキストマネージャー"""
    try:
        return trace(workflow_name=workflow_name, trace_id=trace_id, group_id=group_id)
    except Exception as e:
        logger.warning(f"トレーシング初期化に失敗しました: {e}")
        from contextlib import nullcontext
        return nullcontext()

def safe_custom_span(name: str, data: dict[str, Any] | None = None):
    """カスタムスパンを安全にハンドリングするコンテキストマネージャー"""
    try:
        return custom_span(name=name, data=data)
    except Exception as e:
        logger.warning(f"カスタムスパン作成に失敗しました: {e}")
        from contextlib import nullcontext
        return nullcontext()

# エージェント実行時のトレーシング例
async def run_agent_with_tracing(
    agent: Agent, 
    agent_input: str, 
    context: ArticleContext, 
    run_config: RunConfig
) -> Any:
    """トレーシング付きエージェント実行"""
    
    workflow_name = f"article_generation_{context.process_id}"
    trace_id = f"{context.process_id}_{agent.name}_{int(time.time())}"
    group_id = context.process_id or "unknown"
    
    with safe_trace_context(workflow_name, trace_id, group_id):
        with safe_custom_span(f"agent_execution_{agent.name}", {
            "agent_name": agent.name,
            "step": context.current_step,
            "input_length": len(agent_input),
            "user_id": context.user_id
        }):
            start_time = time.time()
            
            try:
                result = await run_agent(agent, agent_input, context, run_config)
                
                execution_time = time.time() - start_time
                logger.info(f"✅ Agent {agent.name} completed in {execution_time:.2f}s")
                
                # 実行メトリクスをトレースに記録
                with safe_custom_span("execution_metrics", {
                    "execution_time": execution_time,
                    "success": True,
                    "output_length": len(str(result)) if result else 0
                }):
                    pass
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"❌ Agent {agent.name} failed after {execution_time:.2f}s: {e}")
                
                # エラーメトリクスをトレースに記録
                with safe_custom_span("execution_error", {
                    "execution_time": execution_time,
                    "success": False,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }):
                    pass
                
                raise
```

## パフォーマンス最適化

### 並列実行

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def run_parallel_research_queries(
    context: ArticleContext, 
    run_config: RunConfig
) -> List[ResearchQueryResult]:
    """リサーチクエリの並列実行"""
    
    queries = context.research_plan.queries
    results = []
    
    # 並列実行数を制限（APIレート制限を考慮）
    semaphore = asyncio.Semaphore(3)
    
    async def execute_single_query(query_data) -> ResearchQueryResult:
        async with semaphore:
            agent_input = f"クエリ「{query_data.query}」でWeb検索を実行し、「{query_data.focus}」に関する情報を収集してください。"
            
            return await run_agent(
                researcher_agent, 
                agent_input, 
                context, 
                run_config
            )
    
    # 並列実行
    tasks = [execute_single_query(query) for query in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # エラーハンドリング
    successful_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"Query {i} failed: {result}")
        else:
            successful_results.append(result)
    
    return successful_results
```

### キャッシュ機能

```python
from functools import lru_cache
import hashlib
import json

class AgentResultCache:
    """エージェント実行結果のキャッシュ"""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
    
    def _generate_cache_key(self, agent_name: str, agent_input: str, context_hash: str) -> str:
        """キャッシュキーの生成"""
        key_data = f"{agent_name}:{agent_input}:{context_hash}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_context_hash(self, context: ArticleContext) -> str:
        """コンテキストのハッシュ値を計算"""
        relevant_data = {
            "keywords": context.initial_keywords,
            "persona": context.selected_detailed_persona,
            "company_name": context.company_name,
            "style_guide": getattr(context, 'company_style_guide', None)
        }
        return hashlib.md5(json.dumps(relevant_data, sort_keys=True).encode()).hexdigest()
    
    async def get_cached_result(
        self, 
        agent_name: str, 
        agent_input: str, 
        context: ArticleContext
    ) -> Optional[Any]:
        """キャッシュされた結果を取得"""
        
        context_hash = self._get_context_hash(context)
        cache_key = self._generate_cache_key(agent_name, agent_input, context_hash)
        
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            
            # TTL チェック
            if time.time() - cached_item["timestamp"] < self.ttl_seconds:
                logger.info(f"Cache hit for agent {agent_name}")
                return cached_item["result"]
            else:
                # 期限切れのキャッシュを削除
                del self.cache[cache_key]
        
        return None
    
    async def cache_result(
        self, 
        agent_name: str, 
        agent_input: str, 
        context: ArticleContext, 
        result: Any
    ):
        """結果をキャッシュに保存"""
        
        context_hash = self._get_context_hash(context)
        cache_key = self._generate_cache_key(agent_name, agent_input, context_hash)
        
        # キャッシュサイズ制限
        if len(self.cache) >= self.max_size:
            # 最も古いエントリを削除
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest_key]
        
        self.cache[cache_key] = {
            "result": result,
            "timestamp": time.time(),
            "agent_name": agent_name
        }
        
        logger.info(f"Cached result for agent {agent_name}")

# 使用例
agent_cache = AgentResultCache()

async def run_agent_with_cache(
    agent: Agent, 
    agent_input: str, 
    context: ArticleContext, 
    run_config: RunConfig
) -> Any:
    """キャッシュ付きエージェント実行"""
    
    # キャッシュ確認
    cached_result = await agent_cache.get_cached_result(agent.name, agent_input, context)
    if cached_result is not None:
        return cached_result
    
    # キャッシュミス：エージェント実行
    result = await run_agent(agent, agent_input, context, run_config)
    
    # 結果をキャッシュ
    await agent_cache.cache_result(agent.name, agent_input, context, result)
    
    return result
```

このOpenAI Agents SDKの利用仕様により、複雑な記事生成プロセスを構造化されたAIエージェントワークフローとして実装し、高品質で一貫性のあるコンテンツ生成を実現しています。各エージェントの専門化、外部ツールとの連携、堅牢なエラーハンドリング、パフォーマンス最適化により、実用的で拡張性の高いAIシステムを構築しています。
