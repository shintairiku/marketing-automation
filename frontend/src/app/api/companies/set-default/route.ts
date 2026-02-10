import { NextRequest, NextResponse } from 'next/server';

import { backendFetch } from '@/lib/backend-fetch';
import { auth } from '@clerk/nextjs/server';

export async function POST(request: NextRequest) {
  try {
    const { getToken } = await auth();
    const token = await getToken();

    if (!token) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const body = await request.json();

    const response = await backendFetch('/companies/set-default', token, {
      method: 'POST',
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(errorData, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Failed to set default company:', error);
    return NextResponse.json(
      { error: 'Failed to set default company' },
      { status: 500 }
    );
  }
}
