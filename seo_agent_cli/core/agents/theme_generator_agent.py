import json
from typing import List, Type, Optional
from core.context import ArticleGenerationContext, WorkflowState
from core.schemas import GeneratedPersona, KeywordAnalysisReport, Theme
from core.tools.style_template_tool import get_style_template, StyleTemplate
from prompts import load_prompt

# 他のエージェントと同様のモックを使用
class MockAssistant:
    def __init__(self, **kwargs):
        print(f"--- MockAssistant created with name: {kwargs.get('name')} ---")
        self.tools = {tool.__name__: tool for tool in kwargs.get('tools', [])}
        self.response_schema = kwargs.get('response_format', {}).get('schema')
        self.style_template_id = None

    def set_style_template_id(self, style_template_id: Optional[str]):
        self.style_template_id = style_template_id

    def run(self, user_message: str) -> List[Theme]:
        print(f"--- MockAssistant starting run for: {user_message} ---")
        
        # 1. 思考: ペルソナとキーワード分析を基に、魅力的なテーマを考える
        print("  - Thinking: I need to generate compelling themes that align with the persona and keyword analysis.")
        
        style_template: Optional[StyleTemplate] = None
        if self.style_template_id and 'get_style_template' in self.tools:
            # 2. 行動 (条件付き): スタイルテンプレートIDがあれば、ツールを使用する
            print(f"  - Thinking: A style template ID is provided ('{self.style_template_id}'). I should use the 'get_style_template' tool.")
            style_template = self.tools['get_style_template'](style_template_id=self.style_template_id)
            print(f"  - Acting: Executed 'get_style_template'. Got template name: {style_template.name}.")
            print("  - Observing: The style template will influence the tone and angle of the themes.")
        else:
            print("  - Thinking: No style template ID provided, so I will generate themes with a general approach.")

        # 3. 思考 & 最終出力: 全ての情報を統合し、テーマ案を生成する
        print("  - Responding: Generating the final list of themes.")
        
        # ダミーデータを作成
        themes = [
            Theme(
                id=1,
                title="【担当者向け】AIでSEO記事を自動生成する全手順｜高品質コンテンツを安定供給する秘訣",
                reason="具体的な手順を求めるペルソナのニーズに応え、「全手順」「秘訣」という言葉で網羅性と専門性をアピール。検索意図に合致し、クリック率向上が期待できる。",
                target_audience="田中さんのような、具体的なノウハウを求めている実務担当者。"
            ),
            Theme(
                id=2,
                title="まだ疲弊してる？AI記事生成でマーケティングはここまで効率化できる！導入事例と効果まとめ",
                reason="「疲弊してる？」と問いかけることで、ペルソナの課題に共感を示す。「効率化」「導入事例」をキーワードに、経営者層が求める費用対効果の視点を盛り込む。",
                target_audience="鈴木さんのような、ビジネスインパクトを重視する経営者・マーケター。"
            ),
            Theme(
                id=3,
                title="GPT-4はもう古い？最新AIライティングツール5選と、プロが教える次世代コンテンツ戦略",
                reason="「GPT-4はもう古い？」という挑戦的なタイトルで、最新技術に敏感な層の興味を引く。「プロが教える」「次世代」という言葉で、より高度な情報を求める読者に応える。",
                target_audience="佐藤さんのような、常に新しい技術や知識を追い求めるライターやクリエイター。"
            )
        ]
        
        if style_template:
            themes[0].title = f"【{style_template.persona_preference}が解説】" + themes[0].title

        return themes


class ThemeGeneratorAgent:
    """
    選択されたペルソナとキーワード分析に基づき、記事のテーマを複数提案するエージェント。
    """
    def __init__(self, context: ArticleGenerationContext):
        self.context = context

    def run(self) -> ArticleGenerationContext:
        """
        エージェントの主処理を実行し、生成されたテーマで更新されたコンテキストを返す。
        """
        print("===== Running ThemeGeneratorAgent =====")
        self.context.state = WorkflowState.THEME_GENERATION_RUNNING

        if not self.context.selected_persona or not self.context.keyword_analysis_report:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = "SelectedPersona or KeywordAnalysisReport is missing."
            print("===== ThemeGeneratorAgent Failed: Missing required context =====")
            return self.context

        # 1. プロンプトとツールを準備
        try:
            prompt = load_prompt("theme_generator")
        except FileNotFoundError as e:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = str(e)
            return self.context
            
        tools = [get_style_template]

        # 2. Assistant を設定 (モック)
        assistant = MockAssistant(
            name="Theme Generator Agent",
            instructions=prompt,
            tools=tools,
            model="gpt-4-turbo-preview",
            # 戻り値がリストなので、スキーマの指定方法を調整する必要があるかもしれない
            # response_format={"type": "json_object", "schema": ...}
        )
        assistant.set_style_template_id(self.context.style_template_id)

        # 3. ReActループを実行
        user_message = (
            f"Based on the selected persona and keyword analysis, generate 3 compelling article themes.\n\n"
            f"Selected Persona:\n{self.context.selected_persona.model_dump_json(indent=2)}\n\n"
            f"Keyword Analysis Report:\n{self.context.keyword_analysis_report.model_dump_json(indent=2)}"
        )
        
        try:
            themes = assistant.run(user_message)
            self.context.generated_themes = themes
            self.context.state = WorkflowState.AWAITING_THEME_SELECTION
            print("===== ThemeGeneratorAgent Finished Successfully =====")
        except Exception as e:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = f"An error occurred in ThemeGeneratorAgent: {e}"
            print(f"===== ThemeGeneratorAgent Failed: {e} =====")

        return self.context
