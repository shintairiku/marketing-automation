"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { BookOpen, ChevronDown, Maximize2, X } from "lucide-react";

const SLIDES_URL =
  "https://docs.google.com/presentation/d/e/2PACX-1vQ0rZHx8nTz3yzuKiZdCiVefVXAXGLXtLimetKhBeioIqGrrSvVbMruFqIA9KYpWmF1QEQa1r1kPK5E/pubembed?start=false&loop=false&delayms=3000";

interface WordPressGuideSlidesProps {
  /** "inline" = 常時表示（オンボーディング用）, "collapsible" = 折りたたみ式（設定ページ用） */
  variant?: "inline" | "collapsible";
  defaultOpen?: boolean;
}

export function WordPressGuideSlides({
  variant = "inline",
  defaultOpen = true,
}: WordPressGuideSlidesProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [fullscreen, setFullscreen] = useState(false);
  const [loaded, setLoaded] = useState(false);

  if (variant === "collapsible") {
    return (
      <>
        <div className="rounded-2xl border border-blue-100 bg-gradient-to-br from-blue-50/80 via-white to-indigo-50/50 overflow-hidden transition-shadow hover:shadow-sm">
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="w-full cursor-pointer group"
          >
            {/* Top row: icon + title */}
            <div className="flex items-center gap-3 px-5 pt-4 pb-2">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-100 to-indigo-100 flex items-center justify-center group-hover:from-blue-200 group-hover:to-indigo-200 transition-colors flex-shrink-0">
                <BookOpen className="w-[18px] h-[18px] text-blue-600" />
              </div>
              <div className="text-left">
                <p className="font-semibold text-stone-800 text-sm">
                  セットアップガイド
                </p>
                <p className="text-xs text-stone-500">
                  スライドで連携手順を確認できます
                </p>
              </div>
            </div>

            {/* Bottom bar: centered chevron with label — clearly "opens downward" */}
            <div className="flex items-center justify-center gap-1.5 pb-3 pt-1">
              <div className="flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-blue-50 group-hover:bg-blue-100 transition-colors">
                <span className="text-xs font-medium text-blue-600">
                  {isOpen ? "ガイドを閉じる" : "ガイドを見る"}
                </span>
                <ChevronDown
                  className={`w-4 h-4 text-blue-500 transition-transform duration-200 ${
                    isOpen ? "rotate-180" : ""
                  }`}
                />
              </div>
            </div>
          </button>

          <AnimatePresence initial={false}>
            {isOpen && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
                className="overflow-hidden"
              >
                <div className="px-3 pb-3">
                  <SlidesEmbed
                    onFullscreen={() => setFullscreen(true)}
                    loaded={loaded}
                    onLoad={() => setLoaded(true)}
                    rounded
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <FullscreenOverlay
          open={fullscreen}
          onClose={() => setFullscreen(false)}
        />
      </>
    );
  }

  // ── inline variant ──
  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.5 }}
      >
        <div className="rounded-2xl overflow-hidden shadow-sm border border-stone-200 bg-white">
          {/* Header bar */}
          <div className="bg-stone-100 border-b border-stone-200 px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-white border border-stone-200 flex items-center justify-center">
                <BookOpen className="w-4 h-4 text-stone-500" />
              </div>
              <div>
                <h3 className="text-stone-700 font-semibold text-sm">
                  セットアップガイド
                </h3>
                <p className="text-stone-400 text-xs">
                  スライドで手順をかんたん確認
                </p>
              </div>
            </div>
            <button
              onClick={() => setFullscreen(true)}
              className="p-2 rounded-lg hover:bg-stone-200 transition-colors cursor-pointer"
              title="全画面で表示"
            >
              <Maximize2 className="w-4 h-4 text-stone-400" />
            </button>
          </div>

          {/* Slides */}
          <SlidesEmbed
            onFullscreen={() => setFullscreen(true)}
            loaded={loaded}
            onLoad={() => setLoaded(true)}
          />
        </div>
      </motion.div>

      <FullscreenOverlay
        open={fullscreen}
        onClose={() => setFullscreen(false)}
      />
    </>
  );
}

/* ─── Slides iframe embed ─── */
function SlidesEmbed({
  loaded,
  onLoad,
  onFullscreen,
  rounded,
}: {
  loaded: boolean;
  onLoad: () => void;
  onFullscreen: () => void;
  rounded?: boolean;
}) {
  return (
    <div
      className={`relative bg-stone-100 group ${rounded ? "rounded-xl overflow-hidden" : ""}`}
      style={{ aspectRatio: "960 / 569" }}
    >
      {/* Loading state */}
      {!loaded && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-gradient-to-br from-stone-50 to-stone-100">
          <div className="flex flex-col items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-blue-100 flex items-center justify-center animate-pulse">
              <BookOpen className="w-6 h-6 text-blue-400" />
            </div>
            <p className="text-sm text-stone-400 animate-pulse">
              スライドを読み込み中...
            </p>
          </div>
        </div>
      )}

      {/* Fullscreen button overlay (appears on hover) */}
      <button
        onClick={onFullscreen}
        className="absolute top-3 right-3 z-20 p-2 rounded-lg bg-black/40 opacity-0 group-hover:opacity-100 hover:bg-black/60 backdrop-blur-sm transition-all cursor-pointer"
        title="全画面で表示"
      >
        <Maximize2 className="w-4 h-4 text-white" />
      </button>

      <iframe
        src={SLIDES_URL}
        className="absolute inset-0 w-full h-full"
        frameBorder="0"
        allowFullScreen
        onLoad={onLoad}
        title="WordPress連携セットアップガイド"
      />
    </div>
  );
}

/* ─── Fullscreen overlay (portal) ─── */
function FullscreenOverlay({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100]">
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Content */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
        className="absolute inset-4 sm:inset-6 md:inset-8 flex flex-col"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2.5 bg-stone-900 rounded-t-xl border-b border-stone-700/50">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-stone-400" />
            <span className="text-sm font-medium text-stone-200">
              セットアップガイド
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-stone-700/80 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4 text-stone-400 hover:text-stone-200" />
          </button>
        </div>

        {/* Iframe (fills remaining space) */}
        <div className="flex-1 bg-stone-900 rounded-b-xl overflow-hidden">
          <iframe
            src={SLIDES_URL}
            className="w-full h-full"
            frameBorder="0"
            allowFullScreen
            title="WordPress連携セットアップガイド"
          />
        </div>
      </motion.div>
    </div>
  );
}
