import os # osモジュールをファイルの先頭に移動

# --- テスト実行時に必要な環境変数を一時的に設定 ---
# Settingsクラスが必要とするAPIキーをダミー値で設定する
# これにより、config.pyのSettings()インスタンス化時のValidationErrorを回避
# これらのキーはテスト自体では使用されない
print("テスト実行のため、一時的なダミーAPIキーを環境変数に設定します...")
os.environ['OPENAI_API_KEY'] = 'dummy_openai_key_for_testing'
os.environ['GEMINI_API_KEY'] = 'dummy_gemini_key_for_testing'
os.environ['SERPAPI_KEY'] = 'dummy_serpapi_key_for_testing'
print("ダミーAPIキーの設定完了。")
# --- 環境変数の設定ここまで ---

from typing import List, Dict, Any, Optional
from collections import Counter # Added for analyze_user_intent, _find_common_heading_patterns
import re # Added for analyze_user_intent, _find_common_heading_patterns
import numpy as np # ★ Added for statistical analysis
# ScrapedArticle を serpapi_service からインポートすることを想定
# 実際のプロジェクト構成によっては、共通の型定義ファイルなどに移動することも検討
from backend.services.serpapi_service import ScrapedArticle, SerpAnalysisResult # ScrapedArticleに加えてSerpAnalysisResultもインポート（テストデータ作成のため）

