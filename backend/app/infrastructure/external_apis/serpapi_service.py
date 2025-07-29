import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup, NavigableString, Tag, PageElement
from serpapi.google_search import GoogleSearch  # type: ignore[import-untyped]
from app.core.config import settings
import urllib.robotparser
from app.infrastructure.gcp_auth import setup_genai_client
from urllib.parse import urlparse
import time # ★ 追加: 時間計測用
import google.generativeai as genai # ★ 追加: Gemini API用
import re # ★ 追加: 正規表現用（著者情報抽出など）

# スクレイピング時のデフォルトユーザーエージェント
USER_AGENT = "Mozilla/5.0 (compatible; ShintairikuBot/1.0; +https://shintairiku.com/bot)"


@dataclass
class ScrapedArticle:
    """スクレイピングした記事の情報"""
    url: str
    title: str
    headings: List[Dict[str, Any]]  # 見出しのリスト (階層構造対応, char_count_section を含む)
    content: str  # 記事本文
    char_count: int  # 文字数
    image_count: int  # 画像数
    source_type: str  # "related_question" または "organic_result"
    position: Optional[int] = None  # organic_resultの場合の順位
    question: Optional[str] = None  # related_questionの場合の質問文
    # ★ 新しいコンテンツフォーマット分析フィールド
    video_count: int = 0  # 動画数（iframe含む）
    table_count: int = 0  # テーブル数
    list_item_count: int = 0  # リスト項目総数
    external_link_count: int = 0  # 外部リンク数
    internal_link_count: int = 0  # 内部リンク数
    # ★ メタデータフィールド（オプション）
    author_info: Optional[str] = None  # 著者情報
    publish_date: Optional[str] = None  # 公開日
    modified_date: Optional[str] = None  # 更新日
    schema_types: Optional[List[str]] = None  # 構造化データのタイプリスト
    
    def __post_init__(self):
        """デフォルト値の初期化"""
        if self.schema_types is None:
            self.schema_types = []


@dataclass
class SerpAnalysisResult:
    """SerpAPI分析結果"""
    search_query: str
    total_results: int
    related_questions: List[Dict[str, Any]]
    organic_results: List[Dict[str, Any]]
    scraped_articles: List[ScrapedArticle]
    average_char_count: int
    suggested_target_length: int


