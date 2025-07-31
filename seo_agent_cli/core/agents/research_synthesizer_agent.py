from typing import List
from core.context import ArticleGenerationContext, WorkflowState
from core.schemas import ResearchReport
from prompts import load_prompt

# モックアシスタント
class MockAssistant:
    def __init__(self, **kwargs):
        print(f"--- MockAssistant created with name: {kwargs.get('name')} ---")

    def run(self, user_message: str) -> ResearchReport:
        print(f"--- MockAssistant starting run for synthesis ---")
        
        # 1. 思考: 提供された複数のレポートを読み解き、重複を排除し、主要なテーマを特定する
        print("  - Thinking: I need to synthesize all the individual research reports into one cohesive document.")
        print("  - Thinking: I will identify overlapping information, extract the most important key findings, and create a comprehensive summary.")
        
        # 2. 最終出力: 思考結果を単一のResearchReportとして構造化する
        print("  - Responding: Generating the final synthesized research report.")
        
        # ダミーデータを作成
        synthesized_report = ResearchReport(
            query="Synthesized Research for Article",
            summary=(
                "AIによるSEO記事の自動生成は、適切なツール（X, Y, Zなど）の選定と、"
                "高品質なコンテンツを担保するためのプロンプトエンジニアリング、そして編集・校正プロセスが鍵となる。"
                "専門家は、AIの効率性を認めつつも、独自性や著作権に関する注意喚起を行っている。"
            ),
            key_findings=[
                "主要ツールとしては、APIベースのGPT-4と、SaaS型のAIライターが存在する。",
                "高品質化のコツは、具体的なペルソナ設定と、明確な指示を与えるプロンプトにある。",
                "SEO効果を測定するには、順位変動だけでなく、エンゲージメント率やコンバージョン率も追跡する必要がある。",
                "AIが生成したコンテンツは、必ず人間によるファクトチェックと編集校正を経るべきである。",
                "生成物の著作権は、利用するツールの規約に大きく依存するため、商用利用の際は注意が必要。",
            ],
            sources=["https://example.com/source1", "https://example.com/source2", "https://example.com/source3"] # 本来は全レポートのソースを統合
        )
        return synthesized_report

class ResearchSynthesizerAgent:
    """
    全ての調査結果を統合し、包括的な一つのレポートを作成するエージェント。
    """
    def __init__(self, context: ArticleGenerationContext):
        self.context = context

    def run(self) -> ArticleGenerationContext:
        """
        エージェントの主処理を実行し、統合されたレポートでコンテキストを更新する。
        """
        print("===== Running ResearchSynthesizerAgent =====")
        self.context.state = WorkflowState.RESEARCH_SYNTHESIS_RUNNING

        if not self.context.research_reports:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = "ResearchReports are missing."
            print("===== ResearchSynthesizerAgent Failed: Missing research_reports =====")
            return self.context

        # 1. プロンプトを準備
        try:
            prompt = load_prompt("research_synthesizer")
        except FileNotFoundError as e:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = str(e)
            return self.context
            
        # 2. Assistant を設定 (モック)
        assistant = MockAssistant(
            name="Research Synthesizer Agent",
            instructions=prompt,
            model="gpt-4-turbo-preview",
            # response_format は ResearchReport を想定
        )

        # 3. ReActループを実行
        # 全てのレポートを結合して入力メッセージを作成
        reports_json = [report.model_dump_json() for report in self.context.research_reports]
        user_message = (
            "Please synthesize the following research reports into a single, cohesive, and comprehensive report. "
            "Eliminate duplicates, organize information logically, and create a master summary and a list of key findings.\n\n"
            f"Reports to synthesize:\n[\n" + ",\n".join(reports_json) + "\n]"
        )
        
        try:
            synthesized_report = assistant.run(user_message)
            self.context.synthesized_research_report = synthesized_report
            self.context.state = WorkflowState.OUTLINE_GENERATION_RUNNING
            print("===== ResearchSynthesizerAgent Finished Successfully =====")
        except Exception as e:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = f"An error occurred in ResearchSynthesizerAgent: {e}"
            print(f"===== ResearchSynthesizerAgent Failed: {e} =====")

        return self.context
