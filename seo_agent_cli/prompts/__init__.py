from pathlib import Path

def load_prompt(name: str) -> str:
    """
    promptsディレクトリから指定された名前のプロンプトファイルを読み込みます。

    :param name: 拡張子を除いたプロンプトファイル名 (例: "keyword_analyzer")
    :return: プロンプトファイルの内容を含む文字列
    :raises FileNotFoundError: 指定されたプロンプトファイルが見つからない場合
    """
    # このファイルの親ディレクトリの親ディレクトリにある 'prompts' ディレクトリを基準にする
    base_path = Path(__file__).parent.parent 
    prompt_file = base_path / "prompts" / f"{name}.md"
    
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found at {prompt_file}")
        
    return prompt_file.read_text()
