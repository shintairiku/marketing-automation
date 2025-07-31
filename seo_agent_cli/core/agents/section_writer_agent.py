from typing import List
from core.context import ArticleGenerationContext, WorkflowState
from core.schemas import ArticleOutline, Section, ResearchReport
from core.tools.style_template_tool import get_style_template, StyleTemplate
from prompts import load_prompt

# モックアシスタント
class MockAssistant:
    def __init__(self, **kwargs):
        print(f"--- MockAssistant created with name: {kwargs.get('name')} ---")
        self.tools = {tool.__name__: tool for tool in kwargs.get('tools', [])}
        self.style_template_id = kwargs.get('style_template_id')

    def run(self, user_message: str, section: Section) -> str:
        print(f"--- MockAssistant starting run for section: '{section.title}' ---")
        
        # 1. 思考: アウトラインの指示と調査レポートを基に、セクションの内容を構成する
        print(f"  - Thinking: I need to write the content for the section '{section.title}'.")
        print(f"  - Thinking: I will use the provided research report and follow the section description closely.")

        style_template: StyleTemplate | None = None
        if self.style_template_id and 'get_style_template' in self.tools:
            # 2. 行動 (条件付き): スタイルテンプレートIDがあれば、ツールを使用する
            print(f"  - Thinking: A style template ID is provided. I should use the 'get_style_template' tool to match the writing style.")
            style_template = self.tools['get_style_template'](style_template_id=self.style_template_id)
            print(f"  - Acting: Executed 'get_style_template'. Got template name: {style_template.name}.")
        
        # 3. 最終出力: 思考結果をHTML形式の文字列として出力する
        print("  - Responding: Generating the HTML content for the section.")
        
        # ダミーデータを作成
        content = f"<h2>{section.title}</h2>\n"
        content += f"<p>{section.description.replace('解説する', '解説します。').replace('述べる', '述べます。')}</p>\n"
        content += "<p>ここに、調査レポートに基づいた詳細な本文が続きます。ダミーテキストです。</p>\n"
        if section.keywords:
            content += f"<p><em>含めるべきキーワード: {', '.join(section.keywords)}</em></p>\n"
        
        if style_template:
             content = content.replace("キーワード", f"「{style_template.name}」で推奨されるキーワード")

        return content

class SectionWriterAgent:
    """
    アウトラインの各セクションを一つずつ執筆するエージェント。
    """
    def __init__(self, context: ArticleGenerationContext):
        self.context = context

    def _flatten_sections(self, sections: List[Section]) -> List[Section]:
        """アウトラインのセクションをフラットなリストに変換する"""
        flat_list = []
        for section in sections:
            flat_list.append(section)
            if section.subsections:
                flat_list.extend(self._flatten_sections(section.subsections))
        return flat_list

    def run(self) -> ArticleGenerationContext:
        """
        エージェントの主処理を実行し、執筆されたセクションでコンテキストを更新する。
        """
        print("===== Running SectionWriterAgent =====")
        self.context.state = WorkflowState.SECTION_WRITING_RUNNING

        if not self.context.article_outline or not self.context.synthesized_research_report:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = "ArticleOutline or SynthesizedResearchReport is missing."
            print("===== SectionWriterAgent Failed: Missing required context =====")
            return self.context

        # 1. プロンプトとツールを準備
        try:
            prompt = load_prompt("section_writer")
        except FileNotFoundError as e:
            self.context.state = WorkflowState.ERROR
            self.context.error_message = str(e)
            return self.context
            
        tools = [get_style_template]

        # 2. Assistant を設定 (モック)
        assistant = MockAssistant(
            name="Section Writer",
            instructions=prompt,
            tools=tools,
            model="gpt-4-turbo-preview",
            style_template_id=self.context.style_template_id
        )

        # 3. 全セクションをフラットなリストにして、一つずつ執筆
        all_sections = self._flatten_sections(self.context.article_outline.sections)
        written_sections: List[str] = []
        total_sections = len(all_sections)

        for i, section in enumerate(all_sections):
            print(f"--- Writing section {i+1}/{total_sections}: '{section.title}' ---")
            user_message = (
                "Write the content for the following section based on the provided outline and research report. "
                "The output should be a well-structured HTML string.\n\n"
                f"Section to Write:\n{section.model_dump_json(indent=2)}\n\n"
                f"Full Research Report:\n{self.context.synthesized_research_report.model_dump_json(indent=2)}"
            )
            
            try:
                html_content = assistant.run(user_message, section)
                written_sections.append(html_content)
            except Exception as e:
                self.context.state = WorkflowState.ERROR
                self.context.error_message = f"An error occurred while writing section '{section.title}': {e}"
                print(f"===== SectionWriterAgent Failed during section '{section.title}': {e} =====")
                return self.context
        
        self.context.written_sections = written_sections
        self.context.state = WorkflowState.EDITING_RUNNING
        print("===== SectionWriterAgent Finished Successfully =====")
        return self.context
