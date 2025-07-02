"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Header from "@/components/display/header";
import Sidebar from "@/components/display/sidebar";

export default function WordPressIntegrationPage() {
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
              <h1 className="text-3xl font-bold flex items-center gap-2">
                WordPress連携設定
                <Badge variant="secondary">開発中</Badge>
              </h1>
              <p className="text-muted-foreground">
                WordPressサイトとの自動連携を設定できます。
              </p>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>WordPress連携設定</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">
                  このページは準備中です。WordPress REST API連携、自動投稿設定、メディア管理などが実装予定です。
                </p>
              </CardContent>
            </Card>
          </div>
        </main>
      </div>
    </div>
  );
}