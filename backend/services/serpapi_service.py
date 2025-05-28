import json
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
from core.config import settings


@dataclass
class ScrapedArticle:
    """スクレイピングした記事の情報"""
    url: str
    title: str
    headings: List[str]  # 見出しのリスト (H1, H2, H3など)
    content: str  # 記事本文
    char_count: int  # 文字数
    image_count: int  # 画像数
    source_type: str  # "related_question" または "organic_result"
    position: Optional[int] = None  # organic_resultの場合の順位
    question: Optional[str] = None  # related_questionの場合の質問文


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
    
    def __init__(self):
        self.api_key = getattr(settings, 'serpapi_key', None) or "9fbf7061f3a2d6c6b3f80dbfbac178db18cb384bade1ce893e29efdb32b6c8fe"
        
    async def analyze_keywords(self, keywords: List[str], num_articles_to_scrape: int = 5) -> SerpAnalysisResult:
        """
        キーワードを分析し、Google検索結果をSerpAPIで取得してスクレイピングする
        
        Args:
            keywords: 検索キーワードのリスト
            num_articles_to_scrape: スクレイピングする記事数（上位から）
        
        Returns:
            SerpAnalysisResult: 分析結果
        """
        # キーワードを結合して検索クエリを作成
        search_query = " ".join(keywords)
        
        # SerpAPIで検索実行（現在はモックデータを返す）
        search_results = await self._get_search_results(search_query)
        
        # 上位記事のスクレイピング（現在はモックデータを返す）
        scraped_articles = await self._scrape_articles(search_results, num_articles_to_scrape)
        
        # 平均文字数を計算
        if scraped_articles:
            average_char_count = sum(article.char_count for article in scraped_articles) // len(scraped_articles)
            suggested_target_length = int(average_char_count * 1.1)  # 平均の1.1倍を提案
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
        try:
            # 実際のSerpAPI呼び出しを実行
            return self._call_serpapi_real(query)
        except Exception as e:
            print(f"SerpAPI呼び出しエラー、モックデータを使用: {e}")
            # エラーの場合はモックデータを返す
            return self._get_mock_search_results(query)
    
    async def _scrape_articles(self, search_results: Dict[str, Any], num_articles: int) -> List[ScrapedArticle]:
        """
        検索結果からURLを抽出してスクレイピング
        
        Args:
            search_results: SerpAPIの検索結果
            num_articles: スクレイピングする記事数
        
        Returns:
            スクレイピングした記事のリスト
        """
        scraped_articles = []
        
        # related_questionsからURLを取得してスクレイピング
        related_questions = search_results.get("related_questions", [])
        for i, question_data in enumerate(related_questions[:2]):  # 最大2件
            if len(scraped_articles) >= num_articles:
                break
            
            url = question_data.get("link")
            if url:
                try:
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
                            question=question_data.get("question")
                        ))
                except Exception as e:
                    print(f"関連質問記事のスクレイピングエラー {url}: {e}")
                    continue
        
        # organic_resultsからURLを取得してスクレイピング
        organic_results = search_results.get("organic_results", [])
        for result in organic_results[:num_articles-len(scraped_articles)]:
            if len(scraped_articles) >= num_articles:
                break
                
            url = result.get("link")
            if url:
                try:
                    article_data = await self._scrape_url_real(url)
                    if article_data:
                        scraped_articles.append(ScrapedArticle(
                            url=url,
                            title=article_data.get("title", result.get("title", "取得した記事")),
                            headings=article_data.get("headings", []),
                            content=article_data.get("content", ""),
                            char_count=article_data.get("char_count", 0),
                            image_count=article_data.get("image_count", 0),
                            source_type="organic_result",
                            position=result.get("position")
                        ))
                except Exception as e:
                    print(f"記事のスクレイピングエラー {url}: {e}")
                    continue
        
        # スクレイピングできた記事が少ない場合、モックデータで補完
        if len(scraped_articles) < num_articles:
            print(f"スクレイピング記事数が不足 ({len(scraped_articles)}/{num_articles})、モックデータで補完")
            mock_articles = self._get_mock_scraped_articles(search_results, num_articles - len(scraped_articles))
            scraped_articles.extend(mock_articles)
        
        return scraped_articles[:num_articles]
    
    def _get_mock_search_results(self, query: str) -> Dict[str, Any]:
        """モック用の検索結果データ"""
        return {
            "search_metadata": {
                "id": "68371d74eb2bd1887dd70ae6",
                "status": "Success",
                "created_at": "2025-05-28 14:28:04 UTC",
                "total_time_taken": 6.68
            },
            "search_parameters": {
                "engine": "google",
                "q": query,
                "location_used": "Japan",
                "hl": "ja",
                "gl": "jp"
            },
            "search_information": {
                "query_displayed": query,
                "total_results": 3430000,
                "time_taken_displayed": 0.39
            },
            "related_questions": [
                {
                    "question": "子育てしやすい家の特徴は？",
                    "snippet": None,
                    "title": "子育てしやすい家の特徴",
                    "link": "https://www.yamane-m.co.jp/kurasu/6307/",
                    "list": [
                        "子どもを見守りながら家事ができる",
                        "家族が集まって過ごせるスペースがある",
                        "効率良く家事ができる",
                        "子どもの成長に合わせてレイアウトを変えられる"
                    ]
                },
                {
                    "question": "自然素材のメリット・デメリットは？",
                    "snippet": None,
                    "title": "天然素材のメリット・デメリット",
                    "link": "https://ienoki.com/feature_naturalmaterials/",
                    "list": [
                        "肌触りがやさしく、見た目にも優しい",
                        "有害物質をほとんど出さない",
                        "断熱効果・調湿効果がある"
                    ]
                }
            ],
            "organic_results": [
                {
                    "position": 1,
                    "title": "自然素材の家での子育てにデメリットはある？",
                    "link": "https://www.tabatakouji.biz/home_building/example1/",
                    "snippet": "どちらも自然素材の良さを活かした住宅ですが、工務店で建てる場合、自然素材選びの自由度が上がるというメリットがあります。"
                },
                {
                    "position": 2,
                    "title": "子育てに嬉しい！自然素材に包まれる優しい家づくりとは？",
                    "link": "https://dh-f.jp/blog/4485/",
                    "snippet": "健康を第一に考え天然素材を使用した塗り壁は、多孔質な特性で室内の湿気を吸収、放散することで湿度を一定に保ちします。"
                },
                {
                    "position": 3,
                    "title": "自然素材に包まれた子育てがしやすい家",
                    "link": "https://amshome.jp/work/727",
                    "snippet": "創業60年を超える材木会社の経験を活かし、良質の無垢材を使った、注文住宅・リフォームを行っています。"
                }
            ]
        }
    
    def _get_mock_scraped_articles(self, search_results: Dict[str, Any], num_articles: int) -> List[ScrapedArticle]:
        """モック用のスクレイピング結果データ"""
        mock_articles = []
        
        # related_questionsからの記事
        for i, question_data in enumerate(search_results.get("related_questions", [])[:2]):
            mock_articles.append(ScrapedArticle(
                url=question_data.get("link", f"https://example.com/question-{i}"),
                title=question_data.get("title", f"関連質問記事 {i+1}"),
                headings=[
                    "H1: " + question_data.get("title", f"関連質問記事 {i+1}"),
                    "H2: 概要",
                    "H2: 詳細解説",
                    "H3: ポイント1",
                    "H3: ポイント2",
                    "H2: まとめ"
                ],
                content=f"この記事は{question_data.get('question', '質問')}について詳しく解説しています。" * 50,
                char_count=2800 + i * 200,
                image_count=3 + i,
                source_type="related_question",
                question=question_data.get("question")
            ))
        
        # organic_resultsからの記事
        for i, result in enumerate(search_results.get("organic_results", [])[:num_articles-len(mock_articles)]):
            mock_articles.append(ScrapedArticle(
                url=result.get("link", f"https://example.com/organic-{i}"),
                title=result.get("title", f"上位記事 {i+1}"),
                headings=[
                    "H1: " + result.get("title", f"上位記事 {i+1}"),
                    "H2: はじめに",
                    "H2: 基本知識",
                    "H3: 重要なポイント",
                    "H3: 注意事項",
                    "H2: 実践方法",
                    "H3: ステップ1",
                    "H3: ステップ2",
                    "H2: よくある質問",
                    "H2: まとめ"
                ],
                content=f"この記事は{result.get('title', '記事')}について包括的に説明しています。" * 60,
                char_count=3200 + i * 150,
                image_count=4 + i,
                source_type="organic_result",
                position=result.get("position")
            ))
        
        return mock_articles
    
    # 実際のSerpAPI呼び出し用の関数（後で実装）
    def _call_serpapi_real(self, query: str) -> Dict[str, Any]:
        """
        実際のSerpAPI呼び出し（後で実装予定）
        """
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
        
        search = GoogleSearch(params)
        results = search.get_dict()
        return results
    
    async def _scrape_url_real(self, url: str) -> Dict[str, Any]:
        """
        実際のURLスクレイピング
        """
        try:
            # HTTPリクエストでHTMLを取得
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # asyncio.to_threadでブロッキング処理を非同期化
            response = await asyncio.to_thread(
                lambda: requests.get(url, headers=headers, timeout=10)
            )
            
            if response.status_code != 200:
                print(f"HTTP {response.status_code}: {url}")
                return None
            
            # BeautifulSoupで解析
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # タイトルを取得
            title_tag = soup.find('title')
            title = title_tag.get_text().strip() if title_tag else "タイトル取得できず"
            
            # 見出しを取得 (H1, H2, H3)
            headings = []
            for heading_tag in soup.find_all(['h1', 'h2', 'h3']):
                heading_text = heading_tag.get_text().strip()
                if heading_text and len(heading_text) < 200:  # 長すぎる見出しを除外
                    headings.append(f"{heading_tag.name.upper()}: {heading_text}")
            
            # 本文を取得 (article, main, divなどから)
            content_candidates = soup.find_all(['article', 'main', 'div'], class_=lambda x: x and any(
                keyword in str(x).lower() for keyword in ['content', 'article', 'post', 'entry', 'main']
            ))
            
            # フォールバック: pタグから本文を抽出
            if not content_candidates:
                content_candidates = soup.find_all('p')
            
            content_text = ""
            for element in content_candidates[:10]:  # 最大10要素まで
                text = element.get_text().strip()
                if text and len(text) > 50:  # 短すぎるテキストを除外
                    content_text += text + " "
            
            # 文字数をカウント（日本語文字数）
            char_count = len(content_text.replace(" ", ""))
            
            # 画像数をカウント
            img_tags = soup.find_all('img')
            image_count = len([img for img in img_tags if img.get('src')])
            
            return {
                "title": title,
                "headings": headings[:20],  # 最大20個の見出し
                "content": content_text[:1000],  # 最大1000文字のプレビュー
                "char_count": char_count,
                "image_count": image_count
            }
            
        except requests.exceptions.Timeout:
            print(f"タイムアウト: {url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"リクエストエラー {url}: {e}")
            return None
        except Exception as e:
            print(f"スクレイピングエラー {url}: {e}")
            return None


# サービスのインスタンス
serpapi_service = SerpAPIService() 