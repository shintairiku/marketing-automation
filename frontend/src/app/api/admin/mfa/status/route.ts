import { NextResponse } from 'next/server';

import { backendFetch } from '@/lib/backend-fetch';
import { auth } from '@clerk/nextjs/server';

export async function GET() {
  try {
    const { getToken } = await auth();
    const token = await getToken();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const response = await backendFetch('/admin/mfa/status', token);
    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Failed to fetch MFA status:', error);
    return NextResponse.json(
      { error: 'Failed to fetch MFA status' },
      { status: 500 }
    );
  }
}
