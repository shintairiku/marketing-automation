"use client";

import { useCallback,useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AnimatePresence,motion } from "framer-motion";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Circle,
  Edit3,
  ExternalLink,
  FileText,
  ImageIcon,
  Loader2,
  MessageSquare,
  RefreshCw,
  Send,
  SkipForward,
  Upload,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useAuth } from "@clerk/nextjs";
import { createClient } from "@supabase/supabase-js";

interface BlogGenerationState {
  id: string;
  status: "pending" | "in_progress" | "completed" | "error" | "user_input_required" | "cancelled";
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

const steps = [
  { key: "初期化中", label: "初期化" },
  { key: "参考記事分析中", label: "参考記事分析" },
  { key: "情報収集中", label: "情報収集" },
  { key: "記事生成中", label: "記事生成" },
  { key: "下書き作成中", label: "下書き作成" },
];

export default function BlogProcessPage() {
  const params = useParams();
  const router = useRouter();
  const { getToken } = useAuth();
  const processId = params.processId as string;

  const [state, setState] = useState<BlogGenerationState | null>(null);
  const [loading, setLoading] = useState(true);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submittingAnswers, setSubmittingAnswers] = useState(false);

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

  useEffect(() => {
    fetchState();

    // Supabase Realtime subscription
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

    if (supabaseUrl && supabaseKey) {
      const supabase = createClient(supabaseUrl, supabaseKey);

      const channel = supabase
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
          }
        )
        .subscribe();

      return () => {
        supabase.removeChannel(channel);
      };
    }
  }, [fetchState, processId]);

  // Polling fallback
  useEffect(() => {
    if (
      state &&
      (state.status === "in_progress" || state.status === "pending")
    ) {
      const interval = setInterval(fetchState, 3000);
      return () => clearInterval(interval);
    }
  }, [state, fetchState]);

  const handleSubmitAnswers = async (skip = false) => {
    setSubmittingAnswers(true);
    try {
      const token = await getToken();
      const payload = skip ? { answers: {} } : { answers };
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
        await fetchState();
      }
    } catch (err) {
      console.error("Failed to submit answers:", err);
    } finally {
      setSubmittingAnswers(false);
    }
  };

  const getCurrentStepIndex = () => {
    if (!state?.current_step_name) return 0;
    const index = steps.findIndex((s) => state.current_step_name?.includes(s.key));
    return index >= 0 ? index : 0;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-amber-50/50 via-white to-emerald-50/30">
        <Loader2 className="w-8 h-8 animate-spin text-amber-500" />
      </div>
    );
  }

  if (!state) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-br from-amber-50/50 via-white to-emerald-50/30">
        <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
        <p className="text-lg text-stone-600 mb-4">生成プロセスが見つかりません</p>
        <Button variant="outline" onClick={() => router.push("/blog/new")}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          新規作成に戻る
        </Button>
      </div>
    );
  }

  const currentStepIndex = getCurrentStepIndex();

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50/50 via-white to-emerald-50/30">
      <div className="max-w-4xl mx-auto px-6 py-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <Button
            variant="ghost"
            onClick={() => router.push("/blog/new")}
            className="mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            新規作成に戻る
          </Button>
          <h1 className="text-3xl font-bold text-stone-800 mb-2">
            ブログ記事を生成中
          </h1>
          <p className="text-stone-500">{state.user_prompt}</p>
        </motion.div>

        {/* Progress Steps */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8"
        >
          <div className="flex items-center justify-between mb-4">
            {steps.map((step, index) => (
              <div key={step.key} className="flex items-center">
                <div className="flex flex-col items-center">
                  <div
                    className={`
                      w-10 h-10 rounded-full flex items-center justify-center transition-all
                      ${
                        index < currentStepIndex
                          ? "bg-emerald-500 text-white"
                          : index === currentStepIndex
                          ? state.status === "error"
                            ? "bg-red-500 text-white"
                            : state.status === "user_input_required"
                            ? "bg-amber-500 text-white animate-pulse"
                            : "bg-amber-500 text-white animate-pulse"
                          : "bg-stone-200 text-stone-400"
                      }
                    `}
                  >
                    {index < currentStepIndex ? (
                      <CheckCircle2 className="w-5 h-5" />
                    ) : index === currentStepIndex && state.status === "in_progress" ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      <Circle className="w-5 h-5" />
                    )}
                  </div>
                  <span className="text-xs mt-2 text-stone-500">{step.label}</span>
                </div>
                {index < steps.length - 1 && (
                  <div
                    className={`w-16 h-1 mx-2 rounded ${
                      index < currentStepIndex ? "bg-emerald-500" : "bg-stone-200"
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </motion.div>

        {/* Status Card */}
        <AnimatePresence mode="wait">
          {state.status === "completed" ? (
            <motion.div
              key="completed"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
            >
              <Card className="border-emerald-200 bg-emerald-50/50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-emerald-700">
                    <CheckCircle2 className="w-6 h-6" />
                    記事の生成が完了しました
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-stone-600">
                    下書き記事がWordPressに保存されました。プレビューを確認して、必要に応じて編集してください。
                  </p>
                  {state.blog_context.agent_message && (
                    <div className="p-4 rounded-xl bg-white/70 border border-emerald-200">
                      <p className="text-xs font-medium text-emerald-600 mb-2">
                        <FileText className="w-3.5 h-3.5 inline mr-1" />
                        AIからのメッセージ
                      </p>
                      <p className="text-sm text-stone-600 whitespace-pre-wrap leading-relaxed">
                        {state.blog_context.agent_message}
                      </p>
                    </div>
                  )}
                  <div className="flex gap-3">
                    {state.draft_preview_url && (
                      <Button asChild>
                        <a
                          href={state.draft_preview_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <ExternalLink className="w-4 h-4 mr-2" />
                          プレビューを見る
                        </a>
                      </Button>
                    )}
                    {state.draft_edit_url && (
                      <Button variant="outline" asChild>
                        <a
                          href={state.draft_edit_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Edit3 className="w-4 h-4 mr-2" />
                          WordPressで編集
                        </a>
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ) : state.status === "error" ? (
            <motion.div
              key="error"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
            >
              <Card className="border-red-200 bg-red-50/50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-red-700">
                    <AlertCircle className="w-6 h-6" />
                    エラーが発生しました
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-stone-600">{state.error_message || "不明なエラーが発生しました"}</p>
                  <Button variant="outline" onClick={() => router.push("/blog/new")}>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    やり直す
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          ) : state.status === "user_input_required" ? (
            <motion.div
              key="input"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
            >
              <Card className="border-amber-200 bg-amber-50/50">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-amber-700">
                    <MessageSquare className="w-6 h-6" />
                    より良い記事のために教えてください
                  </CardTitle>
                  <p className="text-sm text-stone-500 mt-2">
                    {state.blog_context.question_context ||
                      "AIがサイトを分析しました。以下の質問に答えていただくと、より的確な記事を作成できます。"}
                  </p>
                </CardHeader>
                <CardContent className="space-y-5">
                  {state.blog_context.ai_questions?.map((question, idx) => (
                    <div
                      key={question.question_id}
                      className="space-y-2 p-4 rounded-xl bg-white/70 border border-stone-200"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <Label className="text-stone-700 font-medium leading-relaxed">
                          <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-100 text-amber-700 text-xs font-bold mr-2">
                            {idx + 1}
                          </span>
                          {question.question}
                        </Label>
                        <Badge variant="outline" className="text-xs text-stone-400 border-stone-200 shrink-0">
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
                          className="min-h-[100px] bg-white border-stone-200 focus:border-amber-400 focus:ring-amber-100"
                        />
                      ) : question.input_type === "select" && question.options ? (
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
                          className="bg-white border-stone-200 focus:border-amber-400 focus:ring-amber-100"
                        />
                      )}
                    </div>
                  ))}
                  <div className="flex gap-3 pt-2">
                    <Button
                      onClick={() => handleSubmitAnswers(false)}
                      disabled={submittingAnswers}
                      className="flex-1"
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
          ) : (
            <motion.div
              key="progress"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
            >
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Loader2 className="w-5 h-5 animate-spin text-amber-500" />
                    {state.current_step_name || "処理中..."}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="w-full bg-stone-200 rounded-full h-2">
                    <div
                      className="bg-gradient-to-r from-amber-500 to-emerald-500 h-2 rounded-full transition-all duration-500"
                      style={{ width: `${state.progress_percentage}%` }}
                    />
                  </div>
                  <p className="text-sm text-stone-500 mt-2">
                    {state.progress_percentage}% 完了
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Uploaded Images */}
        {state.uploaded_images.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mt-6"
          >
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-sm">
                  <ImageIcon className="w-4 h-4" />
                  アップロード済み画像
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {state.uploaded_images.map((img, idx) => (
                    <Badge key={idx} variant="secondary">
                      {img.filename}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </div>
    </div>
  );
}
