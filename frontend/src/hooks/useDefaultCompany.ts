import { useEffect,useState } from 'react';
import { toast } from 'sonner';

export interface CompanyInfo {
  id: string;
  name: string;
  website_url: string;
  description: string;
  usp: string;
  target_persona: string;
  is_default: boolean;
  brand_slogan?: string;
  target_keywords?: string;
  industry_terms?: string;
  avoid_terms?: string;
  popular_articles?: string;
  target_area?: string;
  created_at: string;
  updated_at: string;
}

export function useDefaultCompany() {
  const [company, setCompany] = useState<CompanyInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDefaultCompany = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/companies/default');
      
      if (response.status === 404) {
        // No default company set - this is normal for first-time users
        setCompany(null);
        return;
      }
      
      if (!response.ok) {
        throw new Error('デフォルト会社情報の取得に失敗しました');
      }
      
      const data = await response.json();
      setCompany(data);
    } catch (error) {
      console.error('Error fetching default company:', error);
      setError(error instanceof Error ? error.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDefaultCompany();
  }, []);

  const refreshCompany = () => {
    fetchDefaultCompany();
  };

  return {
    company,
    loading,
    error,
    refreshCompany,
    hasCompany: !!company,
  };
}