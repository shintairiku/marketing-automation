import { NextResponse } from 'next/server';

import { auth } from '@clerk/nextjs/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';

export async function GET() {
  try {
    const { getToken } = await auth();
    const token = await getToken();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const response = await fetch(`${BACKEND_URL}/admin/users`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    const bodyText = await response.text();
    let data: unknown = null;

    if (bodyText) {
      try {
        data = JSON.parse(bodyText);
      } catch (parseError) {
        console.error('Failed to parse admin users response:', parseError);
        return NextResponse.json(
          { error: 'Invalid JSON from backend', details: bodyText },
          { status: response.status }
        );
      }
    }

    return NextResponse.json(data ?? {}, { status: response.status });
  } catch (error) {
    console.error('Failed to fetch admin users:', error);
    return NextResponse.json(
      { error: 'Failed to fetch admin users' },
      { status: 500 }
    );
  }
}
