import json
from typing import List, Type, Optional
from core.context import ArticleGenerationContext, WorkflowState
from core.schemas import GeneratedPersona, GeneratedPersonasResponse, KeywordAnalysisReport
from core.tools.company_info_tool import get_company_info, CompanyInfo
from prompts import load_prompt

# KeywordAnalyzerAgentと同様のモックを使用
class MockAssistant:
    def __init__(self, **kwargs):
        print(f"--- MockAssistant created with name: {kwargs.get('name')} ---")
        self.tools = {tool.__name__: tool for tool in kwargs.get('tools', [])}
        self.response_schema = kwargs.get('response_format', {}).get('schema')
        self.company_id = None

    def set_company_id(self, company_id: Optional[str]):
        self.company_id = company_id

    def run(self, user_message: str) -> GeneratedPersonasResponse:
        print(f"--- MockAssistant starting run for: {user_message} ---")
        
        # 1. 思考: ユーザーのメッセージとキーワード分析を基に、ペルソナ生成の方向性を考える
        print("  - Thinking: I need to create several distinct personas based on the provided context.")
        
        company_info: Optional[CompanyInfo] = None
        if self.company_id and 'get_company_info' in self.tools:
            # 2. 行動 (条件付き): 会社IDがあれば、会社情報ツールを使用する
            print(f"  - Thinking: A company ID is provided ('{self.company_id}'). I should use the 'get_company_info' tool.")
            company_info = self.tools['get_company_info'](company_id=self.company_id)
            print(f"  - Acting: Executed 'get_company_info'. Got company name: {company_info.name}.")
            print("  - Observing: The company info will help tailor the personas.")
        else:
            print("  - Thinking: No company ID provided, so I will generate more generic personas.")

        # 3. 思考 & 最終出力: ツール結果（あれば）と分析結果を統合し、最終的なペルソナリストを生成する
        print("  - Responding: Generating the final list of personas.")
        
        # ダミーデータを作成
        personas = [
            GeneratedPersona(
                id=1,
                name="田中さん",
                description="35歳、中小企業のWebマーケティング担当。記事作成の時間短縮と品質向上に課題を感じている。SEOの基礎知識はあるが、最新のトレンドや具体的な施策には自信がない。",
                related_keywords=["SEO記事 外注", "コンテンツマーケティング 効率化", "AIライティング ツール"]
            ),
            GeneratedPersona(
                id=2,
                name="鈴木さん",
                description="42歳、経営者兼マーケター。専門知識は深くないが、自社の認知度向上のためにコンテンツの重要性を理解している。コストを抑えつつ、効果的な情報発信を行いたいと考えている。",
                related_keywords=["中小企業 SEO対策", "ブログ 集客方法", "コンテンツ作成 コツ"]
            ),
            GeneratedPersona(
                id=3,
                name="佐藤さん",
                description="28歳、スタートアップのコンテンツライター。最新のAI技術に興味があり、自身の業務に積極的に取り入れたいと考えている。より専門的で、読者のエンゲージメントを高める記事を作成することが目標。",
                related_keywords=["GPT-4 記事作成", "SEOライティング テクニック", "エンゲージメント率 上げる方法"]
            )
        ]
        
        if company_info:
            personas[0].description += f" 特に、{company_info.name}のようなSaaS企業でのリード獲得を目指している。"

        return GeneratedPersonasResponse(personas=personas)


class PersonaGeneratorAgent:
    """
    キーワード分析とユーザーの指示に基づき、複数のペルソナを生成するエージェント。
    """
    def __init__(self, context: ArticleGenerationContext):
        self.context = context

    def run(self) -> ArticleGenerationContext:
        """
        エージェントの主処理を実行し、生成されたペルソナで更新されたコンテキストを返す。
        """
        print("===== Running PersonaGeneratorAgent =====")
        self.context.state = WorkflowState.PERSONA_GENERATION_RUNNING

        if not self.context.keyword_analysis_report:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = "KeywordAnalysisReport is missing. Cannot generate personas."
            print("===== PersonaGeneratorAgent Failed: Missing KeywordAnalysisReport =====")
            return self.context

        # 1. プロンプトとツールを準備
        try:
            prompt = load_prompt("persona_generator")
        except FileNotFoundError as e:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = str(e)
            return self.context
            
        tools = [get_company_info]

        # 2. Assistant を設定 (モック)
        assistant = MockAssistant(
            name="Persona Generator Agent",
            instructions=prompt,
            tools=tools,
            model="gpt-4-turbo-preview",
            response_format={
                "type": "json_object",
                "schema": GeneratedPersonasResponse.model_json_schema()
            }
        )
        # 会社IDをモックに渡す
        assistant.set_company_id(self.context.company_id)

        # 3. ReActループを実行
        # 実際の入力には、より多くのコンテキスト情報を含める
        user_message = (
            f"Based on the initial prompt '{self.context.initial_persona_prompt}' "
            f"and the following keyword analysis, generate {self.context.num_persona_to_generate} personas.\n\n"
            f"Keyword Analysis Report:\n{self.context.keyword_analysis_report.model_dump_json(indent=2)}"
        )
        
        try:
            response = assistant.run(user_message)
            self.context.generated_personas = response.personas
            self.context.state = WorkflowState.AWAITING_PERSONA_SELECTION
            print("===== PersonaGeneratorAgent Finished Successfully =====")
        except Exception as e:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = f"An error occurred in PersonaGeneratorAgent: {e}"
            print(f"===== PersonaGeneratorAgent Failed: {e} =====")

        return self.context
