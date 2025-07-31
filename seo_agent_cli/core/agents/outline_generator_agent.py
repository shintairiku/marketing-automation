from core.context import ArticleGenerationContext, WorkflowState
from core.schemas import ResearchReport, Theme, ArticleOutline, Section
from prompts import load_prompt

# モックアシスタント
class MockAssistant:
    def __init__(self, **kwargs):
        print(f"--- MockAssistant created with name: {kwargs.get('name')} ---")

    def run(self, user_message: str) -> ArticleOutline:
        print(f"--- MockAssistant starting run for outline generation ---")
        
        # 1. 思考: 調査レポートとテーマを基に、論理的な記事構造を組み立てる
        print("  - Thinking: I need to structure the article logically based on the research and theme.")
        print("  - Thinking: I will create an introduction, several main sections with subsections, and a conclusion.")
        
        # 2. 最終出力: 思考結果をArticleOutlineとして構造化する
        print("  - Responding: Generating the final article outline.")
        
        # ダミーデータを作成
        outline = ArticleOutline(
            title="【担当者向け】AIでSEO記事を自動生成する全手順｜高品質コンテンツを安定供給する秘訣",
            introduction="AIによる記事自動生成の重要性と、本記事で読者が何を得られるかの概説。",
            sections=[
                Section(
                    title="なぜ今、SEO記事の自動生成が重要なのか？",
                    description="コンテンツマーケティングにおける課題（時間、コスト、品質）と、AIがそれをどう解決するのかを解説する。",
                    keywords=["コンテンツマーケティング", "AI", "業務効率化"],
                    subsections=[]
                ),
                Section(
                    title="【実践】AI記事自動生成の5ステップ",
                    description="キーワード選定から公開までの具体的なステップを、ツールを交えながら詳細に解説する。",
                    keywords=["キーワード選定", "ペルソナ設定", "プロンプト", "ファクトチェック", "校正"],
                    subsections=[
                        Section(title="Step 1: 戦略的なキーワード選定", description="...", keywords=[], subsections=[]),
                        Section(title="Step 2: AIにペルソナを深く理解させる", description="...", keywords=[], subsections=[]),
                        Section(title="Step 3: 高品質な出力を引き出すプロンプト術", description="...", keywords=[], subsections=[]),
                        Section(title="Step 4: ファクトチェックと編集・校正", description="...", keywords=[], subsections=[]),
                        Section(title="Step 5: 公開と効果測定", description="...", keywords=[], subsections=[]),
                    ]
                ),
                Section(
                    title="注意点と今後の展望",
                    description="AI生成コンテンツの著作権や独自性に関する注意点を述べ、今後の技術トレンドを予測する。",
                    keywords=["著作権", "独自性", "AI倫理", "今後のトレンド"],
                    subsections=[]
                ),
            ],
            conclusion="本記事で解説したステップの要約と、読者が次にとるべきアクションの提示。"
        )
        return outline

class OutlineGeneratorAgent:
    """
    調査レポートに基づき、記事のアウトラインを作成するエージェント。
    """
    def __init__(self, context: ArticleGenerationContext):
        self.context = context

    def run(self) -> ArticleGenerationContext:
        """
        エージェントの主処理を実行し、生成されたアウトラインでコンテキストを更新する。
        """
        print("===== Running OutlineGeneratorAgent =====")
        self.context.state = WorkflowState.OUTLINE_GENERATION_RUNNING

        if not self.context.synthesized_research_report or not self.context.selected_theme:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = "SynthesizedResearchReport or SelectedTheme is missing."
            print("===== OutlineGeneratorAgent Failed: Missing required context =====")
            return self.context

        # 1. プロンプトを準備
        try:
            prompt = load_prompt("outline_generator")
        except FileNotFoundError as e:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = str(e)
            return self.context
            
        # 2. Assistant を設定 (モック)
        assistant = MockAssistant(
            name="Outline Generator Agent",
            instructions=prompt,
            model="gpt-4-turbo-preview",
            response_format={
                "type": "json_object",
                "schema": ArticleOutline.model_json_schema()
            }
        )

        # 3. ReActループを実行
        user_message = (
            "Based on the following theme and synthesized research, create a detailed and logical article outline. "
            "The outline should be comprehensive enough for a writer to understand what to write in each section.\n\n"
            f"Selected Theme:\n{self.context.selected_theme.model_dump_json(indent=2)}\n\n"
            f"Synthesized Research Report:\n{self.context.synthesized_research_report.model_dump_json(indent=2)}"
        )
        
        try:
            outline = assistant.run(user_message)
            self.context.article_outline = outline
            self.context.state = WorkflowState.AWAITING_OUTLINE_APPROVAL
            print("===== OutlineGeneratorAgent Finished Successfully =====")
        except Exception as e:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = f"An error occurred in OutlineGeneratorAgent: {e}"
            print(f"===== OutlineGeneratorAgent Failed: {e} =====")

        return self.context