class SerpAPIService:
    """SerpAPIとスクレイピング機能を提供するサービス"""
    
    USER_AGENT = USER_AGENT # クラス変数としてユーザーエージェントを定義

    def __init__(self):
        # 設定から正しく読み込み
        self.api_key = settings.serpapi_key
        self.robot_parsers: Dict[str, Optional[urllib.robotparser.RobotFileParser]] = {} # robots.txtパーサーのキャッシュ
        
    def _ensure_api_key(self):
        """APIキーが設定されているかチェックし、なければ例外を発生させる"""
        if not self.api_key or self.api_key.strip() == "":
            # 設定を再読み込みしてみる
            from app.core.config import settings
            self.api_key = settings.serpapi_key
            
            if not self.api_key or self.api_key.strip() == "":
                raise ValueError("SERPAPI_API_KEY が設定されていません。.env ファイルに SERPAPI_API_KEY を設定してください。")
        
    async def analyze_keywords(self, keywords: List[str], num_articles_to_scrape: int = 5) -> SerpAnalysisResult:
        """
        キーワードを分析し、Google検索結果をSerpAPIで取得してスクレイピングする
        
        Args:
            keywords: 検索キーワードのリスト
            num_articles_to_scrape: スクレイピングする記事数（上位から）
        
        Returns:
            SerpAnalysisResult: 分析結果
        """
        self._ensure_api_key()
        search_query = " ".join(keywords)
        search_results = await self._get_search_results(search_query)
        
        # search_results がエラーを含んでいるかチェック
        if "error" in search_results:
            print(f"Cannot proceed to scrape due to SerpAPI error: {search_results.get('error')}")
            # エラー時は空のスクレイプ結果やデフォルト値でSerpAnalysisResultを返すか、例外を発生させる
            return SerpAnalysisResult(
                search_query=search_query,
                total_results=0,
                related_questions=[],
                organic_results=[],
                scraped_articles=[],
                average_char_count=3000, # デフォルト値
                suggested_target_length=3300 # デフォルト値
            )

        scraped_articles = await self._scrape_articles(search_results, num_articles_to_scrape)
        
        if scraped_articles:
            average_char_count = sum(article.char_count for article in scraped_articles) // len(scraped_articles)
            suggested_target_length = int(average_char_count * 1.1)
        else:
            average_char_count = 3000
            suggested_target_length = 3300
        
        return SerpAnalysisResult(
            search_query=search_query,
            total_results=search_results.get("search_information", {}).get("total_results", 0),
            related_questions=search_results.get("related_questions", []),
            organic_results=search_results.get("organic_results", []),
            scraped_articles=scraped_articles,
            average_char_count=average_char_count,
            suggested_target_length=suggested_target_length
        )
    
    async def _get_search_results(self, query: str) -> Dict[str, Any]:
        """
        SerpAPIでGoogle検索結果を取得
        
        Args:
            query: 検索クエリ
        
        Returns:
            SerpAPIの検索結果
        """
        print(f"Attempting to call actual SerpAPI for query: {query}")
        try:
            results = await self._call_serpapi_real(query)
            if "error" in results:
                print(f"SerpAPI call resulted in an error for query '{query}'. Error: {results['error']}")
                return results 
            print(f"Successfully retrieved real SerpAPI data for query: {query}")
            return results
        except Exception as e:
            print(f"Unexpected error during SerpAPI call for query '{query}'. Exception: {e}")
            return {"error": f"Unexpected exception in _get_search_results: {str(e)}", "query": query}
        
    async def _get_robot_parser(self, base_url: str) -> Optional[urllib.robotparser.RobotFileParser]:
        """指定されたベースURLのrobots.txtを取得してパーサーを返す。キャッシュも利用。"""
        if base_url in self.robot_parsers:
            # キャッシュされたパーサーがNone（取得失敗や存在しない）の場合もそのまま返す
            return self.robot_parsers[base_url]

        robots_url = f"{base_url.rstrip('/')}/robots.txt"
        parser = urllib.robotparser.RobotFileParser()
        # parser.set_url(robots_url) # set_urlはread()の中で呼ばれるので通常不要

        try:
            print(f"Fetching robots.txt from: {robots_url}")
            # requests.getはブロッキングするので、非同期実行
            # response = await asyncio.to_thread(
            #     lambda: requests.get(robots_url, headers={"User-Agent": self.USER_AGENT}, timeout=5)
            # )
            # urllib.robotparser.RobotFileParser.read() は内部で urllib.request を使うが、
            # それもブロッキングするので to_thread で包む
            
            # parser.read() を直接非同期化する代わりに、まずrobots.txtの内容を取得
            response_content = None
            try:
                response = await asyncio.to_thread(
                    lambda: requests.get(robots_url, headers={"User-Agent": self.USER_AGENT}, timeout=5)
                )
                if response.status_code == 200:
                    response_content = response.text
                else:
                    print(f"Failed to fetch robots.txt from {robots_url}, status: {response.status_code}. Assuming allowed.")
                    self.robot_parsers[base_url] = None 
                    return None
            except Exception as fetch_exc:
                 print(f"Exception fetching robots.txt from {robots_url}: {fetch_exc}. Assuming allowed.")
                 self.robot_parsers[base_url] = None
                 return None

            if response_content:
                # parser.parse()は文字列のリストを期待する
                parser.parse(response_content.splitlines())
                self.robot_parsers[base_url] = parser
                return parser
            else: # response_content がNoneのままの場合（上記でNoneが返された場合）
                # このケースは上のstatus_code != 200 や exception fetch でカバーされるはず
                self.robot_parsers[base_url] = None
                return None
                
        except Exception as e: # parse時の予期せぬエラー
            print(f"Error parsing robots.txt content from {robots_url}: {e}. Assuming allowed.")
            self.robot_parsers[base_url] = None 
            return None

    async def _can_fetch(self, url: str, user_agent: str) -> bool:
        """指定されたURLをスクレイピングしてよいかrobots.txtに基づいて判断する"""
        try:
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                print(f"Invalid URL for robots.txt check: {url}. Assuming not allowed.")
                return False
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            parser = await self._get_robot_parser(base_url)
            if parser:
                return parser.can_fetch(user_agent, url)
            
            print(f"No valid robots.txt parser for {base_url}, assuming allowed for {url} (default policy).")
            return True # robots.txtがない、または取得/パース失敗時のデフォルトポリシー
        except Exception as e:
            print(f"Error in _can_fetch for URL {url}: {e}. Assuming not allowed for safety.")
            return False


    async def _scrape_articles(self, search_results: Dict[str, Any], num_articles: int) -> List[ScrapedArticle]:
        """
        検索結果からURLを抽出してスクレイピング (robots.txt対応)
        """
        scraped_articles: List[ScrapedArticle] = [] 
        
        # related_questionsからURLを取得してスクレイピング
        related_questions = search_results.get("related_questions", [])
        for i, question_data in enumerate(related_questions[:2]):  # 最大2件
            if len(scraped_articles) >= num_articles:
                break
            
            url = question_data.get("link")
            if url:
                # ★ robots.txt チェック追加
                if not await self._can_fetch(url, self.USER_AGENT):
                    print(f"Skipping (robots.txt): {url}")
                    continue
                try:
                    print(f"Scraping related question URL: {url}")
                    article_data = await self._scrape_url_real(url)
                    if article_data:
                        scraped_articles.append(ScrapedArticle(
                            url=url,
                            title=article_data.get("title", question_data.get("title", f"関連質問記事 {i+1}")),
                            headings=article_data.get("headings", []),
                            content=article_data.get("content", ""),
                            char_count=article_data.get("char_count", 0),
                            image_count=article_data.get("image_count", 0),
                            source_type="related_question",
                            question=question_data.get("question"),
                            video_count=article_data.get("video_count", 0),
                            table_count=article_data.get("table_count", 0),
                            list_item_count=article_data.get("list_item_count", 0),
                            external_link_count=article_data.get("external_link_count", 0),
                            internal_link_count=article_data.get("internal_link_count", 0),
                            author_info=article_data.get("author_info"),
                            publish_date=article_data.get("publish_date"),
                            modified_date=article_data.get("modified_date"),
                            schema_types=article_data.get("schema_types", [])
                        ))
                    await asyncio.sleep(settings.scraping_delay) # ★ 追加: スクレイピング後に遅延
                except Exception as e:
                    print(f"関連質問記事のスクレイピングエラー {url}: {e}")
                    await asyncio.sleep(settings.scraping_delay) # ★ 追加: エラー時も遅延（次のリクエストのため）
                    continue # 次のURLへ
        
        # organic_resultsからURLを取得してスクレイピング
        organic_results = search_results.get("organic_results", [])
        processed_organic_urls = set() # 同じURLを複数回処理しないように

        for result in organic_results: # まずはnum_articlesの制限なしにループ
            if len(scraped_articles) >= num_articles:
                 break # 必要な記事数が集まったら終了
                
            url = result.get("link")
            if url and url not in processed_organic_urls:
                processed_organic_urls.add(url) #処理済みとして記録
                
                if not await self._can_fetch(url, self.USER_AGENT): # ★ robots.txt チェック追加
                    print(f"Skipping (robots.txt): {url}")
                    continue
                try:
                    print(f"Scraping organic result URL: {url}")
                    article_data = await self._scrape_url_real(url)
                    if article_data:
                        scraped_articles.append(ScrapedArticle(
                            url=url, # オリジナルのURLを保存
                            title=article_data.get("title", result.get("title", "取得した記事")),
                            headings=article_data.get("headings", []),
                            content=article_data.get("content", ""),
                            char_count=article_data.get("char_count", 0),
                            image_count=article_data.get("image_count", 0),
                            source_type="organic_result",
                            position=result.get("position"),
                            video_count=article_data.get("video_count", 0),
                            table_count=article_data.get("table_count", 0),
                            list_item_count=article_data.get("list_item_count", 0),
                            external_link_count=article_data.get("external_link_count", 0),
                            internal_link_count=article_data.get("internal_link_count", 0),
                            author_info=article_data.get("author_info"),
                            publish_date=article_data.get("publish_date"),
                            modified_date=article_data.get("modified_date"),
                            schema_types=article_data.get("schema_types", [])
                        ))
                    await asyncio.sleep(settings.scraping_delay) # ★ 追加: スクレイピング後に遅延
                except Exception as e:
                    print(f"記事のスクレイピングエラー {url}: {e}")
                    await asyncio.sleep(settings.scraping_delay) # ★ 追加: エラー時も遅延（次のリクエストのため）
                    continue # 次のURLへ
        
        # スクレイピングできた記事が少ない場合、モックデータで補完 (要件に応じて削除/変更)
        if len(scraped_articles) < num_articles:
            print(f"スクレイピング記事数が不足 ({len(scraped_articles)}/{num_articles})。モック補完は行いません。")
            # mock_needed = num_articles - len(scraped_articles)
            # mock_articles = self._get_mock_scraped_articles(search_results, mock_needed)
            # scraped_articles.extend(mock_articles)
            pass

        return scraped_articles[:num_articles] # 最終的にnum_articlesに切り詰める
    
    # 実際のSerpAPI呼び出し用の関数（後で実装）
    async def _call_serpapi_real(self, query: str) -> Dict[str, Any]:
        """
        実際のSerpAPI呼び出し（後で実装予定）
        """
        self._ensure_api_key()
        params = {
            "api_key": self.api_key,
            "engine": "google",
            "q": query,
            "location": "Japan",
            "google_domain": "google.com",
            "gl": "jp",
            "hl": "ja",
            "device": "desktop"
        }
        
        print(f"Calling SerpAPI with query: {query}, API Key: {'*' * (len(str(settings.serpapi_key)) - 4) + str(settings.serpapi_key)[-4:] if settings.serpapi_key else 'NOT_SET'}") # APIキーの一部のみ表示

        try:
            # SerpAPIのPythonライブラリ `serpapi` は基本的に同期的なライブラリです。
            # 非同期コンテキスト (async def) 内でブロッキングする同期処理を呼び出す場合、
            # イベントループをブロックしないように `asyncio.to_thread` を使うのが一般的です。
            loop = asyncio.get_running_loop()
            search = GoogleSearch(params) # 同期的なオブジェクト作成
            
            # search.get_dict() も同期的なブロッキング処理
            results = await loop.run_in_executor(None, search.get_dict)
            
            # print(f"SerpAPI Result for '{query}': {results}") # デバッグ用（結果が大きいので注意）
            if not results or "error" in results:
                error_message = results.get("error", "Unknown SerpAPI error") if results else "Empty response from SerpAPI"
                print(f"SerpAPI returned an error or empty response: {error_message}")
                # エラー内容に応じて適切な例外を発生させるか、エラーを示す情報を返す
                # 例: raise SerpAPIError(error_message)
                return {"error": error_message, "search_parameters": results.get("search_parameters")}

            return results

        except Exception as e:
            print(f"Exception during SerpAPI call for query '{query}': {e}")
            # ここでネットワークエラーや予期せぬ例外を捕捉
            # 例: raise NetworkError(f"Failed to call SerpAPI: {e}")
            return {"error": str(e), "query_params": params} # エラー情報を含んだdictを返す例
    
    async def _classify_headings_semantically(self, structured_headings: List[Dict[str, Any]], original_url: str = "N/A") -> List[Dict[str, Any]]:
        """
        見出しリストを受け取り、各見出しに意味的な分類を行う (ルールベース)。
        original_url はAPIベースの分類器とのインターフェース互換性のために追加されましたが、この関数では使用されません。
        """
        classified_headings = []
        for heading_node in structured_headings:
            new_node = heading_node.copy()
            level = new_node.get("level", 0)
            text = new_node.get("text", "")
            semantic_type = "body"
            lower_text = text.lower()

            if level <= 2:
                if any(kw in lower_text for kw in ["はじめに", "序論", "導入", "introduction"]):
                    semantic_type = "introduction"
                elif any(kw in lower_text for kw in ["まとめ", "結論", "結論として", "conclusion", "おわりに"]):
                    semantic_type = "conclusion"
            
            new_node["semantic_type"] = semantic_type
            
            if "children" in new_node and new_node["children"]:
                new_node["children"] = await self._classify_headings_semantically(new_node["children"], original_url)
            
            classified_headings.append(new_node)
        return classified_headings
    
    async def _classify_headings_semantically_gemini(self, structured_headings: List[Dict[str, Any]], original_url: str = "N/A") -> List[Dict[str, Any]]:
        """Gemini API を使用して見出しリストを意味的に分類する。"""
        if not settings.gemini_api_key:
            print("Gemini APIキーが設定されていません。ルールベースの分類フォールバックも現状ありません。")
            for heading in structured_headings:
                heading['semantic_type'] = 'body' 
                if heading.get('children'):
                    # 再帰呼び出しにも original_url を渡す
                    await self._classify_headings_semantically_gemini(heading['children'], original_url)
            return structured_headings

        try:
            setup_genai_client()
        except Exception as e:
            print(f"Gemini APIキーの設定に失敗しました: {e}")
            for heading in structured_headings: # フォールバック
                heading['semantic_type'] = 'body'
                if heading.get('children'):
                     # 再帰呼び出しにも original_url を渡す
                     await self._classify_headings_semantically_gemini(heading['children'], original_url)
            return structured_headings

        model = genai.GenerativeModel('gemini-2.0-flash') # または 'gemini-pro'
        
        # APIに渡すために見出しテキストのリストを準備 (IDも振る)
        def _flatten_headings(headings_list, prefix=""):
            flat_list = []
            for i, heading in enumerate(headings_list):
                heading_id = f"{prefix}{i+1}"
                flat_list.append({"id": heading_id, "text": heading["text"], "level": heading["level"]})
                if heading.get("children"):
                    flat_list.extend(_flatten_headings(heading["children"], f"{heading_id}."))
            return flat_list

        flat_headings_with_ids = _flatten_headings(structured_headings)
        
        if not flat_headings_with_ids:
            return structured_headings

        # プロンプトの準備
        prompt_headings = [{"id": h["id"], "text": h["text"], "level": h["level"]} for h in flat_headings_with_ids]
        
        # Gemini用のプロンプト (OpenAI版のものをベースに調整)
        full_prompt = (
            "あなたは、与えられた記事の見出しリストを分析し、各見出しが記事全体の構造の中でどのような意味的役割を持つかを判断するAIアシスタントです。\\n"
            "以下の指示に従って、各見出しを最も適切と思われるカテゴリに分類してください。\\n\\n"
            "【分類カテゴリと判断ヒント】\\n"
            "1. 'introduction': 記事全体の導入部、序論、概要、目的、背景などを説明する見出し。\\n"
            "   - キーワード例: 「はじめに」「序論」「導入」「概要」「この記事について」「目的」「背景」「～とは？」\\n"
            "   - 記事の最初の方（特に最初のH1またはH2）に出現しやすい。\\n"
            "2. 'body': 記事の本論部分。主題に関する具体的な説明、議論、方法、手順、事例、メリット・デメリット、分析、考察など。\\n"
            "   - 上記以外のカテゴリに明確に当てはまらない場合は、このカテゴリを選択してください。\\n"
            "3. 'conclusion': 記事全体の結論部、まとめ、要約、今後の展望、提言など。\\n"
            "   - キーワード例: 「まとめ」「結論」「総括」「おわりに」「最後に」「今後の課題」「提言」\\n"
            "   - 記事の最後の方に出現しやすい。\\n"
            "4. 'faq': よくある質問とその回答をまとめたセクションの見出し。\\n"
            "   - キーワード例: 「FAQ」「よくある質問」「Q&A」\\n"
            "5. 'references': 参考文献、参考資料、関連情報源などを示すセクションの見出し。\\n"
            "   - キーワード例: 「参考文献」「参考資料」「関連リンク」「もっと読む」\\n"
            "6. 'other': 上記のいずれにも明確に当てはまらない特殊な役割を持つ見出し（例: 用語集、会社概要など）。使用は最小限にしてください。\\n\\n"
            "【指示】\\n"
            "- 見出しのテキスト内容、レベル（h1-h6）、そしてリスト内での出現順を考慮して分類してください。\\n"
            "- 特に、'introduction'と'conclusion'は記事構造における位置が重要です。\\n"
            "- 明確なキーワード（例:「まとめ」）が存在する場合は、それを優先して分類してください。\\n"
            "- 回答は、各見出しのIDと分類結果を含むJSONオブジェクトのリスト形式で、以下のように返してください:\\n"
            "  例: [{'id': '1', 'classification': 'introduction'}, {'id': '1.1', 'classification': 'body'}, {'id': '2', 'classification': 'conclusion'}]\\n"
            "- 他の形式ではなく、必ずこのJSONリスト形式で回答してください。\\n\\n"
            "以下の見出しリストを分類してください:\\n"
            f"{json.dumps(prompt_headings, ensure_ascii=False, indent=2)}"
        )

        print(f"Gemini APIを呼び出します (URL: {original_url}, 見出し数: {len(flat_headings_with_ids)})...")
        start_time = time.monotonic()

        try:
            generation_config = genai.types.GenerationConfig(
                # candidate_count=1, # デフォルトは1
                response_mime_type="application/json", 
                temperature=0.2
            )
            response = await model.generate_content_async(
                contents=[full_prompt], 
                generation_config=generation_config
            )
            
            raw_response_content = response.text 
            
            classification_map: Dict[str, str] = {}

            if raw_response_content:
                try:
                    json_data = json.loads(raw_response_content)
                    if isinstance(json_data, list):
                        for item in json_data:
                            if isinstance(item, dict) and "id" in item and "classification" in item:
                                classification_map[item["id"]] = item["classification"] 
                    elif isinstance(json_data, dict):
                        if "classifications" in json_data and isinstance(json_data["classifications"], list):
                            for item in json_data["classifications"]:
                                if isinstance(item, dict) and "id" in item and "classification" in item:
                                    classification_map[item["id"]] = item["classification"] 
                        else: # フラットな辞書またはその他の辞書形式
                            for key, value in json_data.items():
                                if isinstance(value, str): # { "id": "class" }
                                    classification_map[key] = value
                                elif isinstance(value, dict) and "classification" in value: # { "id": {"classification": "class"} }
                                    classification_map[key] = value["classification"]
                            if not classification_map: # 上記で見つからなかった場合
                                print(f"Gemini APIからの辞書形式JSONのパースに失敗 (URL: {original_url}): {raw_response_content[:200]}...")
                    else:
                        print(f"Gemini APIからの予期しないJSONルート型 (URL: {original_url}): {type(json_data)} {raw_response_content[:200]}...")

                except json.JSONDecodeError:
                    print(f"Gemini APIからのJSONパースエラー (URL: {original_url}): {raw_response_content[:200]}...")
            else:
                print(f"Gemini APIからの応答が空でした (URL: {original_url})")
            
            end_time = time.monotonic()
            print(f"Gemini API 処理時間: {end_time - start_time:.2f}秒 (URL: {original_url})")

            def _apply_classification(headings_list, prefix=""):
                for i, heading in enumerate(headings_list):
                    heading_id = f"{prefix}{i+1}"
                    heading["semantic_type"] = classification_map.get(heading_id, "body") 
                    if heading.get("children"):
                        _apply_classification(heading["children"], f"{heading_id}.")
                return headings_list
            
            return _apply_classification(structured_headings)

        except Exception as e:
            print(f"Gemini API呼び出し中または応答処理中にエラーが発生しました (URL: {original_url}): {e}")

        # エラー時やAPIキーがない場合のフォールバック
        for heading_node in structured_headings:
            heading_node['semantic_type'] = 'body' 
            if 'children' in heading_node and heading_node['children']:
                 await self._classify_headings_semantically_gemini(heading_node['children'], original_url) # 再帰呼び出し
        return structured_headings

    def _add_char_counts_to_headings_recursive(
        self,
        heading_node_list: List[Dict[str, Any]], 
        all_heading_tags_in_document: List[Any] # Flat list of all H tags in the order they appear
    ):
        """
        見出しノードのリストにセクション文字数を再帰的に追加する。
        'char_count_section' は、その見出しから次の同位または上位の見出しまでの
        間のテキスト（下位見出しのテキストも含むgrossカウント）の文字数。
        """
        tag_to_document_index_map = {tag: i for i, tag in enumerate(all_heading_tags_in_document)}

        for node in heading_node_list:
            if 'tag' not in node or not hasattr(node['tag'], 'name'):
                node['char_count_section'] = 0
                if node.get('children'):
                    self._add_char_counts_to_headings_recursive(node['children'], all_heading_tags_in_document)
                continue

            current_tag = node['tag']
            current_tag_doc_index = tag_to_document_index_map.get(current_tag)

            section_limit_tag = None
            if current_tag_doc_index is not None:
                for i in range(current_tag_doc_index + 1, len(all_heading_tags_in_document)):
                    potential_next_tag = all_heading_tags_in_document[i]
                    if int(potential_next_tag.name[1:]) <= node['level']:
                        section_limit_tag = potential_next_tag
                        break
            
            text_content_parts = []
            for sibling_element in current_tag.next_siblings:
                if section_limit_tag and sibling_element == section_limit_tag:
                    break 
                
                if hasattr(sibling_element, 'name') and sibling_element.name in ['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']:
                    continue
                
                if isinstance(sibling_element, NavigableString):
                    stripped_text = str(sibling_element).strip()
                    if stripped_text:
                        text_content_parts.append(stripped_text)
                elif hasattr(sibling_element, 'get_text'):
                    stripped_text = sibling_element.get_text(separator=' ', strip=True)
                    if stripped_text:
                        text_content_parts.append(stripped_text)
            
            full_section_text = " ".join(text_content_parts)
            # 文字数はスペースを除いたものをカウント（任意、一貫性のため）
            node['char_count_section'] = len(full_section_text.replace(" ", ""))

            if node.get('children'):
                self._add_char_counts_to_headings_recursive(node['children'], all_heading_tags_in_document)


    async def _scrape_url_real(self, url: str) -> Optional[Dict[str, Any]]:
        """ 実際のURLスクレイピング """
        current_url = url
        try:
            headers = {'User-Agent': self.USER_AGENT}
            response = await asyncio.to_thread(
                lambda: requests.get(current_url, headers=headers, timeout=settings.scraping_timeout, allow_redirects=True)
            )
            
            if response.history:
                current_url = response.url
            if response.status_code != 200:
                return None
            
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'html.parser')
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else "タイトル取得できず"
            
            main_content_selectors = [
                'article', 'main',
                'div[class*="content"]', 'div[class*="post"]', 'div[class*="entry"]', 'div[class*="article"]',
                'section[class*="content"]', 'section[class*="post"]', 'section[class*="entry"]',
                'div[id*="content"]', 'div[id*="main"]',
            ]
            content_element = None
            for selector in main_content_selectors:
                content_element = soup.select_one(selector)
                if content_element:
                    break
            
            if not content_element:
                content_element = soup.body
            if not content_element:
                return {"title": title, "headings": [], "content": "", "char_count": 0, "image_count": 0}

            # 不要要素の除去 (文字数カウント前に実行)
            for unwanted_selector in ['nav', 'footer', 'header', 'aside', 'form', 'script', 'style', '.noprint', '[aria-hidden="true"]', 'figure > figcaption']:
                for tag in content_element.select(unwanted_selector):
                    tag.decompose()
            for ad_selector in ['div[class*="ad"]', 'div[id*="ad"]', 'div[class*="OUTBRAIN"]', 'div[class*="recommend"]', 'aside[class*="related"]']:
                for tag in content_element.select(ad_selector):
                    tag.decompose()

            # 見出しタグの抽出 (除去処理後に行う)
            all_heading_tags_in_content_element = content_element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            
            structured_headings: List[Dict[str, Any]] = []
            parent_stack: List[Tuple[int, List[Dict[str, Any]]]] = [(0, structured_headings)]

            for tag_object in all_heading_tags_in_content_element: # tag_object を直接使用
                if not hasattr(tag_object, 'name') or not tag_object.name:
                    continue
                level = int(tag_object.name[1:])
                text = tag_object.get_text(strip=True)
                if not text or len(text) >= 200:
                    continue

                current_heading_node = {"level": level, "text": text, "children": [], "tag": tag_object} # ★ tag オブジェクトを保存

                while parent_stack[-1][0] >= level:
                    parent_stack.pop()
                parent_stack[-1][1].append(current_heading_node)
                children_list: List[Dict[str, Any]] = current_heading_node["children"]
                parent_stack.append((level, children_list))
            
            # 意味的分類
            classified_final_headings = await self._classify_headings_semantically(structured_headings, original_url=current_url)
            
            # ★ セクション文字数カウントの追加
            if classified_final_headings and all_heading_tags_in_content_element:
                self._add_char_counts_to_headings_recursive(classified_final_headings, all_heading_tags_in_content_element)

            # 記事全体のテキスト抽出と文字数カウント (これは変更なし)
            text_blocks = []
            for element in content_element.find_all(['p', 'div', 'li', 'span', 'td', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'], recursive=True):
                if not hasattr(element, 'find_all'):
                    continue
                # スクリプト/スタイルは既に除去されているはずだが念のため
                for unwanted_tag in element.find_all(['script', 'style'], recursive=False):
                    unwanted_tag.decompose()
                block_text = element.get_text(separator=' ', strip=True)
                if block_text and len(block_text) > 20:
                    parent_text = element.parent.get_text(separator=' ', strip=True) if element.parent else ""
                    if parent_text != block_text or (hasattr(element, 'name') and element.name in ['p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                        text_blocks.append(block_text)
            
            final_content_parts = []
            seen_content_parts = set()
            for block in text_blocks:
                first_part = block[:100]
                if first_part not in seen_content_parts:
                    final_content_parts.append(block)
                    seen_content_parts.add(first_part)
                    if sum(len(p) for p in final_content_parts) > 15000:
                        break
            
            content_text = "\n\n".join(final_content_parts)
            char_count = len("".join(final_content_parts).replace(" ","")) # スペース除外で統一
            
            img_tags = content_element.find_all('img')
            image_count = len([img for img in img_tags if hasattr(img, 'get') and img.get('src') and isinstance(img.get('src'), str) and not img.get('src', '').startswith('data:')])
            
            # ★ 新しいコンテンツフォーマット分析
            # 動画数の計算（video + YouTubeなどのiframe）
            video_tags = content_element.find_all('video')
            iframe_tags = content_element.find_all('iframe')
            video_iframes = [iframe for iframe in iframe_tags 
                           if hasattr(iframe, 'get') and iframe.get('src') and isinstance(iframe.get('src'), str) and any(domain in iframe.get('src', '') 
                               for domain in ['youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com'])]
            video_count = len(video_tags) + len(video_iframes)
            
            # テーブル数
            table_count = len(content_element.find_all('table'))
            
            # リスト項目総数
            list_items = content_element.find_all('li')
            list_item_count = len(list_items)
            
            # リンク分析（外部・内部）
            all_links = content_element.find_all('a', href=True)
            external_links = []
            internal_links = []
            current_domain = urlparse(current_url).netloc if current_url else ""
            
            for link in all_links:
                if not hasattr(link, 'get'):
                    continue
                href = link.get('href', '')
                if not isinstance(href, str):
                    continue
                if href.startswith('http'):
                    link_domain = urlparse(href).netloc
                    if link_domain != current_domain:
                        external_links.append(href)
                    else:
                        internal_links.append(href)
                elif href.startswith('/') or not href.startswith('#'):
                    internal_links.append(href)  # 相対パスは内部リンクとみなす
            
            external_link_count = len(external_links)
            internal_link_count = len(internal_links)
            
            # ★ メタデータ抽出（基本版）
            author_info = None
            publish_date = None
            modified_date = None
            
            # 著者情報の抽出
            author_meta = soup.find('meta', attrs={'name': 'author'})
            if author_meta and hasattr(author_meta, 'get'):
                author_content = author_meta.get('content')
                if isinstance(author_content, str):
                    author_info = author_content
            else:
                # クラス名で著者情報を探す
                author_elements = soup.find_all(['div', 'span', 'p'], class_=re.compile(r'author', re.I))
                if author_elements:
                    author_info = author_elements[0].get_text(strip=True)
            
            # 公開日・更新日の抽出
            pub_meta = soup.find('meta', attrs={'property': 'article:published_time'})
            if pub_meta and hasattr(pub_meta, 'get'):
                pub_content = pub_meta.get('content')
                if isinstance(pub_content, str):
                    publish_date = pub_content
            
            mod_meta = soup.find('meta', attrs={'property': 'article:modified_time'})
            if mod_meta and hasattr(mod_meta, 'get'):
                mod_content = mod_meta.get('content')
                if isinstance(mod_content, str):
                    modified_date = mod_content
            
            # ★ 構造化データ（Schema.org）の抽出
            schema_types = []
            ld_json_scripts = soup.find_all('script', type='application/ld+json')
            for script in ld_json_scripts:
                try:
                    if hasattr(script, 'string') and script.string and isinstance(script.string, str):
                        ld_data = json.loads(script.string)
                        if isinstance(ld_data, dict) and '@type' in ld_data:
                            schema_types.append(ld_data['@type'])
                        elif isinstance(ld_data, list):
                            for item in ld_data:
                                if isinstance(item, dict) and '@type' in item:
                                    schema_types.append(item['@type'])
                except (json.JSONDecodeError, AttributeError, TypeError):
                    continue
            
            return {
                "title": title,
                "headings": classified_final_headings[:30],
                "content": content_text.strip()[:10000],
                "char_count": char_count,
                "image_count": image_count,
                # ★ 新しいフィールド
                "video_count": video_count,
                "table_count": table_count,
                "list_item_count": list_item_count,
                "external_link_count": external_link_count,
                "internal_link_count": internal_link_count,
                "author_info": author_info,
                "publish_date": publish_date,
                "modified_date": modified_date,
                "schema_types": schema_types
            }
            
        except requests.exceptions.Timeout:
            print(f"タイムアウト: {url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"リクエストエラー {url}: {e}")
            return None
        except Exception as e:
            print(f"スクレイピング一般エラー {url}: {e}")
            import traceback
            traceback.print_exc()
            return None

# サービスのインスタンス（遅延ロード）
_serpapi_service_instance = None

def get_serpapi_service() -> SerpAPIService:
    """SerpAPIServiceのシングルトンインスタンスを取得"""
    global _serpapi_service_instance
    if _serpapi_service_instance is None:
        _serpapi_service_instance = SerpAPIService()
    return _serpapi_service_instance

# 使用時は get_serpapi_service() を呼び出してください 

# serpapi_service.py の末尾に追加 (テスト後削除またはコメントアウト)
if __name__ == '__main__':
    import asyncio
    import json 

    async def main_test_call_real():
        service = SerpAPIService()
        test_query = "Python FastAPI" 
        print(f"--- Testing _call_serpapi_real for query: '{test_query}' ---")
        try:
            result = await service._call_serpapi_real(query=test_query)
            print("--- Full API Response (JSON) ---")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("--- End of Full API Response ---")
            if "error" in result:
                print(f"Test FAILED or API returned error: {result['error']}")
            else:
                print("Test SUCCEEDED. Basic API call seems to work.")
        except Exception as e:
            print(f"Test FAILED with unhandled exception: {e}")
        print("--- End of _call_serpapi_real test ---")

    async def main_test_scrape_real_serp(use_generative_ai_for_classification: bool = False): 
        service = SerpAPIService()
        test_query = "犬 ペット ペットショップ ペット用品" 
        num_to_scrape = 3 # ★ テストのため記事数を少なく維持 (元は3)
        print(f"\n--- Testing full analyze_keywords for query: '{test_query}' with {num_to_scrape} articles to scrape ---")
        
        # Temporarily override classification method for testing
        if use_generative_ai_for_classification:
            print("--- 見出し分類に Gemini API を使用します ---")
            # Use Gemini classification directly in the service call
        else:
            print("--- 見出し分類にルールベースを使用します ---")
        
        analysis_result = await service.analyze_keywords(keywords=[test_query], num_articles_to_scrape=num_to_scrape)
        
        print("\n--- SerpAnalysisResult (from analyze_keywords) ---")
        print(f"Search Query: {analysis_result.search_query}")
        print(f"Total Results from SerpAPI: {analysis_result.total_results}")
        print(f"Number of Related Questions from SerpAPI: {len(analysis_result.related_questions)}")
        print(f"Number of Organic Results from SerpAPI: {len(analysis_result.organic_results)}")
        print(f"Number of Scraped Articles: {len(analysis_result.scraped_articles)}")
        print(f"Average Char Count of Scraped: {analysis_result.average_char_count}")
        print(f"Suggested Target Length: {analysis_result.suggested_target_length}")
        
        # ★ 新しいコンテンツフォーマット分析のサマリーを表示
        if analysis_result.scraped_articles:
            total_videos = sum(getattr(article, 'video_count', 0) for article in analysis_result.scraped_articles)
            total_tables = sum(getattr(article, 'table_count', 0) for article in analysis_result.scraped_articles)
            total_list_items = sum(getattr(article, 'list_item_count', 0) for article in analysis_result.scraped_articles)
            total_external_links = sum(getattr(article, 'external_link_count', 0) for article in analysis_result.scraped_articles)
            total_internal_links = sum(getattr(article, 'internal_link_count', 0) for article in analysis_result.scraped_articles)
            
            articles_with_author = sum(1 for article in analysis_result.scraped_articles if getattr(article, 'author_info', None))
            articles_with_publish_date = sum(1 for article in analysis_result.scraped_articles if getattr(article, 'publish_date', None))
            articles_with_schema = sum(1 for article in analysis_result.scraped_articles if getattr(article, 'schema_types', []))
            
            print("")
            print("📊 Content Format Analysis Summary:")
            print(f"  Total Videos: {total_videos} (avg: {total_videos/len(analysis_result.scraped_articles):.1f} per article)")
            print(f"  Total Tables: {total_tables} (avg: {total_tables/len(analysis_result.scraped_articles):.1f} per article)")
            print(f"  Total List Items: {total_list_items} (avg: {total_list_items/len(analysis_result.scraped_articles):.1f} per article)")
            print(f"  Total External Links: {total_external_links} (avg: {total_external_links/len(analysis_result.scraped_articles):.1f} per article)")
            print(f"  Total Internal Links: {total_internal_links} (avg: {total_internal_links/len(analysis_result.scraped_articles):.1f} per article)")
            print("")
            print("🔍 E-E-A-T Metadata Analysis:")
            print(f"  Articles with Author Info: {articles_with_author}/{len(analysis_result.scraped_articles)} ({articles_with_author/len(analysis_result.scraped_articles)*100:.1f}%)")
            print(f"  Articles with Publish Date: {articles_with_publish_date}/{len(analysis_result.scraped_articles)} ({articles_with_publish_date/len(analysis_result.scraped_articles)*100:.1f}%)")
            print(f"  Articles with Schema Data: {articles_with_schema}/{len(analysis_result.scraped_articles)} ({articles_with_schema/len(analysis_result.scraped_articles)*100:.1f}%)")

            print("\n--- Details of Scraped Articles ---")
            if not analysis_result.scraped_articles: 
                print("No articles were scraped.")
            else:
                # ★ 重複チェック追加
                urls_seen = set()
                for i, article in enumerate(analysis_result.scraped_articles):
                    print(f"--- Article {i+1} ---")
                    print(f"  URL: {article.url}")
                    
                    # ★ 重複URLチェック
                    if article.url in urls_seen:
                        print("  ⚠️  WARNING: Duplicate URL detected!")
                    else:
                        urls_seen.add(article.url)
                    
                    print(f"  Title: {article.title}")
                    print(f"  Headings Count: {len(article.headings)}")
                    print("  Headings Structure:")
                    
                    # ★ JSON出力を安全に実行
                    try:
                        def format_headings_for_print(headings_list):
                            formatted = []
                            for h_dict in headings_list: # Renamed h to h_dict to avoid conflict
                                entry = {
                                    "level": h_dict.get("level"), 
                                    "text": h_dict.get("text"), 
                                    "semantic_type": h_dict.get("semantic_type", "N/A"),
                                    "char_count_section": h_dict.get("char_count_section", "N/A") # ★ 追加
                                }
                                if h_dict.get("children"):
                                    entry["children"] = format_headings_for_print(h_dict["children"])
                                formatted.append(entry)
                            return formatted
                            
                        formatted_headings = format_headings_for_print(article.headings)
                        print(json.dumps(formatted_headings, indent=2, ensure_ascii=False))
                        
                    except TypeError as e:
                        print(f"    ❌ Could not serialize headings to JSON: {e}")
                        print(f"    Raw headings data (first 3): {article.headings[:3]}")
                    except Exception as e:
                        print(f"    ❌ Unexpected error in JSON serialization: {e}")

                    content_preview_text = article.content[:200].replace('\n', ' ')
                    print(f"  Content Preview: {content_preview_text}...")
                    print(f"  Char Count: {article.char_count}") # Overall article char count
                    print(f"  Image Count: {article.image_count}")
                    
                    # ★ 新しいコンテンツフォーマット分析結果を表示
                    print(f"  Video Count: {getattr(article, 'video_count', 0)}")
                    print(f"  Table Count: {getattr(article, 'table_count', 0)}")
                    print(f"  List Item Count: {getattr(article, 'list_item_count', 0)}")
                    print(f"  External Link Count: {getattr(article, 'external_link_count', 0)}")
                    print(f"  Internal Link Count: {getattr(article, 'internal_link_count', 0)}")
                    
                    # ★ メタデータ情報を表示
                    author_info = getattr(article, 'author_info', None)
                    if author_info:
                        print(f"  Author Info: {author_info}")
                    else:
                        print("  Author Info: Not found")
                    
                    publish_date = getattr(article, 'publish_date', None)
                    if publish_date:
                        print(f"  Publish Date: {publish_date}")
                    else:
                        print("  Publish Date: Not found")
                    
                    modified_date = getattr(article, 'modified_date', None)
                    if modified_date:
                        print(f"  Modified Date: {modified_date}")
                    else:
                        print("  Modified Date: Not found")
                    
                    schema_types = getattr(article, 'schema_types', [])
                    if schema_types:
                        print(f"  Schema Types: {', '.join(schema_types)}")
                    else:
                        print("  Schema Types: None found")
                    
                    print(f"  Source Type: {article.source_type}")
                    if article.position:
                        print(f"  Original Position: {article.position}")
                    if article.question:
                        print(f"  Original Question: {article.question}")
                
        print("--- End of full analyze_keywords test ---")

    # asyncio.run(main_test_call_real())
    # asyncio.run(main_test_scrape_real_serp(use_generative_ai_for_classification=False)) 
    asyncio.run(main_test_scrape_real_serp(use_generative_ai_for_classification=True)) 