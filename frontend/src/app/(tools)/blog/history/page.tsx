"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Clock,
  Edit3,
  ExternalLink,
  FileText,
  Loader2,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@clerk/nextjs";

interface BlogGenerationState {
  id: string;
  status: "pending" | "in_progress" | "completed" | "error" | "user_input_required" | "cancelled";
  current_step_name: string | null;
  progress_percentage: number;
  user_prompt: string | null;
  draft_post_id: number | null;
  draft_preview_url: string | null;
  draft_edit_url: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

const statusConfig = {
  pending: { label: "待機中", icon: Clock, color: "bg-stone-100 text-stone-600" },
  in_progress: { label: "生成中", icon: Loader2, color: "bg-amber-100 text-amber-700" },
  completed: { label: "完了", icon: CheckCircle2, color: "bg-emerald-100 text-emerald-700" },
  error: { label: "エラー", icon: XCircle, color: "bg-red-100 text-red-700" },
  user_input_required: { label: "入力待ち", icon: AlertCircle, color: "bg-amber-100 text-amber-700" },
  cancelled: { label: "キャンセル", icon: XCircle, color: "bg-stone-100 text-stone-600" },
};

export default function BlogHistoryPage() {
  const router = useRouter();
  const { getToken } = useAuth();
  const [history, setHistory] = useState<BlogGenerationState[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const token = await getToken();
        const response = await fetch("/api/proxy/blog/generation/history?limit=50", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          setHistory(data);
        }
      } catch (err) {
        console.error("Failed to fetch history:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [getToken]);

  const formatDate = (dateString: string) => {
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50/50 via-white to-emerald-50/30">
      <div className="max-w-4xl mx-auto px-6 py-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-3xl font-bold text-stone-800 mb-2">生成履歴</h1>
          <p className="text-stone-500">過去に生成したブログ記事の一覧です</p>
        </motion.div>

        {/* Content */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
          </div>
        ) : history.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-center py-20"
          >
            <FileText className="w-16 h-16 text-stone-300 mx-auto mb-4" />
            <p className="text-lg text-stone-500 mb-4">まだ生成履歴がありません</p>
            <Button onClick={() => router.push("/blog/new")}>
              新規ブログ記事を作成
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-4"
          >
            {history.map((item, index) => {
              const status = statusConfig[item.status];
              const StatusIcon = status.icon;

              return (
                <motion.div
                  key={item.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                  className="bg-white rounded-2xl border border-stone-200 p-5 hover:border-stone-300 hover:shadow-md transition-all cursor-pointer"
                  onClick={() =>
                    item.status === "completed"
                      ? null
                      : router.push(`/blog/${item.id}`)
                  }
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge className={status.color}>
                          <StatusIcon
                            className={`w-3 h-3 mr-1 ${
                              item.status === "in_progress" ? "animate-spin" : ""
                            }`}
                          />
                          {status.label}
                        </Badge>
                        <span className="text-xs text-stone-400">
                          {formatDate(item.created_at)}
                        </span>
                      </div>
                      <p className="text-stone-800 font-medium mb-1">
                        {truncateText(item.user_prompt, 100)}
                      </p>
                      {item.status === "in_progress" && (
                        <div className="flex items-center gap-2 mt-2">
                          <div className="flex-1 bg-stone-200 rounded-full h-1.5 max-w-xs">
                            <div
                              className="bg-amber-500 h-1.5 rounded-full transition-all"
                              style={{ width: `${item.progress_percentage}%` }}
                            />
                          </div>
                          <span className="text-xs text-stone-400">
                            {item.progress_percentage}%
                          </span>
                        </div>
                      )}
                      {item.error_message && (
                        <p className="text-sm text-red-500 mt-1">
                          {truncateText(item.error_message, 80)}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      {item.status === "completed" && item.draft_preview_url && (
                        <Button
                          variant="outline"
                          size="sm"
                          asChild
                          onClick={(e) => e.stopPropagation()}
                        >
                          <a
                            href={item.draft_preview_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        </Button>
                      )}
                      {item.status === "completed" && item.draft_edit_url && (
                        <Button
                          variant="outline"
                          size="sm"
                          asChild
                          onClick={(e) => e.stopPropagation()}
                        >
                          <a
                            href={item.draft_edit_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <Edit3 className="w-4 h-4" />
                          </a>
                        </Button>
                      )}
                      {(item.status === "in_progress" ||
                        item.status === "user_input_required" ||
                        item.status === "pending") && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            router.push(`/blog/${item.id}`);
                          }}
                        >
                          続きを見る
                          <ArrowRight className="w-4 h-4 ml-1" />
                        </Button>
                      )}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </motion.div>
        )}
      </div>
    </div>
  );
}
