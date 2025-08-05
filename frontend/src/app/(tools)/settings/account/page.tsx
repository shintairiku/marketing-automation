"use client";

import { Mail, Shield, User } from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useClerk,useUser } from "@clerk/nextjs";

export default function AccountSettingsPage() {
  const { isLoaded, user } = useUser();
  const { openUserProfile, signOut } = useClerk();

  if (!isLoaded) {
    return (
      <div className="container mx-auto p-6">
        <p className="text-muted-foreground">ユーザー情報を読み込み中...</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="container mx-auto p-6">
        <p className="text-muted-foreground">ユーザー情報が見つかりません</p>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">アカウント設定</h1>
        <p className="text-muted-foreground">
          プロフィール情報、セキュリティ設定を管理できます。
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            プロフィール設定
          </CardTitle>
          <CardDescription>
            基本的なプロフィール情報を管理します
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center space-x-4">
            <Avatar className="h-20 w-20">
              <AvatarImage src={user.imageUrl} alt={user.firstName || "User"} />
              <AvatarFallback>
                <User className="h-10 w-10" />
              </AvatarFallback>
            </Avatar>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="firstName">名前（姓）</Label>
              <Input 
                id="firstName" 
                value={user.firstName || ""}
                disabled
                className="opacity-60"
                placeholder="山田" 
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="lastName">名前（名）</Label>
              <Input 
                id="lastName" 
                value={user.lastName || ""}
                disabled
                className="opacity-60"
                placeholder="太郎" 
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">メールアドレス</Label>
            <Input 
              id="email" 
              type="email" 
              value={user.primaryEmailAddress?.emailAddress || ""}
              disabled
              className="opacity-60"
            />
          </div>

          <div className="flex gap-2">
            <Button onClick={() => openUserProfile()}>
              <User className="mr-2 h-4 w-4" />
              プロフィールを編集
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            セキュリティ設定
          </CardTitle>
          <CardDescription>
            アカウントのセキュリティを管理します
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-base">アカウント管理</div>
              <div className="text-sm text-muted-foreground">
                パスワード変更、二段階認証、ログイン履歴などの詳細設定
              </div>
            </div>
            <Button variant="outline" onClick={() => openUserProfile()}>
              管理画面を開く
            </Button>
          </div>

        </CardContent>
      </Card>

    </div>
  );
}