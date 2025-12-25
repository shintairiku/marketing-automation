import { NextRequest, NextResponse } from 'next/server';

import { auth } from '@clerk/nextjs/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

export async function POST(request: NextRequest) {
  try {
    const { getToken } = await auth();
    const token = await getToken();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();
    if (process.env.NODE_ENV !== 'production') {
      console.info('Auto-generate proxy payload:', body);
    }

    const response = await fetch(`${BACKEND_URL}/companies/auto-generate`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      try {
        const errorData = JSON.parse(errorText);
        return NextResponse.json(errorData, { status: response.status });
      } catch {
        return NextResponse.json(
          { error: 'Backend returned non-JSON error', details: errorText },
          { status: response.status }
        );
      }
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Failed to auto-generate company data:', error);
    return NextResponse.json(
      { error: 'Failed to auto-generate company data' },
      { status: 500 }
    );
  }
}
