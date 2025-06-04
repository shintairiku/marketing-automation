# -*- coding: utf-8 -*-
"""
組織・チーム管理サービス
"""
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class OrganizationService:
    """組織管理のビジネスロジック"""
    
    def __init__(self):
        # Supabaseクライアントを直接初期化
        url = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # サービスロールキーを使用
        if not url or not key:
            raise ValueError("Supabase環境変数が設定されていません")
        self.supabase: Client = create_client(url, key)
    
    async def create_organization(
        self, 
        name: str, 
        slug: str,
        owner_user_id: str,
        max_seats: int = 2,
        billing_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """組織を作成"""
        try:
            # Clerkで組織が作成された後の処理として想定
            organization_data = {
                'id': f'org_{uuid.uuid4().hex[:24]}',  # Clerk組織IDの形式に合わせる
                'name': name,
                'slug': slug,
                'owner_user_id': owner_user_id,
                'max_seats': max_seats,
                'used_seats': 1,  # オーナー分
                'billing_email': billing_email or owner_user_id,  # 仮の値
                'subscription_status': 'inactive'
            }
            
            # 組織をデータベースに挿入
            org_response = self.supabase.table('organizations')\
                .insert(organization_data)\
                .execute()
            
            if not org_response.data:
                raise Exception("組織の作成に失敗しました")
            
            organization = org_response.data[0]
            
            # オーナーをメンバーシップテーブルに追加
            membership_data = {
                'id': f'mem_{uuid.uuid4().hex[:24]}',
                'organization_id': organization['id'],
                'user_id': owner_user_id,
                'role': 'owner',
                'status': 'active'
            }
            
            membership_response = self.supabase.table('organization_memberships')\
                .insert(membership_data)\
                .execute()
            
            if not membership_response.data:
                # 組織作成をロールバック
                self.supabase.table('organizations')\
                    .delete()\
                    .eq('id', organization['id'])\
                    .execute()
                raise Exception("メンバーシップの作成に失敗しました")
            
            # 組織設定のデフォルト値を作成
            settings_data = {
                'organization_id': organization['id'],
                'default_company_name': name,
                'default_company_description': f"{name}の記事生成プロジェクト"
            }
            
            self.supabase.table('organization_settings')\
                .insert(settings_data)\
                .execute()
            
            logger.info(f"組織を作成しました: {organization['id']} ({name})")
            return organization
            
        except Exception as e:
            logger.error(f"組織作成エラー: {e}")
            raise
    
    async def get_organization(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """組織情報を取得"""
        try:
            response = self.supabase.table('organizations')\
                .select('*, organization_settings(*)')\
                .eq('id', organization_id)\
                .single()\
                .execute()
            
            return response.data if response.data else None
            
        except Exception as e:
            logger.error(f"組織情報取得エラー: {e}")
            return None
    
    async def get_organization_members(self, organization_id: str) -> List[Dict[str, Any]]:
        """組織メンバー一覧を取得"""
        try:
            response = self.supabase.table('organization_memberships')\
                .select('*, users(id, full_name, avatar_url)')\
                .eq('organization_id', organization_id)\
                .eq('status', 'active')\
                .order('created_at')\
                .execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"組織メンバー取得エラー: {e}")
            return []
    
    
    async def accept_invitation(self, invitation_token: str, user_id: str) -> Dict[str, Any]:
        """招待を承諾"""
        try:
            # 招待情報を取得
            invitation_response = self.supabase.table('organization_invitations')\
                .select('*')\
                .eq('invitation_token', invitation_token)\
                .eq('status', 'pending')\
                .single()\
                .execute()
            
            if not invitation_response.data:
                raise Exception("無効または期限切れの招待です")
            
            invitation = invitation_response.data
            
            # 有効期限チェック
            expires_at = datetime.fromisoformat(invitation['expires_at'].replace('Z', '+00:00'))
            if datetime.now().replace(tzinfo=expires_at.tzinfo) > expires_at:
                raise Exception("招待の有効期限が切れています")
            
            # 組織のシート制限をチェック
            org = await self.get_organization(invitation['organization_id'])
            if not org:
                raise Exception("組織が見つかりません")
            
            if org['used_seats'] >= org['max_seats']:
                raise Exception("組織のシート上限に達しています")
            
            # メンバーシップを作成
            membership_data = {
                'id': f'mem_{uuid.uuid4().hex[:24]}',
                'organization_id': invitation['organization_id'],
                'user_id': user_id,
                'role': invitation['role'],
                'status': 'active',
                'invited_by': invitation['invited_by']
            }
            
            membership_response = self.supabase.table('organization_memberships')\
                .insert(membership_data)\
                .execute()
            
            if not membership_response.data:
                raise Exception("メンバーシップの作成に失敗しました")
            
            # 招待ステータスを更新
            self.supabase.table('organization_invitations')\
                .update({'status': 'accepted', 'accepted_at': datetime.now().isoformat()})\
                .eq('id', invitation['id'])\
                .execute()
            
            logger.info(f"招待を承諾しました: {user_id} -> {invitation['organization_id']}")
            return membership_response.data[0]
            
        except Exception as e:
            logger.error(f"招待承諾エラー: {e}")
            raise
    
    
    
    async def _get_organization_owner(self, organization_id: str) -> Optional[str]:
        """組織のオーナーユーザーIDを取得"""
        try:
            response = self.supabase.table('organizations')\
                .select('owner_user_id')\
                .eq('id', organization_id)\
                .single()\
                .execute()
            
            return response.data['owner_user_id'] if response.data else None
            
        except Exception as e:
            logger.error(f"組織オーナー取得エラー: {e}")
            return None
    
    async def get_organization_usage(self, organization_id: str, period_start: datetime, period_end: datetime) -> Dict[str, Any]:
        """組織の使用量を取得"""
        try:
            # 期間内の使用量を集計
            response = self.supabase.table('usage_tracking')\
                .select('resource_type, usage_count')\
                .eq('organization_id', organization_id)\
                .gte('billing_period_start', period_start.date().isoformat())\
                .lte('billing_period_end', period_end.date().isoformat())\
                .execute()
            
            # リソースタイプ別に集計
            usage_summary = {}
            for record in response.data:
                resource_type = record['resource_type']
                if resource_type not in usage_summary:
                    usage_summary[resource_type] = 0
                usage_summary[resource_type] += record['usage_count']
            
            return {
                'organization_id': organization_id,
                'period_start': period_start.isoformat(),
                'period_end': period_end.isoformat(),
                'usage': usage_summary
            }
            
        except Exception as e:
            logger.error(f"使用量取得エラー: {e}")
            raise
    
    async def get_pending_invitations(self, organization_id: str) -> List[Dict[str, Any]]:
        """組織の未承諾招待一覧を取得"""
        try:
            response = self.supabase.table('organization_invitations')\
                .select('*')\
                .eq('organization_id', organization_id)\
                .eq('status', 'pending')\
                .order('created_at', desc=True)\
                .execute()
            
            return response.data or []
            
        except Exception as e:
            logger.error(f"招待一覧取得エラー: {e}")
            return []
    
    async def get_member_usage(self, organization_id: str) -> List[Dict[str, Any]]:
        """メンバーの使用量情報を取得"""
        try:
            # 現在の月の使用量を取得
            current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # 組織のメンバー一覧を取得
            members_response = self.supabase.table('organization_memberships')\
                .select('user_id, users(email, full_name)')\
                .eq('organization_id', organization_id)\
                .eq('status', 'active')\
                .execute()
            
            member_usage = []
            for member in members_response.data or []:
                # メンバーの記事生成数を取得
                usage_response = self.supabase.table('usage_tracking')\
                    .select('usage_count')\
                    .eq('organization_id', organization_id)\
                    .eq('user_id', member['user_id'])\
                    .eq('resource_type', 'article_generation')\
                    .gte('created_at', current_month_start.isoformat())\
                    .execute()
                
                total_articles = sum(record['usage_count'] for record in usage_response.data or [])
                
                member_usage.append({
                    'user_id': member['user_id'],
                    'email': member['users']['email'] if member['users'] else 'unknown',
                    'name': member['users']['full_name'] if member['users'] else None,
                    'articles_generated': total_articles
                })
            
            return member_usage
            
        except Exception as e:
            logger.error(f"メンバー使用量取得エラー: {e}")
            return []
    
    async def cancel_invitation(self, invitation_id: str, organization_id: str) -> bool:
        """招待をキャンセル"""
        try:
            response = self.supabase.table('organization_invitations')\
                .update({'status': 'cancelled'})\
                .eq('id', invitation_id)\
                .eq('organization_id', organization_id)\
                .eq('status', 'pending')\
                .execute()
            
            if not response.data:
                raise ValueError("招待が見つからないか、既に処理済みです")
            
            logger.info(f"招待をキャンセルしました: {invitation_id}")
            return True
            
        except Exception as e:
            logger.error(f"招待キャンセルエラー: {e}")
            raise
    
    async def remove_member(self, member_id: str, organization_id: str) -> bool:
        """組織からメンバーを削除"""
        try:
            # メンバーシップを削除
            response = self.supabase.table('organization_memberships')\
                .delete()\
                .eq('id', member_id)\
                .eq('organization_id', organization_id)\
                .execute()
            
            if not response.data:
                raise ValueError("メンバーが見つかりません")
            
            logger.info(f"メンバーを削除しました: {member_id} from {organization_id}")
            return True
            
        except Exception as e:
            logger.error(f"メンバー削除エラー: {e}")
            raise
    
    async def update_seat_count(self, organization_id: str, new_max_seats: int) -> Dict[str, Any]:
        """シート数を更新"""
        try:
            # 現在の組織情報を取得
            org = await self.get_organization(organization_id)
            if not org:
                raise ValueError("組織が見つかりません")
            
            if new_max_seats < org['used_seats']:
                raise ValueError(f"使用中のシート数({org['used_seats']})より少なく設定できません")
            
            # 最小シート数チェック
            if new_max_seats < 2:
                raise ValueError("Teamプランは最低2シートが必要です")
            
            # シート数を更新
            response = self.supabase.table('organizations')\
                .update({'max_seats': new_max_seats})\
                .eq('id', organization_id)\
                .execute()
            
            if not response.data:
                raise ValueError("シート数の更新に失敗しました")
            
            logger.info(f"シート数を更新しました: {organization_id} -> {new_max_seats}")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"シート数更新エラー: {e}")
            raise

    async def invite_member(self, organization_id: str, email: str, role: str = 'member', invited_by: str = None) -> Dict[str, Any]:
        """メンバーを招待（API用の簡易版）"""
        try:
            # 組織情報を取得してシート制限をチェック
            org = await self.get_organization(organization_id)
            if not org:
                raise ValueError("組織が見つかりません")
            
            if org['used_seats'] >= org['max_seats']:
                raise ValueError(f"シート上限に達しています ({org['used_seats']}/{org['max_seats']})")
            
            # 既存の招待をチェック
            existing_invite = self.supabase.table('organization_invitations')\
                .select('*')\
                .eq('organization_id', organization_id)\
                .eq('email', email)\
                .eq('status', 'pending')\
                .execute()
            
            if existing_invite.data:
                raise ValueError("このメールアドレスは既に招待済みです")
            
            # 招待トークン生成
            invitation_token = uuid.uuid4().hex
            
            # 招待レコード作成
            invitation_data = {
                'id': f'inv_{uuid.uuid4().hex[:24]}',
                'organization_id': organization_id,
                'email': email,
                'role': role,
                'invited_by': invited_by,
                'invitation_token': invitation_token,
                'expires_at': (datetime.now() + timedelta(days=7)).isoformat(),
                'status': 'pending'
            }
            
            response = self.supabase.table('organization_invitations')\
                .insert(invitation_data)\
                .execute()
            
            if not response.data:
                raise ValueError("招待の作成に失敗しました")
            
            logger.info(f"メンバーを招待しました: {email} -> {organization_id}")
            return response.data[0]
            
        except Exception as e:
            logger.error(f"メンバー招待エラー: {e}")
            raise