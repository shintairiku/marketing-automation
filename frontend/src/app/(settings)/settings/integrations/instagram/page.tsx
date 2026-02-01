"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function InstagramIntegrationPage() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold flex items-center gap-2">
          Instagram連携設定
          <Badge variant="secondary">開発中</Badge>
        </h1>
        <p className="text-muted-foreground">
          Instagramアカウントとの連携を設定できます。
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Instagram連携設定</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            このページは準備中です。Instagram Basic Display API連携、自動投稿設定、分析データ取得などが実装予定です。
          </p>
        </CardContent>
      </Card>
    </div>
  );
}