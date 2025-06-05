# -*- coding: utf-8 -*-
from agents import Agent
from services.context import ArticleContext
from services.models import GeneratedPersonasResponse
from core.config import settings
from services.prompts import create_persona_generator_instructions
from schemas.request import PersonaType

PERSONA_GENERATOR_AGENT_BASE_PROMPT = """あなたはターゲット顧客の具体的なペルソナ像を鮮明に描き出すプロフェッショナルです。
与えられたSEOキーワード、ターゲット年代、ペルソナ属性、およびクライアント企業情報（あれば）を基に、その顧客がどのような人物で、どのようなニーズや悩みを抱えているのか、具体的な背景情報（家族構成、ライフスタイル、価値観など）を含めて詳細なペルソナ像を複数案作成してください。
あなたの応答は必ず `GeneratedPersonasResponse` 型のJSON形式で、`personas` リストの中に指定された数のペルソナ詳細を `GeneratedPersonaItem` として含めてください。
各ペルソナの `description` は、ユーザーが提供した例のような形式で、具体的かつ簡潔に記述してください。
例:
ユーザー入力: 50代 主婦 キーワード「二重窓 デメリット」
あなたの出力内のペルソナdescriptionの一例:
「築30年の戸建てに暮らす50代後半の女性。家族構成は夫婦（子どもは独立）。年々寒さがこたえるようになり、家の暖かさには窓の性能が大きく関わっていることを知った。内窓を設置して家の断熱性を高めたいと考えている。補助金も気になっている。」
"""

persona_generator_agent = Agent[ArticleContext](
    name="PersonaGeneratorAgent",
    instructions=create_persona_generator_instructions(PERSONA_GENERATOR_AGENT_BASE_PROMPT),
    model=settings.default_model,
    tools=[],
    output_type=GeneratedPersonasResponse,
)
