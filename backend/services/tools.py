# -*- coding: utf-8 -*-
# 既存のスクリプトからツール定義をここに移動
from typing import Dict, Any, Optional, List # <<< Optional, List をインポート
from rich.console import Console # ログ出力用にConsoleを残すか、loggingに切り替える
from agents import function_tool, RunContextWrapper, WebSearchTool, FileSearchTool, Tool # <<< Tool をインポート
# ArticleContext を直接インポート
from services.context import ArticleContext # <<< 修正: 直接インポート

# image_generation関連
import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2 import service_account
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
import asyncio

console = Console() # または logging を使用
# .envファイルから環境変数を読み込む
load_dotenv()

# Vertex AIの初期化
project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
if not project_id:
    raise Exception("GOOGLE_CLOUD_PROJECT環境変数が設定されていません")

# サービスアカウントキーの設定（Docker環境対応）
service_account_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
if not service_account_json:
    raise Exception("GOOGLE_SERVICE_ACCOUNT_JSON環境変数が設定されていません")

try:
    # サービスアカウントの認証情報を設定
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(service_account_json),
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    console.print("[green]デバッグ: サービスアカウントの認証情報を読み込みました[/green]")
    
    # Vertex AIの初期化
    vertexai.init(
        project=project_id,
        location="us-central1",
        credentials=credentials
    )
    console.print("[green]デバッグ: Vertex AIの初期化が完了しました[/green]")
 
except json.JSONDecodeError as e:
    console.print(f"[red]デバッグ: サービスアカウントのJSON形式が不正です: {str(e)}[/red]")
    raise
except Exception as e:
    console.print(f"[red]デバッグ: 認証情報の設定に失敗: {str(e)}[/red]")
    raise

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

