import { NextResponse } from 'next/server';

import {
  createMfaSessionToken,
  getMfaCookieOptions,
} from '@/lib/admin-mfa';
import { backendFetch } from '@/lib/backend-fetch';
import { auth } from '@clerk/nextjs/server';

export async function POST(request: Request) {
  try {
    const { getToken, userId } = await auth();
    const token = await getToken();

    if (!token || !userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();

    const response = await backendFetch('/admin/mfa/setup/confirm', token, {
      method: 'POST',
      body: JSON.stringify({ code: body.code }),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    // 成功: MFA セッションクッキーを設定
    const mfaToken = await createMfaSessionToken(userId);
    const cookieOptions = getMfaCookieOptions();

    const res = NextResponse.json(data, { status: 200 });
    res.cookies.set('admin_mfa_session', mfaToken, cookieOptions);
    // ヒントクッキー (HttpOnly ではない、middleware で読み取る用)
    res.cookies.set('admin_totp_configured', 'true', {
      ...cookieOptions,
      httpOnly: false,
      maxAge: 60 * 60 * 24 * 365, // 1 year
    });

    return res;
  } catch (error) {
    console.error('Failed to confirm MFA setup:', error);
    return NextResponse.json(
      { error: 'Failed to confirm MFA setup' },
      { status: 500 }
    );
  }
}
