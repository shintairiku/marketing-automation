# -*- coding: utf-8 -*-
# 既存のスクリプトからツール定義をここに移動
from typing import Optional, List # <<< Optional, List をインポート
from rich.console import Console # ログ出力用にConsoleを残すか、loggingに切り替える
from agents import WebSearchTool, FileSearchTool, Tool # <<< Tool をインポート
# ArticleContext を直接インポート

console = Console() # または logging を使用

# --- ツール定義 ---
# Web検索ツール (Agents SDK標準)
web_search_tool = WebSearchTool(
    user_location={"type": "approximate", "country": "JP"}
)

# ファイル検索ツール (Agents SDK標準) - 必要に応じて有効化
def get_file_search_tool(vector_store_id: Optional[str]) -> Optional[FileSearchTool]: # <<< Optional を使用
    if vector_store_id:
        return FileSearchTool(vector_store_ids=[vector_store_id])
    return None



# 利用可能なツールのリスト (動的に変更しない場合の例)
available_tools: List[Tool] = [web_search_tool] # <<< 型ヒント修正

# ファイル検索ツールをコンテキストに応じて動的に追加する場合の関数例
# def get_available_tools(context: ArticleContext) -> List[Tool]:
#     tools: List[Tool] = [web_search_tool]
#     fs_tool = get_file_search_tool(context.vector_store_id)
#     if fs_tool:
#         tools.append(fs_tool)
#     return tools

