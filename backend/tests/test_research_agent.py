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
            print(f"\n📊 最終出力タイプ: {type(final_output)}")
            print(f"📊 出力の属性: {[attr for attr in dir(final_output) if not attr.startswith('_')]}")
            
            if hasattr(final_output, 'summary'):
                print(f"\n📝 レポート概要:")
                print(f"{final_output.summary[:500]}")
            else:
                print("❌ summary属性が見つかりません")
                
            if hasattr(final_output, 'queries_used'):
                print(f"\n🔍 使用されたクエリ ({len(final_output.queries_used)} 件):")
                for i, query in enumerate(final_output.queries_used[:5], 1):
                    print(f"   {i}. {query}")
            else:
                print("❌ queries_used属性が見つかりません")
                
            if hasattr(final_output, 'key_findings'):
                print(f"\n📚 主要な発見事項 ({len(final_output.key_findings)} 件):")
                for i, finding in enumerate(final_output.key_findings[:3], 1):
                    finding_str = str(finding)[:150] if finding else "N/A"
                    print(f"   {i}. {finding_str}")
            else:
                print("❌ key_findings属性が見つかりません")
                
            # ResearchReportDataの実際のフィールドを確認
            print(f"\n📋 ResearchReportDataの実際の内容:")
            
            if hasattr(final_output, 'overall_summary') and final_output.overall_summary:
                print(f"\n📝 全体要約:")
                print(f"{final_output.overall_summary[:500]}")
            
            if hasattr(final_output, 'topic') and final_output.topic:
                print(f"\n🎯 トピック: {final_output.topic}")
            
            if hasattr(final_output, 'key_points') and final_output.key_points:
                print(f"\n📚 重要ポイント ({len(final_output.key_points)} 件):")
                for i, point in enumerate(final_output.key_points[:3], 1):
                    print(f"   {i}. {str(point)[:150]}")
            
            if hasattr(final_output, 'interesting_angles') and final_output.interesting_angles:
                print(f"\n💡 興味深い視点 ({len(final_output.interesting_angles)} 件):")
                for i, angle in enumerate(final_output.interesting_angles[:3], 1):
                    print(f"   {i}. {str(angle)[:150]}")
            
            if hasattr(final_output, 'all_sources') and final_output.all_sources:
                print(f"\n🔗 情報源 ({len(final_output.all_sources)} 件):")
                for i, source in enumerate(final_output.all_sources[:3], 1):
                    print(f"   {i}. {str(source)[:100]}")
            
            # 全フィールドの状態確認
            print(f"\n📊 全フィールドの状態:")
            for field in ['topic', 'overall_summary', 'key_points', 'interesting_angles', 'all_sources']:
                value = getattr(final_output, field, None)
                if value:
                    value_type = type(value).__name__
                    if isinstance(value, list):
                        print(f"  ✓ {field}: {value_type} ({len(value)} 件)")
                    else:
                        print(f"  ✓ {field}: {value_type} - 存在")
                else:
                    print(f"  ✗ {field}: 空または未設定")
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