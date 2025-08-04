"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function MembersSettingsPage() {
  return (
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
  );
}