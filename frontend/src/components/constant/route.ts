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

// 非特権ユーザーに表示するグループタイトル
const NON_PRIVILEGED_GROUP_TITLES = ['Blog', 'Settings'];

/**
 * 非特権ユーザー向けにフィルタリングされたグループを返す
 * Blog AI + Settings のみ表示
 */
export function getFilteredGroups(isPrivileged: boolean): Group[] {
  if (isPrivileged) return groups;
  return groups.filter((g) => NON_PRIVILEGED_GROUP_TITLES.includes(g.title));
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
              // { href: '/dashboard', label: 'ダッシュボード' },
              { href: '/seo/manage/list', label: 'ダッシュボード' }
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
        label: 'SEO記事作成・管理',
        sublabel: 'SEO記事作成',
        subLinks: [
          {
            title: '記事生成',
            links: [
              { href: '/seo/generate/new-article',     label: '新規SEO記事生成' },
            ],
          }
          // {
          //   title: '記事管理',
          //   links: [
          //     { href: '/seo/manage/list',     label: '記事管理' },
          //   ],
          // },
          // {
          //   title: '効果測定',
          //   links: [
          //     { href: '/seo/analyze/dashboard',      label: 'ダッシュボード' },
          //   ],
          // },
        ],
      },
    ],
  },
  {
    title: 'Blog',
    links: [
      {
        href: '/blog/new',
        label: 'ブログAI',
        sublabel: 'Blog AI',
        subLinks: [
          {
            title: 'ブログ作成',
            links: [
              { href: '/blog/new', label: '新規ブログ記事作成' },
              { href: '/blog/history', label: '生成履歴' },
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
              { href: '/settings/members', label: 'チームメンバー設定' },
              { href: '/settings/billing', label: '請求&契約設定' },
            ],
          },
          {
            title: 'サービス連携設定',
            links: [
              { href: '/settings/integrations/wordpress', label: 'WordPress連携設定' },
            ],
          },
          {
            title: 'サポート',
            links: [
              { href: '/settings/contact', label: 'お問い合わせ' },
            ],
          },
          {
            title: 'アプリ',
            links: [
              { href: '/settings/install', label: 'アプリをインストール' },
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
              { href: '/settings/contact', label: 'お問い合わせ' },
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
