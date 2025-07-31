import typer
from rich.console import Console
from rich.panel import Panel
from typing import List, Optional

from app.workflow_manager import WorkflowManager
from core.context import ArticleGenerationContext, WorkflowState
from core.schemas import GeneratedPersona, Theme

# TyperアプリケーションとRichコンソールを初期化
app = typer.Typer()
console = Console()

def handle_user_interaction(manager: WorkflowManager):
    """ユーザーの入力が必要な状態を処理する"""
    context = manager.context
    
    if context.state == WorkflowState.AWAITING_PERSONA_SELECTION:
        console.print("\n[bold yellow]👤 ペルソナを選択してください:[/bold yellow]")
        for p in context.generated_personas:
            console.print(Panel(f"[bold]{p.name}[/bold]\n{p.description}\n\n[cyan]関連キーワード: {', '.join(p.related_keywords)}[/cyan]", 
                                title=f"ID: {p.id}", border_style="green"))
        
        try:
            choice = int(typer.prompt("番号を選択してください"))
            selected = next(p for p in context.generated_personas if p.id == choice)
            context.selected_persona = selected
            context.state = WorkflowState.THEME_GENERATION_RUNNING # 次の状態へ手動で遷移
        except (ValueError, StopIteration):
            console.print("[bold red]無効な選択です。ワークフローを中止します。[/bold red]")
            context.state = WorkflowState.ERROR
            context.error_message = "Invalid persona selection."

    elif context.state == WorkflowState.AWAITING_THEME_SELECTION:
        console.print("\n[bold yellow]📝 記事テーマを選択してください:[/bold yellow]")
        for t in context.generated_themes:
             console.print(Panel(f"[bold]{t.title}[/bold]\n\n[dim]理由: {t.reason}[/dim]", 
                                title=f"ID: {t.id}", border_style="blue"))
        try:
            choice = int(typer.prompt("番号を選択してください"))
            selected = next(t for t in context.generated_themes if t.id == choice)
            context.selected_theme = selected
            context.state = WorkflowState.RESEARCH_PLANNING_RUNNING
        except (ValueError, StopIteration):
            console.print("[bold red]無効な選択です。ワークフローを中止します。[/bold red]")
            context.state = WorkflowState.ERROR
            context.error_message = "Invalid theme selection."

    # TODO: AWAITING_RESEARCH_PLAN_APPROVAL と AWAITING_OUTLINE_APPROVAL の処理を追加
    elif context.state == WorkflowState.AWAITING_RESEARCH_PLAN_APPROVAL:
        console.print("\n[bold yellow]🗺️ 調査計画を確認してください:[/bold yellow]")
        for q in context.research_plan.queries:
            console.print(f"  - [cyan]{q.query}[/cyan] (情報源: {q.source})")
        approve = typer.confirm("この計画で調査を進めますか？")
        if approve:
            context.state = WorkflowState.RESEARCH_EXECUTION_RUNNING
        else:
            context.state = WorkflowState.ERROR
            context.error_message = "User rejected the research plan."
            
    elif context.state == WorkflowState.AWAITING_OUTLINE_APPROVAL:
        console.print("\n[bold yellow]뼈 記事アウトラインを確認してください:[/bold yellow]")
        console.print(f"[bold]タイトル: {context.article_outline.title}[/bold]")
        # ここでは簡略化して表示
        for section in context.article_outline.sections:
            console.print(f"  - H2: {section.title}")
            for sub in section.subsections:
                console.print(f"    - H3: {sub.title}")
        approve = typer.confirm("このアウトラインで執筆を進めますか？")
        if approve:
            context.state = WorkflowState.SECTION_WRITING_RUNNING
        else:
            context.state = WorkflowState.ERROR
            context.error_message = "User rejected the article outline."


@app.callback(invoke_without_command=True)
def generate(
    ctx: typer.Context,
    keywords: List[str] = typer.Option(..., "--keyword", "-k", help="SEOキーワード"),
    persona_prompt: str = typer.Option(..., "--persona", "-p", help="ペルソナの概要"),
    company_id: Optional[str] = typer.Option(None, help="（任意）会社ID"),
    style_template_id: Optional[str] = typer.Option(None, help="（任意）スタイルテンプレートID"),
):
    """
    自律型SEO記事生成エージェントシステムを起動します。
    """
    console.print(Panel("[bold green]自律型SEO記事生成ワークフローを開始します[/bold green]"))

    # 1. 初期コンテキストを作成
    context = ArticleGenerationContext(
        initial_keywords=keywords,
        initial_persona_prompt=persona_prompt,
        company_id=company_id,
        style_template_id=style_template_id,
    )

    # 2. ワークフローマネージャーを初期化
    manager = WorkflowManager(context)

    # 3. ワークフローを実行し、ユーザー入力が必要になるか完了するまでループ
    while not manager.state_machine.is_terminal_state(manager.context.state):
        manager.run()

        if manager.state_machine.is_user_interaction_required(manager.context.state):
            handle_user_interaction(manager)
        
        # ユーザー入力ハンドラが状態をERRORにした場合、ループを抜ける
        if manager.context.state == WorkflowState.ERROR:
            break

    # 4. 最終結果を表示
    final_context = manager.context
    if final_context.state == WorkflowState.COMPLETED:
        console.print(Panel("[bold green]🎉 ワークフローが正常に完了しました！[/bold green]"))
        console.print("\n[bold]生成された記事:[/bold]")
        console.print(Panel(final_context.final_article.content_html, 
                            title=final_context.final_article.title,
                            border_style="magenta"))
        console.print("\n[bold]記事の要約:[/bold]")
        console.print(f"[italic]{final_context.final_article.summary}[/italic]")
    else:
        console.print(Panel(f"[bold red]ワークフローがエラーで終了しました[/bold red]\n\n"
                            f"状態: {final_context.state}\n"
                            f"エラーメッセージ: {final_context.error_message}",
                            border_style="red"))

def main():
    app()

if __name__ == "__main__":
    main()

