/**
 * Clerk カスタムセッションクレーム型定義
 *
 * Clerk Dashboard の Sessions → Customize session token で以下を設定:
 * {
 *   "metadata": "{{user.public_metadata}}"
 * }
 *
 * これにより sessionClaims.metadata に publicMetadata が含まれる。
 * role: "admin" | "privileged" | undefined
 */
export {};

declare global {
  interface CustomJwtSessionClaims {
    metadata?: {
      role?: 'admin' | 'privileged';
    };
  }
}
