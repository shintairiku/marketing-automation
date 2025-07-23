# -*- coding: utf-8 -*-
# 既存のスクリプトからツール定義をここに移動
from typing import Dict, Any, Optional, List # <<< Optional, List をインポート
from rich.console import Console # ログ出力用にConsoleを残すか、loggingに切り替える
from agents import function_tool, RunContextWrapper, WebSearchTool, FileSearchTool, Tool # <<< Tool をインポート
# ArticleContext を直接インポート
from app.domains.seo_article.context import ArticleContext # <<< 修正: 直接インポート

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

# 会社情報取得ツール (ダミー)
@function_tool
async def get_company_data(ctx: RunContextWrapper[ArticleContext]) -> Dict[str, Any]: # <<< 修正: 'ArticleContext' -> ArticleContext
    """
    顧客企業のデータベースやCMSから関連情報を取得します。
    (この実装はダミーです。実際のシステムではAPI呼び出し等に置き換えてください)
    """
    console.print("[dim]ツール実行(get_company_data): ダミーデータを返します。[/dim]")
    # コンテキストから会社情報を取得、なければデフォルト値
    return {
        "success": True,
        "company_name": ctx.context.company_name or "株式会社ジョンソンホームズ",
        "company_description": ctx.context.company_description or "住宅の設計・施工、リフォーム工事の設計・施工、不動産の売買および斡旋、インテリア商品の販売、オーダーソファの製造・販売、レストラン・カフェ運営、保険事業、住宅FC本部",
        "company_style_guide": ctx.context.company_style_guide or "文体は丁寧語（ですます調）を基本とし、専門用語は避ける。読者に寄り添うフレンドリーなトーン。",
        "past_articles_summary": ctx.context.past_articles_summary or "過去にはブログやコラム系の記事が多い。",
    }

# 競合分析ツール (ダミー)
@function_tool
async def analyze_competitors(ctx: RunContextWrapper[ArticleContext], query: str) -> Dict[str, Any]: # <<< 修正: 'ArticleContext' -> ArticleContext
    """
    指定されたクエリでWeb検索を行い、競合となる記事の傾向を分析します。
    (この実装はダミーです。WebSearchToolの結果を解析する処理に置き換えてください)

    Args:
        query: 競合分析のための検索クエリ（例：「芝生 育て方 ガイド」）
    """
    console.print(f"[dim]ツール実行(analyze_competitors): クエリ '{query}' のダミー分析結果を返します。[/dim]")
    common_sections_map = {
        "芝生 育て方 初心者": ["準備するもの", "種まき", "水やり", "肥料", "芝刈り"],
        "芝生 手入れ コツ": ["サッチング", "エアレーション", "目土入れ", "病害虫対策"],
        "札幌 注文住宅 自然素材": ["自然素材の種類と特徴", "メリット・デメリット", "施工事例", "費用相場", "工務店選び"],
        "札幌 子育て 住宅": ["間取りの工夫", "収納アイデア", "周辺環境（公園・学校）", "安全性", "体験談"],
    }
    # クエリに部分一致するものがあればそれを返す
    matched_sections = ["基本的な情報", "メリット・デメリット", "事例紹介"] # デフォルト
    for key, sections in common_sections_map.items():
        if key in query:
            matched_sections = sections
            break

    return {
        "success": True,
        "summary": f"'{query}' に関する競合記事は、主に{matched_sections[0]}や{matched_sections[1]}などを解説しています。",
        "common_sections": matched_sections,
        "estimated_length_range": "2000〜4000文字",
    }

# 利用可能なツールのリスト (動的に変更しない場合の例)
available_tools: List[Tool] = [get_company_data, analyze_competitors, web_search_tool] # <<< 型ヒント修正

# ファイル検索ツールをコンテキストに応じて動的に追加する場合の関数例
# def get_available_tools(context: ArticleContext) -> List[Tool]:
#     tools: List[Tool] = [get_company_data, analyze_competitors, web_search_tool]
#     fs_tool = get_file_search_tool(context.vector_store_id)
#     if fs_tool:
#         tools.append(fs_tool)
#     return tools

