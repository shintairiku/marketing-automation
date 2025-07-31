from core.context import ArticleGenerationContext, WorkflowState
from app.state_machine import StateMachine
from core.agents.keyword_analyzer_agent import KeywordAnalyzerAgent
from core.agents.persona_generator_agent import PersonaGeneratorAgent
from core.agents.theme_generator_agent import ThemeGeneratorAgent
from core.agents.research_planner_agent import ResearchPlannerAgent
from core.agents.researcher_agent import ResearcherAgent
from core.agents.research_synthesizer_agent import ResearchSynthesizerAgent
from core.agents.outline_generator_agent import OutlineGeneratorAgent
from core.agents.section_writer_agent import SectionWriterAgent
from core.agents.editor_agent import EditorAgent

class WorkflowManager:
    """
    ワークフロー全体の進行管理とエージェントの呼び出しを行うオーケストレーター。
    """
    def __init__(self, context: ArticleGenerationContext):
        self.context = context
        self.state_machine = StateMachine()
        self.agent_map = {
            WorkflowState.KEYWORD_ANALYSIS_RUNNING: KeywordAnalyzerAgent,
            WorkflowState.PERSONA_GENERATION_RUNNING: PersonaGeneratorAgent,
            WorkflowState.THEME_GENERATION_RUNNING: ThemeGeneratorAgent,
            WorkflowState.RESEARCH_PLANNING_RUNNING: ResearchPlannerAgent,
            WorkflowState.RESEARCH_EXECUTION_RUNNING: ResearcherAgent,
            WorkflowState.RESEARCH_SYNTHESIS_RUNNING: ResearchSynthesizerAgent,
            WorkflowState.OUTLINE_GENERATION_RUNNING: OutlineGeneratorAgent,
            WorkflowState.SECTION_WRITING_RUNNING: SectionWriterAgent,
            WorkflowState.EDITING_RUNNING: EditorAgent,
        }

    def run(self):
        """
        ワークフローの実行を開始し、ユーザーの入力が必要になるか、
        ワークフローが完了するまでエージェントを実行し続ける。
        """
        # 開始状態から最初の実行可能状態へ遷移
        if self.context.state == WorkflowState.START:
            next_state = self.state_machine.get_next_state(self.context.state, "on_success")
            if next_state:
                self.context.state = next_state

        while not self.state_machine.is_terminal_state(self.context.state) and \
              not self.state_machine.is_user_interaction_required(self.context.state):
            
            agent_class = self.agent_map.get(self.context.state)
            
            if not agent_class:
                error_message = f"No agent mapped for state: {self.context.state}"
                print(f"ERROR: {error_message}")
                self.context.state = WorkflowState.ERROR
                self.context.error_message = error_message
                break

            # 実行前の状態を記録
            state_before_run = self.context.state

            # エージェントを実行
            agent = agent_class(self.context)
            self.context = agent.run()

            # エージェントが状態を更新したかチェック
            if self.context.state == state_before_run and self.context.state != WorkflowState.ERROR:
                error_message = f"Agent {agent_class.__name__} did not transition state from {state_before_run}."
                print(f"ERROR: {error_message}")
                self.context.state = WorkflowState.ERROR
                self.context.error_message = error_message
                break
            
            # 状態遷移後の追加処理（もしあれば）
            # 現在はエージェントが状態を完全に管理しているため、ここでは何もしない

        print(f"--- Workflow paused. Current state: {self.context.state} ---")
