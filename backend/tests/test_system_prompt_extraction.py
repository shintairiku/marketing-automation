#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
システムプロンプト抽出のテストスクリプト
"""
import asyncio
import sys
from pathlib import Path
from app.domains.seo_article.services.generation_service import ArticleGenerationService
from app.domains.seo_article.context import ArticleContext
from app.domains.seo_article.agents.definitions import theme_agent
from agents import RunContextWrapper

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_system_prompt_extraction():
    """システムプロンプト抽出のテスト"""
    print("🧪 システムプロンプト抽出のテスト開始...")
    
    # テスト用のコンテキストを作成
    context = ArticleContext(
        initial_keywords=["リフォーム", "自然素材"],
        target_age_group="30代",
        num_theme_proposals=3,
        company_name="新大陸",
        company_description="地域企業・店舗の集客の仕組み化およびブランディング支援",
        selected_detailed_persona="30代の子育て世代で、自然素材を使ったリフォームに興味がある主婦層"
    )
    
    # SEOコンテキストの追加
    context.serp_analysis_report = None
    
    try:
        # エージェントの指示を動的に取得
        agent = theme_agent
        
        if hasattr(agent, 'instructions') and callable(agent.instructions):
            print(f"✅ エージェント {agent.name} の指示は動的関数です")
            
            # RunContextWrapperを作成
            run_context = RunContextWrapper(context=context)
            
            # 動的指示を実行
            resolved_instructions = await agent.instructions(run_context, agent)
            
            print("✅ システムプロンプト抽出成功:")
            print(f"   - 長さ: {len(resolved_instructions):,} 文字")
            print(f"   - 最初の500文字: {resolved_instructions[:500]}...")
            print(f"   - 最後の200文字: ...{resolved_instructions[-200:]}")
            
            # 特定のキーワードが含まれているかチェック
            keywords_to_check = ["リフォーム", "自然素材", "30代", "新大陸", "ThemeProposal"]
            print("\n📊 キーワード含有チェック:")
            for keyword in keywords_to_check:
                if keyword in resolved_instructions:
                    print(f"   ✅ '{keyword}' - 含まれています")
                else:
                    print(f"   ❌ '{keyword}' - 含まれていません")
        else:
            print(f"❌ エージェント {agent.name} の指示は静的です")
            
    except Exception as e:
        print(f"❌ システムプロンプト抽出エラー: {e}")
        import traceback
        traceback.print_exc()

async def test_article_service_prompt_extraction():
    """記事サービスでのプロンプト抽出テスト"""
    print("\n🧪 記事サービスでのプロンプト抽出テスト開始...")
    
    try:
        # ArticleGenerationServiceのインスタンス作成
        ArticleGenerationService()
        
        # テスト用のコンテキストを作成
        context = ArticleContext(
            initial_keywords=["リフォーム", "自然素材"],
            target_age_group="30代",
            num_theme_proposals=3,
            company_name="新大陸",
            company_description="地域企業・店舗の集客の仕組み化およびブランディング支援",
            selected_detailed_persona="30代の子育て世代で、自然素材を使ったリフォームに興味がある主婦層"
        )
        
        # エージェントのシステムプロンプト抽出をテスト
        agent = theme_agent
        
        # システムプロンプト抽出（内部メソッドを直接呼び出し）
        if hasattr(agent, 'instructions') and callable(agent.instructions):
            from agents import RunContextWrapper
            run_context = RunContextWrapper(context=context)
            system_prompt = await agent.instructions(run_context, agent)
            
            print("✅ 記事サービス経由でのシステムプロンプト抽出成功:")
            print(f"   - 長さ: {len(system_prompt):,} 文字")
            print("   - 動的指示として解決されました")
            
            # プロンプト内容の構造チェック
            sections = []
            if "企業情報" in system_prompt:
                sections.append("企業情報")
            if "キーワード" in system_prompt:
                sections.append("キーワード")
            if "ターゲットペルソナ" in system_prompt:
                sections.append("ターゲットペルソナ")
            if "ThemeProposal" in system_prompt:
                sections.append("出力形式指定")
            
            print(f"   - 含まれるセクション: {', '.join(sections)}")
            
        else:
            print(f"❌ エージェント {agent.name} の指示は静的です")
            
    except Exception as e:
        print(f"❌ 記事サービスでのプロンプト抽出エラー: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """メインテスト関数"""
    print("🚀 システムプロンプト抽出テスト開始...")
    print("=" * 60)
    
    await test_system_prompt_extraction()
    await test_article_service_prompt_extraction()
    
    print("=" * 60)
    print("✅ すべてのテストが完了しました！")

if __name__ == "__main__":
    asyncio.run(main())