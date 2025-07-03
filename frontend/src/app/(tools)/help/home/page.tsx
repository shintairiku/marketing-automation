"use client";

import Link from "next/link";
import { IoChatbubbles, IoCode, IoHelp, IoMail, IoMegaphone,IoSchool } from "react-icons/io5";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function HelpHomePage() {
  return (
    <div className="container mx-auto p-6 space-y-8">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">ヘルプ & サポート</h1>
        <p className="text-muted-foreground">
          ご不明な点やお困りの際は、こちらからサポート情報をご確認ください。
        </p>
      </div>

      {/* サポート */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold flex items-center gap-2">
          <IoHelp className="text-primary" />
          サポート
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <IoSchool className="text-primary" />
                はじめに
              </CardTitle>
              <CardDescription>
                サービスの基本的な使い方を学ぶ
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild className="w-full">
                <Link href="/help/getting-started">開始する</Link>
              </Button>
            </CardContent>
          </Card>

          <Card className="hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <IoChatbubbles className="text-primary" />
                よくある質問
              </CardTitle>
              <CardDescription>
                頻繁に寄せられる質問と回答
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild className="w-full">
                <Link href="/help/faq">確認する</Link>
              </Button>
            </CardContent>
          </Card>

          <Card className="hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <IoMail className="text-primary" />
                お問い合わせ
              </CardTitle>
              <CardDescription>
                直接サポートチームに連絡する
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild className="w-full">
                <Link href="/help/contact">問い合わせる</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* ドキュメント */}
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold flex items-center gap-2">
          <IoCode className="text-primary" />
          ドキュメント
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <IoSchool className="text-primary" />
                チュートリアル
              </CardTitle>
              <CardDescription>
                機能別の詳細なガイド
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild className="w-full">
                <Link href="/help/tutorials">確認する</Link>
              </Button>
            </CardContent>
          </Card>

          <Card className="hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <IoCode className="text-primary" />
                API ドキュメント
              </CardTitle>
              <CardDescription>
                開発者向けのAPI仕様
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild className="w-full">
                <Link href="/help/api-docs">確認する</Link>
              </Button>
            </CardContent>
          </Card>

          <Card className="hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <IoMegaphone className="text-primary" />
                リリースノート
              </CardTitle>
              <CardDescription>
                新機能とアップデート情報
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild className="w-full">
                <Link href="/help/release-notes">確認する</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}