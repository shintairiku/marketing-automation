# -*- coding: utf-8 -*-
"""CLI entry point to run Weave evaluations for the SEO article flow."""

from __future__ import annotations

import argparse
import asyncio
from typing import List

import weave
from weave import Evaluation

from app.core.config import settings
from app.evals import (
    EXAMPLES,
    ArticleFlowModel,
    IntentCoverageJudge,
    heading_structure_score,
    length_budget_score,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Weave evaluations for the SEO article flow.")
    parser.add_argument(
        "--project",
        default=settings.weave_project_name,
        help="Weave project name (defaults to WEAVE_PROJECT_NAME).",
    )
    parser.add_argument(
        "--entity",
        default=settings.weave_entity or None,
        help="Weights & Biases entity/organization slug.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=len(EXAMPLES),
        help="Number of dataset rows to evaluate.",
    )
    parser.add_argument(
        "--flow-type",
        default="research_first",
        choices=["research_first", "outline_first"],
        help="Flow configuration passed to ArticleFlowModel.",
    )
    parser.add_argument(
        "--variant",
        default="baseline",
        help="Label for the prompt/model variant under test.",
    )
    parser.add_argument(
        "--display-name",
        default="Flow evaluation run",
        help="Friendly display name shown inside the Weave UI.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    weave.init(project=args.project, entity=args.entity)

    dataset = EXAMPLES[: args.limit]
    scorers = [
        length_budget_score,
        heading_structure_score,
        IntentCoverageJudge(),
    ]

    evaluation = Evaluation(dataset=dataset, scorers=scorers)
    model = ArticleFlowModel(
        outline_prompt_variant=args.variant,
        flow_type=args.flow_type,
    )

    await evaluation.evaluate(
        model,
        __weave={"display_name": args.display_name},
    )


if __name__ == "__main__":
    asyncio.run(main())
