import { NextResponse } from 'next/server';

import { backendFetch } from '@/lib/backend-fetch';
import { auth } from '@clerk/nextjs/server';

export async function POST() {
  try {
    const { getToken } = await auth();
    const token = await getToken();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const response = await backendFetch('/admin/mfa/setup/init', token, {
      method: 'POST',
    });

    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Failed to init MFA setup:', error);
    return NextResponse.json(
      { error: 'Failed to init MFA setup' },
      { status: 500 }
    );
  }
}
