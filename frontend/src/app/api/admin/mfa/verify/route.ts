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

    const response = await backendFetch('/admin/mfa/verify', token, {
      method: 'POST',
      body: JSON.stringify({ code: body.code }),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    if (data.success) {
      // 成功: MFA セッションクッキーを設定
      const mfaToken = await createMfaSessionToken(userId);
      const cookieOptions = getMfaCookieOptions();

      const res = NextResponse.json(data, { status: 200 });
      res.cookies.set('admin_mfa_session', mfaToken, cookieOptions);
      return res;
    }

    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    console.error('Failed to verify MFA:', error);
    return NextResponse.json(
      { error: 'Failed to verify MFA' },
      { status: 500 }
    );
  }
}
