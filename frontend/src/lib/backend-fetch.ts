/**
 * バックエンド API 呼び出しの共通ヘルパー
 *
 * Clerk JWT (Authorization) と Google ID Token (X-Serverless-Authorization) の
 * 両ヘッダーを付与して Cloud Run バックエンドにリクエストを送信する。
 */
import { getCloudRunIdToken } from './google-auth';

const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';

/**
 * バックエンドにリクエストを送信する。
 *
 * @param path - バックエンドのパス (例: "/companies", "/admin/users")
 * @param clerkToken - Clerk JWT トークン
 * @param init - fetch のオプション (method, body, etc.)
 * @returns fetch の Response
 */
export async function backendFetch(
  path: string,
  clerkToken: string,
  init: RequestInit = {}
): Promise<Response> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${clerkToken}`,
    ...(init.headers as Record<string, string>),
  };

  // Cloud Run IAM 認証 (本番環境のみ)
  const idToken = await getCloudRunIdToken();
  if (idToken) {
    headers['X-Serverless-Authorization'] = `Bearer ${idToken}`;
  }

  const url = `${BACKEND_URL}${path}`;
  return fetch(url, {
    ...init,
    headers,
  });
}
