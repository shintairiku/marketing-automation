import { NextRequest, NextResponse } from 'next/server';

import { getCloudRunIdToken } from '@/lib/google-auth';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';

/**
 * バックエンドAPIへのプロキシ
 *
 * 注意:
 * - FastAPI は `redirect_slashes=True` のため、末尾スラッシュ差分で 307 が発生する。
 * - Node.js fetch の自動リダイレクトでは認証ヘッダー喪失のリスクがあるため、
 *   `redirect: 'manual'` で手動追従する。
 * - Cloud Run が返す Location が `http://*.run.app` の場合があるため、https に補正する。
 */

const REDIRECT_STATUS_CODES = new Set([301, 302, 303, 307, 308]);
const MAX_REDIRECT_HOPS = 3;

function normalizeRedirectUrl(location: string, baseUrl: string): string {
  const url = new URL(location, baseUrl);

  // Cloud Run は https 運用なので、http で返ってきたら強制的に https に補正
  if (url.hostname.endsWith('.run.app') && url.protocol === 'http:') {
    url.protocol = 'https:';
  }

  return url.toString();
}

// リダイレクト対応の fetch ラッパー
async function fetchWithRedirect(
  url: string,
  init: RequestInit & { headers: Record<string, string> }
): Promise<Response> {
  let currentUrl = url;

  for (let hop = 0; hop <= MAX_REDIRECT_HOPS; hop += 1) {
    const response = await fetch(currentUrl, {
      ...init,
      redirect: 'manual', // リダイレクトを自動追従しない
    });

    if (!REDIRECT_STATUS_CODES.has(response.status)) {
      return response;
    }

    // 3xx リダイレクトの場合、ヘッダーを保持して再リクエスト
    const location = response.headers.get('location');
    if (!location) {
      return response;
    }

    const redirectUrl = normalizeRedirectUrl(location, currentUrl);
    console.log(`🔄 [PROXY] Redirect ${response.status} → ${redirectUrl}`);
    currentUrl = redirectUrl;
  }

  // ループ上限到達時は最後のURLへ通常リクエストして結果を返す
  return fetch(currentUrl, {
    ...init,
    redirect: 'manual',
  });
}

// レスポンスを NextResponse に変換
async function toNextResponse(response: Response): Promise<NextResponse> {
  let data;
  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    try {
      data = await response.json();
    } catch {
      data = { error: 'Invalid JSON response' };
    }
  } else {
    const text = await response.text();
    try {
      data = JSON.parse(text);
    } catch {
      data = { error: text || 'Empty response' };
    }
  }

  return NextResponse.json(data, {
    status: response.status,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}

// Authorization + Cloud Run IAM ヘッダーを含む共通ヘッダーを構築
async function buildHeaders(request: NextRequest, includeContentType = true): Promise<Record<string, string>> {
  const headers: Record<string, string> = {};
  if (includeContentType) {
    headers['Content-Type'] = 'application/json';
  }
  const authHeader = request.headers.get('Authorization');
  if (authHeader) {
    headers['Authorization'] = authHeader;
  }

  // Cloud Run IAM 認証 (X-Serverless-Authorization)
  // Cloud Run がこのヘッダーで IAM を検証し、除去後に Authorization をそのまま転送する
  const idToken = await getCloudRunIdToken();
  if (idToken) {
    headers['X-Serverless-Authorization'] = `Bearer ${idToken}`;
  }

  return headers;
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path: pathArray } = await params;
  const pathString = pathArray.join('/');
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${API_BASE_URL}/${pathString}${searchParams ? `?${searchParams}` : ''}`;
  const headers = await buildHeaders(request);

  console.log(`📡 [PROXY-GET] ${url} | auth: ${headers['Authorization'] ? 'yes' : 'NO'}`);

  try {
    const response = await fetchWithRedirect(url, { method: 'GET', headers });
    return toNextResponse(response);
  } catch (error) {
    console.error('Proxy API error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch from backend API' },
      { status: 500 }
    );
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path: pathArray } = await params;
  const pathString = pathArray.join('/');
  const url = `${API_BASE_URL}/${pathString}`;

  const contentType = request.headers.get('content-type');
  const isFormData = contentType?.includes('multipart/form-data');

  let body: BodyInit;
  const headers = await buildHeaders(request, !isFormData);

  if (isFormData) {
    body = await request.formData();
  } else {
    body = await request.text();
  }

  console.log(`📡 [PROXY-POST] ${url} | auth: ${headers['Authorization'] ? 'yes' : 'NO'}`);

  try {
    const response = await fetchWithRedirect(url, { method: 'POST', headers, body });
    return toNextResponse(response);
  } catch (error) {
    console.error('Proxy API error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch from backend API' },
      { status: 500 }
    );
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path: pathArray } = await params;
  const pathString = pathArray.join('/');
  const url = `${API_BASE_URL}/${pathString}`;
  const body = await request.text();
  const headers = await buildHeaders(request);

  try {
    const response = await fetchWithRedirect(url, { method: 'PUT', headers, body });
    return toNextResponse(response);
  } catch (error) {
    console.error('Proxy API error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch from backend API' },
      { status: 500 }
    );
  }
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path: pathArray } = await params;
  const pathString = pathArray.join('/');
  const url = `${API_BASE_URL}/${pathString}`;
  const body = await request.text();
  const headers = await buildHeaders(request);

  try {
    const response = await fetchWithRedirect(url, { method: 'PATCH', headers, body });
    return toNextResponse(response);
  } catch (error) {
    console.error('Proxy API error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch from backend API' },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path: pathArray } = await params;
  const pathString = pathArray.join('/');
  const url = `${API_BASE_URL}/${pathString}`;
  const headers = await buildHeaders(request);

  try {
    const response = await fetchWithRedirect(url, { method: 'DELETE', headers });
    return toNextResponse(response);
  } catch (error) {
    console.error('Proxy API error:', error);
    return NextResponse.json(
      { error: 'Failed to fetch from backend API' },
      { status: 500 }
    );
  }
}

export async function OPTIONS() {
  return new Response(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    },
  });
}
