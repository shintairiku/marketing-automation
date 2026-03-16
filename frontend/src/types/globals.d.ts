/**
 * Clerk カスタムセッションクレーム型定義
 *
 * Clerk Dashboard の Sessions → Customize session token で以下を設定:
 * {
 *   "role": "authenticated",
 *   "metadata": "{{user.public_metadata}}",
 *   "twoFactorEnabled": "{{user.two_factor_enabled}}"
 * }
 *
 * - role: Supabase RLS 用 ("authenticated" 固定、削除禁止)
 * - metadata: RBAC 用 (publicMetadata.role = "admin" | "privileged")
 * - twoFactorEnabled: 管理者ページの MFA 強制チェック用
 */
export {};

declare global {
  interface CustomJwtSessionClaims {
    metadata?: {
      role?: 'admin' | 'privileged';
    };
    twoFactorEnabled?: boolean;
  }
}
