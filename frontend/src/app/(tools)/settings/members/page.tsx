"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Header from "@/components/display/header";
import Sidebar from "@/components/display/sidebar";

export default function MembersSettingsPage() {
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
        <h1 className="text-3xl font-bold">メンバー設定</h1>
        <p className="text-muted-foreground">
          チームメンバーの管理と権限設定を行えます。
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>メンバー設定</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            このページは準備中です。メンバー招待、権限管理、ロール設定などが実装予定です。
          </p>
        </CardContent>
      </Card>
          </div>
        </main>
      </div>
    </div>
  );
}