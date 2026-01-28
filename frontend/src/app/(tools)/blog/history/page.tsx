"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Edit3,
  ExternalLink,
  Eye,
  FileText,
  Loader2,
  MessageSquareWarning,
  Plus,
  RefreshCw,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@clerk/nextjs";

interface BlogGenerationHistoryItem {
  id: string;
  status: "pending" | "in_progress" | "completed" | "error" | "user_input_required" | "cancelled";
  current_step_name: string | null;
  progress_percentage: number;
  user_prompt: string | null;
  reference_url: string | null;
  draft_post_id: number | null;
  draft_preview_url: string | null;
  draft_edit_url: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

const statusConfig = {
  pending: {
    label: "待機中",
    icon: Clock,
    color: "bg-stone-100 text-stone-600 border-stone-200",
  },
  in_progress: {
    label: "生成中",
    icon: Loader2,
    color: "bg-amber-50 text-amber-700 border-amber-200",
  },
  completed: {
    label: "完了",
    icon: CheckCircle2,
    color: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  error: {
    label: "エラー",
    icon: XCircle,
    color: "bg-red-50 text-red-700 border-red-200",
  },
  user_input_required: {
    label: "入力待ち",
    icon: MessageSquareWarning,
    color: "bg-blue-50 text-blue-700 border-blue-200",
  },
  cancelled: {
    label: "キャンセル",
    icon: XCircle,
    color: "bg-stone-100 text-stone-500 border-stone-200",
  },
};

export default function BlogHistoryPage() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [history, setHistory] = useState<BlogGenerationHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await getToken();
      const response = await fetch("/api/proxy/blog/generation/history?limit=50", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setHistory(Array.isArray(data) ? data : []);
      } else {
        const errData = await response.json().catch(() => null);
        setError(
          errData?.detail
            ? typeof errData.detail === "string"
              ? errData.detail
              : "データの取得に失敗しました"
            : `サーバーエラー (${response.status})`
        );
      }
    } catch (err) {
      console.error("Failed to fetch history:", err);
      setError("ネットワークエラーが発生しました");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    const diffHour = Math.floor(diffMs / 3600000);
    const diffDay = Math.floor(diffMs / 86400000);

    if (diffMin < 1) return "たった今";
    if (diffMin < 60) return `${diffMin}分前`;
    if (diffHour < 24) return `${diffHour}時間前`;
    if (diffDay < 7) return `${diffDay}日前`;

    return date.toLocaleDateString("ja-JP", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const formatFullDate = (dateString: string) => {
    return new Date(dateString).toLocaleString("ja-JP", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const truncateText = (text: string | null, maxLength: number) => {
    if (!text) return "";
    return text.length > maxLength ? text.substring(0, maxLength) + "..." : text;
  };

  const handleCardClick = (item: BlogGenerationHistoryItem) => {
    // どのステータスでも詳細ページへ遷移可能
    router.push(`/blog/${item.id}`);
  };

  // ステータス別に分類
  const activeItems = history.filter(
    (h) => h.status === "in_progress" || h.status === "user_input_required" || h.status === "pending"
  );
  const completedItems = history.filter((h) => h.status === "completed");
  const otherItems = history.filter(
    (h) => h.status === "error" || h.status === "cancelled"
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50/50 via-white to-emerald-50/30">
      <div className="max-w-4xl mx-auto px-6 py-10">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center justify-between mb-8"
        >
          <div>
            <h1 className="text-3xl font-bold text-stone-800 mb-1">生成履歴</h1>
            <p className="text-stone-500 text-sm">
              過去に生成したブログ記事の一覧です
              {history.length > 0 && (
                <span className="ml-2 text-stone-400">({history.length}件)</span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={fetchHistory}
              disabled={loading}
              className="text-stone-500"
            >
              <RefreshCw className={`w-4 h-4 mr-1.5 ${loading ? "animate-spin" : ""}`} />
              更新
            </Button>
            <Button
              size="sm"
              onClick={() => router.push("/blog/new")}
            >
              <Plus className="w-4 h-4 mr-1.5" />
              新規作成
            </Button>
          </div>
        </motion.div>

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm mb-6"
            >
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
          </div>
        ) : history.length === 0 && !error ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center py-20"
          >
            <FileText className="w-16 h-16 text-stone-300 mx-auto mb-4" />
            <p className="text-lg text-stone-500 mb-2">まだ生成履歴がありません</p>
            <p className="text-sm text-stone-400 mb-6">
              ブログ記事を作成すると、ここに履歴が表示されます
            </p>
            <Button onClick={() => router.push("/blog/new")}>
              新規ブログ記事を作成
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </motion.div>
        ) : (
          <div className="space-y-8">
            {/* 進行中 */}
            {activeItems.length > 0 && (
              <section>
                <h2 className="text-sm font-semibold text-stone-400 uppercase tracking-wider mb-3">
                  進行中
                </h2>
                <div className="space-y-3">
                  {activeItems.map((item, index) => (
                    <HistoryCard
                      key={item.id}
                      item={item}
                      index={index}
                      formatDate={formatDate}
                      formatFullDate={formatFullDate}
                      truncateText={truncateText}
                      onClick={() => handleCardClick(item)}
                    />
                  ))}
                </div>
              </section>
            )}

            {/* 完了済み */}
            {completedItems.length > 0 && (
              <section>
                <h2 className="text-sm font-semibold text-stone-400 uppercase tracking-wider mb-3">
                  完了済み
                </h2>
                <div className="space-y-3">
                  {completedItems.map((item, index) => (
                    <HistoryCard
                      key={item.id}
                      item={item}
                      index={index}
                      formatDate={formatDate}
                      formatFullDate={formatFullDate}
                      truncateText={truncateText}
                      onClick={() => handleCardClick(item)}
                    />
                  ))}
                </div>
              </section>
            )}

            {/* エラー・キャンセル */}
            {otherItems.length > 0 && (
              <section>
                <h2 className="text-sm font-semibold text-stone-400 uppercase tracking-wider mb-3">
                  その他
                </h2>
                <div className="space-y-3">
                  {otherItems.map((item, index) => (
                    <HistoryCard
                      key={item.id}
                      item={item}
                      index={index}
                      formatDate={formatDate}
                      formatFullDate={formatFullDate}
                      truncateText={truncateText}
                      onClick={() => handleCardClick(item)}
                    />
                  ))}
                </div>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function HistoryCard({
  item,
  index,
  formatDate,
  formatFullDate,
  truncateText,
  onClick,
}: {
  item: BlogGenerationHistoryItem;
  index: number;
  formatDate: (d: string) => string;
  formatFullDate: (d: string) => string;
  truncateText: (t: string | null, max: number) => string;
  onClick: () => void;
}) {
  const status = statusConfig[item.status];
  const StatusIcon = status.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
      className="bg-white rounded-2xl border border-stone-200 p-5 hover:border-stone-300 hover:shadow-md transition-all cursor-pointer group"
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* ステータス + 日時 */}
          <div className="flex items-center gap-2 mb-2.5">
            <Badge
              variant="outline"
              className={`${status.color} text-xs font-medium px-2 py-0.5`}
            >
              <StatusIcon
                className={`w-3 h-3 mr-1 ${
                  item.status === "in_progress" ? "animate-spin" : ""
                }`}
              />
              {status.label}
            </Badge>
            <span
              className="text-xs text-stone-400"
              title={formatFullDate(item.created_at)}
            >
              {formatDate(item.created_at)}
            </span>
          </div>

          {/* プロンプト */}
          <p className="text-stone-800 text-sm font-medium leading-relaxed mb-1">
            {truncateText(item.user_prompt, 120) || "（プロンプトなし）"}
          </p>

          {/* 参考URL */}
          {item.reference_url && (
            <p className="text-xs text-stone-400 truncate">
              参考: {item.reference_url}
            </p>
          )}

          {/* 進行状況バー */}
          {item.status === "in_progress" && (
            <div className="flex items-center gap-2 mt-3">
              <div className="flex-1 bg-stone-100 rounded-full h-1.5 max-w-xs">
                <div
                  className="bg-amber-500 h-1.5 rounded-full transition-all duration-500"
                  style={{ width: `${item.progress_percentage}%` }}
                />
              </div>
              <span className="text-xs text-stone-400 tabular-nums">
                {item.progress_percentage}%
              </span>
            </div>
          )}

          {/* ステップ名 */}
          {item.status === "in_progress" && item.current_step_name && (
            <p className="text-xs text-amber-600 mt-1.5">
              {item.current_step_name}
            </p>
          )}

          {/* エラーメッセージ */}
          {item.error_message && (
            <p className="text-xs text-red-500 mt-2 bg-red-50 rounded-lg px-2.5 py-1.5 inline-block">
              {truncateText(item.error_message, 100)}
            </p>
          )}
        </div>

        {/* アクションボタン */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {item.status === "completed" && item.draft_preview_url && (
            <Button
              variant="outline"
              size="sm"
              className="h-8 px-2.5 text-xs"
              asChild
              onClick={(e) => e.stopPropagation()}
            >
              <a
                href={item.draft_preview_url}
                target="_blank"
                rel="noopener noreferrer"
                title="プレビュー"
              >
                <Eye className="w-3.5 h-3.5 mr-1" />
                プレビュー
              </a>
            </Button>
          )}
          {item.status === "completed" && item.draft_edit_url && (
            <Button
              variant="outline"
              size="sm"
              className="h-8 px-2.5 text-xs"
              asChild
              onClick={(e) => e.stopPropagation()}
            >
              <a
                href={item.draft_edit_url}
                target="_blank"
                rel="noopener noreferrer"
                title="編集"
              >
                <Edit3 className="w-3.5 h-3.5 mr-1" />
                編集
              </a>
            </Button>
          )}
          {(item.status === "in_progress" ||
            item.status === "user_input_required" ||
            item.status === "pending") && (
            <Button
              variant="outline"
              size="sm"
              className="h-8 px-2.5 text-xs"
              onClick={(e) => {
                e.stopPropagation();
                onClick();
              }}
            >
              {item.status === "user_input_required" ? "回答する" : "詳細"}
              <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </Button>
          )}
          {/* どのステータスでもカード全体クリックで詳細遷移可能を示す矢印 */}
          <ArrowRight className="w-4 h-4 text-stone-300 group-hover:text-stone-500 transition-colors ml-1" />
        </div>
      </div>
    </motion.div>
  );
}
