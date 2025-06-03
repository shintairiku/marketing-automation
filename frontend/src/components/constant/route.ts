
export const groups = [
  {
    title: 'Home',
    links: [
      {
        href: '/dashboard',
        label: 'ダッシュボード',
        sublabel: 'Dashboard',
        subLinks: [
          {
            title: 'お知らせ',
            links: [
              { href: '/dashboard/news', label: '運営からのお知らせ' },
              { href: '/dashboard/setting', label: '運営からのお知らせ設定' },
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
    title: 'Generate',
    links: [
      {
        href: '/generate/seo/home',
        label: 'SEO記事生成',
        sublabel: 'SEO Tiger',
        imageurl: '/seoTiger.png',
        subLinks: [
          {
            title: '記事生成',
            links: [
              { href: '/generate/seo/new-article',     label: '新規記事作成' },
            ],
          },
          {
            title: '記事管理',
            links: [
              { href: '/manage/seo/list',     label: '記事一覧' },
              { href: '/manage/seo/status',     label: '記事ステータス管理' },
              { href: '/manage/seo/schedule',     label: '配信カレンダー' },
            ],
          },
          {
            title: '効果測定',
            links: [
              { href: '/analyze/seo/dashboard',      label: 'ダッシュボード' },
              { href: '/analyze/seo/report',   label: 'SEO効果レポート' },
              { href: '/analyze/seo/feedback', label: 'AIフィードバック' }, 
            ],
          },
          {
            title: '入力値調整',
            links: [
              { href: '/input/seo/persona',      label: '独自ペルソナ設定' },
            ],
          },
        ],
      },
      {
        href: '/generate/instagram',
        label: 'Instagramコンテンツ生成',
        sublabel: 'Instagram Turtle',
        subLinks: [
          {
            title: 'コンテンツ生成',
            links: [
              { href: '/generate/instagram/caption', label: 'キャプション生成' },
              { href: '/generate/instagram/hashtags',label: 'ハッシュタグ提案' },
              { href: '/generate/instagram/image',   label: '画像生成支援' },
              { href: '/generate/instagram/rewrite', label: 'AI 校正' },
              { href: '/generate/instagram/schedule',label: '予約投稿' },
            ],
          },
          {
            title: 'コンテンツ管理',
            links: [
              { href: '/manage/instagram/list',     label: 'コンテンツ一覧' },
              { href: '/manage/instagram/status',     label: 'コンテンツステータス管理' },
              { href: '/manage/instagram/schedule',     label: '配信カレンダー' },
            ],
          },
          {
            title: '効果測定',
            links: [
              { href: '/analyze/instagram/dashboard',      label: 'ダッシュボード' },
              { href: '/analyze/instagram/report',   label: '効果レポート' },
              { href: '/analyze/instagram/feedback', label: 'AIフィードバック' }, 
            ],
          },
          {
            title: '入力値調整',
            links: [
              { href: '/input/instagram/persona',      label: '独自ペルソナ設定' },
            ],
          },
        ],
      },
      {
        href: '/generate/line',
        label: 'LINE配信コンテンツ生成',
        sublabel: 'LINE Rabbit',
        subLinks: [
          {
            title: 'コンテンツ生成',
            links: [
              { href: '/generate/line/text', label: '文章生成' },
              { href: '/generate/line/image',   label: '画像生成' },
              { href: '/generate/line/rewrite', label: 'ステップ配信' },
              { href: '/generate/line/schedule',label: 'リッチメニュー生成' },
            ],
          },
          {
            title: 'コンテンツ管理',
            links: [
              { href: '/manage/line/list',     label: 'コンテンツ一覧' },
              { href: '/manage/line/status',     label: 'コンテンツステータス管理' },
              { href: '/manage/line/schedule',     label: '配信カレンダー' },
            ],
          },
          {
            title: '効果測定',
            links: [
              { href: '/analyze/line/dashboard',      label: 'ダッシュボード' },
              { href: '/analyze/line/report',   label: '効果レポート' },
              { href: '/analyze/line/feedback', label: 'AIフィードバック' }, 
            ],
          },
          {
            title: '入力値調整',
            links: [
              { href: '/input/line/persona',      label: '独自ペルソナ設定' },
            ],
          },
        ],
      },
    ],
  },
];
