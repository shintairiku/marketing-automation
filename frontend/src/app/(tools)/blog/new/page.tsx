"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence,motion } from "framer-motion";
import {
  AlertCircle,
  Building2,
  CheckCircle2,
  ChevronRight,
  Globe,
  ImagePlus,
  Link2,
  Loader2,
  PenLine,
  Sparkles,
  User,
  X,
} from "lucide-react";

import { useSubscription } from "@/components/subscription/subscription-guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { compressImages } from "@/utils/image-compress";
import { useAuth } from "@clerk/nextjs";

interface WordPressSite {
  id: string;
  site_url: string;
  site_name: string | null;
  connection_status: "connected" | "disconnected" | "error";
  is_active: boolean;
  organization_id: string | null;
  organization_name: string | null;
}

interface SiteGroup {
  key: string;
  label: string;
  icon: "personal" | "org";
  sites: WordPressSite[];
}

export default function BlogNewPage() {
  const router = useRouter();
  const { getToken } = useAuth();
  const { usage, subscription } = useSubscription();

  const [sites, setSites] = useState<WordPressSite[]>([]);
  const [loadingSites, setLoadingSites] = useState(true);
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null);
  const [userPrompt, setUserPrompt] = useState("");
  const [referenceUrl, setReferenceUrl] = useState("");
  const [selectedImages, setSelectedImages] = useState<File[]>([]);
  const [imagePreviewUrls, setImagePreviewUrls] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [compressingImages, setCompressingImages] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;

    const total = selectedImages.length + files.length;
    if (total > 5) {
      setError("画像は最大5枚までです");
      return;
    }

    setSelectedImages((prev) => [...prev, ...files]);
    files.forEach((file) => {
      const url = URL.createObjectURL(file);
      setImagePreviewUrls((prev) => [...prev, url]);
    });
  };

  const handleRemoveImage = (index: number) => {
    setSelectedImages((prev) => prev.filter((_, i) => i !== index));
    setImagePreviewUrls((prev) => {
      URL.revokeObjectURL(prev[index]);
      return prev.filter((_, i) => i !== index);
    });
  };

  useEffect(() => {
    const fetchSites = async () => {
      try {
        const token = await getToken();
        const response = await fetch("/api/proxy/blog/sites", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          setSites(data.sites.filter((s: WordPressSite) => s.connection_status === "connected"));
          // Auto-select active site
          const activeSite = data.sites.find((s: WordPressSite) => s.is_active);
          if (activeSite) {
            setSelectedSiteId(activeSite.id);
          }
        }
      } catch (err) {
        console.error("Failed to fetch sites:", err);
      } finally {
        setLoadingSites(false);
      }
    };
    fetchSites();
  }, [getToken]);

  const handleSubmit = async () => {
    if (!selectedSiteId || !userPrompt.trim()) {
      setError("WordPressサイトを選択し、記事の内容を入力してください");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const token = await getToken();

      // 画像を圧縮（大きい画像をプロキシ経由で送れるようにする）
      let imagesToUpload = selectedImages;
      if (selectedImages.length > 0) {
        setCompressingImages(true);
        try {
          imagesToUpload = await compressImages(selectedImages);
        } finally {
          setCompressingImages(false);
        }
      }

      // FormData で送信（画像あり・なし共通）
      const formData = new FormData();
      formData.append("user_prompt", userPrompt);
      formData.append("wordpress_site_id", selectedSiteId);
      if (referenceUrl) {
        formData.append("reference_url", referenceUrl);
      }
      for (const img of imagesToUpload) {
        formData.append("files", img);
      }

      const response = await fetch("/api/proxy/blog/generation/start", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        router.push(`/blog/${data.id}`);
      } else if (response.status === 429) {
        setError("月間記事生成の上限に達しました。追加の記事生成をご希望の場合はお問い合わせください。");
      } else {
        const errData = await response.json();
        // FastAPIの422バリデーションエラーはdetailが配列
        if (Array.isArray(errData.detail)) {
          const messages = errData.detail.map(
            (e: { msg?: string; loc?: string[] }) =>
              e.msg || "バリデーションエラー"
          );
          setError(messages.join("、"));
        } else {
          setError(
            typeof errData.detail === "string"
              ? errData.detail
              : "生成の開始に失敗しました"
          );
        }
      }
    } catch (err) {
      setError("ネットワークエラーが発生しました");
    } finally {
      setIsSubmitting(false);
    }
  };

  const connectedSites = sites.filter(s => s.connection_status === "connected");

  // 使用量情報
  const isAtLimit = usage ? usage.remaining <= 0 : false;
  const isPrivileged = subscription?.is_privileged ?? false;

  const siteGroups = useMemo((): SiteGroup[] => {
    const personalSites: WordPressSite[] = [];
    const orgMap = new Map<string, WordPressSite[]>();

    for (const site of connectedSites) {
      if (site.organization_id) {
        const existing = orgMap.get(site.organization_id) || [];
        existing.push(site);
        orgMap.set(site.organization_id, existing);
      } else {
        personalSites.push(site);
      }
    }

    const groups: SiteGroup[] = [];

    if (personalSites.length > 0) {
      groups.push({
        key: "personal",
        label: "個人のサイト",
        icon: "personal",
        sites: personalSites,
      });
    }

    for (const [orgId, orgSites] of orgMap) {
      const orgName = orgSites[0]?.organization_name || "組織";
      groups.push({
        key: orgId,
        label: orgName,
        icon: "org",
        sites: orgSites,
      });
    }

    return groups;
  }, [connectedSites]);

  return (
    <div className="bg-gradient-to-br from-amber-50/50 via-white to-emerald-50/30">
      {/* Decorative background elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="hidden md:block absolute top-20 right-20 w-72 h-72 bg-amber-200/20 rounded-full blur-3xl" />
        <div className="hidden md:block absolute bottom-40 left-10 w-96 h-96 bg-emerald-200/20 rounded-full blur-3xl" />
        <div className="hidden md:block absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-radial from-orange-100/10 to-transparent rounded-full" />
      </div>

      <div className="relative max-w-3xl mx-auto px-4 py-6 md:px-6 md:py-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
          className="text-center mb-8 md:mb-12"
        >
          <h1 className="text-4xl md:text-5xl font-bold text-stone-800 tracking-tight mb-4">
            新しいブログ記事を
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-600 to-emerald-600">
              つくる
            </span>
          </h1>
          <p className="text-lg text-stone-500 max-w-lg mx-auto leading-relaxed">
            過去の記事スタイルを参考に、あなたのWordPressサイトにぴったりの記事を生成します
          </p>
        </motion.div>

        {/* Usage Info */}
        {usage && !isPrivileged && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.15 }}
            className={`mx-auto w-full max-w-md px-4 py-3 rounded-2xl border mb-6 ${
              isAtLimit
                ? 'bg-red-50/80 border-red-200'
                : usage.remaining <= (usage.total_limit * 0.2)
                ? 'bg-amber-50/80 border-amber-200'
                : 'bg-white/60 border-stone-200'
            }`}
          >
            <div className="flex items-center justify-between text-sm mb-1.5">
              <span className={isAtLimit ? 'text-red-700 font-medium' : 'text-stone-600'}>
                今月の記事生成
              </span>
              <span className={`font-semibold ${isAtLimit ? 'text-red-700' : 'text-stone-800'}`}>
                {usage.articles_generated} / {usage.total_limit}
              </span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-stone-200 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  isAtLimit ? 'bg-red-500' : usage.remaining <= (usage.total_limit * 0.2) ? 'bg-amber-500' : 'bg-emerald-500'
                }`}
                style={{ width: `${usage.total_limit > 0 ? Math.min(100, (usage.articles_generated / usage.total_limit) * 100) : 0}%` }}
              />
            </div>
            {isAtLimit && (
              <p className="text-xs text-red-600 mt-1.5">
                上限に達しました。追加の記事生成をご希望の場合は
                <a href="/settings/contact" className="underline ml-1">お問い合わせ</a>
                ください。
              </p>
            )}
          </motion.div>
        )}

        {/* Main Form */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
          className="space-y-8"
        >
          {/* WordPress Site Selector */}
          <div className="space-y-3">
            <Label className="flex items-center gap-2 text-stone-700 font-medium">
              <Globe className="w-4 h-4 text-emerald-600" />
              投稿先のWordPressサイト
            </Label>

            {loadingSites ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-stone-400" />
              </div>
            ) : connectedSites.length === 0 ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="p-6 rounded-2xl border-2 border-dashed border-stone-200 bg-stone-50/50 text-center"
              >
                <AlertCircle className="w-10 h-10 text-stone-400 mx-auto mb-3" />
                <p className="text-stone-600 font-medium mb-2">WordPressサイトが連携されていません</p>
                <p className="text-sm text-stone-500 mb-4">
                  ブログ記事を作成するには、まずWordPressサイトを連携してください
                </p>
                <Button
                  variant="outline"
                  onClick={() => router.push("/settings/integrations/wordpress")}
                  className="rounded-xl"
                >
                  WordPress連携設定へ
                  <ChevronRight className="w-4 h-4 ml-1" />
                </Button>
              </motion.div>
            ) : (
              <div className="space-y-4">
                {siteGroups.map((group) => (
                  <div key={group.key} className="space-y-2">
                    {/* Group Header */}
                    {siteGroups.length > 1 && (
                      <div className="flex items-center gap-2 px-1">
                        {group.icon === "personal" ? (
                          <User className="w-3.5 h-3.5 text-stone-400" />
                        ) : (
                          <Building2 className="w-3.5 h-3.5 text-blue-500" />
                        )}
                        <span className="text-xs font-semibold text-stone-400 uppercase tracking-wider">
                          {group.label}
                        </span>
                      </div>
                    )}
                    <div className="grid gap-3">
                      <AnimatePresence mode="popLayout">
                        {group.sites.map((site, index) => (
                          <motion.button
                            key={site.id}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.05 }}
                            onClick={() => setSelectedSiteId(site.id)}
                            className={`
                              relative w-full p-4 rounded-2xl border-2 text-left transition-all duration-200
                              ${selectedSiteId === site.id
                                ? "border-emerald-400 bg-emerald-50/50 shadow-lg shadow-emerald-100/50"
                                : "border-stone-200 bg-white/80 hover:border-stone-300 hover:bg-white"
                              }
                            `}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                <div className={`
                                  w-10 h-10 rounded-xl flex items-center justify-center
                                  ${selectedSiteId === site.id ? "bg-emerald-500" : "bg-stone-200"}
                                `}>
                                  <Globe className={`w-5 h-5 ${selectedSiteId === site.id ? "text-white" : "text-stone-500"}`} />
                                </div>
                                <div>
                                  <div className="flex items-center gap-2">
                                    <p className="font-medium text-stone-800">
                                      {site.site_name || site.site_url}
                                    </p>
                                    {site.organization_name && (
                                      <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                                        {site.organization_name}
                                      </Badge>
                                    )}
                                  </div>
                                  <p className="text-sm text-stone-500 truncate max-w-xs">
                                    {site.site_url}
                                  </p>
                                </div>
                              </div>
                              {selectedSiteId === site.id && (
                                <motion.div
                                  initial={{ scale: 0 }}
                                  animate={{ scale: 1 }}
                                  className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center"
                                >
                                  <CheckCircle2 className="w-4 h-4 text-white" />
                                </motion.div>
                              )}
                            </div>
                          </motion.button>
                        ))}
                      </AnimatePresence>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Main Prompt Input */}
          <div className="space-y-3">
            <Label className="flex items-center gap-2 text-stone-700 font-medium">
              <PenLine className="w-4 h-4 text-amber-600" />
              どんな記事を作りたいですか？
            </Label>
            <div className="relative">
              <Textarea
                value={userPrompt}
                onChange={(e) => setUserPrompt(e.target.value)}
                placeholder="例: 新入社員向けのビジネスマナー講座について、親しみやすいトーンで解説する記事を書きたい。具体的なシーン別の例を多く含めてほしい。"
                className="min-h-[160px] text-base rounded-2xl border-2 border-stone-200 bg-white/80 backdrop-blur-sm resize-none focus:border-amber-400 focus:ring-amber-100 placeholder:text-stone-400 p-4"
              />
              <div className="absolute bottom-3 right-3 text-xs text-stone-400">
                {userPrompt.length} / 2000
              </div>
            </div>
          </div>

          {/* Reference URL Input */}
          <div className="space-y-3">
            <Label className="flex items-center gap-2 text-stone-700 font-medium">
              <Link2 className="w-4 h-4 text-stone-500" />
              参考にする記事URL
              <span className="text-xs font-normal text-stone-400 ml-1">(任意)</span>
            </Label>
            <Input
              type="url"
              value={referenceUrl}
              onChange={(e) => setReferenceUrl(e.target.value)}
              placeholder="https://your-wordpress.com/sample-article/"
              className="h-12 rounded-2xl border-2 border-stone-200 bg-white/80 backdrop-blur-sm focus:border-amber-400 focus:ring-amber-100 placeholder:text-stone-400"
            />
            <p className="text-sm text-stone-500">
              あなたのサイト内の記事URLを指定すると、そのスタイルやトーンを参考に記事を生成します
            </p>
          </div>

          {/* Image Upload */}
          <div className="space-y-3">
            <Label className="flex items-center gap-2 text-stone-700 font-medium">
              <ImagePlus className="w-4 h-4 text-emerald-600" />
              記事に含めたい画像
              <span className="text-xs font-normal text-stone-400 ml-1">(任意・最大5枚)</span>
            </Label>

            <label className="flex items-center justify-center w-full h-28 border-2 border-dashed border-stone-200 rounded-2xl bg-white/60 hover:bg-stone-50 hover:border-stone-300 cursor-pointer transition-all">
              <div className="text-center">
                <ImagePlus className="w-7 h-7 text-stone-400 mx-auto mb-1.5" />
                <p className="text-sm text-stone-600 font-medium">クリックして画像を選択</p>
                <p className="text-xs text-stone-400 mt-0.5">JPG, PNG, WebP</p>
              </div>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                multiple
                onChange={handleImageSelect}
                className="hidden"
              />
            </label>

            {imagePreviewUrls.length > 0 && (
              <div className="grid grid-cols-3 sm:grid-cols-5 gap-3">
                {imagePreviewUrls.map((url, idx) => (
                  <div key={idx} className="relative group aspect-square">
                    <img
                      src={url}
                      alt={`プレビュー ${idx + 1}`}
                      className="w-full h-full object-cover rounded-xl border border-stone-200"
                    />
                    <button
                      type="button"
                      onClick={() => handleRemoveImage(idx)}
                      className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-red-500 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-sm"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <p className="text-sm text-stone-500">
              アップロードした画像はAIが内容を理解し、記事内に適切に配置します
            </p>
          </div>

          {/* Error Message */}
          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm"
              >
                {error}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Submit Button */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="pt-4"
          >
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting || !selectedSiteId || !userPrompt.trim() || loadingSites || (isAtLimit && !isPrivileged)}
              className={`
                w-full h-14 text-lg font-medium rounded-2xl transition-all duration-300
                ${isSubmitting || !selectedSiteId || !userPrompt.trim() || (isAtLimit && !isPrivileged)
                  ? "bg-stone-200 text-stone-500 cursor-not-allowed"
                  : "bg-gradient-to-r from-amber-500 via-orange-500 to-emerald-500 text-white shadow-lg shadow-orange-200/50 hover:shadow-xl hover:shadow-orange-300/50 hover:scale-[1.02]"
                }
              `}
            >
              {isSubmitting && compressingImages ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  画像を最適化中...
                </span>
              ) : isSubmitting ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  生成を開始中...
                </span>
              ) : isAtLimit && !isPrivileged ? (
                <span className="flex items-center gap-2">
                  <AlertCircle className="w-5 h-5" />
                  月間上限に達しています
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5" />
                  ブログ記事を生成する
                </span>
              )}
            </Button>
          </motion.div>

          {/* Info Footer */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="text-center text-sm text-stone-400 pt-4"
          >
            AIが参考記事を分析し、必要に応じて追加情報をお聞きします。
            <br />
            最終的に下書きとしてWordPressに保存されます。
          </motion.p>
        </motion.div>
      </div>
    </div>
  );
}
