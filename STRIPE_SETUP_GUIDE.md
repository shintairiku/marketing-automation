# Stripe商品・価格設定ガイド

## 1. Stripeダッシュボードでの商品作成

### 個人プラン商品

#### Basic個人プラン
1. **商品作成**
   - 商品名: `個人ベーシックプラン`
   - 説明: `個人利用向けの記事生成サービス - 月30記事まで`
   - 商品ID: `prod_individual_basic`

2. **価格設定**
   - 価格: `¥1,500`
   - 課金間隔: `月次`
   - 価格ID: `price_individual_basic_monthly`
   - 通貨: `JPY`

#### Pro個人プラン  
1. **商品作成**
   - 商品名: `個人プロプラン`
   - 説明: `個人利用向けの記事生成サービス - 月100記事まで`
   - 商品ID: `prod_individual_pro`

2. **価格設定**
   - 価格: `¥4,500`
   - 課金間隔: `月次`
   - 価格ID: `price_individual_pro_monthly`
   - 通貨: `JPY`

### Teamプラン商品

#### Team プラン（シート制）
1. **商品作成**
   - 商品名: `Teamプラン`
   - 説明: `チーム利用向けの記事生成サービス - シート単価制`
   - 商品ID: `prod_team`

2. **価格設定**
   - 価格: `¥1,500`
   - 課金間隔: `月次`
   - 価格ID: `price_team_seat_monthly`
   - 通貨: `JPY`
   - **課金方式**: `Per unit` (シート単価)
   - **最小数量**: `2` (最低2シート)

## 2. Stripe CLIでの商品作成コマンド

### 環境変数設定
```bash
export STRIPE_SECRET_KEY=sk_test_xxxxx  # テスト環境
# export STRIPE_SECRET_KEY=sk_live_xxxxx  # 本番環境
```

### 個人ベーシックプラン
```bash
# 商品作成
stripe products create \
  --name="個人ベーシックプラン" \
  --description="個人利用向けの記事生成サービス - 月30記事まで" \
  --id="prod_individual_basic"

# 価格作成
stripe prices create \
  --product="prod_individual_basic" \
  --unit-amount=150000 \
  --currency=jpy \
  --recurring[interval]=month \
  --lookup-key="individual_basic_monthly"
```

### 個人プロプラン
```bash
# 商品作成
stripe products create \
  --name="個人プロプラン" \
  --description="個人利用向けの記事生成サービス - 月100記事まで" \
  --id="prod_individual_pro"

# 価格作成
stripe prices create \
  --product="prod_individual_pro" \
  --unit-amount=450000 \
  --currency=jpy \
  --recurring[interval]=month \
  --lookup-key="individual_pro_monthly"
```

### Teamプラン（シート制）
```bash
# 商品作成
stripe products create \
  --name="Teamプラン" \
  --description="チーム利用向けの記事生成サービス - シート単価制" \
  --id="prod_team"

# 価格作成（シート単価）
stripe prices create \
  --product="prod_team" \
  --unit-amount=150000 \
  --currency=jpy \
  --recurring[interval]=month \
  --billing-scheme=per_unit \
  --lookup-key="team_seat_monthly"
```

## 3. プラン比較表

| プラン | 価格 | 記事数制限 | シート数 | 対象 |
|--------|------|------------|----------|------|
| Free（個人） | ¥0 | 5記事/月 | 1 | 個人試用 |
| Basic（個人） | ¥1,500/月 | 30記事/月 | 1 | 個人利用 |
| Pro（個人） | ¥4,500/月 | 100記事/月 | 1 | 個人ヘビーユーザー |
| Team | ¥1,500/月/シート | 50記事/月/シート | 2〜無制限 | チーム利用 |

## 4. 環境変数設定

### フロントエンド (.env.local)
```bash
# Stripe公開キー
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_xxxxx

# Stripe価格ID（フロントエンドで使用）
NEXT_PUBLIC_STRIPE_PRICE_INDIVIDUAL_BASIC=price_xxxxx
NEXT_PUBLIC_STRIPE_PRICE_INDIVIDUAL_PRO=price_xxxxx  
NEXT_PUBLIC_STRIPE_PRICE_TEAM_SEAT=price_xxxxx
```

### バックエンド (.env)
```bash
# Stripe秘密キー
STRIPE_SECRET_KEY=sk_test_xxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxx
```

## 5. Webhook設定

### Stripeダッシュボードでの設定
1. **Developers** → **Webhooks** → **Add endpoint**
2. **Endpoint URL**: `https://your-domain.com/api/webhooks`
3. **Events to send**:
   - `product.created`
   - `product.updated`
   - `price.created`
   - `price.updated`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `checkout.session.completed`
   - `invoice.paid`
   - `invoice.payment_failed`

## 6. テスト用データ

### テスト用カード番号
```
成功: 4242424242424242
失敗: 4000000000000002
3Dセキュア: 4000002500003155
```

### テスト用顧客作成
```bash
stripe customers create \
  --email="test@example.com" \
  --name="テストユーザー"
```

## 7. プラン設定用のTypeScript定義

### プラン定義ファイル
`src/config/pricing-plans.ts`:
```typescript
export const PRICING_PLANS = {
  individual: {
    free: {
      name: 'Free',
      price: 0,
      priceId: null,
      features: {
        articles: 5,
        support: 'community',
        features: ['基本記事生成', 'コミュニティサポート']
      }
    },
    basic: {
      name: 'Basic',
      price: 1500,
      priceId: process.env.NEXT_PUBLIC_STRIPE_PRICE_INDIVIDUAL_BASIC!,
      features: {
        articles: 30,
        support: 'email',
        features: ['記事生成30件/月', 'メールサポート', 'SEO分析']
      }
    },
    pro: {
      name: 'Pro',
      price: 4500,
      priceId: process.env.NEXT_PUBLIC_STRIPE_PRICE_INDIVIDUAL_PRO!,
      features: {
        articles: 100,
        support: 'priority',
        features: ['記事生成100件/月', '優先サポート', '高度なSEO分析', 'カスタムテンプレート']
      }
    }
  },
  team: {
    name: 'Team',
    pricePerSeat: 1500,
    priceId: process.env.NEXT_PUBLIC_STRIPE_PRICE_TEAM_SEAT!,
    minSeats: 2,
    features: {
      articlesPerSeat: 50,
      support: 'priority',
      features: ['記事生成50件/月/シート', '組織管理', '権限管理', '一括請求', '優先サポート']
    }
  }
} as const;
```

## 8. 次のステップ

1. ✅ Stripe商品・価格を作成
2. ⏳ Webhook URLを設定  
3. ⏳ 環境変数を更新
4. ⏳ テスト決済の実行
5. ⏳ 本番環境への移行

この設定により、個人・チーム両方のプランでの課金システムが利用可能になります。