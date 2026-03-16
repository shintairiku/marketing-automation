import { NextResponse } from 'next/server';

import { backendFetch } from '@/lib/backend-fetch';
import { auth } from '@clerk/nextjs/server';

export async function POST(request: Request) {
  try {
    const { getToken } = await auth();
    const token = await getToken();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    const { targetUserId } = body;

    if (!targetUserId) {
      return NextResponse.json(
        { error: 'targetUserId is required' },
        { status: 400 }
      );
    }

    const response = await backendFetch(
      `/admin/mfa/reset/${targetUserId}`,
      token,
      { method: 'POST' }
    );

    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Failed to reset MFA:', error);
    return NextResponse.json(
      { error: 'Failed to reset MFA' },
      { status: 500 }
    );
  }
}
