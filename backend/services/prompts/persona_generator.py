# -*- coding: utf-8 -*-
from typing import Callable, Awaitable
from agents import Agent, RunContextWrapper
from services.context import ArticleContext
from schemas.request import PersonaType


def create_persona_generator_instructions(base_prompt: str) -> Callable[[RunContextWrapper[ArticleContext], Agent[ArticleContext]], Awaitable[str]]:
    async def dynamic_instructions_func(ctx: RunContextWrapper[ArticleContext], agent: Agent[ArticleContext]) -> str:
        initial_persona_description = "指定なし"
        if ctx.context.persona_type == PersonaType.OTHER and ctx.context.custom_persona:
            initial_persona_description = ctx.context.custom_persona
        elif ctx.context.target_age_group and ctx.context.persona_type:
            initial_persona_description = f"{ctx.context.target_age_group.value}の{ctx.context.persona_type.value}"
        elif ctx.context.custom_persona:
            initial_persona_description = ctx.context.custom_persona

        company_info_str = ""
        if ctx.context.company_name or ctx.context.company_description:
            company_info_str = f"\nクライアント企業名: {ctx.context.company_name or '未設定'}\nクライアント企業概要: {ctx.context.company_description or '未設定'}"

        full_prompt = f"""{base_prompt}

--- 入力情報 ---
SEOキーワード: {', '.join(ctx.context.initial_keywords)}
ターゲット年代: {ctx.context.target_age_group.value if ctx.context.target_age_group else '指定なし'}
ペルソナ属性（大分類）: {ctx.context.persona_type.value if ctx.context.persona_type else '指定なし'}
(上記属性が「その他」の場合のユーザー指定ペルソナ: {ctx.context.custom_persona if ctx.context.persona_type == PersonaType.OTHER else '該当なし'})
生成する具体的なペルソナの数: {ctx.context.num_persona_examples}
{company_info_str}
---

あなたのタスクは、上記入力情報に基づいて、より具体的で詳細なペルソナ像を **{ctx.context.num_persona_examples}個** 生成することです。
各ペルソナは、`GeneratedPersonaItem` の形式で、`id` (0から始まるインデックス) と `description` を含めてください。
"""
        return full_prompt
    return dynamic_instructions_func
