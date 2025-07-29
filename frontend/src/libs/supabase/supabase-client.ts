// Client-side Supabase client for browser use

import { Database } from '@/libs/supabase/types';
import { getEnvVar } from '@/utils/get-env-var';
import { createBrowserClient } from '@supabase/ssr';

// Create a single instance that can be reused across the app
export const supabase = createBrowserClient<Database>(
  getEnvVar(process.env.NEXT_PUBLIC_SUPABASE_URL, 'NEXT_PUBLIC_SUPABASE_URL'),
  getEnvVar(process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY, 'NEXT_PUBLIC_SUPABASE_ANON_KEY')
);

export default supabase;