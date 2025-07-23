#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notion同期システムのテストスクリプト
"""
import sys
import os
from app.infrastructure.external_apis.notion_service import NotionSyncService

# パスを追加（services/を正しくインポートするため）
sys.path.append('.')

# 環境変数をチェック
def check_environment():
    """必要な環境変数がセットされているかチェック"""
    required_vars = [
        'NOTION_API_KEY',
        'NOTION_DATABASE_ID',
        'SUPABASE_URL',
        'SUPABASE_SERVICE_ROLE_KEY'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ 以下の環境変数が設定されていません: {', '.join(missing_vars)}")
        print("   .env ファイルに必要な設定を追加してください。")
        return False
    
    print("✅ 必要な環境変数がすべて設定されています")
    return True

def main():
    """メイン関数"""
    print("🚀 Notion同期システムのテストを実行します")
    print("=" * 60)
    
    # 環境変数チェック
    if not check_environment():
        return
    
    try:
        # NotionSyncServiceの初期化
        sync_service = NotionSyncService()
        
        # テスト実行
        success = sync_service.test_sync()
        
        if success:
            print("\n" + "=" * 60)
            print("🎉 Notion同期システムのテストが成功しました！")
            print("\n📋 利用可能な機能:")
            print("   ✓ 単一セッションの同期")
            print("   ✓ 最新セッションの一括同期") 
            print("   ✓ LLM呼び出し詳細の記録")
            print("   ✓ トークン使用量とコストの計算")
            print("   ✓ パフォーマンス統計の表示")
            
            print("\n🔄 手動同期のテスト")
            # 最新24時間のセッションを同期
            synced_count = sync_service.sync_recent_sessions(hours=24)
            print(f"📊 合計 {synced_count} セッションが同期されました")
        else:
            print("\n❌ テストに失敗しました")
            
    except Exception as e:
        print(f"\n❌ テスト実行中にエラーが発生しました: {e}")
        import traceback
        print(f"エラー詳細:\n{traceback.format_exc()}")

if __name__ == "__main__":
    main()