class ContentAnalyzer:
    """
    スクレイピングされた複数の記事データを分析し、SEO戦略に役立つ洞察を提供するクラス。
    """
    def __init__(self, scraped_articles: List[ScrapedArticle]):
        """
        ContentAnalyzerを初期化します。

        Args:
            scraped_articles: 分析対象のScrapedArticleオブジェクトのリスト。
        """
        self.analysis_results: Dict[str, Any] = {} # 先に初期化

        if not scraped_articles:
            print("ContentAnalyzer初期化: 渡された記事リストが空です。分析結果は空になります。")
            self.articles: List[ScrapedArticle] = []
            return

        print(f"ContentAnalyzer初期化: 元の記事数 {len(scraped_articles)}件。文字数0の記事をフィルタリングします...")
        
        original_count = len(scraped_articles)
        # char_count属性の存在も確認
        filtered_articles = [
            article for article in scraped_articles
            if hasattr(article, 'char_count') and isinstance(article.char_count, (int, float)) and article.char_count > 0
        ]
        
        filtered_out_count = original_count - len(filtered_articles)
        if filtered_out_count > 0:
            print(f"フィルタリング: {filtered_out_count}件の文字数0または文字数取得失敗の記事を除外しました。")

        if not filtered_articles:
            print("警告: ContentAnalyzer - フィルタリングの結果、分析対象となる有効な記事が0件です。")
            self.articles: List[ScrapedArticle] = []
        else:
            self.articles: List[ScrapedArticle] = filtered_articles
            print(f"ContentAnalyzer初期化完了: 分析対象の記事数 {len(self.articles)}件。")

    def _analyze_distribution(self, data: List[float], feature_name: str) -> Dict[str, Any]:
        """数値リストの分布を分析する内部メソッド"""
        if not data:
            return {
                f"{feature_name}_stats": {"message": "データが空のため分析できません。"}
            }

        stats = {
            "mean": float(np.mean(data)),
            "median": float(np.median(data)),
            "std_dev": float(np.std(data)),
            "variance": float(np.var(data)),
            "min": float(np.min(data)),
            "max": float(np.max(data)),
            "range": float(np.max(data) - np.min(data)),
            "q1": float(np.percentile(data, 25)),
            "q3": float(np.percentile(data, 75)),
            "iqr": float(np.percentile(data, 75) - np.percentile(data, 25)),
            "percentiles": {
                "10th": float(np.percentile(data, 10)),
                "90th": float(np.percentile(data, 90))
            },
            "outlier_thresholds": {
                "lower_bound": float(np.percentile(data, 25) - 1.5 * (np.percentile(data, 75) - np.percentile(data, 25))),
                "upper_bound": float(np.percentile(data, 75) + 1.5 * (np.percentile(data, 75) - np.percentile(data, 25)))
            },
            "count": len(data)
        }
        return stats

    def analyze_basic_statistics(self) -> Dict[str, Any]:
        """記事群の基本的な数値特徴に関する統計情報を分析する"""
        print("基本統計量の分析を開始します...")
        if not self.articles: # フィルタリング後なので、ここで空なら本当に分析対象がない
            print("ContentAnalyzer: 分析対象の記事がありません。基本統計分析をスキップします。")
            self.analysis_results["basic_statistics"] = {"message": "記事データが空です。"}
            return self.analysis_results["basic_statistics"]

        # 分析対象のデータを抽出
        char_counts = [article.char_count for article in self.articles if hasattr(article, 'char_count')]
        image_counts = [article.image_count for article in self.articles if hasattr(article, 'image_count')]
        
        # heading_counts の計算方法を修正: 記事内の全Hタグの総数をカウント
        heading_counts = []
        for article in self.articles:
            if hasattr(article, 'headings') and article.headings: # None や空リストでないことを確認
                flat_headings = self._extract_headings_flat(article.headings)
                heading_counts.append(len(flat_headings))
            else:
                heading_counts.append(0)
        
        # 各特徴量について分布分析
        char_count_dist_stats = self._analyze_distribution(char_counts, "char_count")
        image_count_dist_stats = self._analyze_distribution(image_counts, "image_count")
        heading_count_dist_stats = self._analyze_distribution(heading_counts, "heading_count")
        
        section_char_counts = []
        for article in self.articles:
            if hasattr(article, 'headings') and article.headings is not None:
                for heading_node in self._extract_headings_flat(article.headings):
                    if 'char_count_section' in heading_node and isinstance(heading_node['char_count_section'], (int, float)):
                        section_char_counts.append(heading_node['char_count_section'])
        
        section_char_dist_stats = self._analyze_distribution(section_char_counts, "section_char_count")
        
        result = {
            "article_count": len(self.articles),
            "char_count_analysis": {"stats": char_count_dist_stats},
            "image_count_analysis": {"stats": image_count_dist_stats},
            "heading_count_analysis": {"stats": heading_count_dist_stats},
            "section_char_count_analysis": {"stats": section_char_dist_stats}
        }
        
        self.analysis_results["basic_statistics"] = result
        print("基本統計量の分析が完了しました。")
        return result

    def _extract_headings_flat(self, headings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """見出し階層をフラットなリストに変換"""
        flat_headings = []
        
        def _flatten_recursive(heading_list):
            for heading in heading_list:
                if not isinstance(heading, dict): # スキップまたはログ記録
                    # print(f"Warning: Expected dict, got {type(heading)}. Skipping item: {heading}")
                    continue
                flat_headings.append({
                    'level': heading.get('level'),
                    'text': heading.get('text', ''),
                    'semantic_type': heading.get('semantic_type', 'body'),
                    'char_count_section': heading.get('char_count_section', 0)
                })
                if heading.get('children'):
                    _flatten_recursive(heading['children'])
        
        if headings: 
             _flatten_recursive(headings)
        return flat_headings

    def analyze_heading_structure(self) -> Dict[str, Any]:
        """記事群の見出し構造を分析する"""
        print("見出し構造の分析を開始します...")
        if not self.articles:
            print("分析対象の記事がありません。見出し構造分析をスキップします。")
            self.analysis_results["heading_structure"] = {"message": "記事データが空です。"}
            return self.analysis_results["heading_structure"]

        all_flat_headings = []
        level_usage_per_article_list = []
        max_depth_per_article_list = []
        heading_text_lengths_all = []
        heading_text_lengths_by_level = {f'h{i}': [] for i in range(1, 7)}

        for article in self.articles:
            if not hasattr(article, 'headings') or article.headings is None:
                level_usage_per_article_list.append({f'h{i}': 0 for i in range(1, 7)})
                max_depth_per_article_list.append(0)
                continue

            flat_headings = self._extract_headings_flat(article.headings)
            all_flat_headings.extend(flat_headings)
            
            current_article_level_usage = Counter()
            current_max_depth = 0
            for heading in flat_headings:
                level = heading.get('level')
                if level and isinstance(level, int) and 1 <= level <= 6:
                    current_article_level_usage[f'h{level}'] += 1
                    if level > current_max_depth:
                        current_max_depth = level
                    
                    text = heading.get('text', '')
                    if isinstance(text, str):
                        heading_text_lengths_all.append(len(text))
                        heading_text_lengths_by_level[f'h{level}'].append(len(text))
            
            level_usage_per_article_list.append(dict(current_article_level_usage))
            max_depth_per_article_list.append(current_max_depth)

        total_level_distribution = Counter()
        for usage in level_usage_per_article_list:
            total_level_distribution.update(usage)
        
        avg_level_usage = {level: total_level_distribution.get(level, 0) / len(self.articles) 
                           for level in [f'h{i}' for i in range(1,7)]}
        
        total_headings_count = sum(total_level_distribution.values())
        percentage_level_usage = {level: total_level_distribution.get(level, 0) / total_headings_count if total_headings_count else 0
                                  for level in [f'h{i}' for i in range(1,7)]}
        
        # テキスト長の統計
        text_length_stats_all = self._analyze_distribution(heading_text_lengths_all, "all_headings_text_length")
        text_length_stats_by_level = {}
        for level_key, lengths in heading_text_lengths_by_level.items():
            if lengths: # データがある場合のみ分析
                 text_length_stats_by_level[level_key] = self._analyze_distribution(lengths, f"{level_key}_text_length")
            else:
                 text_length_stats_by_level[level_key] = {"message": f"{level_key}のテキストデータがありません。"}                             

        result = {
            "level_usage_per_article": level_usage_per_article_list,
            "total_level_distribution": dict(total_level_distribution),
            "average_level_usage": avg_level_usage,
            "percentage_level_usage": percentage_level_usage,
            "max_depth_per_article": max_depth_per_article_list,
            "average_max_depth": np.mean(max_depth_per_article_list) if max_depth_per_article_list else 0,
            "most_common_max_depth": Counter(max_depth_per_article_list).most_common(1)[0][0] if max_depth_per_article_list else 0,
            "depth_variance": np.var(max_depth_per_article_list) if max_depth_per_article_list else 0,
            "heading_text_length_analysis": {
                "overall": text_length_stats_all,
                "by_level": text_length_stats_by_level
            }
        }

        self.analysis_results["heading_structure"] = result
        print("見出し構造の分析が完了しました。")
        return result

    def analyze_content_patterns(self) -> Dict[str, Any]:
        """
        複数の競合記事から共通のコンテンツパターンを分析します。
        例えば、頻出する見出しのトピック、構造の共通性などを抽出します。

        Returns:
            分析されたコンテンツパターンの情報を含む辞書。
        """
        print(f"コンテンツパターンの分析を開始します。対象記事数: {len(self.articles)}")
        
        # TODO: ここに統計ベースのパターン分析を実装していく
        # 例: 共通見出しキーワードの頻度、意味的分類の出現パターンなど

        # 現状は基本統計と見出し構造の呼び出しに依存する形にするか、
        # または、このメソッド独自の分析項目を定義する。
        # ここでは一旦、analyze_heading_structureの結果の一部を参照するダミー実装とする。
        if "heading_structure" not in self.analysis_results:
            self.analyze_heading_structure() # 事前に実行しておく

        patterns_result = {
            "message": "コンテンツパターン分析は部分的に実装中です。",
            "analyzed_article_count": len(self.articles),
            "common_heading_levels_summary": self.analysis_results.get("heading_structure", {}).get("total_level_distribution")
        }
        
        self.analysis_results["content_patterns"] = patterns_result
        print("コンテンツパターンの分析が完了しました（部分実装）。")
        return patterns_result

    def extract_content_gaps(
        self, 
        target_article_headings: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        競合記事と比較して、ターゲット記事（指定された場合）に不足している
        可能性のあるコンテンツギャップを抽出します。

        Args:
            target_article_headings: オプション。
                比較対象となるターゲット記事の見出し構造リスト。
                ScrapedArticle.headings と同じ形式を期待。
                指定されない場合は、競合間の一般的なギャップや機会を探るモードも考えられる。

        Returns:
            コンテンツギャップに関する情報を含む辞書。
        """
        print("コンテンツギャップの抽出を開始します。")
        if target_article_headings:
            print(f"ターゲット記事の見出し数: {len(target_article_headings)}")
        else:
            print("ターゲット記事は指定されていません。")

        gaps_result = {
            "message": "extract_content_gaps はまだ実装されていません。",
            "missing_topics": [],
            "underdeveloped_sections": []
        }
        self.analysis_results["content_gaps"] = gaps_result
        print("コンテンツギャップの抽出が完了しました（ダミー）。")
        return gaps_result

    def identify_competitive_advantages(
        self,
        target_article_headings: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        競合記事と比較して、ターゲット記事（指定された場合）が持つ可能性のある
        競争上の優位性や、深掘りすべきユニークな点を特定します。

        Args:
            target_article_headings: オプション。
                比較対象となるターゲット記事の見出し構造リスト。

        Returns:
            競争上の優位性に関する情報を含む辞書。
        """
        print("競争上の優位性の特定を開始します。")
        if target_article_headings:
            print(f"ターゲット記事の見出し数: {len(target_article_headings)}")
        else:
            print("ターゲット記事は指定されていません。")
        
        advantages_result = {
            "message": "identify_competitive_advantages はまだ実装されていません。",
            "unique_topics_covered": [],
            "stronger_sections": []
        }
        self.analysis_results["competitive_advantages"] = advantages_result
        print("競争上の優位性の特定が完了しました（ダミー）。")
        return advantages_result

    def get_full_analysis(self, target_article_headings: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        全ての分析を実行し、統合された結果を返します。
        """
        print("完全なコンテンツ分析を開始します...")
        self.analyze_basic_statistics() 
        self.analyze_heading_structure() # ★ 見出し構造分析を呼び出し
        self.analyze_content_patterns()
        self.extract_content_gaps(target_article_headings)
        self.identify_competitive_advantages(target_article_headings)
        print("完全なコンテンツ分析が完了しました。")
        return self.analysis_results

# --- ここから下は、テストや動作確認のための簡易的なコード ---

def create_dummy_scraped_articles() -> List[ScrapedArticle]:
    """テスト用のScrapedArticleオブジェクトのリストを作成する"""
    articles = [
        ScrapedArticle(
            url="http://example.com/article1", title="記事1", char_count=1500, image_count=3, source_type="organic",
            content="記事1の本文です。", # contentフィールド追加
            headings=[
                {"level": 1, "text": "H1-1", "char_count_section": 300, "semantic_type": "introduction", "children": [
                    {"level": 2, "text": "H2-1-1", "char_count_section": 200, "semantic_type": "body", "children": []},
                    {"level": 2, "text": "H2-1-2", "char_count_section": 400, "semantic_type": "body", "children": [
                        {"level": 3, "text": "H3-1-2-1", "char_count_section": 150, "semantic_type": "body", "children": []}
                    ]},
                ]},
                {"level": 1, "text": "H1-2", "char_count_section": 500, "semantic_type": "conclusion", "children": []}
            ]
        ),
        ScrapedArticle(
            url="http://example.com/article2", title="記事2", char_count=2500, image_count=5, source_type="organic",
            content="記事2の本文です。", # contentフィールド追加
            headings=[
                {"level": 1, "text": "H1 A", "char_count_section": 1000, "semantic_type": "introduction", "children": []},
                {"level": 2, "text": "H2 B", "char_count_section": 800, "semantic_type": "body", "children": []},
                {"level": 2, "text": "H2 C", "char_count_section": 700, "semantic_type": "body", "children": []}
            ]
        ),
        ScrapedArticle(
            url="http://example.com/article3", title="記事3", char_count=800, image_count=1, source_type="related_question",
            content="記事3の本文です。見出しはありません。", # contentフィールド追加
            headings=None # 見出しがないケース
        ),
        ScrapedArticle(
            url="http://example.com/article4", title="記事4", char_count=3200, image_count=8, source_type="organic",
            content="記事4の本文。", # contentフィールド追加
            headings=[
                {"level": 2, "text": "主要セクションX", "char_count_section": 1200, "semantic_type": "body", "children": []},
                {"level": 2, "text": "主要セクションY", "char_count_section": 1500, "semantic_type": "body", "children": []},
                {"level": 3, "text": "サブセクションZ", "char_count_section": 500, "semantic_type": "body", "children": []} # H2なしでH3が登場するケース
            ]
        ),
        ScrapedArticle(
            url="http://example.com/article5_empty_headings", title="記事5", char_count=500, image_count=0, source_type="organic",
            content="記事5の本文。空の見出しリスト。", # contentフィールド追加
            headings=[] # 見出しリストは空
        )
    ]
    return articles

def create_actual_serp_like_articles() -> List[ScrapedArticle]:
    """ユーザー提供のserpapi_service.py出力に似せたScrapedArticleオブジェクトのリストを作成する"""
    articles = [
        ScrapedArticle(
            url="https://last-data.co.jp/media/scraping-exposed/#:~:text=%E4%B8%80%E8%88%AC%E7%9A%84%E3%81%AB%E3%80%81%E4%BA%BA%E9%96%93%E3%81%8C,%E3%81%99%E3%82%8B1%E3%81%A4%E3%81%AE%E6%96%B9%E6%B3%95%E3%81%A7%E3%81%99%E3%80%82",
            title="スクレイピングはバレる？法的リスクに注意！安全に行うための対策を徹底解説 - 活学（IKIGAKU）キャリアBlog",
        headings=[
                {"level": 2, "text": "スクレイピングとは？", "semantic_type": "introduction", "char_count_section": 547, "children": [
                    {"level": 3, "text": "スクレイピングの定義と種類", "semantic_type": "body", "char_count_section": 132, "children": []},
                    {"level": 3, "text": "スクレイピングとクローリングの違い", "semantic_type": "body", "char_count_section": 154, "children": []},
                    {"level": 3, "text": "スクレイピングの一般的な使用", "semantic_type": "body", "char_count_section": 109, "children": []}
                ]},
                {"level": 2, "text": "スクレイピングをするメリット", "semantic_type": "body", "char_count_section": 430, "children": [
                    {"level": 3, "text": "データ収集を効率化できる", "semantic_type": "body", "char_count_section": 142, "children": []},
                    {"level": 3, "text": "大量の情報から価値ある洞察を抽出できる", "semantic_type": "body", "char_count_section": 99, "children": []},
                    {"level": 3, "text": "ビジネスや研究で広範に利用できる", "semantic_type": "body", "char_count_section": 118, "children": []}
                ]},
                {"level": 2, "text": "スクレイピングをするデメリット", "semantic_type": "body", "char_count_section": 579, "children": [
                    {"level": 3, "text": "法的リスクを伴う可能性がある", "semantic_type": "body", "char_count_section": 177, "children": []},
                    {"level": 3, "text": "技術的な困難やサーバーへの負荷がある", "semantic_type": "body", "char_count_section": 181, "children": []},
                    {"level": 3, "text": "スクレイピングがバレるリスクがある", "semantic_type": "body", "char_count_section": 138, "children": []}
                ]},
                {"level": 2, "text": "スクレイピングがバレる主な原因とその対策", "semantic_type": "body", "char_count_section": 925, "children": [
                    {"level": 3, "text": "バレる主な要因", "semantic_type": "body", "char_count_section": 216, "children": []},
                    {"level": 3, "text": "バレるとどうなるか", "semantic_type": "body", "char_count_section": 122, "children": []},
                    {"level": 3, "text": "バレないための具体的な対策", "semantic_type": "body", "char_count_section": 247, "children": []},
                    {"level": 3, "text": "今後のスクレイピングの動向と予想", "semantic_type": "body", "char_count_section": 258, "children": []}
                ]},
                {"level": 2, "text": "スクレイピングがバレた時の法的リスクと対処法", "semantic_type": "body", "char_count_section": 603, "children": [
                    {"level": 3, "text": "バレた場合の法的リスク", "semantic_type": "body", "char_count_section": 205, "children": []},
                    {"level": 3, "text": "問題となった事例の紹介", "semantic_type": "body", "char_count_section": 185, "children": []},
                    {"level": 3, "text": "バレた場合の対処法", "semantic_type": "body", "char_count_section": 143, "children": []}
                ]},
                {"level": 2, "text": "ばれにくいスクレイピングの方法", "semantic_type": "body", "char_count_section": 707, "children": [
                    {"level": 3, "text": "適切なアクセス間隔と時間", "semantic_type": "body", "char_count_section": 189, "children": []},
                    {"level": 3, "text": "IPアドレスのローテーション", "semantic_type": "body", "char_count_section": 185, "children": []},
                    {"level": 3, "text": "スクレイピングのツールとテクニック", "semantic_type": "body", "char_count_section": 161, "children": []}
                ]},
                {"level": 2, "text": "スクレイピングの適切な使用方法とエチケット", "semantic_type": "body", "char_count_section": 592, "children": [
                    {"level": 3, "text": "合法的な使用範囲", "semantic_type": "body", "char_count_section": 170, "children": []},
                    {"level": 3, "text": "スクレイピングの際のマナー", "semantic_type": "body", "char_count_section": 136, "children": []},
                    {"level": 3, "text": "スクレイピングによるサーバ負荷とその対策", "semantic_type": "body", "char_count_section": 205, "children": []}
                ]},
                {"level": 2, "text": "まとめ", "semantic_type": "conclusion", "char_count_section": 207, "children": []}
            ],
            content="スクレイピングは、 ウェブ上の情報を自動的に収集する技術 で、データ分析や市場調査など、さまざまな場面で活用されています。 スクレイピングは法的に問題ないの？ スクレイピングがバレたらどうなるの？ といった疑問や不安を抱えている方も多いのではないでしょうか。 この記事では、 そんなスクレイピングの基本的な知識から、法的リスクや対策、スクレイピングのメリットとデメリットまで幅広く解説 します。 初め...",
            char_count=9936,
            image_count=15,
            source_type="related_question",
            question="スクレイピングがバレる原因は何ですか？"
        ),
        ScrapedArticle(
            url="https://fastapi.tiangolo.com/ja/tutorial/response-status-code/#:~:text=200%20%E3%81%AF%E3%83%87%E3%83%95%E3%82%A9%E3%83%AB%E3%83%88%E3%81%AE%E3%82%B9%E3%83%86%E3%83%BC%E3%82%BF%E3%82%B9,%E3%81%93%E3%81%A8%E3%82%92%E6%84%8F%E5%91%B3%E3%81%97%E3%81%BE%E3%81%99%E3%80%82",
            title="レスポンスステータスコード - FastAPI",
            headings=[
                {"level": 1, "text": "レスポンスステータスコード¶", "semantic_type": "introduction", "char_count_section": 1653, "children": [
                    {"level": 2, "text": "HTTPステータスコードについて¶", "semantic_type": "body", "char_count_section": 719, "children": []},
                    {"level": 2, "text": "名前を覚えるための近道¶", "semantic_type": "body", "char_count_section": 457, "children": []},
                    {"level": 2, "text": "デフォルトの変更¶", "semantic_type": "body", "char_count_section": 55, "children": []}
                ]}
            ],
            content="レスポンスモデルを指定するのと同じ方法で、レスポンスに使用されるHTTPステータスコードを以下の path operations のいずれかの status_code パラメータで宣言することもできます。 Python 3.8+ from fastapi import FastAPI app = FastAPI () @app . post ( \"/items/\" , status_code =...",
            char_count=2112,
            image_count=2,
            source_type="related_question",
            question="FastAPIの200はOKですか？"
        ),
        ScrapedArticle(
            url="https://qiita.com/KWS_0901/items/da7237e26a83b1c8fc80",
            title="[Python]FastAPIを用いたWebスクレイピングAPI 作成方法 メモ #BeautifulSoup - Qiita",
            headings=[
                {"level": 1, "text": "[Python]FastAPIを用いたWebスクレイピングAPI 作成方法 メモ", "semantic_type": "introduction", "char_count_section": 51, "children": [
                    {"level": 2, "text": "構成", "semantic_type": "body", "char_count_section": 43, "children": []},
                    {"level": 2, "text": "コード", "semantic_type": "body", "char_count_section": 719, "children": []},
                    {"level": 2, "text": "動作確認", "semantic_type": "body", "char_count_section": 331, "children": []},
                    {"level": 2, "text": "参考情報", "semantic_type": "references", "char_count_section": 81, "children": []}
                ]}
            ],
            content="More than 3 years have passed since last update. @ KWS_0901 [Python]FastAPIを用いたWebスクレイピングAPI 作成方法 メモ Python スクレイピング BeautifulSoup FastAPI Posted at 2021-07-22 [Python]FastAPIを用いたWebスクレイピングAPI 作成方法 メ...",
            char_count=2205,
        image_count=3,
        source_type="organic_result",
        position=1
    )
    ]
    return articles

async def run_analyzer_tests():
    """ContentAnalyzerの主要メソッドをテストする"""
    print("--- ContentAnalyzer ユニットテスト開始 ---")

    # 1. データが空の場合のテスト
    print("\n--- ケース1: データが空 --- ")
    empty_analyzer = ContentAnalyzer([])
    empty_basic_stats = empty_analyzer.analyze_basic_statistics()
    assert empty_basic_stats["message"] == "記事データが空です。"
    print("空データ時の basic_statistics: OK")
    empty_heading_stats = empty_analyzer.analyze_heading_structure()
    assert empty_heading_stats["message"] == "記事データが空です。"
    print("空データ時の heading_structure: OK")

    # 2. ダミーデータを使ったテスト
    print("\n--- ケース2: ダミーデータ使用 --- ")
    dummy_articles = create_dummy_scraped_articles()
    analyzer = ContentAnalyzer(dummy_articles)

    # analyze_basic_statistics のテスト
    print("\n--- テスト: analyze_basic_statistics --- ")
    basic_stats_result = analyzer.analyze_basic_statistics()
    print("analyze_basic_statistics 結果 (一部):")
    assert basic_stats_result["article_count"] == 5
    print(f"  記事数: {basic_stats_result['article_count']}")
    print(f"  平均文字数: {basic_stats_result['char_count_analysis']['stats']['mean']:.2f}")
    print(f"  画像数中央値: {basic_stats_result['image_count_analysis']['stats']['median']}")
    print(f"  見出し数分析の対象記事数（0個も含む）: {basic_stats_result['heading_count_analysis']['stats']['count']}")
    print(f"  平均セクション文字数: {basic_stats_result['section_char_count_analysis']['stats']['mean']:.2f}")
    # ここにさらに詳細なアサーションを追加可能

    # analyze_heading_structure のテスト
    print("\n--- テスト: analyze_heading_structure --- ")
    heading_structure_result = analyzer.analyze_heading_structure()
    print("analyze_heading_structure 結果 (一部):")
    assert len(heading_structure_result["level_usage_per_article"]) == 5
    print(f"  レベル別使用回数 (記事1): {heading_structure_result['level_usage_per_article'][0]}")
    print(f"  レベル別使用回数 (記事3 - 見出しNone): {heading_structure_result['level_usage_per_article'][2]}") # h1-h6全て0のはず
    assert heading_structure_result['level_usage_per_article'][2] == {'h1': 0, 'h2': 0, 'h3': 0, 'h4': 0, 'h5': 0, 'h6': 0}
    print(f"  合計H1数: {heading_structure_result['total_level_distribution'].get('h1', 0)}")
    print(f"  平均最大深さ: {heading_structure_result['average_max_depth']:.2f}") 
    print(f"  H2見出しの平均文字数: {heading_structure_result['heading_text_length_analysis']['by_level'].get('h2',{}).get('stats',{}).get('mean', 'N/A')}")
    # ここにさらに詳細なアサーションを追加可能

    # get_full_analysis の簡単なテスト（各メソッドが呼び出されることの確認程度）
    print("\n--- テスト: get_full_analysis --- ")
    full_result = analyzer.get_full_analysis()
    assert "basic_statistics" in full_result
    assert "heading_structure" in full_result
    assert "content_patterns" in full_result # ダミーでもキーが存在することを確認
    print("get_full_analysis 実行完了。主要キーの存在確認: OK")
    
    print("\n--- ContentAnalyzer ユニットテスト終了 ---")
    print("\n詳細な分析結果は analyzer.analysis_results を確認してください:")
    # print(json.dumps(analyzer.analysis_results, indent=2, ensure_ascii=False)) # 必要に応じて出力

async def example_usage_with_serpapi_like_data():
    """ユーザー提供の実際のSerpAPI出力風データを使用した分析例"""
    import json 
    
    print("\n\n=== SerpAPI実データ風 テスト開始 ===")
    
    actual_articles = create_actual_serp_like_articles()
    if not actual_articles:
        print("実データ風記事が取得できませんでした。分析を終了します。")
        return

    analyzer = ContentAnalyzer(actual_articles)
    full_analysis = analyzer.get_full_analysis()
    
    print("\n--- 実データ風分析結果サマリー (JSON) ---")
    print(json.dumps(full_analysis, indent=2, ensure_ascii=False))
    print("\n=== SerpAPI実データ風 テスト終了 ===")

if __name__ == '__main__':
    import asyncio
    import json 
    
    # ContentAnalyzer のユニットテストを実行
    asyncio.run(run_analyzer_tests())
    
    # SerpAPI実データ風のテストを実行
    asyncio.run(example_usage_with_serpapi_like_data())
