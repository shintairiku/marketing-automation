"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  ArrowLeft,
  Check,
  CheckCircle2,
  ChevronDown,
  Edit3,
  ExternalLink,
  FileText,
  ImageIcon,
  ImagePlus,
  Loader2,
  MessageSquare,
  RefreshCw,
  Send,
  SkipForward,
  Upload,
  X,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import ChatMarkdown from "@/features/tools/seo/generate/edit-article/components/ChatMarkdown";
import { compressImage } from "@/utils/image-compress";
import { useAuth } from "@clerk/nextjs";
import { createClient } from "@supabase/supabase-js";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BlogGenerationState {
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
  is_waiting_for_input: boolean;
  input_type: string | null;
  blog_context: {
    ai_questions?: Array<{
      question_id: string;
      question: string;
      input_type: string;
      options?: string[];
    }>;
    question_context?: string;
    user_answers?: Record<string, string>;
    agent_message?: string;
  };
  user_prompt: string | null;
  reference_url: string | null;
  uploaded_images: Array<{
    filename: string;
    wp_url?: string;
  }>;
  draft_post_id: number | null;
  draft_preview_url: string | null;
  draft_edit_url: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

interface ProcessEvent {
  id: string;
  process_id: string;
  event_type: string;
  event_data: {
    tool_name?: string;
    step_phase?: string;
    message?: string;
    progress?: number;
    tool_call_id?: string;
    error?: string;
    content?: string;
    [key: string]: unknown;
  };
  event_sequence: number;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Activity entry derived from events
// ---------------------------------------------------------------------------

interface ActivityEntry {
  id: string;
  type: "tool" | "thinking" | "system";
  message: string;
  phase?: string;
  status: "running" | "done" | "error";
  timestamp: string;
  sequence: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function parseStepMessage(stepName: string | null): {
  phase: string;
  message: string;
} {
  if (!stepName) return { phase: "", message: "準備中..." };
  const parts = stepName.split(" - ");
  if (parts.length >= 2) {
    return { phase: parts[0], message: parts.slice(1).join(" - ") };
  }
  return { phase: "", message: stepName };
}

function elapsedLabel(createdAt: string): string {
  const seconds = Math.floor(
    (Date.now() - new Date(createdAt).getTime()) / 1000
  );
  if (seconds < 60) return `${seconds}秒前`;
  return `${Math.floor(seconds / 60)}分前`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function BlogProcessPage() {
  const params = useParams();
  const router = useRouter();
  const { getToken } = useAuth();
  const processId = params.processId as string;

  // Ref to always hold the latest getToken so the accessToken callback stays fresh
  const getTokenRef = useRef(getToken);
  getTokenRef.current = getToken;

  // Realtime-dedicated Supabase client with accessToken callback
  // This ensures Realtime automatically gets fresh JWTs from Clerk
  const realtimeClient = useMemo(() => {
    return createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        accessToken: async () => {
          const token = await getTokenRef.current();
          return token ?? null;
        },
      }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const [state, setState] = useState<BlogGenerationState | null>(null);
  const [loading, setLoading] = useState(true);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submittingAnswers, setSubmittingAnswers] = useState(false);

  // Image upload state for question phase
  const [questionImages, setQuestionImages] = useState<
    Record<string, { files: File[]; previewUrls: string[]; uploadedNames: string[]; uploading: boolean }>
  >({});
  const imageInputRefs = useRef<Record<string, HTMLInputElement | null>>({});

  // Activity feed from process events
  const [activities, setActivities] = useState<ActivityEntry[]>([]);
  const activityEndRef = useRef<HTMLDivElement>(null);
  const feedContainerRef = useRef<HTMLDivElement>(null);
  const isNearBottomRef = useRef(true);
  const [, setTick] = useState(0); // for elapsed time refresh
  const [activityLogOpen, setActivityLogOpen] = useState(false);
  const [justCompleted, setJustCompleted] = useState(false);
  const prevStatusRef = useRef<string | null>(null);

  // ---- Fetch initial state ----
  const fetchState = useCallback(async () => {
    try {
      const token = await getToken();
      const response = await fetch(`/api/proxy/blog/generation/${processId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setState(data);
      }
    } catch (err) {
      console.error("Failed to fetch state:", err);
    } finally {
      setLoading(false);
    }
  }, [getToken, processId]);

  // ---- Convert a single event to an ActivityEntry (or null) ----
  const convertEventToActivity = useCallback(
    (event: ProcessEvent): ActivityEntry | null => {
      const { event_type, event_data, event_sequence, created_at, id } = event;

      if (event_type === "tool_call_started") {
        return {
          id,
          type: "tool",
          message: event_data.message || event_data.tool_name || "処理中",
          phase: event_data.step_phase,
          status: "running",
          timestamp: created_at,
          sequence: event_sequence,
        };
      } else if (event_type === "reasoning") {
        return {
          id,
          type: "thinking",
          message: event_data.message || "分析・構成を検討中...",
          status: "done",
          timestamp: created_at,
          sequence: event_sequence,
        };
      } else if (
        event_type === "generation_started" ||
        event_type === "generation_resumed"
      ) {
        return {
          id,
          type: "system",
          message: event_data.message || "処理を開始しました",
          status: "done",
          timestamp: created_at,
          sequence: event_sequence,
        };
      } else if (event_type === "generation_error") {
        return {
          id,
          type: "system",
          message: event_data.message || "エラーが発生しました",
          status: "error",
          timestamp: created_at,
          sequence: event_sequence,
        };
      }
      // tool_call_completed and others handled separately
      return null;
    },
    []
  );

  // ---- Fetch existing events (initial load + catch-up) ----
  const fetchExistingEvents = useCallback(async () => {
    try {
      const token = await getToken();
      const response = await fetch(
        `/api/proxy/blog/generation/${processId}/events`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (response.ok) {
        const events: ProcessEvent[] = await response.json();
        // Process each event, deduplicating by id
        setActivities((prev) => {
          const existingIds = new Set(prev.map((a) => a.id));
          let updated = [...prev];
          for (const event of events) {
            if (!existingIds.has(event.id)) {
              const entry = convertEventToActivity(event);
              if (entry) updated.push(entry);
            }
          }
          // Also apply tool_call_completed status updates
          for (const event of events) {
            if (event.event_type === "tool_call_completed") {
              for (let i = updated.length - 1; i >= 0; i--) {
                if (
                  updated[i].type === "tool" &&
                  updated[i].status === "running"
                ) {
                  updated[i] = { ...updated[i], status: "done" };
                  break;
                }
              }
            }
          }
          return updated.sort((a, b) => a.sequence - b.sequence);
        });
      }
    } catch (err) {
      console.error("Failed to fetch existing events:", err);
    }
  }, [getToken, processId, convertEventToActivity]);

  // ---- Unified data fetcher (state + events in one call) ----
  const fetchAll = useCallback(async () => {
    await Promise.all([fetchState(), fetchExistingEvents()]);
  }, [fetchState, fetchExistingEvents]);

  // ---- Realtime: single channel on blog_generation_state ----
  // State UPDATE is reliable. On every state change we also fetch events,
  // so the activity feed stays in sync without a separate events channel.
  useEffect(() => {
    fetchAll();

    const channel = realtimeClient
      .channel(`blog_generation:${processId}`)
      .on(
        "postgres_changes",
        {
          event: "UPDATE",
          schema: "public",
          table: "blog_generation_state",
          filter: `id=eq.${processId}`,
        },
        (payload) => {
          setState(payload.new as BlogGenerationState);
          // Piggyback: fetch events whenever state updates
          fetchExistingEvents();
        }
      )
      .subscribe();

    return () => {
      realtimeClient.removeChannel(channel);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [processId]);

  // ---- Polling fallback (state + events, unified) ----
  useEffect(() => {
    if (
      state &&
      (state.status === "in_progress" || state.status === "pending")
    ) {
      const interval = setInterval(fetchAll, 5000);
      return () => clearInterval(interval);
    }
  }, [state, fetchAll]);

  // ---- Elapsed time refresh ----
  useEffect(() => {
    if (
      state &&
      (state.status === "in_progress" || state.status === "pending")
    ) {
      const interval = setInterval(() => setTick((t) => t + 1), 5000);
      return () => clearInterval(interval);
    }
  }, [state]);

  // ---- Detect completion transition ----
  useEffect(() => {
    if (
      prevStatusRef.current &&
      prevStatusRef.current !== "completed" &&
      state?.status === "completed"
    ) {
      setJustCompleted(true);
      const timer = setTimeout(() => setJustCompleted(false), 2000);
      return () => clearTimeout(timer);
    }
    if (state?.status) {
      prevStatusRef.current = state.status;
    }
  }, [state?.status]);

  // ---- Track whether user is near the bottom of the feed ----
  const handleFeedScroll = useCallback(() => {
    const el = feedContainerRef.current;
    if (!el) return;
    const threshold = 80;
    isNearBottomRef.current =
      el.scrollHeight - el.scrollTop - el.clientHeight <= threshold;
  }, []);

  // ---- Auto-scroll activity feed (only when user is near bottom) ----
  useEffect(() => {
    if (isNearBottomRef.current) {
      activityEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [activities]);

  // ---- Image upload handlers for question phase ----
  const handleQuestionImageSelect = useCallback(
    (questionId: string, files: FileList | null) => {
      if (!files || files.length === 0) return;
      const newFiles = Array.from(files);
      setQuestionImages((prev) => {
        const existing = prev[questionId] || { files: [], previewUrls: [], uploadedNames: [], uploading: false };
        // Max 5 images per question
        const combined = [...existing.files, ...newFiles].slice(0, 5);
        const newPreviews = newFiles.map((f) => URL.createObjectURL(f));
        const combinedPreviews = [...existing.previewUrls, ...newPreviews].slice(0, 5);
        return { ...prev, [questionId]: { ...existing, files: combined, previewUrls: combinedPreviews } };
      });
    },
    []
  );

  const handleRemoveQuestionImage = useCallback(
    (questionId: string, index: number) => {
      setQuestionImages((prev) => {
        const existing = prev[questionId];
        if (!existing) return prev;
        URL.revokeObjectURL(existing.previewUrls[index]);
        const files = existing.files.filter((_, i) => i !== index);
        const previewUrls = existing.previewUrls.filter((_, i) => i !== index);
        const uploadedNames = existing.uploadedNames.filter((_, i) => i !== index);
        return { ...prev, [questionId]: { ...existing, files, previewUrls, uploadedNames } };
      });
    },
    []
  );

  const uploadQuestionImages = useCallback(
    async (questionId: string): Promise<string[]> => {
      const entry = questionImages[questionId];
      if (!entry || entry.files.length === 0) return [];
      // Already uploaded
      if (entry.uploadedNames.length === entry.files.length) return entry.uploadedNames;

      setQuestionImages((prev) => ({
        ...prev,
        [questionId]: { ...prev[questionId], uploading: true },
      }));

      const token = await getToken();
      const uploadedNames: string[] = [];

      for (const file of entry.files) {
        try {
          // 画像を圧縮してからアップロード
          const compressed = await compressImage(file).catch(() => file);
          const formData = new FormData();
          formData.append("file", compressed);
          const res = await fetch(
            `/api/proxy/blog/generation/${processId}/upload-image`,
            {
              method: "POST",
              headers: { Authorization: `Bearer ${token}` },
              body: formData,
            }
          );
          if (res.ok) {
            const data = await res.json();
            uploadedNames.push(data.filename || file.name);
          }
        } catch (err) {
          console.error("Failed to upload question image:", err);
        }
      }

      setQuestionImages((prev) => ({
        ...prev,
        [questionId]: { ...prev[questionId], uploading: false, uploadedNames },
      }));
      return uploadedNames;
    },
    [questionImages, getToken, processId]
  );

  // ---- Submit answers ----
  const handleSubmitAnswers = async (skip = false) => {
    setSubmittingAnswers(true);
    try {
      const token = await getToken();

      // Upload any pending images before submitting answers
      const finalAnswers = skip ? {} : { ...answers };
      if (!skip) {
        for (const question of state?.blog_context.ai_questions || []) {
          if (question.input_type === "image_upload" && questionImages[question.question_id]?.files.length > 0) {
            const uploadedNames = await uploadQuestionImages(question.question_id);
            if (uploadedNames.length > 0) {
              finalAnswers[question.question_id] = `uploaded:${uploadedNames.join(",")}`;
            }
          }
        }
      }

      const payload = { answers: finalAnswers };
      const response = await fetch(
        `/api/proxy/blog/generation/${processId}/user-input`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify(payload),
        }
      );
      if (response.ok) {
        setAnswers({});
        // Clean up image previews
        Object.values(questionImages).forEach((entry) =>
          entry.previewUrls.forEach((url) => URL.revokeObjectURL(url))
        );
        setQuestionImages({});
        await fetchState();
        // Fetch events that may have been inserted during the transition
        await fetchExistingEvents();
      }
    } catch (err) {
      console.error("Failed to submit answers:", err);
    } finally {
      setSubmittingAnswers(false);
    }
  };

  // ---- Render helpers ----
  const stepInfo = parseStepMessage(state?.current_step_name ?? null);
  const isWorking =
    state?.status === "in_progress" || state?.status === "pending";

  // ---------------------------------------------------------------------------
  // Loading
  // ---------------------------------------------------------------------------
  if (loading) {
    return (
      <div className="flex items-center justify-center bg-gradient-to-br from-amber-50/50 via-white to-emerald-50/30" style={{ minHeight: 'calc(100dvh - 57px)' }}>
        <div className="flex items-center gap-3 text-stone-400">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm tracking-wide">読み込み中</span>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Not found
  // ---------------------------------------------------------------------------
  if (!state) {
    return (
      <div className="flex flex-col items-center justify-center bg-gradient-to-br from-amber-50/50 via-white to-emerald-50/30" style={{ minHeight: 'calc(100dvh - 57px)' }}>
        <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
        <p className="text-lg text-stone-600 mb-4">
          生成プロセスが見つかりません
        </p>
        <Button variant="outline" onClick={() => router.push("/blog/new")}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          新規作成に戻る
        </Button>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Main render
  // ---------------------------------------------------------------------------
  return (
    <div className="bg-gradient-to-br from-amber-50/50 via-white to-emerald-50/30">
      <div className="max-w-3xl mx-auto px-4 py-6 md:px-6 md:py-10">
        {/* ---- Back nav ---- */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <Button
            variant="ghost"
            onClick={() => router.push("/blog/new")}
            className="mb-6 -ml-2 text-stone-400 hover:text-stone-600"
          >
            <ArrowLeft className="w-4 h-4 mr-1.5" />
            新規作成
          </Button>
        </motion.div>

        {/* ---- Header ---- */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.05 }}
          className="mb-8"
        >
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-1.5">
            <AnimatePresence mode="wait">
              <motion.h1
                key={state.status}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.3 }}
                className="text-2xl font-bold text-stone-800 tracking-tight"
              >
                {state.status === "completed"
                  ? "記事の生成が完了しました"
                  : state.status === "error"
                    ? "エラーが発生しました"
                    : state.status === "user_input_required"
                      ? "追加情報をお聞きしています"
                      : "ブログ記事を生成しています"}
              </motion.h1>
            </AnimatePresence>
            {state.status === "completed" && (
              <motion.div
                className="flex gap-2 flex-shrink-0"
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.4, duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
              >
                {state.draft_preview_url && (
                  <Button
                    asChild
                    size="sm"
                    className="rounded-lg bg-stone-800 hover:bg-stone-700 text-xs h-9 px-4"
                  >
                    <a
                      href={state.draft_preview_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <ExternalLink className="w-3.5 h-3.5 mr-1.5" />
                      プレビューを見る
                    </a>
                  </Button>
                )}
                {state.draft_edit_url && (
                  <Button
                    variant="outline"
                    asChild
                    size="sm"
                    className="rounded-lg text-xs h-9 px-4"
                  >
                    <a
                      href={state.draft_edit_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <Edit3 className="w-3.5 h-3.5 mr-1.5" />
                      編集
                    </a>
                  </Button>
                )}
              </motion.div>
            )}
          </div>
          {state.user_prompt && (
            <p className="text-stone-400 text-sm leading-relaxed line-clamp-2">
              {state.user_prompt}
            </p>
          )}
        </motion.div>

        {/* ---- Integrated progress bar (only when working) ---- */}
        <AnimatePresence>
          {isWorking && (
            <motion.div
              initial={{ opacity: 0, scaleY: 0 }}
              animate={{ opacity: 1, scaleY: 1 }}
              exit={{ opacity: 0, height: 0, marginBottom: 0, transition: { duration: 0.4, delay: 0.1, ease: "easeInOut" } }}
              transition={{ duration: 0.3 }}
              style={{ originY: 0 }}
              className="mb-6"
            >
              <div className="relative h-1 w-full rounded-full bg-stone-100 overflow-hidden">
                <motion.div
                  className="absolute inset-y-0 left-0 rounded-full"
                  initial={{ width: 0 }}
                  animate={{
                    width: `${state.progress_percentage}%`,
                    background: state.progress_percentage >= 100
                      ? "linear-gradient(to right, #34d399, #10b981)"
                      : "linear-gradient(to right, #fbbf24, #f97316, #10b981)",
                  }}
                  transition={{ duration: 0.8, ease: "easeOut" }}
                />
                {/* Shimmer overlay */}
                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-[shimmer_2s_infinite] " />
              </div>
              <div className="flex items-center justify-between mt-2">
                <span className="text-xs text-stone-400 tracking-wide">
                  {stepInfo.message}
                </span>
                <span className="text-xs tabular-nums text-stone-300">
                  {state.progress_percentage}%
                </span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ==== STATUS-SPECIFIC CONTENT ==== */}
        <AnimatePresence mode="wait">
          {/* ---- COMPLETED ---- */}
          {state.status === "completed" && (
            <motion.div
              key="completed"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{
                duration: 0.6,
                delay: 0.15,
                ease: [0.22, 1, 0.36, 1],
              }}
              className="space-y-5"
            >
              {/* Success banner — collapsible to reveal activity log */}
              <div className={`rounded-2xl border border-emerald-200/60 bg-emerald-50/70 overflow-hidden ${
                justCompleted ? "animate-[successGlow_1s_ease-out]" : ""
              }`}>
                {/* Clickable header */}
                <button
                  type="button"
                  onClick={() => activities.length > 0 && setActivityLogOpen((prev) => !prev)}
                  className={`w-full flex items-center gap-3 p-5 text-left transition-colors ${
                    activities.length > 0 ? "cursor-pointer hover:bg-emerald-50" : "cursor-default"
                  }`}
                >
                  <motion.div
                    className="w-7 h-7 rounded-full bg-emerald-500 flex items-center justify-center flex-shrink-0"
                    initial={justCompleted ? { scale: 0 } : { scale: 1 }}
                    animate={{ scale: 1 }}
                    transition={
                      justCompleted
                        ? { type: "spring", stiffness: 400, damping: 15, delay: 0.3 }
                        : { duration: 0 }
                    }
                  >
                    <Check className="w-4 h-4 text-white" strokeWidth={3} />
                  </motion.div>
                  <div className="flex-1 min-w-0">
                    <p className="text-stone-700 font-medium text-sm">
                      下書き記事がWordPressに保存されました
                    </p>
                    <p className="text-stone-500 text-xs mt-0.5">
                      {activities.length > 0
                        ? "タップして生成プロセスの詳細を表示"
                        : "プレビューを確認して、必要に応じて編集してください"}
                    </p>
                  </div>
                  {activities.length > 0 && (
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="text-xs text-stone-400 tabular-nums hidden sm:inline">
                        {activities.filter((a) => a.status === "done").length}件
                      </span>
                      <motion.div
                        animate={{ rotate: activityLogOpen ? 180 : 0 }}
                        transition={{ duration: 0.2 }}
                      >
                        <ChevronDown className="w-4 h-4 text-stone-400" />
                      </motion.div>
                    </div>
                  )}
                </button>

                {/* Collapsible activity feed */}
                <AnimatePresence initial={false}>
                  {activityLogOpen && activities.length > 0 && (
                    <motion.div
                      key="activity-log"
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
                      className="overflow-hidden"
                    >
                      <div className="border-t border-emerald-200/40 bg-white/60">
                        <div
                          className="overflow-y-auto overscroll-contain"
                          style={{ maxHeight: "400px" }}
                        >
                          <div className="divide-y divide-stone-100">
                            {activities.map((entry, idx) => (
                              <div
                                key={entry.id || idx}
                                className="flex items-start gap-3 px-5 py-3 group"
                              >
                                {/* Status dot */}
                                <div className="mt-1.5 flex-shrink-0">
                                  {entry.status === "running" ? (
                                    <span className="relative flex h-2 w-2">
                                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
                                      <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500" />
                                    </span>
                                  ) : entry.status === "error" ? (
                                    <span className="inline-flex rounded-full h-2 w-2 bg-red-400" />
                                  ) : entry.type === "thinking" ? (
                                    <span className="inline-flex rounded-full h-2 w-2 bg-stone-300" />
                                  ) : (
                                    <span className="inline-flex rounded-full h-2 w-2 bg-emerald-400" />
                                  )}
                                </div>

                                {/* Content */}
                                <div className="flex-1 min-w-0">
                                  {entry.type === "thinking" ? (
                                    <div className="text-xs text-stone-400 italic [&_p]:my-0.5 [&_ul]:my-1 [&_ol]:my-1 [&_*]:text-xs [&_p]:text-stone-400 [&_strong]:text-stone-500 [&_li]:text-stone-400 [&_.prose]:text-xs">
                                      <ChatMarkdown
                                        content={entry.message}
                                        className="!text-xs !leading-snug"
                                      />
                                    </div>
                                  ) : (
                                    <p
                                      className={`text-sm leading-snug ${
                                        entry.status === "running"
                                          ? "text-stone-700"
                                          : "text-stone-500"
                                      }`}
                                    >
                                      {entry.message}
                                    </p>
                                  )}
                                  {entry.phase && entry.type === "tool" && (
                                    <p className="text-[11px] text-stone-300 mt-0.5">
                                      {entry.phase}
                                    </p>
                                  )}
                                </div>

                                {/* Timestamp */}
                                <span className="text-[11px] text-stone-300 tabular-nums flex-shrink-0 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                                  {elapsedLabel(entry.timestamp)}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Footer */}
                        <div className="flex items-center justify-between px-5 py-2.5 border-t border-stone-100 bg-stone-50/50">
                          <span className="text-[11px] text-stone-400">
                            {activities.filter((a) => a.status === "done").length} 件完了
                          </span>
                          <span className="text-[11px] text-stone-300 tabular-nums">
                            {state.created_at &&
                              `開始: ${new Date(state.created_at).toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" })}`}
                          </span>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Agent message */}
              {state.blog_context.agent_message && (
                <motion.div
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.25, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
                  className="p-5 rounded-2xl bg-white/70 border border-stone-200/60"
                >
                  <p className="text-xs font-medium text-stone-400 mb-3 flex items-center gap-1.5 uppercase tracking-wider">
                    <FileText className="w-3.5 h-3.5" />
                    AIからのメッセージ
                  </p>
                  <ChatMarkdown
                    content={state.blog_context.agent_message}
                    className="text-stone-600"
                  />
                </motion.div>
              )}
            </motion.div>
          )}

          {/* ---- ERROR ---- */}
          {state.status === "error" && (
            <motion.div
              key="error"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="space-y-4"
            >
              <div className="flex items-start gap-3 p-5 rounded-2xl bg-red-50/70 border border-red-200/60">
                <AlertCircle className="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-stone-700 font-medium text-sm">
                    生成中にエラーが発生しました
                  </p>
                  <p className="text-stone-500 text-xs mt-1">
                    {state.error_message || "不明なエラー"}
                  </p>
                </div>
              </div>
              <Button
                variant="outline"
                onClick={() => router.push("/blog/new")}
                className="rounded-xl"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                やり直す
              </Button>
            </motion.div>
          )}

          {/* ---- USER INPUT REQUIRED ---- */}
          {state.status === "user_input_required" && (
            <motion.div
              key="input"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <Card className="border-amber-200/60 bg-amber-50/30 rounded-2xl shadow-none">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-stone-700 text-lg">
                    <MessageSquare className="w-5 h-5 text-amber-600" />
                    より良い記事のために教えてください
                  </CardTitle>
                  <p className="text-sm text-stone-500 mt-1">
                    {state.blog_context.question_context ||
                      "AIがサイトを分析しました。以下の質問に答えていただくと、より的確な記事を作成できます。"}
                  </p>
                </CardHeader>
                <CardContent className="space-y-5">
                  {state.blog_context.ai_questions?.map((question, idx) => (
                    <div
                      key={question.question_id}
                      className="space-y-2 p-4 rounded-xl bg-white/70 border border-stone-200/50"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <Label className="text-stone-700 font-medium leading-relaxed">
                          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-100 text-amber-700 text-xs font-bold mr-2">
                            {idx + 1}
                          </span>
                          {question.question}
                        </Label>
                        <Badge
                          variant="outline"
                          className="text-xs text-stone-400 border-stone-200 shrink-0"
                        >
                          任意
                        </Badge>
                      </div>
                      {question.input_type === "textarea" ? (
                        <Textarea
                          value={answers[question.question_id] || ""}
                          onChange={(e) =>
                            setAnswers({
                              ...answers,
                              [question.question_id]: e.target.value,
                            })
                          }
                          placeholder="わかる範囲でお書きください..."
                          className="min-h-[100px] bg-white border-stone-200 focus:border-amber-400 focus:ring-amber-100 rounded-xl"
                        />
                      ) : question.input_type === "image_upload" ? (
                        <div className="space-y-3">
                          {/* Selected images preview */}
                          {(questionImages[question.question_id]?.previewUrls.length ?? 0) > 0 && (
                            <div className="grid grid-cols-3 gap-2">
                              {questionImages[question.question_id].previewUrls.map(
                                (url, imgIdx) => (
                                  <div key={imgIdx} className="relative group aspect-square rounded-lg overflow-hidden border border-stone-200 bg-stone-50">
                                    {/* eslint-disable-next-line @next/next/no-img-element */}
                                    <img
                                      src={url}
                                      alt={`画像 ${imgIdx + 1}`}
                                      className="w-full h-full object-cover"
                                    />
                                    {questionImages[question.question_id]?.uploadedNames[imgIdx] ? (
                                      <div className="absolute top-1 right-1 w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center">
                                        <CheckCircle2 className="w-3 h-3 text-white" />
                                      </div>
                                    ) : (
                                      <button
                                        type="button"
                                        onClick={() => handleRemoveQuestionImage(question.question_id, imgIdx)}
                                        className="absolute top-1 right-1 w-5 h-5 rounded-full bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                                      >
                                        <X className="w-3 h-3 text-white" />
                                      </button>
                                    )}
                                  </div>
                                )
                              )}
                            </div>
                          )}

                          {/* Upload button / drop zone */}
                          {(questionImages[question.question_id]?.files.length ?? 0) < 5 && (
                            <button
                              type="button"
                              onClick={() => imageInputRefs.current[question.question_id]?.click()}
                              className="w-full flex flex-col items-center justify-center gap-2 py-6 border-2 border-dashed border-stone-200 hover:border-amber-300 rounded-xl bg-white/50 hover:bg-amber-50/30 transition-colors cursor-pointer"
                            >
                              {questionImages[question.question_id]?.uploading ? (
                                <>
                                  <Loader2 className="w-6 h-6 text-amber-500 animate-spin" />
                                  <span className="text-xs text-stone-500">アップロード中...</span>
                                </>
                              ) : (
                                <>
                                  <ImagePlus className="w-6 h-6 text-stone-400" />
                                  <span className="text-xs text-stone-500">
                                    クリックして画像を選択（最大5枚）
                                  </span>
                                </>
                              )}
                            </button>
                          )}

                          <input
                            ref={(el) => { imageInputRefs.current[question.question_id] = el; }}
                            type="file"
                            accept="image/*"
                            multiple
                            className="hidden"
                            onChange={(e) => {
                              handleQuestionImageSelect(question.question_id, e.target.files);
                              e.target.value = "";
                            }}
                          />

                          {(questionImages[question.question_id]?.files.length ?? 0) > 0 && (
                            <p className="text-xs text-stone-400">
                              {questionImages[question.question_id].files.length}枚選択済み
                              {questionImages[question.question_id].uploadedNames.length > 0 &&
                                ` (${questionImages[question.question_id].uploadedNames.length}枚アップロード済み)`}
                            </p>
                          )}
                        </div>
                      ) : question.input_type === "select" &&
                        question.options ? (
                        <div className="flex flex-wrap gap-2">
                          {question.options.map((option) => (
                            <Button
                              key={option}
                              variant={
                                answers[question.question_id] === option
                                  ? "default"
                                  : "outline"
                              }
                              size="sm"
                              onClick={() =>
                                setAnswers({
                                  ...answers,
                                  [question.question_id]: option,
                                })
                              }
                              className="rounded-lg"
                            >
                              {option}
                            </Button>
                          ))}
                        </div>
                      ) : (
                        <Input
                          value={answers[question.question_id] || ""}
                          onChange={(e) =>
                            setAnswers({
                              ...answers,
                              [question.question_id]: e.target.value,
                            })
                          }
                          placeholder="わかる範囲でお書きください..."
                          className="bg-white border-stone-200 focus:border-amber-400 focus:ring-amber-100 rounded-xl"
                        />
                      )}
                    </div>
                  ))}
                  <div className="flex gap-3 pt-2">
                    <Button
                      onClick={() => handleSubmitAnswers(false)}
                      disabled={submittingAnswers}
                      className="flex-1 rounded-xl"
                    >
                      {submittingAnswers ? (
                        <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4 mr-2" />
                      )}
                      回答を送信して続行
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => handleSubmitAnswers(true)}
                      disabled={submittingAnswers}
                      className="rounded-xl"
                    >
                      <SkipForward className="w-4 h-4 mr-2" />
                      スキップ
                    </Button>
                  </div>
                  <p className="text-xs text-stone-400 text-center">
                    すべての質問は任意です。スキップしてもリクエスト内容をもとに記事を作成します。
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* ---- IN PROGRESS ---- */}
          {isWorking && (
            <motion.div
              key="progress"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10, scale: 0.97, filter: "blur(4px)", transition: { duration: 0.35, ease: "easeIn" } }}
              transition={{ duration: 0.4 }}
              className="space-y-4"
            >
              {/* Current activity indicator */}
              <div className="flex items-center gap-3 px-1">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500" />
                </span>
                <span className="text-sm font-medium text-stone-600">
                  {stepInfo.phase || "作業中"}
                </span>
                {stepInfo.phase && stepInfo.message !== stepInfo.phase && (
                  <span className="text-sm text-stone-400">
                    — {stepInfo.message}
                  </span>
                )}
              </div>

              {/* Activity feed */}
              <div className="rounded-2xl border border-stone-200/60 bg-white/50 backdrop-blur-sm overflow-hidden">
                <div
                  ref={feedContainerRef}
                  onScroll={handleFeedScroll}
                  className="overflow-y-auto overscroll-contain min-h-[250px]"
                  style={{ maxHeight: 'calc(100dvh - 355px)' }}
                >
                  {activities.length === 0 ? (
                    <div className="px-5 py-10 text-center">
                      <Loader2 className="w-5 h-5 animate-spin text-stone-300 mx-auto mb-3" />
                      <p className="text-sm text-stone-400">
                        エージェントが作業を開始するのを待っています...
                      </p>
                    </div>
                  ) : (
                    <div className="divide-y divide-stone-100">
                      {activities.map((entry, idx) => (
                        <motion.div
                          key={entry.id || idx}
                          initial={{ opacity: 0, x: -8 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{
                            duration: 0.3,
                            ease: [0.22, 1, 0.36, 1],
                          }}
                          className="flex items-start gap-3 px-5 py-3 group"
                        >
                          {/* Status dot */}
                          <div className="mt-1.5 flex-shrink-0">
                            {entry.status === "running" ? (
                              <span className="relative flex h-2 w-2">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500" />
                              </span>
                            ) : entry.status === "error" ? (
                              <span className="inline-flex rounded-full h-2 w-2 bg-red-400" />
                            ) : entry.type === "thinking" ? (
                              <span className="inline-flex rounded-full h-2 w-2 bg-stone-300" />
                            ) : (
                              <span className="inline-flex rounded-full h-2 w-2 bg-emerald-400" />
                            )}
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            {entry.type === "thinking" ? (
                              <div className="text-xs text-stone-400 italic [&_p]:my-0.5 [&_ul]:my-1 [&_ol]:my-1 [&_*]:text-xs [&_p]:text-stone-400 [&_strong]:text-stone-500 [&_li]:text-stone-400 [&_.prose]:text-xs">
                                <ChatMarkdown
                                  content={entry.message}
                                  className="!text-xs !leading-snug"
                                />
                              </div>
                            ) : (
                              <p
                                className={`text-sm leading-snug ${
                                  entry.status === "running"
                                    ? "text-stone-700"
                                    : "text-stone-500"
                                }`}
                              >
                                {entry.message}
                              </p>
                            )}
                            {entry.phase && entry.type === "tool" && (
                              <p className="text-[11px] text-stone-300 mt-0.5">
                                {entry.phase}
                              </p>
                            )}
                          </div>

                          {/* Timestamp */}
                          <span className="text-[11px] text-stone-300 tabular-nums flex-shrink-0 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                            {elapsedLabel(entry.timestamp)}
                          </span>
                        </motion.div>
                      ))}
                      <div ref={activityEndRef} />
                    </div>
                  )}
                </div>

                {/* Feed footer */}
                {activities.length > 0 && (
                  <div className="flex items-center justify-between px-5 py-2.5 border-t border-stone-100 bg-stone-50/50">
                    <span className="text-[11px] text-stone-400">
                      {activities.filter((a) => a.status === "done").length} 件完了
                    </span>
                    <span className="text-[11px] text-stone-300 tabular-nums">
                      {state.created_at &&
                        `開始: ${new Date(state.created_at).toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit" })}`}
                    </span>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ---- Uploaded Images ---- */}
        {state.uploaded_images.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mt-6"
          >
            <Card className="rounded-2xl shadow-none border-stone-200/60">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm text-stone-500 font-medium">
                  <ImageIcon className="w-4 h-4" />
                  アップロード済み画像
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {state.uploaded_images.map((img, idx) => (
                    <Badge
                      key={idx}
                      variant="secondary"
                      className="rounded-lg"
                    >
                      {img.filename}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </div>

      {/* Shimmer keyframe (inline for the progress bar) */}
      <style jsx global>{`
        @keyframes shimmer {
          0% {
            transform: translateX(-100%);
          }
          100% {
            transform: translateX(100%);
          }
        }
        @keyframes successGlow {
          0% {
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4);
          }
          50% {
            box-shadow: 0 0 20px 4px rgba(16, 185, 129, 0.15);
          }
          100% {
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
          }
        }
      `}</style>
    </div>
  );
}
