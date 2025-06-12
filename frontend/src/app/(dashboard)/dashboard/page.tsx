'use client';

import { useEffect,useState } from 'react';
import Link from 'next/link';
import { 
  IoAnalytics,
  IoArrowForward,
  IoChatbubbles,
  IoCheckmarkCircle,
  IoDocumentText,
  IoGlobe,
  IoLogoInstagram,
  IoNotifications,
  IoPencil,
  IoRocket,
  IoSparkles,
  IoStatsChart,
  IoTimerOutline,
  IoTrendingUp} from 'react-icons/io5';

import { ApiConnectionStatus } from '@/components/ApiConnectionStatus';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { useUser } from '@clerk/nextjs';

// プラットフォームのデータ
const platforms = [
  {
    id: 'seo',
    name: 'SEO Blog',
    icon: IoGlobe,
    color: 'from-purple-500 to-indigo-600',
    bgColor: 'bg-purple-50',
    iconColor: 'text-purple-600',
    stats: {
      articles: 12,
      published: 8,
      views: '2.4K'
    },
    recentActivity: '3時間前に記事を公開',
    link: '/seo/home',
    quickActions: [
      { label: '新規記事作成', href: '/seo/generate/new-article', icon: IoPencil },
      { label: '記事管理', href: '/seo/manage/list', icon: IoDocumentText },
      { label: 'ダッシュボード', href: '/seo/analyze/dashboard', icon: IoAnalytics }
    ]
  },
  {
    id: 'instagram',
    name: 'Instagram',
    icon: IoLogoInstagram,
    color: 'from-pink-500 to-purple-600',
    bgColor: 'bg-pink-50',
    iconColor: 'text-pink-600',
    stats: {
      posts: 24,
      scheduled: 5,
      engagement: '4.2%'
    },
    recentActivity: '昨日投稿を公開',
    link: '/instagram/home',
    quickActions: [
      { label: 'キャプション生成', href: '/instagram/generate/caption', icon: IoPencil },
      { label: 'コンテンツ一覧', href: '/instagram/manage/list', icon: IoDocumentText },
      { label: 'ダッシュボード', href: '/instagram/analyze/dashboard', icon: IoAnalytics }
    ]
  },
  {
    id: 'line',
    name: 'LINE',
    icon: IoChatbubbles,
    color: 'from-green-500 to-teal-600',
    bgColor: 'bg-green-50',
    iconColor: 'text-green-600',
    stats: {
      messages: 18,
      sent: 15,
      openRate: '82%'
    },
    recentActivity: '2日前にメッセージ配信',
    link: '/line/home',
    quickActions: [
      { label: '文章生成', href: '/line/generate/text', icon: IoPencil },
      { label: 'コンテンツ一覧', href: '/line/manage/list', icon: IoDocumentText },
      { label: 'ダッシュボード', href: '/line/analyze/dashboard', icon: IoAnalytics }
    ]
  }
];

// モックデータ：最近のアクティビティ
const recentActivities = [
  { id: 1, type: 'seo', action: '記事を公開', title: 'SEO対策の完全ガイド', time: '3時間前', status: 'completed' },
  { id: 2, type: 'instagram', action: '投稿を予約', title: '新商品の紹介投稿', time: '5時間前', status: 'scheduled' },
  { id: 3, type: 'line', action: 'メッセージを配信', title: '週末セールのお知らせ', time: '昨日', status: 'completed' },
  { id: 4, type: 'seo', action: '記事を下書き保存', title: 'コンテンツマーケティング戦略', time: '2日前', status: 'draft' }
];

// モックデータ：パフォーマンスデータ
const performanceData = [
  { day: '月', value: 65 },
  { day: '火', value: 78 },
  { day: '水', value: 82 },
  { day: '木', value: 91 },
  { day: '金', value: 87 },
  { day: '土', value: 94 },
  { day: '日', value: 89 }
];

