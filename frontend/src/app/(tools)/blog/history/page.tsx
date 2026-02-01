"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  ChevronRight,
  ExternalLink,
  FileText,
  Globe,
  ImageIcon,
  Loader2,
  MessageCircle,
  PenLine,
  Plus,
  Sparkles,
  XCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/utils/cn";
import { useAuth } from "@clerk/nextjs";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BlogGenerationHistoryItem {
  id: string;
  status:
    | "pending"
    | "in_progress"
    | "completed"
    | "error"
    | "user_input_required"
    | "cancelled";
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
  wordpress_site_name?: string | null;
  wordpress_site_url?: string | null;
  image_count?: number;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ACTIVE_STATUSES = new Set([
  "in_progress",
  "pending",
  "user_input_required",
]);
const PAGE_SIZE = 20;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatRelative(dateString: string): string {
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
    month: "short",
    day: "numeric",
  });
}

function formatFullDate(dateString: string): string {
  return new Date(dateString).toLocaleString("ja-JP", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function groupByDate(
  items: BlogGenerationHistoryItem[]
): { label: string; items: BlogGenerationHistoryItem[] }[] {
  const groups = new Map<string, BlogGenerationHistoryItem[]>();

  for (const item of items) {
    const d = new Date(item.created_at);
    const now = new Date();
    const diffDays = Math.floor(
      (now.getTime() - d.getTime()) / 86400000
    );

    let key: string;
    if (diffDays === 0) key = "today";
    else if (diffDays === 1) key = "yesterday";
    else if (diffDays < 7) key = "thisWeek";
    else if (diffDays < 30) key = "thisMonth";
    else
      key = d.toLocaleDateString("ja-JP", {
        year: "numeric",
        month: "long",
      });

    const arr = groups.get(key) || [];
    arr.push(item);
    groups.set(key, arr);
  }

  const labelMap: Record<string, string> = {
    today: "今日",
    yesterday: "昨日",
    thisWeek: "今週",
    thisMonth: "今月",
  };

  return Array.from(groups.entries()).map(([key, items]) => ({
    label: labelMap[key] || key,
    items,
  }));
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function BlogHistoryPage() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [history, setHistory] = useState<BlogGenerationHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const offsetRef = useRef(0);

  // Track whether we have active items for polling (ref to avoid re-triggering effect)
  const hasActiveRef = useRef(false);

  const fetchHistory = useCallback(
    async (loadMore = false) => {
      if (loadMore) setLoadingMore(true);
      else if (!hasActiveRef.current) {
        // Only show loading spinner on initial load, not on poll refreshes
        setLoading(true);
        offsetRef.current = 0;
      }
      setError(null);

      try {
        const token = await getToken();
        const currentOffset = loadMore ? offsetRef.current : 0;
        const res = await fetch(
          `/api/proxy/blog/generation/history?limit=${PAGE_SIZE}&offset=${currentOffset}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );

        if (res.ok) {
          const data: BlogGenerationHistoryItem[] = await res.json();
          const items = Array.isArray(data) ? data : [];
          if (loadMore) setHistory((prev) => [...prev, ...items]);
          else setHistory(items);
          offsetRef.current = currentOffset + items.length;
          setHasMore(items.length === PAGE_SIZE);

          // Update active flag for polling
          hasActiveRef.current = items.some((h) =>
            ACTIVE_STATUSES.has(h.status)
          );
        } else {
          const errData = await res.json().catch(() => null);
          setError(
            errData?.detail
              ? typeof errData.detail === "string"
                ? errData.detail
                : "データの取得に失敗しました"
              : `サーバーエラー (${res.status})`
          );
        }
      } catch {
        setError("ネットワークエラーが発生しました");
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [getToken]
  );

  // Initial fetch
  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  // Auto-poll: start once and check hasActiveRef inside the interval
  useEffect(() => {
    const interval = setInterval(() => {
      if (hasActiveRef.current) {
        fetchHistory();
      }
    }, 12000);
    return () => clearInterval(interval);
  }, [fetchHistory]);

  const [showAllActive, setShowAllActive] = useState(false);
  const ACTIVE_PREVIEW_COUNT = 3;

  const activeItems = history.filter((h) => ACTIVE_STATUSES.has(h.status));
  const visibleActiveItems = showAllActive
    ? activeItems
    : activeItems.slice(0, ACTIVE_PREVIEW_COUNT);
  const hiddenActiveCount = activeItems.length - ACTIVE_PREVIEW_COUNT;
  const pastItems = history.filter((h) => !ACTIVE_STATUSES.has(h.status));
  const dateGroups = groupByDate(pastItems);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="max-w-3xl mx-auto px-4 py-4 md:px-6 md:py-8">
      {/* ─── Header ─── */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between mb-6"
      >
        <div>
          <h1 className="text-lg font-bold text-stone-800 tracking-tight">
            生成履歴
          </h1>
          <p className="text-xs text-stone-400 mt-0.5">
            {history.length > 0
              ? `${history.length}件の記事`
              : "ブログ記事の生成履歴"}
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => router.push("/blog/new")}
          className="rounded-xl bg-stone-800 hover:bg-stone-700 text-white shadow-none"
        >
          <Plus className="w-3.5 h-3.5 mr-1.5" />
          新規作成
        </Button>
      </motion.div>

      {/* ─── Error ─── */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden mb-4"
          >
            <div className="flex items-center gap-2 px-3 py-2.5 rounded-xl bg-red-50 border border-red-200/60 text-red-600 text-sm">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ─── Loading skeleton ─── */}
      {loading ? (
        <div className="space-y-3 mt-8">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="h-16 rounded-2xl bg-stone-100/60 animate-pulse"
              style={{ animationDelay: `${i * 100}ms` }}
            />
          ))}
        </div>
      ) : history.length === 0 && !error ? (
        /* ─── Empty state ─── */
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center py-20"
        >
          <div className="relative mb-6">
            <div className="w-16 h-16 rounded-3xl bg-gradient-to-br from-amber-100 to-emerald-100 flex items-center justify-center">
              <PenLine className="w-7 h-7 text-stone-400" />
            </div>
            <motion.div
              className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-custom-orange flex items-center justify-center"
              animate={{ scale: [1, 1.15, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <Sparkles className="w-3 h-3 text-white" />
            </motion.div>
          </div>
          <p className="text-stone-700 font-medium mb-1">
            まだ記事がありません
          </p>
          <p className="text-sm text-stone-400 mb-6 text-center max-w-xs">
            AIがリサーチからWordPress投稿まで自動で行います
          </p>
          <Button
            onClick={() => router.push("/blog/new")}
            className="rounded-xl bg-stone-800 hover:bg-stone-700"
          >
            最初の記事を作成する
            <ArrowRight className="w-4 h-4 ml-1.5" />
          </Button>
        </motion.div>
      ) : (
        <div className="space-y-6">
          {/* ═══════════════════════════════════════════
              ACTIVE ZONE — "Now"
          ═══════════════════════════════════════════ */}
          <AnimatePresence>
            {activeItems.length > 0 && (
              <motion.section
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                className="space-y-2.5"
              >
                <p className="text-[11px] font-semibold text-amber-600/80 uppercase tracking-widest px-1">
                  進行中
                  {activeItems.length > ACTIVE_PREVIEW_COUNT && (
                    <span className="ml-1.5 text-stone-400 normal-case tracking-normal">
                      {activeItems.length}件
                    </span>
                  )}
                </p>
                {visibleActiveItems.map((item, i) => (
                  <ActiveCard
                    key={item.id}
                    item={item}
                    index={i}
                    onClick={() => router.push(`/blog/${item.id}`)}
                  />
                ))}
                {!showAllActive && hiddenActiveCount > 0 && (
                  <button
                    onClick={() => setShowAllActive(true)}
                    className="w-full py-2 text-xs text-amber-600 hover:text-amber-700 transition-colors"
                  >
                    他 {hiddenActiveCount}件を表示
                  </button>
                )}
                {showAllActive && activeItems.length > ACTIVE_PREVIEW_COUNT && (
                  <button
                    onClick={() => setShowAllActive(false)}
                    className="w-full py-2 text-xs text-stone-400 hover:text-stone-600 transition-colors"
                  >
                    折りたたむ
                  </button>
                )}
              </motion.section>
            )}
          </AnimatePresence>

          {/* ═══════════════════════════════════════════
              PAST ZONE — date-grouped timeline
          ═══════════════════════════════════════════ */}
          {dateGroups.length > 0 && (
            <section className="space-y-5">
              {activeItems.length > 0 && pastItems.length > 0 && (
                <div className="h-px bg-stone-200/60" />
              )}
              {dateGroups.map((group, gi) => (
                <motion.div
                  key={group.label}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: gi * 0.04 }}
                >
                  <p className="text-[11px] font-semibold text-stone-400 uppercase tracking-widest px-1 mb-2">
                    {group.label}
                  </p>
                  <div className="rounded-2xl border border-stone-200/60 bg-white overflow-hidden divide-y divide-stone-100">
                    {group.items.map((item, i) => (
                      <PastRow
                        key={item.id}
                        item={item}
                        index={i}
                        onClick={() => router.push(`/blog/${item.id}`)}
                      />
                    ))}
                  </div>
                </motion.div>
              ))}

              {/* Load more */}
              {hasMore && (
                <div className="flex justify-center pt-2">
                  <button
                    onClick={() => fetchHistory(true)}
                    disabled={loadingMore}
                    className="text-sm text-stone-400 hover:text-stone-600 transition-colors disabled:opacity-50"
                  >
                    {loadingMore ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      "もっと見る"
                    )}
                  </button>
                </div>
              )}
            </section>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ActiveCard — breathing, prominent card for running/waiting items
// ---------------------------------------------------------------------------

function ActiveCard({
  item,
  index,
  onClick,
}: {
  item: BlogGenerationHistoryItem;
  index: number;
  onClick: () => void;
}) {
  const isWaiting = item.status === "user_input_required";
  const progress = item.progress_percentage;

  // SVG ring params
  const radius = 18;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <motion.button
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
      onClick={onClick}
      className={cn(
        "w-full text-left rounded-2xl p-4 transition-all group relative overflow-hidden",
        isWaiting
          ? "bg-gradient-to-r from-blue-50 to-indigo-50/50 border border-blue-200/50 hover:border-blue-300/70"
          : "bg-gradient-to-r from-amber-50/80 to-orange-50/40 border border-amber-200/50 hover:border-amber-300/70"
      )}
    >
      {/* Subtle animated gradient overlay */}
      <motion.div
        className={cn(
          "absolute inset-0 opacity-[0.03]",
          isWaiting
            ? "bg-gradient-to-r from-blue-400 to-indigo-400"
            : "bg-gradient-to-r from-amber-400 to-orange-400"
        )}
        animate={{ opacity: [0.03, 0.06, 0.03] }}
        transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
      />

      <div className="relative flex items-center gap-3.5">
        {/* Progress ring */}
        <div className="relative flex-shrink-0 w-11 h-11">
          <svg
            className="w-11 h-11 -rotate-90"
            viewBox="0 0 44 44"
          >
            <circle
              cx="22"
              cy="22"
              r={radius}
              fill="none"
              stroke={isWaiting ? "#dbeafe" : "#fde68a"}
              strokeWidth="3"
            />
            <motion.circle
              cx="22"
              cy="22"
              r={radius}
              fill="none"
              stroke={isWaiting ? "#3b82f6" : "#f59e0b"}
              strokeWidth="3"
              strokeLinecap="round"
              strokeDasharray={circumference}
              initial={{ strokeDashoffset: circumference }}
              animate={{ strokeDashoffset }}
              transition={{ duration: 0.8, ease: "easeOut" }}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            {isWaiting ? (
              <MessageCircle className="w-4 h-4 text-blue-500" />
            ) : item.status === "pending" ? (
              <Loader2 className="w-4 h-4 text-amber-500 animate-spin" />
            ) : (
              <span className="text-[10px] font-bold tabular-nums text-amber-700">
                {progress}
              </span>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-stone-700 truncate">
            {item.user_prompt || "（プロンプトなし）"}
          </p>
          <div className="flex items-center gap-2 mt-1">
            {isWaiting ? (
              <span className="text-xs font-medium text-blue-600">
                入力を待っています
              </span>
            ) : item.current_step_name ? (
              <span className="text-xs text-amber-600">
                {item.current_step_name}
              </span>
            ) : (
              <span className="text-xs text-stone-400">準備中...</span>
            )}
            <span className="text-[10px] text-stone-300">
              {formatRelative(item.created_at)}
            </span>
          </div>
        </div>

        {/* Action hint */}
        <div className="flex-shrink-0">
          {isWaiting ? (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-blue-500 text-white text-xs font-medium shadow-sm">
              回答する
            </span>
          ) : (
            <ChevronRight className="w-4 h-4 text-stone-300 group-hover:text-stone-500 transition-colors" />
          )}
        </div>
      </div>
    </motion.button>
  );
}

// ---------------------------------------------------------------------------
// PastRow — compact, dense row for completed/error/cancelled items
// ---------------------------------------------------------------------------

function PastRow({
  item,
  index,
  onClick,
}: {
  item: BlogGenerationHistoryItem;
  index: number;
  onClick: () => void;
}) {
  const isCompleted = item.status === "completed";
  const isError = item.status === "error";

  return (
    <motion.button
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: Math.min(index * 0.02, 0.2) }}
      onClick={onClick}
      className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-stone-50/80 active:bg-stone-100/60 transition-colors group"
    >
      {/* Status icon */}
      <div className="flex-shrink-0">
        {isCompleted ? (
          <div className="w-7 h-7 rounded-lg bg-emerald-50 flex items-center justify-center">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
          </div>
        ) : isError ? (
          <div className="w-7 h-7 rounded-lg bg-red-50 flex items-center justify-center">
            <XCircle className="w-3.5 h-3.5 text-red-400" />
          </div>
        ) : (
          <div className="w-7 h-7 rounded-lg bg-stone-100 flex items-center justify-center">
            <XCircle className="w-3.5 h-3.5 text-stone-400" />
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            "text-sm truncate",
            isCompleted ? "text-stone-700" : "text-stone-400"
          )}
        >
          {item.user_prompt || "（プロンプトなし）"}
        </p>
        <div className="flex items-center gap-1.5 mt-0.5">
          <span
            className="text-[11px] text-stone-400"
            title={formatFullDate(item.created_at)}
          >
            {formatRelative(item.created_at)}
          </span>
          {isError && item.error_message && (
            <>
              <span className="text-stone-300">·</span>
              <span className="text-[11px] text-red-400 truncate max-w-[180px]">
                {item.error_message}
              </span>
            </>
          )}
          {item.wordpress_site_name && (
            <>
              <span className="text-stone-300">·</span>
              <span className="text-[11px] text-stone-400 flex items-center gap-0.5">
                <Globe className="w-2.5 h-2.5" />
                {item.wordpress_site_name}
              </span>
            </>
          )}
          {item.image_count != null && item.image_count > 0 && (
            <>
              <span className="text-stone-300">·</span>
              <span className="text-[11px] text-stone-400 flex items-center gap-0.5">
                <ImageIcon className="w-2.5 h-2.5" />
                {item.image_count}
              </span>
            </>
          )}
        </div>
      </div>

      {/* Right actions */}
      <div className="flex-shrink-0 flex items-center gap-1">
        {isCompleted && item.draft_preview_url && (
          <a
            href={item.draft_preview_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-medium text-emerald-700 bg-emerald-50 hover:bg-emerald-100 transition-colors"
            title="WordPressで開く"
          >
            <ExternalLink className="w-3 h-3" />
            <span className="hidden sm:inline">開く</span>
          </a>
        )}
        <ChevronRight className="w-4 h-4 text-stone-300 group-hover:text-stone-500 transition-colors" />
      </div>
    </motion.button>
  );
}
