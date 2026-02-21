"use client";

import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronDown,
  Copy,
  Download,
  ExternalLink,
  Globe,
  Loader2,
  Plug,
  Settings,
  Upload,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@clerk/nextjs";

const PLUGIN_DOWNLOAD_URL =
  "https://github.com/als141/wordpress-ability-plugin/releases/download/v1.1.2/wordpress-mcp-ability-plugin-1.1.2.zip";

interface WordPressOnboardingProps {
  onConnected: () => void;
}

export function WordPressOnboarding({ onConnected }: WordPressOnboardingProps) {
  const { getToken } = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);

  const [connectionUrl, setConnectionUrl] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [expandedStep, setExpandedStep] = useState<number>(1);

  const handleConnect = async () => {
    const url = connectionUrl.trim();
    if (!url) return;

    try {
      const parsed = new URL(url);
      if (!parsed.searchParams.get("code")) {
        setError(
          "接続URLに code パラメータが含まれていません。WordPress管理画面で生成された接続URLを貼り付けてください。"
        );
        return;
      }
    } catch {
      setError("有効なURLを入力してください。");
      return;
    }

    setConnecting(true);
    setError(null);

    try {
      const token = await getToken();
      const response = await fetch("/api/proxy/blog/connect/wordpress/url", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ connection_url: url }),
      });

      if (response.ok) {
        setSuccess(true);
        setConnectionUrl("");
        setTimeout(() => onConnected(), 1500);
      } else {
        const data = await response.json();
        setError(data.detail || "連携に失敗しました");
      }
    } catch {
      setError("ネットワークエラーが発生しました");
    } finally {
      setConnecting(false);
    }
  };

  const toggleStep = (step: number) => {
    setExpandedStep(expandedStep === step ? 0 : step);
  };

  const steps = [
    {
      number: 1,
      title: "プラグインをインストール",
      subtitle: "WordPressにMCP連携プラグインを追加します",
      icon: Download,
      color: "amber",
    },
    {
      number: 2,
      title: "接続URLを取得",
      subtitle: "WordPress管理画面で接続URLを生成します",
      icon: Settings,
      color: "blue",
    },
    {
      number: 3,
      title: "ここに貼り付けて連携",
      subtitle: "生成されたURLを貼り付けるだけで完了！",
      icon: Plug,
      color: "emerald",
    },
  ];

  const colorMap: Record<string, { bg: string; border: string; text: string; ring: string; indicator: string; iconBg: string }> = {
    amber: {
      bg: "bg-amber-50",
      border: "border-amber-200",
      text: "text-amber-700",
      ring: "ring-amber-200",
      indicator: "bg-amber-500",
      iconBg: "bg-amber-100",
    },
    blue: {
      bg: "bg-blue-50",
      border: "border-blue-200",
      text: "text-blue-700",
      ring: "ring-blue-200",
      indicator: "bg-blue-500",
      iconBg: "bg-blue-100",
    },
    emerald: {
      bg: "bg-emerald-50",
      border: "border-emerald-200",
      text: "text-emerald-700",
      ring: "ring-emerald-200",
      indicator: "bg-emerald-500",
      iconBg: "bg-emerald-100",
    },
  };

  if (success) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="max-w-2xl mx-auto"
      >
        <div className="relative overflow-hidden rounded-3xl border-2 border-emerald-200 bg-gradient-to-br from-emerald-50 to-green-50 p-8 md:p-12 text-center">
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute top-6 right-10 w-32 h-32 bg-emerald-200/30 rounded-full blur-2xl" />
            <div className="absolute bottom-6 left-10 w-40 h-40 bg-green-200/30 rounded-full blur-2xl" />
          </div>
          <div className="relative">
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ type: "spring", stiffness: 300, damping: 20, delay: 0.1 }}
              className="w-20 h-20 rounded-full bg-emerald-500 flex items-center justify-center mx-auto mb-6"
            >
              <Check className="w-10 h-10 text-white" strokeWidth={3} />
            </motion.div>
            <motion.h2
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="text-2xl font-bold text-emerald-800 mb-2"
            >
              連携が完了しました！
            </motion.h2>
            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="text-emerald-600"
            >
              ブログ記事の生成を始めましょう...
            </motion.p>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="max-w-2xl mx-auto"
    >
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-100 to-orange-100 mb-5">
          <Globe className="w-8 h-8 text-amber-600" />
        </div>
        <h2 className="text-2xl md:text-3xl font-bold text-stone-800 mb-3">
          WordPressサイトを連携しましょう
        </h2>
        <p className="text-stone-500 max-w-md mx-auto leading-relaxed">
          3つのステップで簡単にセットアップできます。
          <br className="hidden sm:block" />
          あなたのWordPressサイトにAIがブログ記事を書きます。
        </p>
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {steps.map((step, idx) => {
          const colors = colorMap[step.color];
          const isExpanded = expandedStep === step.number;
          const StepIcon = step.icon;

          return (
            <motion.div
              key={step.number}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 + 0.2 }}
            >
              <div
                className={`
                  w-full text-left rounded-2xl border-2 transition-all duration-200
                  ${isExpanded
                    ? `${colors.bg} ${colors.border} shadow-sm`
                    : "bg-white border-stone-200 hover:border-stone-300 hover:bg-stone-50/50"
                  }
                `}
              >
                {/* Step Header (clickable) */}
                <button
                  type="button"
                  onClick={() => toggleStep(step.number)}
                  className="flex items-center gap-4 p-4 md:p-5 w-full text-left cursor-pointer"
                >
                  {/* Number badge */}
                  <div
                    className={`
                      flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center font-bold text-white text-sm
                      ${isExpanded ? colors.indicator : "bg-stone-300"}
                    `}
                  >
                    {step.number}
                  </div>

                  {/* Title & subtitle */}
                  <div className="flex-1 min-w-0">
                    <p className={`font-semibold ${isExpanded ? colors.text : "text-stone-700"}`}>
                      {step.title}
                    </p>
                    <p className="text-sm text-stone-500 mt-0.5">{step.subtitle}</p>
                  </div>

                  {/* Icon */}
                  <div className={`flex-shrink-0 ${isExpanded ? colors.iconBg : "bg-stone-100"} rounded-xl p-2.5`}>
                    <StepIcon className={`w-5 h-5 ${isExpanded ? colors.text : "text-stone-400"}`} />
                  </div>

                  {/* Chevron */}
                  <ChevronDown
                    className={`w-5 h-5 text-stone-400 flex-shrink-0 transition-transform duration-200 ${
                      isExpanded ? "rotate-180" : ""
                    }`}
                  />
                </button>

                {/* Expanded Content */}
                <AnimatePresence initial={false}>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
                      className="overflow-hidden"
                    >
                      <div className="px-4 pb-5 md:px-5 md:pb-6 pt-0">
                        <div className="border-t border-stone-200/60 pt-4">
                          {step.number === 1 && <Step1Content />}
                          {step.number === 2 && <Step2Content />}
                          {step.number === 3 && (
                            <Step3Content
                              connectionUrl={connectionUrl}
                              setConnectionUrl={(v) => {
                                setConnectionUrl(v);
                                setError(null);
                              }}
                              connecting={connecting}
                              error={error}
                              onConnect={handleConnect}
                              inputRef={inputRef}
                            />
                          )}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Help link */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6 }}
        className="text-center mt-6"
      >
        <p className="text-sm text-stone-400">
          困ったときは{" "}
          <a
            href="/settings/contact"
            className="text-amber-600 hover:text-amber-700 underline underline-offset-2"
          >
            お問い合わせ
          </a>{" "}
          からご相談ください
        </p>
      </motion.div>
    </motion.div>
  );
}

