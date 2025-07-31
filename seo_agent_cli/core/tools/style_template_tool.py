from typing import Dict, Any, List
from pydantic import BaseModel, Field

# Pydanticモデルでツールの戻り値を定義
class StyleTemplate(BaseModel):
    id: str
    name: str = Field(description="テンプレート名")
    tone: str = Field(description="記事全体のトーン＆マナー")
    formatting_rules: List[str] = Field(description="フォーマットに関するルール")
    persona_preference: str = Field(description="推奨されるペルソナのタイプ")

def get_style_template(style_template_id: str) -> StyleTemplate:
    """
    DBから指定されたIDのスタイルテンプレートを取得する。
    
    :param style_template_id: スタイルテンプレートのID。
    :return: スタイルテンプレート情報。
    """
    print(f"--- TOOL: Executing get_style_template for ID: {style_template_id} ---")
    # TODO: データベースクライアントを呼び出すように実装する
    
    # ダミーデータの返却
    return StyleTemplate(
        id=style_template_id,
        name="専門家による丁寧な解説スタイル",
        tone="読者に寄り添い、専門的な内容を分かりやすく解説する丁寧な口調。ですます調を基本とする。",
        formatting_rules=[
            "重要なキーワードは「」で括るか、太字にする。",
            "3〜4文ごとに改行を入れ、可読性を高める。",
            "箇条書きや表を積極的に活用して情報を整理する。",
            "各見出しの冒頭で、そのセクションで何を学べるかを簡潔に提示する。",
        ],
        persona_preference="業界の専門家や経験豊富なコンサルタント"
    )
