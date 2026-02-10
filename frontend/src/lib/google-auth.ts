/**
 * Google Cloud Run IAM認証用 ID Token 生成ユーティリティ
 *
 * Cloud Run を --no-allow-unauthenticated で保護し、
 * Vercel サーバーサイドからのみアクセスを許可する。
 *
 * X-Serverless-Authorization ヘッダーに ID Token を設定すると、
 * Cloud Run が IAM 検証後にこのヘッダーを除去し、
 * Authorization ヘッダー (Clerk JWT) はそのままコンテナに転送される。
 */
import { GoogleAuth, IdTokenClient } from 'google-auth-library';

const CLOUD_RUN_AUDIENCE_URL = process.env.CLOUD_RUN_AUDIENCE_URL;
const SA_KEY_BASE64 = process.env.GOOGLE_SA_KEY_BASE64;

// モジュールスコープでキャッシュ (Vercel warm invocation 間で再利用)
let _auth: GoogleAuth | null = null;
let _clientPromise: Promise<IdTokenClient> | null = null;

function getAuth(): GoogleAuth {
  if (!_auth) {
    if (SA_KEY_BASE64) {
      const json = Buffer.from(SA_KEY_BASE64, 'base64').toString();
      _auth = new GoogleAuth({ credentials: JSON.parse(json) });
    } else {
      throw new Error(
        'GOOGLE_SA_KEY_BASE64 is not set. Cannot generate Cloud Run ID token.'
      );
    }
  }
  return _auth;
}

/**
 * Cloud Run 用の Google ID Token を取得する。
 *
 * - CLOUD_RUN_AUDIENCE_URL 未設定 (開発環境): null を返す
 * - 設定済み (本番環境): ID Token 文字列を返す
 * - トークンは google-auth-library が自動キャッシュ (~1時間有効)
 */
export async function getCloudRunIdToken(): Promise<string | null> {
  if (!CLOUD_RUN_AUDIENCE_URL) {
    return null;
  }

  if (!_clientPromise) {
    _clientPromise = getAuth().getIdTokenClient(CLOUD_RUN_AUDIENCE_URL);
  }

  const client = await _clientPromise;
  return client.idTokenProvider.fetchIdToken(CLOUD_RUN_AUDIENCE_URL);
}
