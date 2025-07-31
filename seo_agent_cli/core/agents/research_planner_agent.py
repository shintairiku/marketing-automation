from typing import List
from core.context import ArticleGenerationContext, WorkflowState
from core.schemas import Theme, ResearchPlan, ResearchQuery
from prompts import load_prompt

# モックアシスタント
class MockAssistant:
    def __init__(self, **kwargs):
        print(f"--- MockAssistant created with name: {kwargs.get('name')} ---")

    def run(self, user_message: str) -> ResearchPlan:
        print(f"--- MockAssistant starting run for: {user_message} ---")
        
        # 1. 思考: 選択されたテーマを分解し、どのような情報が必要かを考える
        print("  - Thinking: I need to break down the selected theme into specific research questions.")
        print("  - Thinking: These questions will become the search queries for the next agent.")
        
        # 2. 最終出力: 思考結果をResearchPlanとして構造化する
        print("  - Responding: Generating the final research plan.")
        
        # ダミーデータを作成
        queries = [
            ResearchQuery(query="AI SEO記事 自動生成 ツール 比較", source="Google Search"),
            ResearchQuery(query="高品質なAIコンテンツを作成するコツ", source="専門家のブログ"),
            ResearchQuery(query="AIライティング SEO効果測定 事例", source="Google Search"),
            ResearchQuery(query="AI生成コンテンツの編集・校正プロセス", source="専門家のブログ"),
            ResearchQuery(query="AIライティング 著作権 問題点", source="Google Search"),
        ]
        
        return ResearchPlan(queries=queries)

class ResearchPlannerAgent:
    """
    選択されたテーマに基づき、調査計画（検索クエリ群）を立案するエージェント。
    """
    def __init__(self, context: ArticleGenerationContext):
        self.context = context

    def run(self) -> ArticleGenerationContext:
        """
        エージェントの主処理を実行し、生成された調査計画でコンテキストを更新する。
        """
        print("===== Running ResearchPlannerAgent =====")
        self.context.state = WorkflowState.RESEARCH_PLANNING_RUNNING

        if not self.context.selected_theme:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = "SelectedTheme is missing."
            print("===== ResearchPlannerAgent Failed: Missing selected_theme =====")
            return self.context

        # 1. プロンプトを準備
        try:
            prompt = load_prompt("research_planner")
        except FileNotFoundError as e:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = str(e)
            return self.context
            
        # 2. Assistant を設定 (モック)
        assistant = MockAssistant(
            name="Research Planner Agent",
            instructions=prompt,
            model="gpt-4-turbo-preview",
            response_format={
                "type": "json_object",
                "schema": ResearchPlan.model_json_schema()
            }
        )

        # 3. ReActループを実行
        user_message = (
            f"Based on the following theme, create a detailed research plan. "
            f"The plan should be a list of precise search queries to gather all necessary information to write the article.\n\n"
            f"Selected Theme:\n{self.context.selected_theme.model_dump_json(indent=2)}"
        )
        
        try:
            plan = assistant.run(user_message)
            self.context.research_plan = plan
            self.context.state = WorkflowState.AWAITING_RESEARCH_PLAN_APPROVAL
            print("===== ResearchPlannerAgent Finished Successfully =====")
        except Exception as e:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = f"An error occurred in ResearchPlannerAgent: {e}"
            print(f"===== ResearchPlannerAgent Failed: {e} =====")

        return self.context
