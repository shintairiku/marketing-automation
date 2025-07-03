"use client";

import Link from "next/link";
import { IoCash, IoClipboard, IoLinkSharp,IoPencil, IoPeople, IoPerson, IoSettings } from "react-icons/io5";

import Header from "@/components/display/header";
import Sidebar from "@/components/display/sidebar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SettingsHomePage() {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="flex mt-[45px]">
        <div className="fixed left-0 top-[45px] h-[calc(100vh-45px)]">
          <Sidebar />
        </div>
        <main className="flex-1 ml-[314px] p-5">
          <div className="container mx-auto p-6 space-y-8">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">設定</h1>
        <p className="text-muted-foreground">
          アカウント、会社情報、サービス連携などの設定を管理できます。
        </p>
      </div>

      {/* 基本設定 */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold flex items-center gap-2">
          <IoSettings className="text-primary" />
          基本設定
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <IoPerson className="text-primary" />
                アカウント設定
              </CardTitle>
              <CardDescription>
                プロフィール、パスワード、通知設定を管理
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild className="w-full">
                <Link href="/settings/account">設定を開く</Link>
              </Button>
            </CardContent>
          </Card>

          <Card className="hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <IoPeople className="text-primary" />
                メンバー設定
              </CardTitle>
              <CardDescription>
                チームメンバーの招待と権限管理
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild className="w-full">
                <Link href="/settings/members">設定を開く</Link>
              </Button>
            </CardContent>
          </Card>

          <Card className="hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <IoCash className="text-primary" />
                請求&契約設定
              </CardTitle>
              <CardDescription>
                プラン、支払い方法、請求履歴の管理
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild className="w-full">
                <Link href="/settings/billing">設定を開く</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* 会社情報設定 */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold flex items-center gap-2">
          <IoClipboard className="text-primary" />
          会社情報設定
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <IoClipboard className="text-primary" />
                会社情報設定
              </CardTitle>
              <CardDescription>
                企業情報、USP、ペルソナなどを設定
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild className="w-full">
                <Link href="/settings/company">設定を開く</Link>
              </Button>
            </CardContent>
          </Card>

          <Card className="hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <IoPencil className="text-primary" />
                スタイルガイド設定
              </CardTitle>
              <CardDescription>
                ブランドカラー、フォント、トーンの設定
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild className="w-full">
                <Link href="/settings/style-guide">設定を開く</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* サービス連携設定 */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold flex items-center gap-2">
          <IoLinkSharp className="text-primary" />
          サービス連携設定
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="hover:shadow-md transition-shadow opacity-50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <IoLinkSharp className="text-gray-400" />
                ワードプレス連携設定
              </CardTitle>
              <CardDescription>
                WordPressサイトとの自動連携
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button disabled className="w-full">
                開発中
              </Button>
            </CardContent>
          </Card>

          <Card className="hover:shadow-md transition-shadow opacity-50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <IoLinkSharp className="text-gray-400" />
                Instagram連携設定
              </CardTitle>
              <CardDescription>
                Instagramアカウントとの連携
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button disabled className="w-full">
                開発中
              </Button>
            </CardContent>
          </Card>

          <Card className="hover:shadow-md transition-shadow opacity-50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <IoLinkSharp className="text-gray-400" />
                LINE連携設定
              </CardTitle>
              <CardDescription>
                LINE公式アカウントとの連携
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button disabled className="w-full">
                開発中
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>
          </div>
        </main>
      </div>
    </div>
  );
}