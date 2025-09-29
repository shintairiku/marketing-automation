#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
統合リサーチエージェントのテストスクリプト
"""
import asyncio
import sys
import os
from pathlib import Path

# バックエンドのパスを追加
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.domains.seo_article.agents.definitions import research_agent
from app.domains.seo_article.context import ArticleContext
from app.domains.seo_article.schemas import ThemeProposalData
from agents import RunContextWrapper, Runner, RunConfig

async def test_research_agent():
    """統合リサーチエージェントをテスト"""
    print("🧪 統合リサーチエージェントのテストを開始...")
    
    # テスト用のコンテキストを作成
    context = ArticleContext()
    context.initial_keywords = ["Python", "プログラミング", "初心者"]
    context.selected_theme = ThemeProposalData(
        title="Python初心者向けプログラミング学習ガイド",
        description="プログラミング初心者がPythonを効率的に学習するための完全ガイド",
        keywords=["Python", "プログラミング", "初心者", "学習"]
    )
    # ペルソナを設定
    context.selected_detailed_persona = "プログラミング未経験の20代会社員。論理的思考は得意だが、技術的な専門用語は理解しづらい。効率的で実践的な学習方法を求めている。"
    
    # エージェント実行
    try:
        print("📊 リサーチエージェントを実行中...")
        
        # 入力データを準備
        input_data = "Python初心者向けの学習ガイドについてリサーチしてください。"
        
        # RunConfigを設定
        run_config = RunConfig()
        
        result = await Runner.run(
            starting_agent=research_agent,
            input=input_data,
            context=context,
            run_config=run_config,
            max_turns=10
        )
        
        print("✅ リサーチが完了しました!")
        print(f"📝 結果タイプ: {type(result)}")
        print(f"📝 結果属性: {dir(result)}")
        
        # final_outputがあれば表示
        if hasattr(result, 'final_output') and result.final_output:
            final_output = result.final_output
            print(f"📊 最終出力タイプ: {type(final_output)}")
            if hasattr(final_output, 'summary'):
                print(f"📝 レポート概要: {final_output.summary[:200]}...")
            if hasattr(final_output, 'queries_used'):
                print(f"🔍 検索クエリ数: {len(final_output.queries_used)}")
            if hasattr(final_output, 'key_findings'):
                print(f"📚 収集した情報数: {len(final_output.key_findings)}")
        else:
            print("📝 final_output が見つかりません")
        
        return True
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        print(f"エラータイプ: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_research_agent())
    if success:
        print("\n🎉 統合リサーチエージェントのテストが成功しました！")
    else:
        print("\n💥 テストに失敗しました。")
    exit(0 if success else 1)