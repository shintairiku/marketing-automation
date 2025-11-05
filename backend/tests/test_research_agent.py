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
from app.domains.seo_article.schemas import ThemeProposalData, ResearchReport
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
            print(f"\n📊 最終出力タイプ: {type(final_output)}")
            if isinstance(final_output, str):
                sanitized_output = final_output.strip()
                report_model = ResearchReport(
                    topic=context.selected_theme.title if context.selected_theme else None,
                    report_text=sanitized_output
                )
            elif isinstance(final_output, ResearchReport):
                report_model = final_output
            else:
                print("⚠️ 想定外の出力型です。")
                report_model = None
            
            if report_model:
                preview = report_model.report_text[:500]
                print(f"\n📝 レポート本文冒頭:\n{preview}")
                print(f"\n🎯 トピック: {report_model.topic}")
                print(f"\n📊 フィールドチェック:")
                for field in ['topic', 'report_text']:
                    value = getattr(report_model, field, None)
                    value_type = type(value).__name__
                    status = "存在" if value else "空または未設定"
                    print(f"  - {field}: {value_type} / {status}")
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
