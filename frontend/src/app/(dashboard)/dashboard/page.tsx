'use client';

import { useEffect,useState } from 'react';
import Link from 'next/link';
import { 
  IoAnalytics,
  IoArrowForward,
  IoCheckmarkCircle,
  IoDocumentText,
  IoGlobe,
  IoPencil,
  IoSparkles,
  IoTrendingUp} from 'react-icons/io5';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { useArticleStats } from '@/hooks/useArticles';
import { useUser } from '@clerk/nextjs';

// SEOプラットフォームのデータ
const seoplatform = {
  id: 'seo',
  name: 'SEO記事作成',
  icon: IoGlobe,
  color: 'from-purple-500 to-indigo-600',
  bgColor: 'bg-purple-50',
  iconColor: 'text-purple-600',
  recentActivity: '3時間前に記事を公開',
  link: '/seo/generate/new-article',
  quickActions: [
    { label: '新規SEO記事生成', href: '/seo/generate/new-article', icon: IoPencil },
    { label: '記事管理', href: '/seo/manage/list', icon: IoDocumentText },
    { label: 'ダッシュボード', href: '/seo/analyze/dashboard', icon: IoAnalytics }
  ]
};


export default function DashboardPage() {
  const { user } = useUser();
  const [greeting, setGreeting] = useState('');
  const { stats, loading: statsLoading, error: statsError } = useArticleStats();

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
          </div>
          <div className="flex gap-3">
            <Button className="bg-primary hover:bg-primary/90 text-white" asChild>
              <Link href="/seo/generate/new-article">
                <IoSparkles className="mr-2" size={18} />
                新規SEO記事を作成
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
                {statsLoading ? (
                  <div className="text-2xl font-bold text-gray-400">---</div>
                ) : (
                  <div className="text-2xl font-bold text-gray-900">{stats?.this_month_count || 0}</div>
                )}
                <p className="text-xs text-gray-500 mt-1">今月生成された記事</p>
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
                {statsLoading ? (
                  <div className="text-2xl font-bold text-gray-400">---</div>
                ) : (
                  <div className="text-2xl font-bold text-gray-900">{stats?.total_published || 0}</div>
                )}
                <p className="text-xs text-gray-500 mt-1">公開中の記事</p>
              </div>
              <div className="bg-gradient-to-br from-green-100 to-teal-100 p-3 rounded-lg">
                <IoCheckmarkCircle className="text-green-600" size={24} />
              </div>
            </div>
          </CardContent>
        </Card>

      </div>

      {/* SEOプラットフォームクイックアクセス */}
      <Card className="bg-white shadow-lg hover:shadow-xl transition-all duration-200 overflow-hidden group">
        <div className={`h-2 bg-gradient-to-r ${seoplatform.color}`} />
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`${seoplatform.bgColor} p-3 rounded-lg group-hover:scale-110 transition-transform duration-200`}>
                <seoplatform.icon className={seoplatform.iconColor} size={24} />
              </div>
              <div>
                <CardTitle className="text-lg">{seoplatform.name}</CardTitle>
                <CardDescription className="text-xs">{seoplatform.recentActivity}</CardDescription>
              </div>
            </div>
            <Button variant="ghost" size="icon" asChild>
              <Link href={seoplatform.link}>
                <IoArrowForward size={18} />
              </Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4 text-center">
            <div>
              {statsLoading ? (
                <p className="text-2xl font-bold text-gray-400">---</p>
              ) : (
                <p className="text-2xl font-bold text-gray-900">{stats?.total_generated || 0}</p>
              )}
              <p className="text-xs text-gray-600">総記事数</p>
            </div>
            <div>
              {statsLoading ? (
                <p className="text-2xl font-bold text-gray-400">---</p>
              ) : (
                <p className="text-2xl font-bold text-gray-900">{stats?.total_published || 0}</p>
              )}
              <p className="text-xs text-gray-600">公開済み</p>
            </div>
          </div>
          <div className="space-y-2">
            {seoplatform.quickActions.map((action) => (
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
    </div>
  );
}