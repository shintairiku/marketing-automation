from typing import List
from core.context import ArticleGenerationContext, WorkflowState
from core.schemas import ArticleOutline, FinalArticle
from prompts import load_prompt

# モックアシスタント
class MockAssistant:
    def __init__(self, **kwargs):
        print(f"--- MockAssistant created with name: {kwargs.get('name')} ---")

    def run(self, user_message: str, title: str, all_sections_html: str) -> FinalArticle:
        print(f"--- MockAssistant starting run for final editing ---")
        
        # 1. 思考: 全てのセクションを読み込み、全体の流れをチェックする
        print("  - Thinking: I need to review all the written sections and ensure they flow together smoothly.")
        print("  - Thinking: I will check for consistency in tone, add transition phrases, and write a final summary.")
        
        # 2. 最終出力: 思考結果をFinalArticleとして構造化する
        print("  - Responding: Generating the final, polished article.")
        
        # ダミーデータを作成
        # 導入と結論部分を生成し、全体を結合する
        final_html = f"<h1>{title}</h1>\n"
        final_html += "<p>（ここに、アウトラインに基づいた導入文が入ります。AIによる記事自動生成の重要性と、本記事で読者が何を得られるかの概説です。）</p>\n"
        final_html += all_sections_html
        final_html += "<h2>まとめ</h2>\n"
        final_html += "<p>（ここに、アウトラインに基づいた結論文が入ります。本記事で解説したステップの要約と、読者が次にとるべきアクションの提示です。）</p>"

        final_article = FinalArticle(
            title=title,
            content_html=final_html,
            summary="AIを活用したSEO記事の自動生成は、キーワード選定から始まる5つのステップで実現可能です。本記事では、その具体的な手順と、品質を担保するための秘訣を詳しく解説しました。"
        )
        return final_article

class EditorAgent:
    """
    全セクションを統合し、推敲・校正して最終的な記事を完成させるエージェント。
    """
    def __init__(self, context: ArticleGenerationContext):
        self.context = context

    def run(self) -> ArticleGenerationContext:
        """
        エージェントの主処理を実行し、完成した記事でコンテキストを更新する。
        """
        print("===== Running EditorAgent =====")
        self.context.state = WorkflowState.EDITING_RUNNING

        if not self.context.written_sections or not self.context.article_outline:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = "WrittenSections or ArticleOutline is missing."
            print("===== EditorAgent Failed: Missing required context =====")
            return self.context

        # 1. プロンプトを準備
        try:
            prompt = load_prompt("editor")
        except FileNotFoundError as e:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = str(e)
            return self.context
            
        # 2. Assistant を設定 (モック)
        assistant = MockAssistant(
            name="Final Editor",
            instructions=prompt,
            model="gpt-4-turbo-preview",
            # response_format は FinalArticle を想定
        )

        # 3. ReActループを実行
        all_sections_html = "\n".join(self.context.written_sections)
        user_message = (
            "Please edit and combine the following HTML sections into a single, final article. "
            "Ensure smooth transitions between sections, check for overall consistency, "
            "and write the introduction and conclusion based on the provided outline.\n\n"
            f"Article Outline:\n{self.context.article_outline.model_dump_json(indent=2)}\n\n"
            f"HTML Sections to combine:\n{all_sections_html}"
        )
        
        try:
            final_article = assistant.run(
                user_message, 
                self.context.article_outline.title,
                all_sections_html
            )
            self.context.final_article = final_article
            self.context.state = WorkflowState.COMPLETED
            print("===== EditorAgent Finished Successfully: Workflow Complete! =====")
        except Exception as e:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = f"An error occurred in EditorAgent: {e}"
            print(f"===== EditorAgent Failed: {e} =====")

        return self.context