/* ─── Step 1: プラグインインストール ─── */
function Step1Content() {
  const [copied, setCopied] = useState(false);

  const handleCopyUrl = () => {
    navigator.clipboard.writeText(PLUGIN_DOWNLOAD_URL);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-4">
      {/* Download button */}
      <a
        href={PLUGIN_DOWNLOAD_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-3 p-4 rounded-xl bg-white border border-amber-200 hover:border-amber-300 hover:shadow-sm transition-all group"
      >
        <div className="w-11 h-11 rounded-xl bg-amber-500 flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform">
          <Download className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-stone-800 text-sm">プラグインZIPをダウンロード</p>
          <p className="text-xs text-stone-500 truncate">wordpress-mcp-ability-plugin.zip</p>
        </div>
        <ExternalLink className="w-4 h-4 text-stone-400 flex-shrink-0" />
      </a>

      {/* URL copy fallback */}
      <button
        onClick={handleCopyUrl}
        className="flex items-center gap-2 text-xs text-stone-400 hover:text-stone-600 transition-colors mx-auto"
      >
        {copied ? (
          <>
            <Check className="w-3.5 h-3.5 text-emerald-500" />
            <span className="text-emerald-600">コピーしました</span>
          </>
        ) : (
          <>
            <Copy className="w-3.5 h-3.5" />
            <span>ダウンロードURLをコピー</span>
          </>
        )}
      </button>

      {/* Installation steps */}
      <div className="space-y-2.5 pl-1">
        <InstructionRow number="1" text="ダウンロードしたZIPファイルを保存します" />
        <InstructionRow
          number="2"
          text={
            <>
              WordPress管理画面 →{" "}
              <span className="font-semibold text-stone-700">プラグイン</span> →{" "}
              <span className="font-semibold text-stone-700">新規プラグインを追加</span>
            </>
          }
        />
        <InstructionRow
          number="3"
          text={
            <>
              <span className="font-semibold text-stone-700">プラグインのアップロード</span>
              をクリック → ZIPファイルを選択 →{" "}
              <span className="font-semibold text-stone-700">今すぐインストール</span>
            </>
          }
        />
        <InstructionRow
          number="4"
          text={
            <>
              <span className="font-semibold text-stone-700">プラグインを有効化</span>
              をクリック
            </>
          }
        />
      </div>

      {/* Next step hint */}
      <div className="flex items-center gap-2 text-xs text-amber-600 bg-amber-50 rounded-lg px-3 py-2 mt-2">
        <ArrowRight className="w-3.5 h-3.5 flex-shrink-0" />
        有効化したら、次のステップへ進んでください
      </div>
    </div>
  );
}

/* ─── Step 2: 接続URL取得 ─── */
function Step2Content() {
  return (
    <div className="space-y-4">
      <div className="space-y-2.5 pl-1">
        <InstructionRow
          number="1"
          text={
            <>
              WordPress管理画面 →{" "}
              <span className="font-semibold text-stone-700">設定</span> →{" "}
              <span className="font-semibold text-stone-700">MCP連携</span>
              を開きます
            </>
          }
        />
        <InstructionRow
          number="2"
          text={
            <>
              接続名を入力して{" "}
              <span className="inline-flex items-center px-2 py-0.5 rounded bg-blue-600 text-white text-xs font-medium">
                接続URLを生成する
              </span>{" "}
              をクリック
            </>
          }
        />
        <InstructionRow
          number="3"
          text="表示された接続URLをコピーします"
        />
      </div>

      {/* Visual hint */}
      <div className="rounded-xl bg-white border border-blue-100 p-4">
        <p className="text-xs font-medium text-stone-500 mb-2">接続URLの例:</p>
        <div className="flex items-center gap-2 p-2.5 rounded-lg bg-stone-50 border border-stone-200 font-mono text-xs text-stone-500 break-all">
          <Globe className="w-4 h-4 flex-shrink-0 text-stone-400" />
          https://example.com/wp-json/wp-mcp/v1/register?code=xxxxxxxx...
        </div>
      </div>

      <div className="flex items-center gap-2 text-xs text-stone-500 bg-stone-50 rounded-lg px-3 py-2">
        <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 text-stone-400" />
        接続URLは生成から10分間有効です。期限切れの場合は再度生成してください。
      </div>

      <div className="flex items-center gap-2 text-xs text-blue-600 bg-blue-50 rounded-lg px-3 py-2">
        <ArrowRight className="w-3.5 h-3.5 flex-shrink-0" />
        コピーしたら、次のステップでここに貼り付けてください
      </div>
    </div>
  );
}

/* ─── Step 3: 接続URL貼り付け ─── */
function Step3Content({
  connectionUrl,
  setConnectionUrl,
  connecting,
  error,
  onConnect,
  inputRef,
}: {
  connectionUrl: string;
  setConnectionUrl: (v: string) => void;
  connecting: boolean;
  error: string | null;
  onConnect: () => void;
  inputRef: React.RefObject<HTMLInputElement | null>;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-stone-600">
        WordPress管理画面でコピーした接続URLをここに貼り付けてください。
      </p>

      {/* Input */}
      <div className="flex gap-2">
        <Input
          ref={inputRef}
          type="url"
          placeholder="https://example.com/wp-json/wp-mcp/v1/register?code=..."
          value={connectionUrl}
          onChange={(e) => setConnectionUrl(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && connectionUrl.trim()) {
              onConnect();
            }
          }}
          disabled={connecting}
          className="flex-1 font-mono text-sm h-12 rounded-xl border-2 border-stone-200 focus:border-emerald-400 focus:ring-emerald-100"
        />
        <Button
          onClick={onConnect}
          disabled={connecting || !connectionUrl.trim()}
          className={`
            h-12 px-6 rounded-xl font-medium transition-all
            ${connecting || !connectionUrl.trim()
              ? "bg-stone-200 text-stone-500"
              : "bg-emerald-500 hover:bg-emerald-600 text-white shadow-sm hover:shadow-md"
            }
          `}
        >
          {connecting ? (
            <>
              <Loader2 className="w-4 h-4 mr-1.5 animate-spin" />
              接続中
            </>
          ) : (
            <>
              <Upload className="w-4 h-4 mr-1.5" />
              連携する
            </>
          )}
        </Button>
      </div>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            className="flex items-start gap-2 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm"
          >
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{error}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/* ─── Instruction row helper ─── */
function InstructionRow({
  number,
  text,
}: {
  number: string;
  text: React.ReactNode;
}) {
  return (
    <div className="flex items-start gap-3">
      <span className="flex-shrink-0 w-5 h-5 rounded-full bg-stone-200 text-stone-600 text-xs font-bold flex items-center justify-center mt-0.5">
        {number}
      </span>
      <p className="text-sm text-stone-600 leading-relaxed">{text}</p>
    </div>
  );
}
