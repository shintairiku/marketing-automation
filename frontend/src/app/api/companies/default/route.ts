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

    const response = await backendFetch('/companies/default', token);

    if (!response.ok) {
      const errorData = await response.json();
      return NextResponse.json(errorData, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Failed to fetch default company:', error);
    return NextResponse.json(
      { error: 'Failed to fetch default company' },
      { status: 500 }
    );
  }
}
