#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notion統合の修正をテストするスクリプト
"""
import sys
from pathlib import Path
from app.infrastructure.analysis.cost_calculation_service import CostCalculationService

try:
    from app.infrastructure.external_apis.notion_service import NotionService as NotionSyncService
except ImportError:
    NotionSyncService = None

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_cost_calculation_service():
    """コスト計算サービスのテスト"""
    print("🧪 コスト計算サービスのテスト開始...")
    
    # 様々なモデルでテスト
    test_cases = [
        {"model_name": "gpt-4o", "prompt_tokens": 1000, "completion_tokens": 500, "cached_tokens": 200, "reasoning_tokens": 0},
        {"model_name": "gpt-4o-mini", "prompt_tokens": 1000, "completion_tokens": 500, "cached_tokens": 200, "reasoning_tokens": 0},
        {"model_name": "o1-preview", "prompt_tokens": 1000, "completion_tokens": 500, "cached_tokens": 200, "reasoning_tokens": 300},
        {"model_name": "gpt-4-turbo", "prompt_tokens": 1000, "completion_tokens": 500, "cached_tokens": 200, "reasoning_tokens": 0},
        {"model_name": "unknown-model", "prompt_tokens": 1000, "completion_tokens": 500, "cached_tokens": 200, "reasoning_tokens": 0},
    ]
    
    for case in test_cases:
        cost_info = CostCalculationService.calculate_cost(**case)
        print(f"📊 {case['model_name']}: ${cost_info['cost_breakdown']['total_cost_usd']:.6f}")
        print(f"   - 入力トークン: {case['prompt_tokens']:,} (コスト: ${cost_info['cost_breakdown']['input_cost_usd']:.6f})")
        print(f"   - 出力トークン: {case['completion_tokens']:,} (コスト: ${cost_info['cost_breakdown']['output_cost_usd']:.6f})")
        print(f"   - キャッシュトークン: {case['cached_tokens']:,} (コスト: ${cost_info['cost_breakdown']['cache_cost_usd']:.6f})")
        print(f"   - 推論トークン: {case['reasoning_tokens']:,} (コスト: ${cost_info['cost_breakdown']['reasoning_cost_usd']:.6f})")
        print(f"   - キャッシュ節約: ${cost_info['cost_savings']['cache_savings_usd']:.6f}")
        print()
    
    print("✅ コスト計算サービステスト完了")

def test_notion_sync_service():
    """Notion同期サービスのテスト"""
    print("🧪 Notion同期サービスのテスト開始...")
    
    try:
        sync_service = NotionSyncService()
        
        # 接続テスト
        print("1️⃣ Notion API接続テスト...")
        connection_success = sync_service.notion_service.test_connection()
        
        if connection_success:
            print("✅ Notion API接続成功")
            
            # 最新セッションの同期テスト
            print("2️⃣ 最新セッションの同期テスト...")
            synced_count = sync_service.sync_recent_sessions(hours=48)
            
            if synced_count > 0:
                print(f"✅ {synced_count} 件のセッションが同期されました")
            else:
                print("ℹ️  同期対象のセッションが見つかりませんでした")
                
        else:
            print("❌ Notion API接続失敗")
            
    except Exception as e:
        print(f"❌ Notion同期テストエラー: {e}")
        import traceback
        traceback.print_exc()

def main():
    """メインテスト関数"""
    print("🚀 Notion統合修正のテスト開始...")
    print("=" * 50)
    
    # コスト計算サービスのテスト
    test_cost_calculation_service()
    print("=" * 50)
    
    # Notion同期サービスのテスト
    test_notion_sync_service()
    print("=" * 50)
    
    print("✅ すべてのテストが完了しました！")

if __name__ == "__main__":
    main()