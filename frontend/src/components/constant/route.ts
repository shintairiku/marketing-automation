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
        href: '/seo/generate/new-article',
        label: 'SEO記事作成',
        sublabel: 'SEO記事作成',
        subLinks: [
          {
            title: '記事生成',
            links: [
              { href: '/seo/generate/new-article',     label: '新規SEO記事生成' },
            ],
          },
          {
            title: '記事管理',
            links: [
              { href: '/seo/manage/list',     label: '記事管理' },
            ],
          },
          {
            title: '効果測定',
            links: [
              { href: '/seo/analyze/dashboard',      label: 'ダッシュボード' },
            ],
          },
        ],
      },
    ],
  },
  {
    title: 'Company',
    links: [
      {
        href: '/company-settings/company',
        label: '会社情報設定',
        sublabel: '会社設定',
        subLinks: [
          {
            title: '基本設定',
            links: [
              { href: '/company-settings/company', label: '会社情報設定' },
              { href: '/company-settings/style-guide', label: '記事スタイル設定' },
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
        href: '/settings/account',
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
