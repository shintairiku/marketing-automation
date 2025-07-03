"use client";

import Header from "@/components/display/header";
import Sidebar from "@/components/display/sidebar";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function BillingSettingsPage() {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="flex mt-[45px]">
        <div className="fixed left-0 top-[45px] h-[calc(100vh-45px)]">
          <Sidebar />
        </div>
        <main className="flex-1 ml-[314px] p-5">
          <div className="container mx-auto p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">請求&契約設定</h1>
        <p className="text-muted-foreground">
          プランの管理、支払い方法、請求履歴を確認できます。
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>請求&契約設定</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            このページは準備中です。プラン変更、支払い方法設定、請求履歴表示などが実装予定です。
          </p>
        </CardContent>
      </Card>
          </div>
        </main>
      </div>
    </div>
  );
}