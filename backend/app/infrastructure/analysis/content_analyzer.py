import os # osモジュールをファイルの先頭に移動

from typing import List, Dict, Any, Optional
from collections import Counter # Added for analyze_user_intent, _find_common_heading_patterns
import re # Added for analyze_user_intent, _find_common_heading_patterns
import numpy as np # ★ Added for statistical analysis
import json # ★ Added for JSON export
import datetime # ★ Added for timestamp in exports
# ScrapedArticle を serpapi_service からインポートすることを想定
# 実際のプロジェクト構成によっては、共通の型定義ファイルなどに移動することも検討
from app.infrastructure.external_apis.serpapi_service import ScrapedArticle, SerpAnalysisResult # ScrapedArticleに加えてSerpAnalysisResultもインポート（テストデータ作成のため）
import asyncio
from app.infrastructure.gcp_auth import setup_genai_client

class ContentAnalyzer:
    """
    スクレイピングされた複数の記事データを分析し、SEO戦略に役立つ洞察を提供するクラス。
    """
    
    @classmethod
    def quick_analyze(cls, scraped_articles: List[ScrapedArticle], output_file: str = None, language: str = "jp") -> Dict[str, Any]:
        """
        ワンライナーで分析を実行し、結果を返す簡易メソッド
        
        Args:
            scraped_articles: 分析対象の記事リスト
            output_file: オプション。JSONファイル出力先
            language: "jp" (日本語) または "en" (英語) または "both" (両方)
            
        Returns:
            分析結果の辞書
        """
        analyzer = cls(scraped_articles)
        results = analyzer.get_full_analysis()
        
        if output_file:
            analyzer.export_to_json(output_file, language)
            
        return results
    
    @classmethod 
    async def quick_analyze_with_ai(cls, scraped_articles: List[ScrapedArticle], output_file: str = None, language: str = "jp") -> Dict[str, Any]:
        """
        Gemini AIを使った高度分析をワンライナーで実行
        
        Args:
            scraped_articles: 分析対象の記事リスト
            output_file: オプション。JSONファイル出力先
            language: "jp" (日本語) または "en" (英語) または "both" (両方)
            
        Returns:
            AI分析結果の辞書
        """
        analyzer = cls(scraped_articles)
        results = await analyzer.get_full_analysis_with_gemini()
        
        if output_file:
            analyzer.export_to_json(output_file, language)
            
        return results

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
            "平均値": float(np.mean(data)),
            "mean": float(np.mean(data)),
            "中央値": float(np.median(data)),
            "median": float(np.median(data)),
            "標準偏差": float(np.std(data)),
            "std_dev": float(np.std(data)),
            "分散": float(np.var(data)),
            "variance": float(np.var(data)),
            "最小値": float(np.min(data)),
            "min": float(np.min(data)),
            "最大値": float(np.max(data)),
            "max": float(np.max(data)),
            "範囲（最大値-最小値）": float(np.max(data) - np.min(data)),
            "range": float(np.max(data) - np.min(data)),
            "第1四分位数（25パーセンタイル）": float(np.percentile(data, 25)),
            "q1": float(np.percentile(data, 25)),
            "第3四分位数（75パーセンタイル）": float(np.percentile(data, 75)),
            "q3": float(np.percentile(data, 75)),
            "四分位範囲": float(np.percentile(data, 75) - np.percentile(data, 25)),
            "iqr": float(np.percentile(data, 75) - np.percentile(data, 25)),
            "パーセンタイル値": {
                "10パーセンタイル": float(np.percentile(data, 10)),
                "10th": float(np.percentile(data, 10)),
                "90パーセンタイル": float(np.percentile(data, 90)),
                "90th": float(np.percentile(data, 90))
            },
            "percentiles": {
                "10th": float(np.percentile(data, 10)),
                "90th": float(np.percentile(data, 90))
            },
            "外れ値判定基準": {
                "外れ値の下限": float(np.percentile(data, 25) - 1.5 * (np.percentile(data, 75) - np.percentile(data, 25))),
                "lower_bound": float(np.percentile(data, 25) - 1.5 * (np.percentile(data, 75) - np.percentile(data, 25))),
                "外れ値の上限": float(np.percentile(data, 75) + 1.5 * (np.percentile(data, 75) - np.percentile(data, 25))),
                "upper_bound": float(np.percentile(data, 75) + 1.5 * (np.percentile(data, 75) - np.percentile(data, 25)))
            },
            "outlier_thresholds": {
                "lower_bound": float(np.percentile(data, 25) - 1.5 * (np.percentile(data, 75) - np.percentile(data, 25))),
                "upper_bound": float(np.percentile(data, 75) + 1.5 * (np.percentile(data, 75) - np.percentile(data, 25)))
            },
            "データ数": len(data),
            "count": len(data),
            "統計サマリー": f"データ数{len(data)}件の統計: 平均{float(np.mean(data)):.1f}, 中央値{float(np.median(data)):.1f}, 最小値{float(np.min(data)):.1f}, 最大値{float(np.max(data)):.1f}",
            "summary_jp": f"データ数{len(data)}件の統計: 平均{float(np.mean(data)):.1f}, 中央値{float(np.median(data)):.1f}, 最小値{float(np.min(data)):.1f}, 最大値{float(np.max(data)):.1f}"
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
        
        # ★ 新しいコンテンツフォーマット関連の統計
        video_counts = [getattr(article, 'video_count', 0) for article in self.articles]
        table_counts = [getattr(article, 'table_count', 0) for article in self.articles]
        list_item_counts = [getattr(article, 'list_item_count', 0) for article in self.articles]
        external_link_counts = [getattr(article, 'external_link_count', 0) for article in self.articles]
        internal_link_counts = [getattr(article, 'internal_link_count', 0) for article in self.articles]
        
        # 各特徴量について分布分析
        char_count_dist_stats = self._analyze_distribution(char_counts, "char_count")
        image_count_dist_stats = self._analyze_distribution(image_counts, "image_count")
        heading_count_dist_stats = self._analyze_distribution(heading_counts, "heading_count")
        
        # ★ 新しいフォーマット分析
        video_count_dist_stats = self._analyze_distribution(video_counts, "video_count")
        table_count_dist_stats = self._analyze_distribution(table_counts, "table_count")
        list_item_count_dist_stats = self._analyze_distribution(list_item_counts, "list_item_count")
        external_link_count_dist_stats = self._analyze_distribution(external_link_counts, "external_link_count")
        internal_link_count_dist_stats = self._analyze_distribution(internal_link_counts, "internal_link_count")
        
        section_char_counts = []
        for article in self.articles:
            if hasattr(article, 'headings') and article.headings is not None:
                for heading_node in self._extract_headings_flat(article.headings):
                    if 'char_count_section' in heading_node and isinstance(heading_node['char_count_section'], (int, float)):
                        section_char_counts.append(heading_node['char_count_section'])
        
        section_char_dist_stats = self._analyze_distribution(section_char_counts, "section_char_count")
        
        result = {
            "分析対象記事数": len(self.articles),
            "article_count": len(self.articles),
            "文字数分析": {
                "説明": "記事全体の文字数分析",
                "description_jp": "記事全体の文字数分析",
                "統計値": char_count_dist_stats,
                "stats": char_count_dist_stats
            },
            "char_count_analysis": {
                "stats": char_count_dist_stats,
                "description_jp": "記事全体の文字数分析"
            },
            "画像数分析": {
                "説明": "記事内の画像数分析",
                "description_jp": "記事内の画像数分析", 
                "統計値": image_count_dist_stats,
                "stats": image_count_dist_stats
            },
            "image_count_analysis": {
                "stats": image_count_dist_stats,
                "description_jp": "記事内の画像数分析"
            },
            "見出し数分析": {
                "説明": "記事内の見出し総数分析",
                "description_jp": "記事内の見出し総数分析",
                "統計値": heading_count_dist_stats,
                "stats": heading_count_dist_stats
            },
            "heading_count_analysis": {
                "stats": heading_count_dist_stats,
                "description_jp": "記事内の見出し総数分析"
            },
            # ★ 新しいコンテンツフォーマット分析結果を追加
            "動画数分析": {
                "説明": "記事内の動画・iframe埋め込み数分析",
                "description_jp": "記事内の動画・iframe埋め込み数分析",
                "統計値": video_count_dist_stats,
                "stats": video_count_dist_stats
            },
            "video_count_analysis": {
                "stats": video_count_dist_stats,
                "description_jp": "記事内の動画・iframe埋め込み数分析"
            },
            "テーブル数分析": {
                "説明": "記事内のテーブル数分析（強調スニペット対策指標）",
                "description_jp": "記事内のテーブル数分析（強調スニペット対策指標）",
                "統計値": table_count_dist_stats,
                "stats": table_count_dist_stats
            },
            "table_count_analysis": {
                "stats": table_count_dist_stats,
                "description_jp": "記事内のテーブル数分析（強調スニペット対策指標）"
            },
            "リスト項目数分析": {
                "説明": "記事内のリスト項目総数分析（網羅性指標）",
                "description_jp": "記事内のリスト項目総数分析（網羅性指標）",
                "統計値": list_item_count_dist_stats,
                "stats": list_item_count_dist_stats
            },
            "list_item_count_analysis": {
                "stats": list_item_count_dist_stats,
                "description_jp": "記事内のリスト項目総数分析（網羅性指標）"
            },
            "外部リンク数分析": {
                "説明": "記事内の外部リンク数分析（信頼性・権威性指標）",
                "description_jp": "記事内の外部リンク数分析（信頼性・権威性指標）",
                "統計値": external_link_count_dist_stats,
                "stats": external_link_count_dist_stats
            },
            "external_link_count_analysis": {
                "stats": external_link_count_dist_stats,
                "description_jp": "記事内の外部リンク数分析（信頼性・権威性指標）"
            },
            "内部リンク数分析": {
                "説明": "記事内の内部リンク数分析（サイト回遊性指標）",
                "description_jp": "記事内の内部リンク数分析（サイト回遊性指標）",
                "統計値": internal_link_count_dist_stats,
                "stats": internal_link_count_dist_stats
            },
            "internal_link_count_analysis": {
                "stats": internal_link_count_dist_stats,
                "description_jp": "記事内の内部リンク数分析（サイト回遊性指標）"
            },
            "セクション文字数分析": {
                "説明": "各見出しセクションの文字数分析",
                "description_jp": "各見出しセクションの文字数分析",
                "統計値": section_char_dist_stats,
                "stats": section_char_dist_stats
            },
            "section_char_count_analysis": {
                "stats": section_char_dist_stats,
                "description_jp": "各見出しセクションの文字数分析"
            },
            "分析サマリー": f"拡張分析完了: {len(self.articles)}記事を対象に、文字数・画像数・見出し構造・動画・テーブル・リスト・リンク構造の統計分析を実施しました。",
            "summary_jp": f"拡張分析完了: {len(self.articles)}記事を対象に、文字数・画像数・見出し構造・動画・テーブル・リスト・リンク構造の統計分析を実施しました。"
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

    async def _analyze_frequent_headings(self) -> Dict[str, Any]:
        """競合記事間での頻出見出しパターンを分析する（Gemini AI enhanced版）"""
        print("頻出見出しパターンの分析を開始します（Gemini AI enhanced）...")
        
        if not self.articles:
            return {
                "エラー": "分析対象の記事がありません。",
                "error": "No articles available for analysis."
            }

        # すべての見出しを収集
        all_headings_with_context = []
        for i, article in enumerate(self.articles):
            if not hasattr(article, 'headings') or not article.headings:
                continue
            
            flat_headings = self._extract_headings_flat(article.headings)
            for heading in flat_headings:
                all_headings_with_context.append({
                    'text': heading.get('text', ''),
                    'level': heading.get('level'),
                    'semantic_type': heading.get('semantic_type', 'body'),
                    'article_index': i,
                    'article_url': getattr(article, 'url', f'記事{i+1}'),
                    'char_count_section': heading.get('char_count_section', 0)
                })

        # 1. 完全一致の頻出見出し分析
        exact_matches = Counter()
        for heading in all_headings_with_context:
            text = heading['text'].strip()
            if text and len(text) > 0:
                exact_matches[text] += 1

        frequent_exact = [(text, count) for text, count in exact_matches.items() if count >= 2]
        frequent_exact.sort(key=lambda x: x[1], reverse=True)

        # 2. レベル別頻出見出し分析
        level_based_analysis = {}
        for level in range(1, 7):
            level_headings = [h['text'].strip() for h in all_headings_with_context 
                             if h['level'] == level and h['text'].strip()]
            if level_headings:
                level_counter = Counter(level_headings)
                frequent_in_level = [(text, count) for text, count in level_counter.items() if count >= 2]
                frequent_in_level.sort(key=lambda x: x[1], reverse=True)
                level_based_analysis[f'h{level}'] = {
                    '総数': len(level_headings),
                    '頻出見出し': frequent_in_level[:10],  # 上位10個
                    '一意見出し数': len(set(level_headings))
                }

        # 3. 意味分類別頻出見出し分析
        semantic_based_analysis = {}
        for semantic_type in ['introduction', 'body', 'conclusion', 'faq', 'references']:
            semantic_headings = [h['text'].strip() for h in all_headings_with_context 
                               if h['semantic_type'] == semantic_type and h['text'].strip()]
            if semantic_headings:
                semantic_counter = Counter(semantic_headings)
                frequent_in_semantic = [(text, count) for text, count in semantic_counter.items() if count >= 2]
                frequent_in_semantic.sort(key=lambda x: x[1], reverse=True)
                semantic_based_analysis[semantic_type] = {
                    '総数': len(semantic_headings),
                    '頻出見出し': frequent_in_semantic[:10],
                    '一意見出し数': len(set(semantic_headings))
                }

        # 4. ★ Gemini APIを使った高度な頻出単語・類似見出し分析
        print("   🤖 Gemini APIで頻出単語・類似見出しを分析中...")
        gemini_analysis = await self._analyze_headings_with_gemini(all_headings_with_context)

        result = {
            "全見出し統計": {
                "総見出し数": len(all_headings_with_context),
                "一意見出し数": len(set(h['text'].strip() for h in all_headings_with_context if h['text'].strip())),
                "重複見出し数": len(all_headings_with_context) - len(set(h['text'].strip() for h in all_headings_with_context if h['text'].strip()))
            },
            "完全一致頻出見出し": {
                "説明": "複数記事で全く同じテキストが使われている見出し",
                "トップ20": frequent_exact[:20],
                "頻出見出し総数": len(frequent_exact)
            },
            "レベル別頻出分析": level_based_analysis,
            "意味分類別頻出分析": semantic_based_analysis,
            "Gemini_AI分析結果": gemini_analysis
        }

        print(f"✅ 頻出見出し分析完了: {len(all_headings_with_context)}個の見出しを分析")
        print(f"   📊 完全一致頻出見出し: {len(frequent_exact)}種類")
        if "エラー" not in gemini_analysis:
            print(f"   🤖 Gemini AI分析: 成功")
        else:
            print(f"   ❌ Gemini AI分析: {gemini_analysis.get('エラー', 'エラー発生')}")
        
        return result

    async def _analyze_headings_with_gemini(self, headings_with_context: List[Dict]) -> Dict[str, Any]:
        """Gemini APIを使用した頻出単語・類似見出しの高精度分析"""
        
        try:
            from app.core.config import settings
            import google.generativeai as genai
            
            if not settings.gemini_api_key:
                return {
                    "エラー": "Gemini APIキーが設定されていません。",
                    "error": "Gemini API key not configured."
                }
            
            setup_genai_client()
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            
            # 見出しリストの準備
            headings_list = [h['text'].strip() for h in headings_with_context if h['text'].strip()]
            
            # 記事別見出し情報の準備
            articles_headings = {}
            for h in headings_with_context:
                article_index = h['article_index']
                if article_index not in articles_headings:
                    articles_headings[article_index] = {
                        'url': h['article_url'],
                        'headings': []
                    }
                articles_headings[article_index]['headings'].append({
                    'text': h['text'],
                    'level': h['level'],
                    'semantic_type': h['semantic_type']
                })

            # Gemini APIへのプロンプト作成
            prompt = f"""
あなたは、SEOコンテンツ分析の専門家です。以下の競合記事の見出しデータを分析して、頻出単語パターンと類似見出しグループを特定してください。

【分析対象データ】
全見出しリスト: {json.dumps(headings_list, ensure_ascii=False, indent=2)}

記事別見出し構造: {json.dumps(articles_headings, ensure_ascii=False, indent=2)}
-
【分析要求】
以下の項目について詳細に分析し、JSON形式で回答してください：

1. 頻出キーワード分析: 見出しに多く使われている重要な単語・フレーズ
2. 類似見出しグループ: 意味的に類似している見出しのグループ化
3. 見出しパターン分析: よく使われる見出しの構造パターン
4. トピック分析: 主要なトピック・テーマの特定
5. SEO戦略的インサイト: これらの見出し分析から得られるSEO戦略の提案

【出力形式】
{{
  "頻出キーワード分析": {{
    "重要キーワード": [
      {{
        "キーワード": "string",
        "出現回数": number,
        "使用記事数": number,
        "重要度": "高|中|低",
        "SEO価値": "string"
      }}
    ],
    "重要フレーズ": [
      {{
        "フレーズ": "string", 
        "出現回数": number,
        "文脈": "string"
      }}
    ]
  }},
  "類似見出しグループ": [
    {{
      "グループ名": "string",
      "見出しリスト": ["string1", "string2", ...],
      "類似理由": "string",
      "共通テーマ": "string",
      "SEO効果": "string"
    }}
  ],
  "見出しパターン分析": {{
    "頻出パターン": [
      {{
        "パターン": "string",
        "例": ["string1", "string2"],
        "使用頻度": "高|中|低"
      }}
    ],
    "レベル別特徴": {{
      "h1": "string",
      "h2": "string", 
      "h3": "string"
    }}
  }},
  "主要トピック分析": [
    {{
      "トピック名": "string",
      "関連見出し": ["string1", "string2"],
      "重要度": number,
      "説明": "string"
    }}
  ],
  "SEO戦略的インサイト": {{
    "競合で頻出する必須トピック": ["string1", "string2"],
    "差別化のチャンス": ["string1", "string2"], 
    "推奨見出し戦略": "string",
    "避けるべきパターン": ["string1", "string2"]
  }},
  "分析サマリー": {{
    "総見出し数": number,
    "主要な競合戦略": "string",
    "最も重要な発見": "string"
  }}
}}

【分析時の注意点】
- 同義語・類義語を考慮した分析を行ってください
- SEOの観点から価値の高いキーワード・パターンを重視してください  
- 競合記事の戦略的意図を読み取って分析してください
- 日本語の表記揺れ（ひらがな・カタカナ・漢字）も考慮してください
"""

            print("   📤 Gemini APIに見出し分析を依頼中...")
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.3
            )
            
            response = await model.generate_content_async(
                contents=[prompt],
                generation_config=generation_config
            )
            
            if not response.text:
                return {
                    "エラー": "Gemini APIからの応答が空でした。",
                    "error": "Empty response from Gemini API."
                }

            try:
                gemini_result = json.loads(response.text)
                
                # メタデータを追加
                enhanced_result = {
                    "分析実行日時": datetime.datetime.now().isoformat(),
                    "分析対象見出し数": len(headings_list),
                    "分析対象記事数": len(articles_headings),
                    "分析手法": "Gemini AI による意味的分析",
                    **gemini_result
                }
                
                print("   ✅ Gemini APIによる見出し分析完了")
                return enhanced_result
                
            except json.JSONDecodeError as e:
                return {
                    "エラー": f"Gemini APIの応答をJSONとして解析できませんでした: {str(e)}",
                    "error": f"Failed to parse Gemini API response as JSON: {str(e)}",
                    "生の応答": response.text[:500]
                }

        except Exception as e:
            return {
                "エラー": f"Gemini API呼び出し中にエラーが発生しました: {str(e)}",
                "error": f"Error during Gemini API call: {str(e)}"
            }

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
            "記事別見出しレベル使用状況": level_usage_per_article_list,
            "level_usage_per_article": level_usage_per_article_list,
            "全記事での見出しレベル別総数": dict(total_level_distribution),
            "total_level_distribution": dict(total_level_distribution),
            "見出しレベル別平均使用数（記事あたり）": avg_level_usage,
            "average_level_usage": avg_level_usage,
            "見出しレベル別使用割合（全見出し中）": percentage_level_usage,
            "percentage_level_usage": percentage_level_usage,
            "記事別最大見出し深度": max_depth_per_article_list,
            "max_depth_per_article": max_depth_per_article_list,
            "平均最大見出し深度": np.mean(max_depth_per_article_list) if max_depth_per_article_list else 0,
            "average_max_depth": np.mean(max_depth_per_article_list) if max_depth_per_article_list else 0,
            "最も多い最大見出し深度": Counter(max_depth_per_article_list).most_common(1)[0][0] if max_depth_per_article_list else 0,
            "most_common_max_depth": Counter(max_depth_per_article_list).most_common(1)[0][0] if max_depth_per_article_list else 0,
            "最大見出し深度の分散": np.var(max_depth_per_article_list) if max_depth_per_article_list else 0,
            "depth_variance": np.var(max_depth_per_article_list) if max_depth_per_article_list else 0,
            "見出しテキスト長分析": {
                "全見出しテキスト長の統計": text_length_stats_all,
                "overall": text_length_stats_all,
                "見出しレベル別テキスト長の統計": text_length_stats_by_level,
                "by_level": text_length_stats_by_level
            },
            "heading_text_length_analysis": {
                "overall": text_length_stats_all,
                "overall_jp": "全見出しテキスト長の統計",
                "by_level": text_length_stats_by_level,
                "by_level_jp": "見出しレベル別テキスト長の統計"
            },
            "分析サマリー": f"見出し構造分析完了: 全{len(self.articles)}記事から{total_headings_count}個の見出しを分析。平均最大深度はH{np.mean(max_depth_per_article_list) if max_depth_per_article_list else 0:.1f}レベルです。",
            "summary_jp": f"見出し構造分析完了: 全{len(self.articles)}記事から{total_headings_count}個の見出しを分析。平均最大深度はH{np.mean(max_depth_per_article_list) if max_depth_per_article_list else 0:.1f}レベルです。"
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
            "実装状況": "コンテンツパターン分析は部分的に実装中です。",
            "message": "コンテンツパターン分析は部分的に実装中です。",
            "分析対象記事数": len(self.articles),
            "analyzed_article_count": len(self.articles),
            "共通見出しレベル使用状況": self.analysis_results.get("heading_structure", {}).get("total_level_distribution"),
            "common_heading_levels_summary": self.analysis_results.get("heading_structure", {}).get("total_level_distribution"),
            "分析サマリー": f"コンテンツパターン分析: {len(self.articles)}記事を分析中（機能は今後拡張予定）",
            "summary_jp": f"コンテンツパターン分析: {len(self.articles)}記事を分析中（機能は今後拡張予定）"
        }
        
        self.analysis_results["content_patterns"] = patterns_result
        print("コンテンツパターンの分析が完了しました（部分実装）。")
        return patterns_result



    def _analyze_frequent_headings_sync(self) -> Dict[str, Any]:
        """競合記事間での頻出見出しパターンを分析する（同期版・基本分析）"""
        print("頻出見出しパターンの分析を開始します（基本版）...")
        
        if not self.articles:
            return {
                "エラー": "分析対象の記事がありません。",
                "error": "No articles available for analysis."
            }

        # すべての見出しを収集
        all_headings_with_context = []
        for i, article in enumerate(self.articles):
            if not hasattr(article, 'headings') or not article.headings:
                continue
            
            flat_headings = self._extract_headings_flat(article.headings)
            for heading in flat_headings:
                all_headings_with_context.append({
                    'text': heading.get('text', ''),
                    'level': heading.get('level'),
                    'semantic_type': heading.get('semantic_type', 'body'),
                    'article_index': i,
                    'article_url': getattr(article, 'url', f'記事{i+1}'),
                    'char_count_section': heading.get('char_count_section', 0)
                })

        # 1. 完全一致の頻出見出し分析
        exact_matches = Counter()
        for heading in all_headings_with_context:
            text = heading['text'].strip()
            if text and len(text) > 0:
                exact_matches[text] += 1

        frequent_exact = [(text, count) for text, count in exact_matches.items() if count >= 2]
        frequent_exact.sort(key=lambda x: x[1], reverse=True)

        # 2. レベル別頻出見出し分析
        level_based_analysis = {}
        for level in range(1, 7):
            level_headings = [h['text'].strip() for h in all_headings_with_context 
                             if h['level'] == level and h['text'].strip()]
            if level_headings:
                level_counter = Counter(level_headings)
                frequent_in_level = [(text, count) for text, count in level_counter.items() if count >= 2]
                frequent_in_level.sort(key=lambda x: x[1], reverse=True)
                level_based_analysis[f'h{level}'] = {
                    '総数': len(level_headings),
                    '頻出見出し': frequent_in_level[:10],  # 上位10個
                    '一意見出し数': len(set(level_headings))
                }

        # 3. 意味分類別頻出見出し分析
        semantic_based_analysis = {}
        for semantic_type in ['introduction', 'body', 'conclusion', 'faq', 'references']:
            semantic_headings = [h['text'].strip() for h in all_headings_with_context 
                               if h['semantic_type'] == semantic_type and h['text'].strip()]
            if semantic_headings:
                semantic_counter = Counter(semantic_headings)
                frequent_in_semantic = [(text, count) for text, count in semantic_counter.items() if count >= 2]
                frequent_in_semantic.sort(key=lambda x: x[1], reverse=True)
                semantic_based_analysis[semantic_type] = {
                    '総数': len(semantic_headings),
                    '頻出見出し': frequent_in_semantic[:10],
                    '一意見出し数': len(set(semantic_headings))
                }

        # 4. 類似見出しグループの基本分析（同期版・簡易）
        similarity_groups = {}
        processed_headings = set()
        similarity_group_list = []
        
        for heading in all_headings_with_context:
            text = heading['text'].strip().lower()
            if text in processed_headings or len(text) < 3:
                continue
                
            # 簡易類似判定（単語の重複による）
            similar_headings = []
            text_words = set(text.split())
            
            for other_heading in all_headings_with_context:
                other_text = other_heading['text'].strip().lower()
                if other_text != text and other_text not in processed_headings:
                    other_words = set(other_text.split())
                    # 50%以上の単語が共通していれば類似とみなす
                    common_words = text_words & other_words
                    if len(common_words) > 0 and len(common_words) / max(len(text_words), len(other_words)) >= 0.5:
                        similar_headings.append(other_heading['text'])
                        processed_headings.add(other_text)
            
            if similar_headings:
                similarity_group_list.append({
                    'ベース見出し': heading['text'],
                    '類似見出し': similar_headings,
                    '類似グループサイズ': len(similar_headings) + 1,
                    'ベースレベル': heading['level']
                })
                processed_headings.add(text)
        
        # 類似グループをサイズ順にソート
        similarity_group_list.sort(key=lambda x: x['類似グループサイズ'], reverse=True)
        
        similarity_groups = {
            '類似グループ総数': len(similarity_group_list),
            'トップ10グループ': similarity_group_list[:10]
        }

        result = {
            "全見出し統計": {
                "総見出し数": len(all_headings_with_context),
                "一意見出し数": len(set(h['text'].strip() for h in all_headings_with_context if h['text'].strip())),
                "重複見出し数": len(all_headings_with_context) - len(set(h['text'].strip() for h in all_headings_with_context if h['text'].strip()))
            },
            "完全一致頻出見出し": {
                "説明": "複数記事で全く同じテキストが使われている見出し",
                "トップ20": frequent_exact[:20],
                "頻出見出し総数": len(frequent_exact)
            },
            "レベル別頻出分析": level_based_analysis,
            "意味分類別頻出分析": semantic_based_analysis,
            "類似見出しグループ": similarity_groups,
            "分析手法": "基本的な統計分析とシンプルな類似判定"
        }

        print(f"✅ 頻出見出し分析完了（基本版）: {len(all_headings_with_context)}個の見出しを分析")
        print(f"   📊 完全一致頻出見出し: {len(frequent_exact)}種類")
        print(f"   🔗 類似見出しグループ: {len(similarity_group_list)}グループ")
        
        return result

    def get_full_analysis(self, target_article_headings: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        全ての分析を実行し、統合された結果を返します。
        """
        print("完全なコンテンツ分析を開始します...")
        self.analyze_basic_statistics() 
        self.analyze_heading_structure() # ★ 見出し構造分析を呼び出し
        
        # ★ 頻出見出し分析（基本版）を追加
        frequent_headings_result = self._analyze_frequent_headings_sync()
        self.analysis_results["frequent_headings_basic"] = frequent_headings_result
        
        # ★ 新しい高度分析メソッドを追加
        self.analyze_multimedia_strategy() # マルチメディア戦略分析
        self.analyze_eeat_factors() # E-E-A-T要因分析
        
        self.analyze_content_patterns()
        
        # 分析結果全体に日本語サマリーを追加
        self.analysis_results["分析サマリー"] = {
            "実行日時": datetime.datetime.now().isoformat(),
            "分析対象記事数": len(self.articles),
            "実行した分析項目": [
                "基本統計分析（文字数・画像数・見出し数・動画・テーブル・リンク）",
                "見出し構造分析（レベル別使用状況・深度分析）", 
                "頻出見出し分析（Gemini AI enhanced）",
                "マルチメディア戦略分析（動画・テーブル・リスト活用状況）",
                "E-E-A-T要因分析（専門性・権威性・信頼性・鮮度）",
                "コンテンツパターン分析"
            ],
            "完了メッセージ": f"{len(self.articles)}記事の完全なコンテンツ分析（Gemini AI enhanced）が完了しました。",
            "Gemini_AI分析": "有効 - 意味的な見出し分析と頻出単語の高精度抽出を実行"
        }
        self.analysis_results["analysis_summary_jp"] = {
            "実行日時": "分析実行完了",
            "分析対象記事数": len(self.articles),
            "実行した分析項目": [
                "基本統計分析（文字数・画像数・見出し数）",
                "見出し構造分析（レベル別使用状況・深度分析）", 
                "頻出見出し分析（基本版）",  # ★ 追加
                "コンテンツパターン分析（部分実装）",
                "コンテンツギャップ抽出（未実装）",
                "競争優位性特定（未実装）"
            ],
            "利用可能な統計値": [
                "平均値・中央値・標準偏差",
                "最大値・最小値・四分位数", 
                "パーセンタイル・外れ値判定基準"
            ],
            "完了メッセージ": f"{len(self.articles)}記事の完全なコンテンツ分析が完了しました。",
            "Gemini_AI分析について": "Gemini AIを使った高度な分析は get_full_analysis_with_gemini() メソッドをご利用ください。"
        }
        
        print("完全なコンテンツ分析が完了しました。")
        return self.analysis_results

    async def get_full_analysis_with_gemini(self, target_article_headings: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Gemini AIを使った高度な分析を含む全ての分析を実行し、統合された結果を返します。
        """
        print("Gemini AI enhanced コンテンツ分析を開始します...")
        
        # 基本分析を実行
        self.analyze_basic_statistics() 
        self.analyze_heading_structure()
        
        # ★ Gemini AIを使った頻出見出し分析
        frequent_headings_gemini_result = await self._analyze_frequent_headings()
        self.analysis_results["frequent_headings_gemini"] = frequent_headings_gemini_result
        
        # ★ 新しい高度分析メソッドを追加
        self.analyze_multimedia_strategy() # マルチメディア戦略分析
        self.analyze_eeat_factors() # E-E-A-T要因分析
        
        self.analyze_content_patterns()
        
        # 分析結果全体に日本語サマリーを追加
        self.analysis_results["分析サマリー"] = {
            "実行日時": "分析実行完了",
            "分析対象記事数": len(self.articles),
            "実行した分析項目": [
                "基本統計分析（文字数・画像数・見出し数）",
                "見出し構造分析（レベル別使用状況・深度分析）", 
                "頻出見出し分析（Gemini AI enhanced）",  # ★ 追加
                "コンテンツパターン分析（部分実装）",
                "コンテンツギャップ抽出（未実装）",
                "競争優位性特定（未実装）"
            ],
            "利用可能な統計値": [
                "平均値・中央値・標準偏差",
                "最大値・最小値・四分位数", 
                "パーセンタイル・外れ値判定基準"
            ],
            "完了メッセージ": f"{len(self.articles)}記事の完全なコンテンツ分析（Gemini AI enhanced）が完了しました。",
            "Gemini_AI分析": "有効 - 意味的な見出し分析と頻出単語の高精度抽出を実行"
        }
        self.analysis_results["analysis_summary_jp"] = {
            "実行日時": "分析実行完了",
            "分析対象記事数": len(self.articles),
            "実行した分析項目": [
                "基本統計分析（文字数・画像数・見出し数）",
                "見出し構造分析（レベル別使用状況・深度分析）", 
                "頻出見出し分析（Gemini AI enhanced）",  # ★ 追加
                "コンテンツパターン分析（部分実装）",
                "コンテンツギャップ抽出（未実装）",
                "競争優位性特定（未実装）"
            ],
            "利用可能な統計値": [
                "平均値・中央値・標準偏差",
                "最大値・最小値・四分位数", 
                "パーセンタイル・外れ値判定基準"
            ],
            "完了メッセージ": f"{len(self.articles)}記事の完全なコンテンツ分析（Gemini AI enhanced）が完了しました。",
            "Gemini_AI分析": "有効 - 意味的な見出し分析と頻出単語の高精度抽出を実行"
        }
        
        print("Gemini AI enhanced コンテンツ分析が完了しました。")
        return self.analysis_results

    def _filter_keys_by_language(self, data: Dict[str, Any], language: str = "jp") -> Dict[str, Any]:
        """
        データ内のキーを指定言語でフィルタリングする
        
        Args:
            data: フィルタリング対象のデータ
            language: "jp" (日本語キーのみ) または "en" (英語キーのみ)
            
        Returns:
            フィルタリングされたデータ
        """
        if not isinstance(data, dict):
            return data
        
        # 日本語キーと英語キーのペア定義
        key_pairs = {
            # 基本統計関連
            "文字数分析": "char_count_analysis",
            "画像数分析": "image_count_analysis", 
            "見出し数分析": "heading_count_analysis",
            "動画数分析": "video_count_analysis",
            "テーブル数分析": "table_count_analysis",
            "リスト項目数分析": "list_item_count_analysis",
            "外部リンク数分析": "external_link_count_analysis",
            "内部リンク数分析": "internal_link_count_analysis",
            "セクション文字数分析": "section_char_count_analysis",
            
            # 統計値関連
            "統計値": "stats",
            "説明": "description",
            "分析対象記事数": "article_count",
            "分析サマリー": "summary_jp",
            
            # 見出し構造関連
            "記事別見出しレベル使用状況": "level_usage_per_article",
            "全記事での見出しレベル別総数": "total_level_distribution",
            "見出しレベル別平均使用数（記事あたり）": "average_level_usage",
            "見出しレベル別使用割合（全見出し中）": "percentage_level_usage",
            "記事別最大見出し深度": "max_depth_per_article",
            "平均最大見出し深度": "average_max_depth",
            "最も多い最大見出し深度": "most_common_max_depth",
            "最大見出し深度の分散": "depth_variance",
            "見出しテキスト長分析": "heading_text_length_analysis",
            
            # 統計項目
            "平均値": "mean",
            "中央値": "median", 
            "標準偏差": "std_dev",
            "分散": "variance",
            "最小値": "min",
            "最大値": "max",
            "範囲（最大値-最小値）": "range",
            "第1四分位数（25パーセンタイル）": "q1",
            "第3四分位数（75パーセンタイル）": "q3",
            "四分位範囲": "iqr",
            "パーセンタイル値": "percentiles",
            "外れ値判定基準": "outlier_thresholds",
            "データ数": "count",
            "統計サマリー": "summary_jp",
            
            # ★ 見出し提案関連
            "分析実行日時": "analysis_timestamp",
            "入力パラメータ": "input_parameters",
            "ターゲットキーワード": "target_keyword",
            "記事目的": "article_purpose", 
            "ターゲット読者": "target_audience",
            "競合記事分析サマリー": "competitor_analysis_summary",
            "分析記事数": "analyzed_articles",
            "総見出し数": "total_headings",
            "頻出見出し分析結果": "frequent_headings_analysis",
            "Gemini分析結果": "gemini_analysis",
            "Gemini_AI分析結果": "gemini_analysis_results"
        }
        
        filtered_data = {}
        
        if language == "jp":
            # 日本語版: 日本語キーを残し、対応する英語キーは除外
            jp_keys = set(key_pairs.keys())
            en_keys = set(key_pairs.values())
            
            for key, value in data.items():
                # 英語キーで対応する日本語キーが存在する場合はスキップ
                if key in en_keys:
                    jp_equivalent = None
                    for jp_key, en_key in key_pairs.items():
                        if en_key == key:
                            jp_equivalent = jp_key
                            break
                    if jp_equivalent and jp_equivalent in data:
                        continue
                
                # 再帰的にフィルタリング
                if isinstance(value, dict):
                    filtered_data[key] = self._filter_keys_by_language(value, language)
                elif isinstance(value, list):
                    filtered_data[key] = [
                        self._filter_keys_by_language(item, language) if isinstance(item, dict) else item
                        for item in value
                    ]
                else:
                    filtered_data[key] = value
                    
        elif language == "en":
            # 英語版: 英語キーを残し、日本語キーは除外
            for key, value in data.items():
                # 日本語キーで対応する英語キーが存在する場合は、英語キーのみ残す
                if key in key_pairs:
                    en_key = key_pairs[key]
                    if en_key in data:
                        continue  # 対応する英語キーがあるので日本語キーはスキップ
                
                # 再帰的にフィルタリング
                if isinstance(value, dict):
                    filtered_data[key] = self._filter_keys_by_language(value, language)
                elif isinstance(value, list):
                    filtered_data[key] = [
                        self._filter_keys_by_language(item, language) if isinstance(item, dict) else item
                        for item in value
                    ]
                else:
                    filtered_data[key] = value
        
        return filtered_data

    def export_to_json(self, filename: str, language: str = "jp"):
        """
        分析結果をJSON形式でファイルに出力します。

        Args:
            filename: 出力するJSONファイルの名前。
            language: "jp" (日本語キーのみ) または "en" (英語キーのみ) または "both" (両方)
        """
        if language == "both":
            # 両方の言語で出力
            base_name = filename.replace('.json', '')
            
            # 日本語版
            jp_filename = f"{base_name}_jp.json"
            self.export_to_json(jp_filename, "jp")
            
            # 英語版
            en_filename = f"{base_name}_en.json"
            self.export_to_json(en_filename, "en")
            
            print(f"✅ 両言語版JSON分析データが出力されました:")
            print(f"   🇯🇵 日本語版: {jp_filename}")
            print(f"   🇺🇸 英語版: {en_filename}")
            return
        
        # 言語別にフィルタリング
        filtered_results = self._filter_keys_by_language(self.analysis_results, language)
        
        # メタデータを追加
        if language == "jp":
            export_data = {
                "分析メタデータ": {
                    "実行日時": datetime.datetime.now().isoformat(),
                    "分析対象記事数": len(self.articles),
                    "エクスポート形式": "JSON",
                    "言語": "日本語"
                },
                "分析結果": filtered_results
            }
            lang_label = "日本語版"
        else:
            export_data = {
                "analysis_metadata": {
                    "execution_time": datetime.datetime.now().isoformat(),
                    "analyzed_articles": len(self.articles),
                    "export_format": "JSON",
                    "language": "English"
                },
                "analysis_results": filtered_results
            }
            lang_label = "英語版"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        print(f"✅ {lang_label}JSON分析データが {filename} に保存されました。")

    async def _infer_topic_from_articles(self) -> Dict[str, str]:
        """
        記事のタイトルと頻出見出しを分析し、Gemini を使用して中心的なトピック、
        記事の目的、ターゲット読者を推測します。
        """
        print("🤖 Gemini APIを使用してコンテンツから中心トピックを推測中...")
        if not self.articles:
            return {
                "target_keyword": "不明なトピック",
                "article_purpose": "一般的な記事",
                "target_audience": "一般読者"
            }

        try:
            from app.core.config import settings
            import google.generativeai as genai

            if not settings.gemini_api_key:
                raise ValueError("Gemini APIキーが設定されていません。")
            
            setup_genai_client()
            model = genai.GenerativeModel('gemini-2.0-flash')

            # データ収集
            article_titles = [getattr(article, 'title', '') for article in self.articles]
            
            if "frequent_headings_basic" not in self.analysis_results:
                self._analyze_frequent_headings_sync()
                
            frequent_headings_result = self.analysis_results.get("frequent_headings_basic", {})
            frequent_headings = [h[0] for h in frequent_headings_result.get("完全一致頻出見出し", {}).get("トップ20", [])[:10]]

            prompt = f"""
あなたは優れたSEOアナリストです。以下のデータから、これらの記事群がターゲットとしている「中心的な検索キーワード」、「記事の目的」、「ターゲット読者」を推測してください。

【分析対象データ】
■ 記事タイトル ({len(article_titles)}件):
{json.dumps(article_titles, ensure_ascii=False, indent=2)}

■ 頻出する見出し ({len(frequent_headings)}件):
{json.dumps(frequent_headings, ensure_ascii=False, indent=2)}

【指示】
上記の情報を基に、最も可能性の高いキーワード、目的、読者層を特定し、以下のJSON形式で回答してください。キーワードは、ユーザーが検索窓に入力するような具体的で短いフレーズにしてください。

【出力形式】
{{
  "target_keyword": "string",
  "article_purpose": "string",
  "target_audience": "string"
}}

余計な説明は含めず、JSONオブジェクトのみを返してください。
"""
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
            
            response = await model.generate_content_async(
                contents=[prompt],
                generation_config=generation_config
            )

            if not response.text:
                raise ValueError("Gemini APIからの応答が空でした。")

            result = json.loads(response.text)
            print(f"   ✅ トピック推測成功: キーワード「{result.get('target_keyword')}」")
            return result

        except Exception as e:
            print(f"   ⚠️ トピック推測でエラーが発生: {e}. デフォルト値を返します。")
            return {
                "target_keyword": "分析されたトピック",
                "article_purpose": "SEO効果的な詳細記事",
                "target_audience": "一般読者"
            }

    async def suggest_optimal_headings(
        self, 
        target_keyword: Optional[str] = None, 
        article_purpose: Optional[str] = None,
        target_audience: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        競合記事の見出し構造をすべて分析し、Gemini APIを使用して
        SEO効果的な最適な見出し構造を提案します。
        キーワードなどが指定されない場合は、分析済みコンテンツから推測します。

        Args:
            target_keyword: オプション。ターゲットキーワード。
            article_purpose: オプション。記事の目的。
            target_audience: オプション。ターゲット読者層。

        Returns:
            提案された最適な見出し構造を含む辞書
        """
        print(f"最適見出し構造の提案を開始します...")
        
        # キーワード等が指定されていない場合、コンテンツから推測する
        if not target_keyword or not article_purpose or not target_audience:
            print("...ターゲット情報が不足しているため、コンテンツから推測します。")
            try:
                inferred_topic = await self._infer_topic_from_articles()
                # 指定されていない引数のみ、推測結果で上書きする
                if not target_keyword:
                    target_keyword = inferred_topic.get("target_keyword", "分析トピック")
                if not article_purpose:
                    article_purpose = inferred_topic.get("article_purpose", "詳細ガイド")
                if not target_audience:
                    target_audience = inferred_topic.get("target_audience", "一般読者")
            except Exception as e:
                print(f"⚠️ トピックの推測中にエラーが発生しました: {e}。デフォルト値を使用します。")
                target_keyword = target_keyword or "分析されたトピック"
                article_purpose = article_purpose or "SEO効果的な詳細記事"
                target_audience = target_audience or "一般読者"
        
        print(f"ターゲットキーワード: {target_keyword}")
        print(f"記事の目的: {article_purpose}")
        print(f"ターゲット読者: {target_audience}")

        if not self.articles:
            return {
                "エラー": "分析対象の記事がありません。",
                "error": "No articles available for analysis."
            }

        # Gemini APIの設定確認
        try:
            from app.core.config import settings
            import google.generativeai as genai
            
            if not settings.gemini_api_key:
                return {
                    "エラー": "Gemini APIキーが設定されていません。",
                    "error": "Gemini API key not configured."
                }
            
            setup_genai_client()
            model = genai.GenerativeModel('gemini-2.0-flash')
            
        except Exception as e:
            return {
                "エラー": f"Gemini API設定エラー: {str(e)}",
                "error": f"Gemini API configuration error: {str(e)}"
            }

        # すべての競合記事から見出し構造を抽出
        all_competitor_headings = []
        for i, article in enumerate(self.articles):
            if not hasattr(article, 'headings') or not article.headings:
                continue
            
            flat_headings = self._extract_headings_flat(article.headings)
            competitor_data = {
                "記事番号": i + 1,
                "記事URL": getattr(article, 'url', f'記事{i+1}'),
                "記事タイトル": getattr(article, 'title', f'タイトル{i+1}'),
                "文字数": getattr(article, 'char_count', 0),
                "画像数": getattr(article, 'image_count', 0),
                # ★ 新しいコンテンツフォーマット情報を追加
                "動画数": getattr(article, 'video_count', 0),
                "テーブル数": getattr(article, 'table_count', 0),
                "リスト項目数": getattr(article, 'list_item_count', 0),
                "外部リンク数": getattr(article, 'external_link_count', 0),
                "内部リンク数": getattr(article, 'internal_link_count', 0),
                # ★ E-E-A-T関連情報を追加
                "著者情報": getattr(article, 'author_info', None),
                "公開日": getattr(article, 'publish_date', None),
                "更新日": getattr(article, 'modified_date', None),
                "構造化データ": getattr(article, 'schema_types', []),
                "見出し構造": [
                    {
                        "レベル": h.get('level'),
                        "テキスト": h.get('text'),
                        "意味分類": h.get('semantic_type', 'body'),
                        "セクション文字数": h.get('char_count_section', 0)
                    }
                    for h in flat_headings
                ]
            }
            all_competitor_headings.append(competitor_data)

        # ★ 頻出見出し分析を実行
        print("📊 頻出見出しパターンを分析中...")
        frequent_headings_analysis = self._analyze_frequent_headings_sync()

        # ★ 統計情報の準備（新しいデータを含む）
        stats_summary = ""
        if "basic_statistics" in self.analysis_results:
            char_stats = self.analysis_results["basic_statistics"]["文字数分析"]["統計値"]
            image_stats = self.analysis_results["basic_statistics"]["画像数分析"]["統計値"]
            video_stats = self.analysis_results["basic_statistics"]["動画数分析"]["統計値"]
            table_stats = self.analysis_results["basic_statistics"]["テーブル数分析"]["統計値"]
            list_stats = self.analysis_results["basic_statistics"]["リスト項目数分析"]["統計値"]
            ext_link_stats = self.analysis_results["basic_statistics"]["外部リンク数分析"]["統計値"]
            int_link_stats = self.analysis_results["basic_statistics"]["内部リンク数分析"]["統計値"]
            
            stats_summary = f"""
基本コンテンツ統計:
- 平均文字数: {char_stats['平均値']:.0f}文字 (範囲: {char_stats['最小値']:.0f}〜{char_stats['最大値']:.0f}文字)
- 平均画像数: {image_stats['平均値']:.1f}個 (範囲: {image_stats['最小値']:.0f}〜{image_stats['最大値']:.0f}個)

マルチメディア戦略統計:
- 平均動画数: {video_stats['平均値']:.1f}個 (範囲: {video_stats['最小値']:.0f}〜{video_stats['最大値']:.0f}個)
- 平均テーブル数: {table_stats['平均値']:.1f}個 (範囲: {table_stats['最小値']:.0f}〜{table_stats['最大値']:.0f}個)
- 平均リスト項目数: {list_stats['平均値']:.1f}項目 (範囲: {list_stats['最小値']:.0f}〜{list_stats['最大値']:.0f}項目)

リンク戦略統計:
- 平均外部リンク数: {ext_link_stats['平均値']:.1f}個 (信頼性・権威性指標)
- 平均内部リンク数: {int_link_stats['平均値']:.1f}個 (サイト回遊性指標)
"""

        if "heading_structure" in self.analysis_results:
            heading_stats = self.analysis_results["heading_structure"]
            total_dist = heading_stats.get("全記事での見出しレベル別総数", {})
            stats_summary += f"""
見出し使用状況:
- H1: {total_dist.get('h1', 0)}回
- H2: {total_dist.get('h2', 0)}回  
- H3: {total_dist.get('h3', 0)}回
- H4: {total_dist.get('h4', 0)}回
- H5: {total_dist.get('h5', 0)}回
- H6: {total_dist.get('h6', 0)}回
"""

        # ★ マルチメディア・E-E-A-T分析結果も追加
        if "multimedia_strategy" in self.analysis_results:
            multimedia = self.analysis_results["multimedia_strategy"]
            stats_summary += f"""
マルチメディア戦略パターン:
- 動画採用記事: {multimedia['動画コンテンツ分析']['採用率']}
- テーブル採用記事: {multimedia['テーブル活用分析']['採用率']}
- リスト構造採用記事: {multimedia['リスト構造分析']['採用率']}
"""

        if "eeat_factors" in self.analysis_results:
            eeat = self.analysis_results["eeat_factors"]
            stats_summary += f"""
E-E-A-T要因統計:
- 著者情報明記: {eeat['専門性・権威性分析']['著者情報明記率']}
- 外部リンク活用: {eeat['信頼性分析']['外部リンク採用率']}
- 構造化データ活用: {eeat['技術的信頼性分析']['構造化データ採用率']}
- E-E-A-T総合スコア: {eeat['E-E-A-T総合評価']['総合スコア']}
"""

        # ★ 頻出見出し情報もstats_summaryに追加
        if "エラー" not in frequent_headings_analysis:
            exact_frequent = frequent_headings_analysis.get("完全一致頻出見出し", {})
            similarity_groups = frequent_headings_analysis.get("類似見出しグループ", {})
            stats_summary += f"""
頻出見出し分析:
- 完全一致頻出見出し: {exact_frequent.get('頻出見出し総数', 0)}種類
- 類似見出しグループ: {similarity_groups.get('類似グループ総数', 0)}グループ
- 重複見出し率: {frequent_headings_analysis.get('全見出し統計', {}).get('重複見出し数', 0)}/{frequent_headings_analysis.get('全見出し統計', {}).get('総見出し数', 1)}
"""

        # ★ ターミナルに送信データの詳細を表示
        print("\n" + "="*60)
        print("🔍 Gemini APIに送信するデータの詳細:")
        print("="*60)
        print(f"📋 ターゲット情報:")
        print(f"   • キーワード: {target_keyword}")
        print(f"   • 記事目的: {article_purpose}")
        print(f"   • ターゲット読者: {target_audience}")
        
        print(f"\n📊 基本統計情報:")
        if "basic_statistics" in self.analysis_results:
            char_stats = self.analysis_results["basic_statistics"]["文字数分析"]["統計値"]
            print(f"   • 平均文字数: {char_stats['平均値']:.0f}文字")
            print(f"   • 文字数範囲: {char_stats['最小値']:.0f}〜{char_stats['最大値']:.0f}文字")
        
        print(f"\n🏗️  見出し構造情報:")
        total_headings = sum(len(comp["見出し構造"]) for comp in all_competitor_headings)
        print(f"   • 分析記事数: {len(all_competitor_headings)}記事")
        print(f"   • 総見出し数: {total_headings}個")
        
        if "heading_structure" in self.analysis_results:
            heading_stats = self.analysis_results["heading_structure"]
            total_dist = heading_stats.get("全記事での見出しレベル別総数", {})
            for level in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                count = total_dist.get(level, 0)
                if count > 0:
                    print(f"   • {level.upper()}: {count}個")
        
        print(f"\n🔄 頻出見出し分析結果:")
        if "エラー" not in frequent_headings_analysis:
            exact_frequent = frequent_headings_analysis.get("完全一致頻出見出し", {})
            similarity_groups = frequent_headings_analysis.get("類似見出しグループ", {})
            stats = frequent_headings_analysis.get("全見出し統計", {})
            
            print(f"   • 総見出し数: {stats.get('総見出し数', 0)}個")
            print(f"   • 一意見出し数: {stats.get('一意見出し数', 0)}個")
            print(f"   • 重複見出し数: {stats.get('重複見出し数', 0)}個")
            print(f"   • 完全一致頻出見出し: {exact_frequent.get('頻出見出し総数', 0)}種類")
            print(f"   • 類似見出しグループ: {similarity_groups.get('類似グループ総数', 0)}グループ")
            
            # トップ5の頻出見出しを表示
            top_frequent = exact_frequent.get("トップ20", [])[:5]
            if top_frequent:
                print(f"   • トップ5頻出見出し:")
                for i, (text, count) in enumerate(top_frequent):
                    print(f"     {i+1}. 「{text}」({count}回)")
            
            # トップ3の類似グループを表示
            top_groups = similarity_groups.get("トップ10グループ", [])[:3]
            if top_groups:
                print(f"   • トップ3類似グループ:")
                for i, group in enumerate(top_groups):
                    base_text = group.get('ベース見出し', '')
                    group_size = group.get('類似グループサイズ', 0)
                    print(f"     {i+1}. 「{base_text}」類似グループ ({group_size}個)")
        else:
            print(f"   ❌ 頻出見出し分析エラー: {frequent_headings_analysis.get('エラー', 'Unknown')}")
        
        print("="*60)

        # ★ 強化されたGemini APIプロンプト作成
        prompt = f"""
あなたは、SEO専門のコンテンツ戦略アドバイザーです。以下の競合記事分析結果を基に、最適な見出し構造を提案してください。

【ターゲット情報】
- キーワード: {target_keyword}
- 記事の目的: {article_purpose}
- ターゲット読者: {target_audience}

【競合記事の統計情報】
{stats_summary}

【頻出見出しパターン分析】
{json.dumps(frequent_headings_analysis, ensure_ascii=False, indent=2)}

【競合記事の詳細分析データ】
{json.dumps(all_competitor_headings, ensure_ascii=False, indent=2)}

【提案要件】
1. 上記の競合記事を分析し、必須とみられる見出しトピックを特定してください
2. 頻出見出しパターンから重要なトピックを抽出してください
3. 競合記事にない独自性のある見出しを提案してください  
4. SEO効果を最大化する見出し構造を設計してください
5. ユーザーの検索意図に応える包括的な構成を提案してください
6. ★ マルチメディア戦略も考慮してください（動画・テーブル・リストの活用）
7. ★ E-E-A-T要因も考慮してください（著者情報・外部リンク・構造化データ）
8. 適切な文字数ターゲットも併せて提案してください

【出力形式】
以下のJSON形式で回答してください：

{{
  "提案サマリー": {{
    "競合分析の要点": "string",
    "頻出パターンの特徴": "string",
    "提案の特徴": "string", 
    "SEO戦略": "string"
  }},
  "推奨見出し構造": [
    {{
      "レベル": 1,
      "見出しテキスト": "string",
      "目的": "introduction|body|conclusion|faq|references",
      "推奨文字数": number,
      "選定理由": "string",
      "競合での使用状況": "string",
      "頻出度": "高|中|低|独自"
    }}
  ],
  "独自性のある提案": [
    {{
      "見出しテキスト": "string", 
      "レベル": number,
      "差別化ポイント": "string",
      "期待効果": "string"
    }}
  ],
  "記事全体の推奨仕様": {{
    "推奨総文字数": number,
    "推奨見出し数": number,
    "推奨画像数": number,
    "推奨動画数": number,
    "推奨テーブル数": number,
    "推奨リスト項目数": number,
    "推奨外部リンク数": number,
    "推奨内部リンク数": number,
    "主要なSEOポイント": ["string1", "string2", "string3"]
  }},
  "E-E-A-T戦略提案": {{
    "著者情報の扱い": "string",
    "外部リンク戦略": "string", 
    "構造化データ活用": "string",
    "日付情報の明記": "string"
  }},
  "マルチメディア戦略提案": {{
    "動画コンテンツ戦略": "string",
    "テーブル活用戦略": "string",
    "リスト構造戦略": "string",
    "画像配置戦略": "string"
  }}
}}

必ずこのJSON形式で回答し、他の形式は使用しないでください。
"""

        print(f"\n🚀 Gemini APIに分析を依頼します...")
        print(f"   📤 送信データサイズ: 約{len(prompt):,}文字")
        print(f"   🎯 競合記事数: {len(all_competitor_headings)}記事")
        print(f"   📊 頻出見出し分析結果も含む")
        
        try:
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.3
            )
            
            response = await model.generate_content_async(
                contents=[prompt],
                generation_config=generation_config
            )
            
            if not response.text:
                return {
                    "エラー": "Gemini APIからの応答が空でした。",
                    "error": "Empty response from Gemini API."
                }

            try:
                gemini_result = json.loads(response.text)
            except json.JSONDecodeError as e:
                return {
                    "エラー": f"Gemini APIの応答をJSONとして解析できませんでした: {str(e)}",
                    "error": f"Failed to parse Gemini API response as JSON: {str(e)}",
                    "生の応答": response.text[:500]
                }

            # 結果の後処理と日本語化
            result = {
                "分析実行日時": datetime.datetime.now().isoformat(),
                "analysis_timestamp": datetime.datetime.now().isoformat(),
                "入力パラメータ": {
                    "ターゲットキーワード": target_keyword,
                    "target_keyword": target_keyword,
                    "記事目的": article_purpose,
                    "article_purpose": article_purpose,
                    "ターゲット読者": target_audience,
                    "target_audience": target_audience
                },
                "input_parameters": {
                    "target_keyword": target_keyword,
                    "article_purpose": article_purpose,
                    "target_audience": target_audience
                },
                "競合記事分析サマリー": {
                    "分析記事数": len(self.articles),
                    "analyzed_articles": len(self.articles),
                    "総見出し数": sum(len(comp["見出し構造"]) for comp in all_competitor_headings),
                    "total_headings": sum(len(comp["見出し構造"]) for comp in all_competitor_headings)
                },
                "competitor_analysis_summary": {
                    "analyzed_articles": len(self.articles),
                    "total_headings": sum(len(comp["見出し構造"]) for comp in all_competitor_headings)
                },
                "頻出見出し分析結果": frequent_headings_analysis,  # ★ 頻出見出し分析結果を追加
                "frequent_headings_analysis": frequent_headings_analysis,
                "Gemini分析結果": gemini_result,
                "gemini_analysis": gemini_result,
                "分析サマリー": f"Gemini APIによる最適見出し構造の提案が完了しました。キーワード「{target_keyword}」に対する{len(self.articles)}記事の分析結果です。",
                "summary_jp": f"Gemini APIによる最適見出し構造の提案が完了しました。キーワード「{target_keyword}」に対する{len(self.articles)}記事の分析結果です。"
            }

            print("✅ 最適見出し構造の提案が完了しました。")
            
            # analysis_resultsにも保存
            self.analysis_results["optimal_headings_suggestion"] = result
            
            return result

        except Exception as e:
            error_msg = f"Gemini API呼び出し中にエラーが発生しました: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "エラー": error_msg,
                "error": error_msg,
                "入力パラメータ": {
                    "target_keyword": target_keyword,
                    "article_purpose": article_purpose,
                    "target_audience": target_audience
                }
            }

    def analyze_multimedia_strategy(self) -> Dict[str, Any]:
        """
        競合記事のマルチメディア戦略を分析する
        動画、テーブル、リストの使用状況から、ユーザーエンゲージメント戦略を解析
        """
        print("マルチメディア戦略の分析を開始します...")
        
        if not self.articles:
            return {
                "エラー": "分析対象の記事がありません。",
                "error": "No articles available for analysis."
            }

        # データ収集
        video_counts = [getattr(article, 'video_count', 0) for article in self.articles]
        table_counts = [getattr(article, 'table_count', 0) for article in self.articles]
        list_item_counts = [getattr(article, 'list_item_count', 0) for article in self.articles]
        
        # 統計分析
        video_stats = self._analyze_distribution(video_counts, "video_count")
        table_stats = self._analyze_distribution(table_counts, "table_count")
        list_item_stats = self._analyze_distribution(list_item_counts, "list_item_count")
        
        # 戦略的分析
        articles_with_video = sum(1 for count in video_counts if count > 0)
        articles_with_tables = sum(1 for count in table_counts if count > 0)
        articles_with_lists = sum(1 for count in list_item_counts if count > 0)
        
        total_articles = len(self.articles)
        video_adoption_rate = (articles_with_video / total_articles) * 100
        table_adoption_rate = (articles_with_tables / total_articles) * 100
        list_adoption_rate = (articles_with_lists / total_articles) * 100
        
        # 戦略パターンの特定
        multimedia_strategies = []
        
        if video_adoption_rate >= 70:
            multimedia_strategies.append("動画重視戦略が主流")
        elif video_adoption_rate >= 30:
            multimedia_strategies.append("動画を部分的に活用")
        else:
            multimedia_strategies.append("動画活用は少数派")
            
        if table_adoption_rate >= 70:
            multimedia_strategies.append("テーブル活用が一般的（強調スニペット対策）")
        elif table_adoption_rate >= 30:
            multimedia_strategies.append("テーブルを適度に活用")
        else:
            multimedia_strategies.append("テーブル活用の機会あり")
            
        if list_adoption_rate >= 80:
            multimedia_strategies.append("リスト形式が標準的")
        elif list_adoption_rate >= 50:
            multimedia_strategies.append("リスト形式を積極活用")
        else:
            multimedia_strategies.append("リスト活用で差別化可能")

        # 推奨戦略の生成
        recommendations = []
        
        if video_stats['平均値'] > 0:
            recommendations.append(f"動画コンテンツ: 平均{video_stats['平均値']:.1f}個を目標に動画埋め込みを検討")
        else:
            recommendations.append("動画コンテンツ: 競合がほぼ未活用のため、動画で大きく差別化可能")
            
        if table_stats['平均値'] >= 2:
            recommendations.append(f"テーブル活用: 平均{table_stats['平均値']:.1f}個のテーブルで情報整理を強化")
        else:
            recommendations.append("テーブル活用: 情報を整理して強調スニペット獲得を狙う")
            
        if list_item_stats['平均値'] >= 10:
            recommendations.append(f"リスト構造: 平均{list_item_stats['平均値']:.1f}項目の網羅性を目指す")
        else:
            recommendations.append("リスト構造: より詳細な項目立てで網羅性をアピール")

        result = {
            "分析対象記事数": total_articles,
            "動画コンテンツ分析": {
                "統計情報": video_stats,
                "採用率": f"{video_adoption_rate:.1f}% ({articles_with_video}/{total_articles}記事)",
                "戦略的評価": "高エンゲージメント戦略" if video_adoption_rate >= 50 else "動画活用で差別化のチャンス"
            },
            "テーブル活用分析": {
                "統計情報": table_stats,
                "採用率": f"{table_adoption_rate:.1f}% ({articles_with_tables}/{total_articles}記事)",
                "戦略的評価": "強調スニペット対策が標準" if table_adoption_rate >= 60 else "テーブル活用で検索結果向上の機会"
            },
            "リスト構造分析": {
                "統計情報": list_item_stats,
                "採用率": f"{list_adoption_rate:.1f}% ({articles_with_lists}/{total_articles}記事)",
                "戦略的評価": "網羅性重視が主流" if list_adoption_rate >= 70 else "リスト活用で読みやすさ向上の余地"
            },
            "競合戦略パターン": multimedia_strategies,
            "推奨マルチメディア戦略": recommendations,
            "戦略サマリー": f"マルチメディア分析完了: 動画{video_adoption_rate:.0f}%、テーブル{table_adoption_rate:.0f}%、リスト{list_adoption_rate:.0f}%の採用率",
            "summary_jp": f"マルチメディア分析完了: 動画{video_adoption_rate:.0f}%、テーブル{table_adoption_rate:.0f}%、リスト{list_adoption_rate:.0f}%の採用率"
        }
        
        self.analysis_results["multimedia_strategy"] = result
        print("マルチメディア戦略の分析が完了しました。")
        return result

    def analyze_eeat_factors(self) -> Dict[str, Any]:
        """
        E-E-A-T（Experience, Expertise, Authoritativeness, Trustworthiness）要因を分析する
        著者情報、外部リンク、公開日、構造化データなどから信頼性指標を評価
        """
        print("E-E-A-T要因の分析を開始します...")
        
        if not self.articles:
            return {
                "エラー": "分析対象の記事がありません。",
                "error": "No articles available for analysis."
            }

        total_articles = len(self.articles)
        
        # 1. Expertise & Authoritativeness（専門性・権威性）
        articles_with_author = sum(1 for article in self.articles if getattr(article, 'author_info', None))
        author_coverage_rate = (articles_with_author / total_articles) * 100
        
        # 2. Trustworthiness（信頼性）- 外部リンク分析
        external_link_counts = [getattr(article, 'external_link_count', 0) for article in self.articles]
        internal_link_counts = [getattr(article, 'internal_link_count', 0) for article in self.articles]
        
        external_link_stats = self._analyze_distribution(external_link_counts, "external_links")
        internal_link_stats = self._analyze_distribution(internal_link_counts, "internal_links")
        
        articles_with_external_links = sum(1 for count in external_link_counts if count > 0)
        external_link_adoption_rate = (articles_with_external_links / total_articles) * 100
        
        # 3. Experience & Freshness（経験・鮮度）
        articles_with_publish_date = sum(1 for article in self.articles if getattr(article, 'publish_date', None))
        articles_with_modified_date = sum(1 for article in self.articles if getattr(article, 'modified_date', None))
        
        publish_date_rate = (articles_with_publish_date / total_articles) * 100
        modified_date_rate = (articles_with_modified_date / total_articles) * 100
        
        # 4. Technical Trustworthiness（技術的信頼性）- 構造化データ
        articles_with_schema = sum(1 for article in self.articles 
                                 if getattr(article, 'schema_types', []))
        schema_adoption_rate = (articles_with_schema / total_articles) * 100
        
        # 構造化データの種類分析
        all_schema_types = []
        for article in self.articles:
            schema_types = getattr(article, 'schema_types', [])
            all_schema_types.extend(schema_types)
        
        schema_counter = Counter(all_schema_types)
        popular_schemas = schema_counter.most_common(5)
        
        # E-E-A-T総合スコア計算（簡易版）
        eeat_factors = {
            "著者情報明記": author_coverage_rate * 0.25,
            "外部リンク活用": min(external_link_adoption_rate, 80) * 0.20,  # 80%を上限
            "日付情報明記": max(publish_date_rate, modified_date_rate) * 0.15,
            "構造化データ活用": min(schema_adoption_rate, 90) * 0.20,  # 90%を上限
            "情報の参照性": min(external_link_stats['平均値'] * 10, 30) * 0.20  # 平均外部リンク数×10、30を上限
        }
        
        total_eeat_score = sum(eeat_factors.values())
        
        # 戦略的評価
        eeat_evaluation = []
        if author_coverage_rate >= 70:
            eeat_evaluation.append("著者情報の明記が標準的")
        elif author_coverage_rate >= 30:
            eeat_evaluation.append("著者情報の明記は部分的")
        else:
            eeat_evaluation.append("著者情報明記で大きく差別化可能")
            
        if external_link_adoption_rate >= 70:
            eeat_evaluation.append("外部リンクによる権威性アピールが一般的")
        elif external_link_adoption_rate >= 30:
            eeat_evaluation.append("外部リンク活用は中程度")
        else:
            eeat_evaluation.append("外部リンクで信頼性向上の機会大")
            
        if schema_adoption_rate >= 50:
            eeat_evaluation.append("構造化データ活用が進んでいる")
        else:
            eeat_evaluation.append("構造化データで技術的優位性を獲得可能")

        # 推奨施策
        recommendations = []
        
        if author_coverage_rate < 50:
            recommendations.append("著者情報の明記: 専門性をアピールして信頼性を向上")
        
        if external_link_stats['平均値'] < 3:
            recommendations.append("外部リンク強化: 信頼できる情報源への参照を3件以上追加")
        elif external_link_stats['平均値'] > 10:
            recommendations.append("外部リンク最適化: 過度なリンクは避け、厳選した参照に絞る")
            
        if publish_date_rate < 30:
            recommendations.append("日付情報明記: 公開日・更新日を明示して情報の鮮度をアピール")
            
        if schema_adoption_rate < 30:
            recommendations.append("構造化データ実装: Article, FAQ等のスキーマでリッチリザルト対策")

        result = {
            "分析対象記事数": total_articles,
            "専門性・権威性分析": {
                "著者情報明記率": f"{author_coverage_rate:.1f}% ({articles_with_author}/{total_articles}記事)",
                "著者情報一覧": [getattr(article, 'author_info', 'なし') for article in self.articles],
                "戦略的評価": "権威性アピールが標準" if author_coverage_rate >= 60 else "専門性アピールで差別化のチャンス"
            },
            "信頼性分析": {
                "外部リンク統計": external_link_stats,
                "外部リンク採用率": f"{external_link_adoption_rate:.1f}% ({articles_with_external_links}/{total_articles}記事)",
                "内部リンク統計": internal_link_stats,
                "戦略的評価": "参照による信頼性が確立" if external_link_adoption_rate >= 70 else "外部参照で信頼性向上の余地"
            },
            "鮮度・経験分析": {
                "公開日明記率": f"{publish_date_rate:.1f}% ({articles_with_publish_date}/{total_articles}記事)",
                "更新日明記率": f"{modified_date_rate:.1f}% ({articles_with_modified_date}/{total_articles}記事)",
                "戦略的評価": "情報鮮度の透明性が高い" if max(publish_date_rate, modified_date_rate) >= 50 else "日付明記で鮮度アピールの機会"
            },
            "技術的信頼性分析": {
                "構造化データ採用率": f"{schema_adoption_rate:.1f}% ({articles_with_schema}/{total_articles}記事)",
                "人気スキーマタイプ": [{"タイプ": schema, "使用回数": count} for schema, count in popular_schemas],
                "戦略的評価": "技術SEO対策が進んでいる" if schema_adoption_rate >= 40 else "構造化データで技術的優位性の機会"
            },
            "E-E-A-T総合評価": {
                "総合スコア": f"{total_eeat_score:.1f}/100",
                "要因別スコア": eeat_factors,
                "評価レベル": "優秀" if total_eeat_score >= 70 else "良好" if total_eeat_score >= 50 else "改善余地あり"
            },
            "競合E-E-A-T戦略": eeat_evaluation,
            "推奨E-E-A-T施策": recommendations,
            "戦略サマリー": f"E-E-A-T分析完了: 総合スコア{total_eeat_score:.0f}/100、著者明記{author_coverage_rate:.0f}%、外部リンク活用{external_link_adoption_rate:.0f}%",
            "summary_jp": f"E-E-A-T分析完了: 総合スコア{total_eeat_score:.0f}/100、著者明記{author_coverage_rate:.0f}%、外部リンク活用{external_link_adoption_rate:.0f}%"
        }
        
        self.analysis_results["eeat_factors"] = result
        print("E-E-A-T要因の分析が完了しました。")
        return result

