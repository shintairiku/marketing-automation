"use client";

import { useEffect,useState } from "react";
import { Bell } from "lucide-react";
import { Edit2, Mail, Shield, Trash2,User } from "lucide-react";
import { toast } from "sonner";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useClerk,useUser } from "@clerk/nextjs";

export default function AccountSettingsPage() {
  const { isLoaded, user } = useUser();
  const { openUserProfile, signOut } = useClerk();
  const [isEditing, setIsEditing] = useState(false);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    if (user) {
      setFirstName(user.firstName || "");
      setLastName(user.lastName || "");
    }
  }, [user]);

  const handleUpdateProfile = async () => {
    if (!user) return;
    
    setIsUpdating(true);
    try {
      await user.update({
        firstName: firstName.trim(),
        lastName: lastName.trim(),
      });
      setIsEditing(false);
      toast.success("プロフィールを更新しました");
    } catch (error) {
      console.error("プロフィール更新エラー:", error);
      toast.error("プロフィールの更新に失敗しました");
    } finally {
      setIsUpdating(false);
    }
  };

  const handleCancelEdit = () => {
    setFirstName(user?.firstName || "");
    setLastName(user?.lastName || "");
    setIsEditing(false);
  };

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
          プロフィール情報、通知設定、セキュリティ設定を管理できます。
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
            <div className="space-y-2">
              <Button variant="outline" onClick={() => openUserProfile()}>
                画像を変更
              </Button>
              <p className="text-sm text-muted-foreground">
                JPG、PNG形式のファイルをアップロードできます（最大2MB）
              </p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="firstName">名前（姓）</Label>
              <Input 
                id="firstName" 
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                disabled={!isEditing}
                placeholder="山田" 
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="lastName">名前（名）</Label>
              <Input 
                id="lastName" 
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                disabled={!isEditing}
                placeholder="太郎" 
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">メールアドレス</Label>
            <div className="flex items-center gap-2">
              <Input 
                id="email" 
                type="email" 
                value={user.primaryEmailAddress?.emailAddress || ""}
                disabled
                className="opacity-60"
              />
              <Button variant="outline" size="sm" onClick={() => openUserProfile()}>
                <Edit2 className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              メールアドレスの変更は専用画面で行います
            </p>
          </div>

          <div className="flex gap-2">
            {!isEditing ? (
              <Button onClick={() => setIsEditing(true)}>
                <Edit2 className="mr-2 h-4 w-4" />
                編集
              </Button>
            ) : (
              <>
                <Button 
                  onClick={handleUpdateProfile}
                  disabled={isUpdating}
                >
                  {isUpdating ? "更新中..." : "保存"}
                </Button>
                <Button 
                  variant="outline" 
                  onClick={handleCancelEdit}
                  disabled={isUpdating}
                >
                  キャンセル
                </Button>
              </>
            )}
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

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-base">アカウント削除</div>
              <div className="text-sm text-muted-foreground">
                <Badge variant="destructive" className="mr-2">危険</Badge>
                この操作は取り消せません
              </div>
            </div>
            <Button variant="destructive" onClick={() => openUserProfile()}>
              <Trash2 className="h-4 w-4 mr-2" />
              削除する
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            通知設定
          </CardTitle>
          <CardDescription>
            どの通知を受け取るかを設定します
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-base">記事生成完了通知</div>
              <div className="text-sm text-muted-foreground">
                SEO記事の生成が完了したときに通知を受け取る
              </div>
            </div>
            <Switch />
          </div>
          
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-base">メンバー招待通知</div>
              <div className="text-sm text-muted-foreground">
                新しいメンバーが招待されたときに通知を受け取る
              </div>
            </div>
            <Switch />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-base">システムメンテナンス通知</div>
              <div className="text-sm text-muted-foreground">
                システムのメンテナンス情報を受け取る
              </div>
            </div>
            <Switch defaultChecked />
          </div>

          <Button>設定を保存</Button>
        </CardContent>
      </Card>
    </div>
  );
}