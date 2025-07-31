from typing import List
from core.context import ArticleGenerationContext, WorkflowState
from core.schemas import ResearchPlan, ResearchQuery, ResearchReport
from core.tools.serpapi_tool import search_google_and_scrape, SerpAnalysisResult
from prompts import load_prompt

# モックアシスタント
class MockAssistant:
    def __init__(self, **kwargs):
        print(f"--- MockAssistant created with name: {kwargs.get('name')} ---")
        self.tools = {tool.__name__: tool for tool in kwargs.get('tools', [])}

    def run(self, user_message: str, query: ResearchQuery) -> ResearchReport:
        print(f"--- MockAssistant starting run for query: '{query.query}' ---")
        
        # 1. 思考: ツールを使って情報を検索する必要があると判断
        print(f"  - Thinking: I need to research '{query.query}'. I will use the 'search_google_and_scrape' tool.")
        
        # 2. 行動: ツールを実行
        tool_result: SerpAnalysisResult = self.tools['search_google_and_scrape'](keywords=[query.query], num_articles_to_scrape=2)
        print(f"  - Acting: Executed 'search_google_and_scrape'. Got {len(tool_result.organic_results)} results.")

        # 3. 観察 & 思考: 結果を要約し、キーポイントを抽出する
        print("  - Observing & Thinking: The tool results are in. I will now synthesize this into a ResearchReport.")
        
        # 4. 最終出力: 構造化されたレポートを生成 (ダミーデータ)
        report = ResearchReport(
            query=query.query,
            summary=f"'{query.query}'に関する調査結果の要約です。主要なツールはX, Y, Zで、専門家はAとBの重要性を指摘しています。",
            key_findings=[
                "主要な論点1",
                "注目すべきデータや統計2",
                "専門家の意見3"
            ],
            sources=[res.link for res in tool_result.organic_results]
        )
        print(f"  - Responding: Generated the research report for '{query.query}'.")
        return report

class ResearcherAgent:
    """
    調査計画に基づき、検索クエリを一つずつ実行し、情報を収集・要約するエージェント。
    """
    def __init__(self, context: ArticleGenerationContext):
        self.context = context

    def run(self) -> ArticleGenerationContext:
        """
        エージェントの主処理を実行し、調査レポートでコンテキストを更新する。
        """
        print("===== Running ResearcherAgent =====")
        self.context.state = WorkflowState.RESEARCH_EXECUTION_RUNNING

        if not self.context.research_plan:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = "ResearchPlan is missing."
            print("===== ResearcherAgent Failed: Missing research_plan =====")
            return self.context

        # 1. プロンプトとツールを準備
        try:
            prompt = load_prompt("researcher")
        except FileNotFoundError as e:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = str(e)
            return self.context
            
        tools = [search_google_and_scrape]

        # 2. Assistant を設定 (モック)
        # このアシスタントはループ内でクエリごとに使われる
        assistant = MockAssistant(
            name="Single Query Researcher",
            instructions=prompt,
            tools=tools,
            model="gpt-4-turbo-preview",
            # response_format は ResearchReport を想定
        )

        # 3. 計画の各クエリに対してReActループを実行
        all_reports: List[ResearchReport] = []
        total_queries = len(self.context.research_plan.queries)
        for i, query in enumerate(self.context.research_plan.queries):
            print(f"--- Researching query {i+1}/{total_queries}: '{query.query}' ---")
            user_message = (
                f"Please research the following query and provide a structured report. "
                f"Focus on extracting key findings and reliable sources.\n\n"
                f"Query: {query.query}\n"
                f"Source Type: {query.source}"
            )
            
            try:
                report = assistant.run(user_message, query)
                all_reports.append(report)
            except Exception as e:
                self.context.state = WorkflowState.ERROR
                self.context.error_message = f"An error occurred during research for query '{query.query}': {e}"
                print(f"===== ResearcherAgent Failed during query '{query.query}': {e} =====")
                return self.context
        
        self.context.research_reports = all_reports
        self.context.state = WorkflowState.RESEARCH_SYNTHESIS_RUNNING
        print("===== ResearcherAgent Finished Successfully =====")
        return self.context
