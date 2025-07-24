interface SubLink {
  href: string;
  label: string;
  disabled?: boolean;
}

interface LinkSection {
  title: string;
  links: SubLink[];
}

interface MainLink {
  href: string;
  label: string;
  sublabel: string;
  imageurl?: string;
  subLinks: LinkSection[];
}

interface Group {
  title: string;
  links: MainLink[];
}

export const groups: Group[] = [
  {
    title: 'Home',
    links: [
      {
        href: '/dashboard',
        label: 'ダッシュボード',
        sublabel: 'Dashboard',
        subLinks: [
          {
            title: 'ホーム',
            links: [
              { href: '/dashboard', label: 'ダッシュボード' },
              { href: '/dashboard/news', label: '運営からのお知らせ' },
            ],
          },
          {
            title: 'コンテンツ管理',
            links: [
              { href: '/dashboard/overview', label: '生成コンテンツ一覧' },
              { href: '/dashboard/calendar', label: '配信カレンダー' },
              { href: '/dashboard/performance', label: '全体効果測定' },
            ],
          },
        ],
      },
    ],
  },
  {
    title: 'SNS Content',
    links: [
      {
        href: '/seo/home',
        label: 'SEO Blog',
        sublabel: 'SEO Tiger',
        imageurl: '/seoTiger.png',
        subLinks: [
          {
            title: '記事生成',
            links: [
              { href: '/seo/generate/new-article',     label: '新規記事作成' },
              { href: '/seo/generate/realtime-article', label: 'Realtime記事生成' },
            ],
          },
          {
            title: '記事管理',
            links: [
              { href: '/seo/manage/list',     label: '記事管理' },
              { href: '/seo/manage/status',     label: '記事ステータス管理' },
              { href: '/seo/manage/schedule',     label: '配信カレンダー' },
            ],
          },
          {
            title: '効果測定',
            links: [
              { href: '/seo/analyze/dashboard',      label: 'ダッシュボード' },
              { href: '/seo/analyze/report',   label: 'SEO効果レポート' },
              { href: '/seo/analyze/feedback', label: 'AIフィードバック' }, 
            ],
          },
          {
            title: '入力値調整',
            links: [
              { href: '/seo/input/persona',      label: '独自ペルソナ設定' },
            ],
          },
        ],
      },
      {
        href: '/instagram/home',
        label: 'Instagram',
        sublabel: 'Instagram Turtle',
        subLinks: [
          {
            title: 'コンテンツ生成',
            links: [
              { href: '/instagram/generate/caption', label: 'キャプション生成' },
              { href: '/instagram/generate/hashtags',label: 'ハッシュタグ提案' },
              { href: '/instagram/generate/image',   label: '画像生成支援' },
              { href: '/instagram/generate/rewrite', label: 'AI 校正' },
              { href: '/instagram/generate/schedule',label: '予約投稿' },
            ],
          },
          {
            title: 'コンテンツ管理',
            links: [
              { href: '/instagram/manage/list',     label: 'コンテンツ一覧' },
              { href: '/instagram/manage/status',     label: 'コンテンツステータス管理' },
              { href: '/instagram/manage/schedule',     label: '配信カレンダー' },
            ],
          },
          {
            title: '効果測定',
            links: [
              { href: '/instagram/analyze/dashboard',      label: 'ダッシュボード' },
              { href: '/instagram/analyze/report',   label: '効果レポート' },
              { href: '/instagram/analyze/feedback', label: 'AIフィードバック' }, 
            ],
          },
          {
            title: '入力値調整',
            links: [
              { href: '/instagram/input/persona',      label: '独自ペルソナ設定' },
            ],
          },
        ],
      },
      {
        href: '/line/home',
        label: 'LINE',
        sublabel: 'LINE Rabbit',
        subLinks: [
          {
            title: 'コンテンツ生成',
            links: [
              { href: '/line/generate/text', label: '文章生成' },
              { href: '/line/generate/image',   label: '画像生成' },
              { href: '/line/generate/rewrite', label: 'ステップ配信' },
              { href: '/line/generate/schedule',label: 'リッチメニュー生成' },
            ],
          },
          {
            title: 'コンテンツ管理',
            links: [
              { href: '/line/manage/list',     label: 'コンテンツ一覧' },
              { href: '/line/manage/status',     label: 'コンテンツステータス管理' },
              { href: '/line/manage/schedule',     label: '配信カレンダー' },
            ],
          },
          {
            title: '効果測定',
            links: [
              { href: '/line/analyze/dashboard',      label: 'ダッシュボード' },
              { href: '/line/analyze/report',   label: '効果レポート' },
              { href: '/line/analyze/feedback', label: 'AIフィードバック' }, 
            ],
          },
          {
            title: '入力値調整',
            links: [
              { href: '/line/input/persona',      label: '独自ペルソナ設定' },
            ],
          },
        ],
      },
    ],
  },
  {
    title: 'Settings',
    links: [
      {
        href: '/settings/home',
        label: '設定',
        sublabel: 'Settings',
        subLinks: [
          {
            title: '基本設定',
            links: [
              { href: '/settings/account', label: 'アカウント設定' },
              { href: '/settings/members', label: 'メンバー設定' },
              { href: '/settings/billing', label: '請求&契約設定' },
            ],
          },
          {
            title: '会社情報設定',
            links: [
              { href: '/settings/company', label: '会社情報設定' },
              { href: '/settings/style-guide', label: 'スタイルガイド設定' },
            ],
          },
          {
            title: 'サービス連携設定',
            links: [
              { href: '/settings/integrations/wordpress', label: 'ワードプレス連携設定', disabled: true },
              { href: '/settings/integrations/instagram', label: 'Instagram連携設定', disabled: true },
              { href: '/settings/integrations/line', label: 'LINE連携設定', disabled: true },
            ],
          },
        ],
      },
    ],
  },
  {
    title: 'Help',
    links: [
      {
        href: '/help/home',
        label: 'ヘルプ',
        sublabel: 'Help & Support',
        subLinks: [
          {
            title: 'サポート',
            links: [
              { href: '/help/getting-started', label: 'はじめに' },
              { href: '/help/faq', label: 'よくある質問' },
              { href: '/help/contact', label: 'お問い合わせ' },
            ],
          },
          {
            title: 'ドキュメント',
            links: [
              { href: '/help/tutorials', label: 'チュートリアル' },
              { href: '/help/api-docs', label: 'API ドキュメント' },
              { href: '/help/release-notes', label: 'リリースノート' },
            ],
          },
        ],
      },
    ],
  },
];
