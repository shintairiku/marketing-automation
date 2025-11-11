# -*- coding: utf-8 -*-
"""Curated evaluation prompts for the SEO article generation system."""

from __future__ import annotations

from typing import Any, Dict, List

EXAMPLES: List[Dict[str, Any]] = [
    {
        "initial_keywords": ["家づくり", "失敗しない", "札幌", "自然素材"],
        "target_age_group": "30代",
        "persona_type": "社会人",
        "custom_persona": "札幌近郊で自然素材の戸建てを検討する共働き夫婦",
        "target_length": 4200,
        "company_name": "ナチュラルホームズ札幌",
        "flow_type": "research_first",
        "style_template_id": None,
    },
    {
        "initial_keywords": ["B2B SaaS", "マーケティングオートメーション", "活用事例"],
        "target_age_group": "40代",
        "persona_type": "経営者・役員",
        "custom_persona": "年商10億円規模のSaaSスタートアップCMO",
        "target_length": 3600,
        "company_name": "Shintairiku Marketing",
        "flow_type": "outline_first",
        "style_template_id": None,
    },
    {
        "initial_keywords": ["生成AI", "業務効率化", "中小企業", "導入手順"],
        "target_age_group": "20代",
        "persona_type": "社会人",
        "custom_persona": "総務・情シスを兼務する中小企業の若手リーダー",
        "target_length": 4000,
        "company_name": "Generative Ops Lab",
        "flow_type": "research_first",
        "style_template_id": None,
    },
]
