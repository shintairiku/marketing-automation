"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Globe,
  Link2,
  Loader2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth, useUser } from "@clerk/nextjs";

export default function WordPressConnectPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { getToken, isSignedIn } = useAuth();
  const { user } = useUser();

  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // URLパラメータを取得
  const siteUrl = searchParams.get("site_url") || "";
  const siteName = searchParams.get("site_name") || "";
  const mcpEndpoint = searchParams.get("mcp_endpoint") || "";
  const registerEndpoint = searchParams.get("register_endpoint") || "";
  const registrationCode = searchParams.get("registration_code") || "";
  const callbackUrl = searchParams.get("callback_url") || "";

  const handleConnect = async () => {
    if (!isSignedIn) {
      router.push(`/sign-in?redirect_url=${encodeURIComponent(window.location.href)}`);
      return;
    }

    setConnecting(true);
    setError(null);

    try {
      const token = await getToken();
      const response = await fetch("/api/proxy/blog/connect/wordpress/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          site_url: siteUrl,
          site_name: siteName,
          mcp_endpoint: mcpEndpoint,
          register_endpoint: registerEndpoint,
          registration_code: registrationCode,
          callback_url: callbackUrl,
        }),
      });

      if (response.ok) {
        setSuccess(true);
        // 3秒後に設定ページにリダイレクト
        setTimeout(() => {
          router.push("/settings/integrations/wordpress");
        }, 3000);
      } else {
        const data = await response.json();
        setError(data.detail || "連携に失敗しました");
      }
    } catch (err) {
      setError("ネットワークエラーが発生しました");
    } finally {
      setConnecting(false);
    }
  };

  // パラメータがない場合
  if (!siteUrl || !mcpEndpoint || !registrationCode) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-amber-50/50 via-white to-emerald-50/30">
        <Card className="max-w-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-600">
              <AlertCircle className="w-5 h-5" />
              無効なリクエスト
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-stone-600">
              WordPressプラグインからの連携リクエストが正しくありません。
              WordPressの管理画面から再度連携を開始してください。
            </p>
            <Button
              variant="outline"
              onClick={() => router.push("/settings/integrations/wordpress")}
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              設定ページに戻る
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-amber-50/50 via-white to-emerald-50/30 p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-lg"
      >
        {success ? (
          <Card className="border-emerald-200 bg-emerald-50/50">
            <CardHeader className="text-center">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", duration: 0.5 }}
                className="w-16 h-16 rounded-full bg-emerald-500 flex items-center justify-center mx-auto mb-4"
              >
                <CheckCircle2 className="w-8 h-8 text-white" />
              </motion.div>
              <CardTitle className="text-emerald-700">連携が完了しました</CardTitle>
              <CardDescription>
                {siteName || siteUrl} との連携が正常に完了しました
              </CardDescription>
            </CardHeader>
            <CardContent className="text-center">
              <p className="text-stone-600 mb-4">
                まもなく設定ページにリダイレクトされます...
              </p>
              <Button
                variant="outline"
                onClick={() => router.push("/settings/integrations/wordpress")}
              >
                今すぐ設定ページへ
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader className="text-center">
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center mx-auto mb-4">
                <Link2 className="w-8 h-8 text-white" />
              </div>
              <CardTitle>WordPress連携の確認</CardTitle>
              <CardDescription>
                以下のWordPressサイトとの連携を許可しますか？
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* サイト情報 */}
              <div className="p-4 rounded-xl bg-stone-50 border border-stone-200">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-xl bg-blue-500 flex items-center justify-center">
                    <Globe className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <p className="font-semibold text-stone-800">
                      {siteName || "WordPress サイト"}
                    </p>
                    <p className="text-sm text-stone-500">{siteUrl}</p>
                  </div>
                </div>
              </div>

              {/* 許可内容 */}
              <div className="space-y-2">
                <p className="text-sm font-medium text-stone-700">
                  連携すると以下のことが可能になります：
                </p>
                <ul className="text-sm text-stone-600 space-y-1">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    過去の記事を分析してスタイルを学習
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    新しい記事を下書きとして作成
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    メディアライブラリに画像をアップロード
                  </li>
                </ul>
              </div>

              {/* エラー表示 */}
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm"
                >
                  {error}
                </motion.div>
              )}

              {/* ログイン状態の確認 */}
              {!isSignedIn && (
                <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-700 text-sm">
                  連携を完了するにはログインが必要です
                </div>
              )}

              {/* ボタン */}
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => router.push("/settings/integrations/wordpress")}
                >
                  キャンセル
                </Button>
                <Button
                  className="flex-1 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600"
                  onClick={handleConnect}
                  disabled={connecting}
                >
                  {connecting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      連携中...
                    </>
                  ) : isSignedIn ? (
                    "連携を許可する"
                  ) : (
                    "ログインして連携"
                  )}
                </Button>
              </div>

              {/* ユーザー情報 */}
              {isSignedIn && user && (
                <p className="text-xs text-center text-stone-400">
                  {user.primaryEmailAddress?.emailAddress} としてログイン中
                </p>
              )}
            </CardContent>
          </Card>
        )}
      </motion.div>
    </div>
  );
}
