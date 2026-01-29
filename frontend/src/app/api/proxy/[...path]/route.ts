import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';

/**
 * バックエンドAPIへのプロキシ
 *
 * 注意: FastAPI はデフォルトで redirect_slashes=True のため、
 * /organizations → 307 → /organizations/ にリダイレクトする。
 * Node.js の fetch はリダイレクト時に Authorization ヘッダーを削除するため、
 * redirect: 'manual' で手動処理する。
 */

// 末尾スラッシュを付与して 307 リダイレクトを回避
function ensureTrailingSlash(path: string): string {
  if (path.endsWith('/') || path.includes('?') || path.includes('.')) return path;
  return `${path}/`;
}

// リダイレクト対応の fetch ラッパー
async function fetchWithRedirect(
  url: string,
  init: RequestInit & { headers: Record<string, string> }
): Promise<Response> {
  const response = await fetch(url, {
    ...init,
    redirect: 'manual', // リダイレクトを自動追従しない
  });

  // 307/308 リダイレクトの場合、ヘッダーを保持して再リクエスト
  if (response.status === 307 || response.status === 308 || response.status === 301 || response.status === 302) {
    const location = response.headers.get('location');
    if (location) {
      const redirectUrl = location.startsWith('http')
        ? location
        : `${API_BASE_URL}${location}`;
      console.log(`🔄 [PROXY] Redirect ${response.status} → ${redirectUrl}`);
      return fetch(redirectUrl, {
        ...init,
        redirect: 'manual',
      });
    }
  }

  return response;
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

// Authorization ヘッダーを含む共通ヘッダーを構築
function buildHeaders(request: NextRequest, includeContentType = true): Record<string, string> {
  const headers: Record<string, string> = {};
  if (includeContentType) {
    headers['Content-Type'] = 'application/json';
  }
  const authHeader = request.headers.get('Authorization');
  if (authHeader) {
    headers['Authorization'] = authHeader;
  }
  return headers;
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path: pathArray } = await params;
  const pathString = ensureTrailingSlash(pathArray.join('/'));
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${API_BASE_URL}/${pathString}${searchParams ? `?${searchParams}` : ''}`;
  const headers = buildHeaders(request);

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
  const pathString = ensureTrailingSlash(pathArray.join('/'));
  const url = `${API_BASE_URL}/${pathString}`;

  const contentType = request.headers.get('content-type');
  const isFormData = contentType?.includes('multipart/form-data');

  let body: BodyInit;
  const headers = buildHeaders(request, !isFormData);

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
  const pathString = ensureTrailingSlash(pathArray.join('/'));
  const url = `${API_BASE_URL}/${pathString}`;
  const body = await request.text();
  const headers = buildHeaders(request);

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
  const pathString = ensureTrailingSlash(pathArray.join('/'));
  const url = `${API_BASE_URL}/${pathString}`;
  const body = await request.text();
  const headers = buildHeaders(request);

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
  const pathString = ensureTrailingSlash(pathArray.join('/'));
  const url = `${API_BASE_URL}/${pathString}`;
  const headers = buildHeaders(request);

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
