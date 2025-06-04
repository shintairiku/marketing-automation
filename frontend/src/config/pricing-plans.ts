/**
 * 料金プラン定義
 * 個人プランとTeamプランの設定
 */

export interface PlanFeatures {
  articles: number;
  support: 'community' | 'email' | 'priority';
  features: string[];
}

export interface IndividualPlan {
  name: string;
  price: number;
  priceId: string | null;
  features: PlanFeatures;
  popular?: boolean;
}

export interface TeamPlan {
  name: string;
  pricePerSeat: number;
  priceId: string;
  minSeats: number;
  maxSeats?: number;
  features: PlanFeatures & {
    articlesPerSeat: number;
  };
}

export const PRICING_PLANS = {
  individual: {
    free: {
      name: 'Free',
      price: 0,
      priceId: null,
      features: {
        articles: 5,
        support: 'community' as const,
        features: [
          '記事生成 5件/月',
          'コミュニティサポート',
          '基本SEO分析',
          'テンプレート利用'
        ]
      }
    },
    basic: {
      name: 'Basic',
      price: 1500,
      priceId: process.env.NEXT_PUBLIC_STRIPE_PRICE_INDIVIDUAL_BASIC || '',
      popular: true,
      features: {
        articles: 30,
        support: 'email' as const,
        features: [
          '記事生成 30件/月',
          'メールサポート',
          '高度なSEO分析',
          'SerpAPI競合分析',
          'カスタムペルソナ',
          '記事履歴保存'
        ]
      }
    },
    pro: {
      name: 'Pro',
      price: 4500,
      priceId: process.env.NEXT_PUBLIC_STRIPE_PRICE_INDIVIDUAL_PRO || '',
      features: {
        articles: 100,
        support: 'priority' as const,
        features: [
          '記事生成 100件/月',
          '優先サポート',
          '高度なSEO分析',
          'SerpAPI競合分析',
          'カスタムペルソナ',
          '記事履歴保存',
          'カスタムテンプレート',
          'API連携',
          '詳細レポート'
        ]
      }
    }
  } as Record<string, IndividualPlan>,
  
  team: {
    name: 'Team',
    pricePerSeat: 1500,
    priceId: process.env.NEXT_PUBLIC_STRIPE_PRICE_TEAM_SEAT || '',
    minSeats: 2,
    maxSeats: 1000, // ChatGPT Teamと同様
    features: {
      articlesPerSeat: 50,
      articles: 0, // 計算で求める
      support: 'priority' as const,
      features: [
        '記事生成 50件/月/シート',
        '組織管理機能',
        'メンバー権限管理',
        'シート数の柔軟な変更',
        '一括請求・管理',
        '優先サポート',
        '全ての個人Proプラン機能',
        'チーム分析レポート',
        '管理者ダッシュボード'
      ]
    }
  } as TeamPlan
} as const;

// 型定義のエクスポート
export type IndividualPlanKey = keyof typeof PRICING_PLANS.individual;
export type PricingPlans = typeof PRICING_PLANS;

/**
 * プラン情報を取得するヘルパー関数
 */
export function getIndividualPlan(planKey: IndividualPlanKey): IndividualPlan {
  return PRICING_PLANS.individual[planKey];
}

export function getTeamPlan(): TeamPlan {
  return PRICING_PLANS.team;
}

/**
 * シート数に基づくTeamプランの総額を計算
 */
export function calculateTeamPlanPrice(seatCount: number): number {
  const teamPlan = getTeamPlan();
  return Math.max(seatCount, teamPlan.minSeats) * teamPlan.pricePerSeat;
}

/**
 * シート数に基づく総記事数を計算
 */
export function calculateTeamPlanArticles(seatCount: number): number {
  const teamPlan = getTeamPlan();
  return Math.max(seatCount, teamPlan.minSeats) * teamPlan.features.articlesPerSeat;
}

/**
 * プランの種類を判定
 */
export function getPlanType(priceId: string): 'individual' | 'team' | 'unknown' {
  // 個人プランかチェック
  for (const plan of Object.values(PRICING_PLANS.individual)) {
    if (plan.priceId === priceId) {
      return 'individual';
    }
  }
  
  // Teamプランかチェック
  if (PRICING_PLANS.team.priceId === priceId) {
    return 'team';
  }
  
  return 'unknown';
}

/**
 * プライスIDから個人プラン名を取得
 */
export function getIndividualPlanByPriceId(priceId: string): IndividualPlanKey | null {
  for (const [key, plan] of Object.entries(PRICING_PLANS.individual)) {
    if (plan.priceId === priceId) {
      return key as IndividualPlanKey;
    }
  }
  return null;
}

/**
 * プラン使用量の計算
 */
export interface PlanUsage {
  planName: string;
  articleLimit: number;
  articlesUsed: number;
  articlesRemaining: number;
  usagePercentage: number;
  isOverLimit: boolean;
}

export function calculatePlanUsage(
  planType: 'individual' | 'team',
  planKey: IndividualPlanKey | null,
  seatCount: number,
  articlesUsed: number
): PlanUsage {
  let planName: string;
  let articleLimit: number;
  
  if (planType === 'individual' && planKey) {
    const plan = getIndividualPlan(planKey);
    planName = plan.name;
    articleLimit = plan.features.articles;
  } else if (planType === 'team') {
    const teamPlan = getTeamPlan();
    planName = `${teamPlan.name} (${seatCount}シート)`;
    articleLimit = calculateTeamPlanArticles(seatCount);
  } else {
    planName = 'Unknown';
    articleLimit = 0;
  }
  
  const articlesRemaining = Math.max(0, articleLimit - articlesUsed);
  const usagePercentage = articleLimit > 0 ? (articlesUsed / articleLimit) * 100 : 0;
  const isOverLimit = articlesUsed > articleLimit;
  
  return {
    planName,
    articleLimit,
    articlesUsed,
    articlesRemaining,
    usagePercentage,
    isOverLimit,
  };
}