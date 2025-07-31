from core.context import WorkflowState
from typing import Dict, Optional

# 状態遷移を定義するディクショナリ
# Key: 現在の状態
# Value: { "on_success": 次の状態, "on_failure": エラー状態 }
STATE_TRANSITIONS: Dict[WorkflowState, Dict[str, WorkflowState]] = {
    WorkflowState.START: {
        "on_success": WorkflowState.KEYWORD_ANALYSIS_RUNNING,
    },
    WorkflowState.KEYWORD_ANALYSIS_RUNNING: {
        "on_success": WorkflowState.PERSONA_GENERATION_RUNNING,
        "on_failure": WorkflowState.ERROR,
    },
    WorkflowState.PERSONA_GENERATION_RUNNING: {
        "on_success": WorkflowState.AWAITING_PERSONA_SELECTION,
        "on_failure": WorkflowState.ERROR,
    },
    WorkflowState.AWAITING_PERSONA_SELECTION: {
        "on_success": WorkflowState.THEME_GENERATION_RUNNING, # ユーザーが選択した場合
        "on_failure": WorkflowState.ERROR, # ユーザーがキャンセルした場合
    },
    WorkflowState.THEME_GENERATION_RUNNING: {
        "on_success": WorkflowState.AWAITING_THEME_SELECTION,
        "on_failure": WorkflowState.ERROR,
    },
    WorkflowState.AWAITING_THEME_SELECTION: {
        "on_success": WorkflowState.RESEARCH_PLANNING_RUNNING,
        "on_failure": WorkflowState.ERROR,
    },
    WorkflowState.RESEARCH_PLANNING_RUNNING: {
        "on_success": WorkflowState.AWAITING_RESEARCH_PLAN_APPROVAL,
        "on_failure": WorkflowState.ERROR,
    },
    WorkflowState.AWAITING_RESEARCH_PLAN_APPROVAL: {
        "on_success": WorkflowState.RESEARCH_EXECUTION_RUNNING,
        "on_failure": WorkflowState.ERROR,
    },
    WorkflowState.RESEARCH_EXECUTION_RUNNING: {
        "on_success": WorkflowState.RESEARCH_SYNTHESIS_RUNNING,
        "on_failure": WorkflowState.ERROR,
    },
    WorkflowState.RESEARCH_SYNTHESIS_RUNNING: {
        "on_success": WorkflowState.OUTLINE_GENERATION_RUNNING,
        "on_failure": WorkflowState.ERROR,
    },
    WorkflowState.OUTLINE_GENERATION_RUNNING: {
        "on_success": WorkflowState.AWAITING_OUTLINE_APPROVAL,
        "on_failure": WorkflowState.ERROR,
    },
    WorkflowState.AWAITING_OUTLINE_APPROVAL: {
        "on_success": WorkflowState.SECTION_WRITING_RUNNING,
        "on_failure": WorkflowState.ERROR,
    },
    WorkflowState.SECTION_WRITING_RUNNING: {
        "on_success": WorkflowState.EDITING_RUNNING,
        "on_failure": WorkflowState.ERROR,
    },
    WorkflowState.EDITING_RUNNING: {
        "on_success": WorkflowState.COMPLETED,
        "on_failure": WorkflowState.ERROR,
    },
}

class StateMachine:
    """
    ワークフローの状態遷移を管理するクラス。
    """
    def get_next_state(self, current_state: WorkflowState, event: str = "on_success") -> Optional[WorkflowState]:
        """
        現在の状態とイベントに基づいて次の状態を返す。

        :param current_state: 現在のワークフローの状態。
        :param event: 発生したイベント ("on_success" または "on_failure")。
        :return: 次のワークフローの状態。遷移先がなければNone。
        """
        transitions = STATE_TRANSITIONS.get(current_state)
        if transitions:
            return transitions.get(event)
        return None

    def is_user_interaction_required(self, state: WorkflowState) -> bool:
        """
        指定された状態がユーザーの入力を待つ状態かどうかを判定する。
        """
        return state.name.startswith("AWAITING_")

    def is_terminal_state(self, state: WorkflowState) -> bool:
        """
        指定された状態が終了状態（COMPLETEDまたはERROR）かどうかを判定する。
        """
        return state in [WorkflowState.COMPLETED, WorkflowState.ERROR]
