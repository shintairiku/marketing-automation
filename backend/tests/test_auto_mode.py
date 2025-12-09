import pytest

from app.domains.seo_article.context import ArticleContext
from app.domains.seo_article.schemas import (
    OutlineData,
    OutlineSectionData,
    ThemeProposalData,
)
from app.domains.seo_article.services.background_task_manager import (
    BackgroundTaskManager,
)


class _DummyService:
    """Minimal service stub for BackgroundTaskManager."""

    def __init__(self):
        class _DummyPersistence:
            async def save_context_to_db(self, *args, **kwargs):
                return None

        self.persistence_service = _DummyPersistence()


@pytest.mark.asyncio
async def test_auto_persona_best_match_selects_relevant_candidate():
    manager = BackgroundTaskManager(_DummyService())
    context = ArticleContext(
        initial_keywords=["札幌", "注文住宅"],
        company_target_keywords="自然素材,子育て",
        auto_selection_strategy="best_match",
    )
    context.generated_detailed_personas = [
        "東京都内でIT企業に勤める20代エンジニア",
        "札幌で自然素材の注文住宅を探す30代子育て世代",
    ]

    user_input, decision = await manager._build_auto_user_input(
        context, "persona_generated"
    )

    assert user_input["response_type"] == "select_persona"
    assert user_input["payload"]["selected_id"] == 1
    assert "best_match_score" in decision.get("reason", "")


@pytest.mark.asyncio
async def test_auto_theme_first_strategy_picks_first_option():
    manager = BackgroundTaskManager(_DummyService())
    context = ArticleContext(auto_selection_strategy="first")
    context.generated_themes = [
        ThemeProposalData(
            title="北海道の自然と暮らす家づくり",
            description="自然素材を生かした家づくり",
            keywords=["北海道", "自然素材"],
        ),
        ThemeProposalData(
            title="都市型コンパクト住宅",
            description="都心向けのコンパクト設計",
            keywords=["東京", "コンパクト"],
        ),
    ]

    user_input, _ = await manager._build_auto_user_input(context, "theme_proposed")

    assert user_input["response_type"] == "select_theme"
    assert user_input["payload"]["selected_index"] == 0


@pytest.mark.asyncio
async def test_auto_outline_validation_passes_and_approves():
    manager = BackgroundTaskManager(_DummyService())
    context = ArticleContext(outline_top_level_heading=2)
    context.generated_outline = OutlineData(
        title="サンプル記事",
        suggested_tone="",
        top_level_heading=2,
        sections=[
            OutlineSectionData(heading="導入", level=2),
            OutlineSectionData(heading="本論", level=2),
            OutlineSectionData(heading="まとめ", level=2),
        ],
    )

    user_input, decision = await manager._build_auto_user_input(
        context, "outline_generated"
    )

    assert user_input["response_type"] == "approve_outline"
    assert user_input["payload"]["approved"] is True
    assert decision["reason"] in {"outline_valid", "outline_validated"}