export default function DashboardPage() {
  const { user } = useUser();
  const [greeting, setGreeting] = useState('');

  useEffect(() => {
    const hour = new Date().getHours();
    if (hour < 12) setGreeting('おはようございます');
    else if (hour < 18) setGreeting('こんにちは');
    else setGreeting('こんばんは');
  }, []);

  return (
    <div className="space-y-6">
      {/* ウェルカムセクション */}
      <div className="bg-white rounded-xl shadow-lg p-8">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              {greeting}、{user?.firstName || 'ユーザー'}さん
            </h1>
            <p className="text-gray-600">
              今日もマーケティング活動を効率化しましょう。
            </p>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" asChild>
              <Link href="/dashboard/news">
                <IoNotifications className="mr-2" size={18} />
                お知らせ
              </Link>
            </Button>
            <Button variant="sexy" asChild>
              <Link href="/seo/generate/new-article">
                <IoSparkles className="mr-2" size={18} />
                コンテンツを作成
              </Link>
            </Button>
          </div>
        </div>
      </div>

      {/* 統計サマリー */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-white shadow-lg hover:shadow-xl transition-shadow duration-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-600">今月の生成数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end justify-between">
              <div>
                <div className="text-2xl font-bold text-gray-900">54</div>
                <p className="text-xs text-green-600 flex items-center mt-1">
                  <IoTrendingUp className="mr-1" size={12} />
                  +12% 前月比
                </p>
              </div>
              <div className="bg-gradient-to-br from-purple-100 to-indigo-100 p-3 rounded-lg">
                <IoDocumentText className="text-purple-600" size={24} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white shadow-lg hover:shadow-xl transition-shadow duration-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-600">公開済み</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end justify-between">
              <div>
                <div className="text-2xl font-bold text-gray-900">38</div>
                <p className="text-xs text-gray-500 mt-1">総コンテンツ数</p>
              </div>
              <div className="bg-gradient-to-br from-green-100 to-teal-100 p-3 rounded-lg">
                <IoCheckmarkCircle className="text-green-600" size={24} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white shadow-lg hover:shadow-xl transition-shadow duration-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-600">予約投稿</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end justify-between">
              <div>
                <div className="text-2xl font-bold text-gray-900">16</div>
                <p className="text-xs text-gray-500 mt-1">今週の予定</p>
              </div>
              <div className="bg-gradient-to-br from-blue-100 to-sky-100 p-3 rounded-lg">
                <IoTimerOutline className="text-blue-600" size={24} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white shadow-lg hover:shadow-xl transition-shadow duration-200">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-gray-600">エンゲージメント</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-end justify-between">
              <div>
                <div className="text-2xl font-bold text-gray-900">4.8%</div>
                <p className="text-xs text-green-600 flex items-center mt-1">
                  <IoTrendingUp className="mr-1" size={12} />
                  +0.3% 向上
                </p>
              </div>
              <div className="bg-gradient-to-br from-pink-100 to-purple-100 p-3 rounded-lg">
                <IoStatsChart className="text-pink-600" size={24} />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* プラットフォームクイックアクセス */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {platforms.map((platform) => (
          <Card key={platform.id} className="bg-white shadow-lg hover:shadow-xl transition-all duration-200 overflow-hidden group">
            <div className={`h-2 bg-gradient-to-r ${platform.color}`} />
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`${platform.bgColor} p-3 rounded-lg group-hover:scale-110 transition-transform duration-200`}>
                    <platform.icon className={platform.iconColor} size={24} />
                  </div>
                  <div>
                    <CardTitle className="text-lg">{platform.name}</CardTitle>
                    <CardDescription className="text-xs">{platform.recentActivity}</CardDescription>
                  </div>
                </div>
                <Button variant="ghost" size="icon" asChild>
                  <Link href={platform.link}>
                    <IoArrowForward size={18} />
                  </Link>
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-4 text-center">
                {Object.entries(platform.stats).map(([key, value]) => (
                  <div key={key}>
                    <p className="text-2xl font-bold text-gray-900">{value}</p>
                    <p className="text-xs text-gray-600 capitalize">
                      {key === 'articles' && '記事数'}
                      {key === 'posts' && '投稿数'}
                      {key === 'messages' && 'メッセージ'}
                      {key === 'published' && '公開済み'}
                      {key === 'scheduled' && '予約'}
                      {key === 'sent' && '配信済み'}
                      {key === 'views' && '閲覧数'}
                      {key === 'engagement' && 'エンゲージ'}
                      {key === 'openRate' && '開封率'}
                    </p>
                  </div>
                ))}
              </div>
              <div className="space-y-2">
                {platform.quickActions.map((action) => (
                  <Button
                    key={action.href}
                    variant="ghost"
                    size="sm"
                    className="w-full justify-start hover:bg-gray-50"
                    asChild
                  >
                    <Link href={action.href}>
                      <action.icon className="mr-2" size={16} />
                      {action.label}
                    </Link>
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* パフォーマンスと最近のアクティビティ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* パフォーマンスグラフ */}
        <Card className="bg-white shadow-lg h-full">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>週間パフォーマンス</CardTitle>
                <CardDescription>エンゲージメント率の推移</CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-green-600 font-medium">+15%</span>
                <IoTrendingUp className="text-green-600" size={20} />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-64 flex items-end justify-between gap-2">
              {performanceData.map((data) => (
                <div
                  key={data.day}
                  className="flex-1 bg-gradient-to-t from-purple-500 to-indigo-400 rounded-t-lg relative group"
                  style={{ height: `${data.value}%` }}
                >
                  <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-gray-900 text-white text-xs px-2 py-1 rounded">
                    {data.value}%
                  </div>
                  <div className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 text-xs text-gray-600">
                    {data.day}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 最近のアクティビティ */}
        <Card className="bg-white shadow-lg h-full">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>最近のアクティビティ</CardTitle>
              <Button variant="ghost" size="sm" asChild>
                <Link href="/dashboard/activities">
                  すべて見る
                  <IoArrowForward className="ml-1" size={14} />
                </Link>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentActivities.map((activity) => {
                const platform = platforms.find(p => p.id === activity.type);
                return (
                  <div
                    key={activity.id}
                    className="flex items-center gap-4 p-3 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className={`${platform?.bgColor} p-2 rounded-lg`}>
                      {platform && <platform.icon className={platform.iconColor} size={20} />}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">{activity.action}</p>
                      <p className="text-xs text-gray-600">{activity.title}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-gray-500">{activity.time}</p>
                      {activity.status === 'completed' && (
                        <span className="inline-flex items-center text-xs text-green-600">
                          <IoCheckmarkCircle size={12} className="mr-1" />
                          完了
                        </span>
                      )}
                      {activity.status === 'scheduled' && (
                        <span className="inline-flex items-center text-xs text-blue-600">
                          <IoTimerOutline size={12} className="mr-1" />
                          予約済み
                        </span>
                      )}
                      {activity.status === 'draft' && (
                        <span className="inline-flex items-center text-xs text-gray-500">
                          <IoPencil size={12} className="mr-1" />
                          下書き
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* API接続状況 */}
        <ApiConnectionStatus />
      </div>

      {/* お知らせセクション */}
      <Card className="bg-gradient-to-r from-purple-50 to-indigo-50 border-purple-200 shadow-lg">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="bg-white p-3 rounded-lg shadow-sm">
              <IoRocket className="text-purple-600" size={24} />
            </div>
            <div>
              <CardTitle className="text-purple-900">新機能のお知らせ</CardTitle>
              <CardDescription className="text-purple-700">
                Instagram Reelsの自動生成機能がリリースされました
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-purple-800 mb-4">
            短尺動画コンテンツの需要に応えるため、Instagram Reels用のキャプションとハッシュタグを
            自動生成する機能を追加しました。ぜひお試しください。
          </p>
          <Button variant="outline" className="border-purple-300 text-purple-700 hover:bg-purple-100">
            詳細を見る
            <IoArrowForward className="ml-2" size={16} />
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}