# Imagen 3.0画像生成ツール
@function_tool
async def imagen3_image_generation(prompt: str, negative_prompt: str = "", aspect_ratio: str = "1:1") -> str:
    """
    Google Vertex AIのImagen 3.0を使用して画像を**1枚だけ**生成し、その**ファイルパス**を返します。
    
    Args:
        prompt (str): 画像生成のためのプロンプト（英語推奨）
        negative_prompt (str, optional): 生成を避けたい要素のプロンプト
        aspect_ratio (str, optional): 画像のアスペクト比（"1:1", "9:16", "16:9", "3:4", "4:3"）
        
    Returns:
        str: 生成された画像のファイルパス
    """
    
    console.print("[red]デバッグ: 関数の開始[/red]")
    
    # デバッグ用：呼び出し回数の追跡
    if not hasattr(imagen3_image_generation, '_call_count'):
        imagen3_image_generation._call_count = 0
    imagen3_image_generation._call_count += 1
    console.print(f"[yellow]デバッグ: imagen3_image_generationツールが呼び出されました (呼び出し回数: {imagen3_image_generation._call_count})[/yellow]")

    # プロンプトの構築
    final_prompt = f"{prompt}, avoid: {negative_prompt}" if negative_prompt else prompt
    console.print(f"[red]デバッグ: 最終プロンプト: {final_prompt}[/red]")

    try:
        console.print("[red]デバッグ: Imagenモデルの初期化開始[/red]")
        # Imagenモデルの初期化
        generation_model = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
        console.print("[red]デバッグ: モデル初期化完了[/red]")

        # 画像生成の実行（タイムアウト設定付き）
        console.print("[red]デバッグ: 画像生成開始[/red]")
        async with asyncio.timeout(180):  # タイムアウトを180秒に延長
            try:
                # 画像生成の実行
                response = await asyncio.to_thread(
                    generation_model.generate_images,
                    prompt=final_prompt,
                    number_of_images=1,
                    aspect_ratio=aspect_ratio,
                    safety_filter_level="block_some",
                    person_generation="allow_all"
                )
                console.print("[red]デバッグ: 画像生成API呼び出し完了[/red]")
                
                # レスポンスの形式を確認
                console.print(f"[yellow]デバッグ: レスポンスの型: {type(response)}[/yellow]")
                
                # 画像データの取得
                if not response:
                    console.print("[red]デバッグ: 生成された画像が空です[/red]")
                    raise Exception("画像生成に失敗しました: 結果が空です")

                console.print("[red]デバッグ: 画像データの取得開始[/red]")
                # 画像データをbase64エンコード
                try:
                    # 画像データの取得方法を変更
                    if hasattr(response, 'images') and len(response.images) > 0:
                        generated_image = response.images[0]
                        # GeneratedImageオブジェクトのデバッグ情報
                        console.print(f"[yellow]デバッグ: GeneratedImageオブジェクトの型: {type(generated_image)}[/yellow]")
                        console.print(f"[yellow]デバッグ: GeneratedImageの属性: {dir(generated_image)}[/yellow]")
                        
                        # 正しい属性名を使用してバイトデータを取得
                        if hasattr(generated_image, '_image_bytes'):
                            image_bytes = generated_image._image_bytes
                            console.print("[green]デバッグ: _image_bytes属性で画像データの取得に成功[/green]")
                        elif hasattr(generated_image, 'data'):
                            image_bytes = generated_image.data
                            console.print("[green]デバッグ: data属性で画像データの取得に成功[/green]")
                        elif hasattr(generated_image, 'image_data'):
                            image_bytes = generated_image.image_data
                            console.print("[green]デバッグ: image_data属性で画像データの取得に成功[/green]")
                        elif hasattr(generated_image, 'content'):
                            image_bytes = generated_image.content
                            console.print("[green]デバッグ: content属性で画像データの取得に成功[/green]")
                        else:
                            # 属性が見つからない場合はエラー
                            raise Exception(f"GeneratedImageオブジェクトから画像データを取得できません。利用可能な属性: {[attr for attr in dir(generated_image) if not attr.startswith('_')]}")
                    elif hasattr(response, 'bytes'):
                        image_bytes = response.bytes
                        console.print("[green]デバッグ: bytes属性で画像データの取得に成功[/green]")
                    elif hasattr(response, 'image_bytes'):
                        image_bytes = response.image_bytes
                        console.print("[green]デバッグ: image_bytes属性で画像データの取得に成功[/green]")
                    elif hasattr(response, 'image'):
                        image_bytes = response.image
                        console.print("[green]デバッグ: image属性で画像データの取得に成功[/green]")
                    else:
                        # 画像データを直接取得
                        image_bytes = response
                        console.print("[green]デバッグ: 直接画像データの取得に成功[/green]")
                except Exception as e:
                    console.print(f"[red]デバッグ: 画像データの取得に失敗: {str(e)}[/red]")
                    raise Exception(f"画像データの取得に失敗しました: {str(e)}")

                # 画像保存用ディレクトリを作成
                image_dir = Path("generated_images")
                image_dir.mkdir(exist_ok=True)
                
                # ユニークなファイル名を生成
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_id = str(uuid.uuid4())[:8]
                filename = f"imagen_{timestamp}_{unique_id}.png"
                file_path = image_dir / filename
                
                # 画像をファイルに保存
                with open(file_path, "wb") as f:
                    f.write(image_bytes)
                
                console.print(f"[green]デバッグ: 画像を保存しました: {file_path}[/green]")
                console.print(f"[yellow]デバッグ: ファイルサイズ: {len(image_bytes) / 1024 / 1024:.2f} MB[/yellow]")
                
                # WebアクセスURL用のパスを返す（スラッシュ区切り）
                web_path = f"/{file_path.as_posix()}"
                console.print(f"[yellow]デバッグ: 返すWebパス: {web_path}[/yellow]")
                
                console.print("[red]デバッグ: 関数の正常終了[/red]")
                return web_path

            except Exception as api_error:
                error_message = str(api_error)
                console.print(f"[red]デバッグ: APIエラーの詳細: {error_message}[/red]")
                if "billed users" in error_message.lower():
                    raise Exception("Google Vertex AIのImagen APIは現在、課金ユーザーのみが利用可能です。APIの課金設定を確認してください。\n"
                                  "1. Google Cloud ConsoleでVertex AI APIが有効化されているか確認\n"
                                  "2. プロジェクトに課金アカウントが紐付けられているか確認\n"
                                  "3. 無料トライアルのクレジットが残っているか確認")
                raise

    except asyncio.TimeoutError:
        console.print("[red]デバッグ: タイムアウトエラー発生[/red]")
        raise Exception("画像生成がタイムアウトしました（180秒）。もう一度お試しください。")
    except Exception as e:
        console.print(f"[red]デバッグ: エラー発生: {str(e)}[/red]")
        raise Exception(f"画像生成中にエラーが発生しました: {str(e)}")

# 利用可能なツールのリスト (動的に変更しない場合の例)
available_tools: List[Tool] = [get_company_data, analyze_competitors, web_search_tool, imagen3_image_generation] # <<< 型ヒント修正

# ファイル検索ツールをコンテキストに応じて動的に追加する場合の関数例
# def get_available_tools(context: ArticleContext) -> List[Tool]:
#     tools: List[Tool] = [get_company_data, analyze_competitors, web_search_tool]
#     fs_tool = get_file_search_tool(context.vector_store_id)
#     if fs_tool:
#         tools.append(fs_tool)
#     return tools

