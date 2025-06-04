"use client";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent } from "@/components/ui/card";
import { IoSparkles } from "react-icons/io5";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { IoRefresh, IoPencil, IoChevronForward } from "react-icons/io5";
import { Input } from "@/components/ui/input";
import React, { useState, useEffect } from "react";
import { StepIndicator } from "../component/StepIndicator";

// ダミーデータ
const dummyTitlesData = {
  Webマーケティング: [
    "Webマーケティングの完全ガイド | 初心者でもわかる実践的方法",
    "2024年版 Webマーケティングで成功する秘訣とは？",
    "プロが教えるWebマーケティングの活用術 | 効果的な戦略",
    "Webマーケティングとは？基礎から応用まで徹底解説",
    "Webマーケティングの最新トレンド | 業界動向2024",
    "Webマーケティングを始める前に知っておきたい5つのポイント",
    "Webマーケティングの効果的な使い方 | 成功事例付き",
    "初心者向けWebマーケティング講座 | ステップバイステップガイド",
  ],
  SEO: [
    "SEO対策の完全ガイド | 検索上位を狙う実践的方法",
    "2024年版 SEO対策で成果を出す最新テクニック",
    "プロが教えるSEO対策の基本から応用まで",
    "SEO対策とは？初心者でもわかる基礎知識",
    "SEO対策の最新アルゴリズム対応術",
    "SEO対策で失敗しないための重要ポイント",
    "効果的なSEO対策 | 検索流入を増やす方法",
    "初心者向けSEO対策講座 | 今すぐ始められる施策",
  ],
  コンテンツマーケティング: [
    "コンテンツマーケティングの完全ガイド | 成果につながる戦略",
    "2024年版 コンテンツマーケティングの最新手法",
    "プロが教えるコンテンツマーケティングの実践術",
    "コンテンツマーケティングとは？基礎から学ぶ入門講座",
    "コンテンツマーケティングの効果測定と改善方法",
    "コンテンツマーケティングで集客を成功させるコツ",
    "効果的なコンテンツマーケティング | 企業事例付き",
    "初心者向けコンテンツマーケティング | 始め方ガイド",
  ],
};

// バックエンド連携を意識した取得関数
function fetchDummyTitles() {
  // 今後API連携に差し替えやすいように
  // 今はSEOカテゴリから1件ランダム取得
  const titles = dummyTitlesData["SEO"];
  const randomIdx = Math.floor(Math.random() * titles.length);
  return titles[randomIdx];
}

export default function GeneratedTitleSection() {
  // タイトル型
  type TitleItem = {
    id: string;
    title: string;
    isSelected: boolean;
    characters: number;
  };

  // 状態管理
  const [generatedTitles, setGeneratedTitles] = useState<TitleItem[]>([]);
  const [isEditing, setIsEditing] = useState(false);
  const [editingTitleId, setEditingTitleId] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState("");
  const [selectedTitles, setSelectedTitles] = useState<string[]>([]);

  // 初期ダミーデータ投入
  useEffect(() => {
    // SEOカテゴリの全タイトルをセット
    const seoTitles = dummyTitlesData["SEO"];
    setGeneratedTitles(
      seoTitles.map((title, idx) => ({
        id: `seo-${idx}`,
        title,
        isSelected: false,
        characters: title.length,
      }))
    );
  }, []);

  // タイトル選択
  const toggleTitleSelection = (id: string) => {
    setGeneratedTitles((prev) =>
      prev.map((t) =>
        t.id === id ? { ...t, isSelected: !t.isSelected } : t
      )
    );
    setSelectedTitles((prev) =>
      prev.includes(id)
        ? prev.filter((tid) => tid !== id)
        : [...prev, id]
    );
  };

  // 編集開始・完了
  const handleEditClick = () => {
    if (isEditing && editingTitleId) {
      // 編集完了
      setGeneratedTitles((prev) =>
        prev.map((t) =>
          t.id === editingTitleId
            ? { ...t, title: editingValue, characters: editingValue.length }
            : t
        )
      );
      setIsEditing(false);
      setEditingTitleId(null);
      setEditingValue("");
    } else {
      // 編集開始（最初の選択タイトル or 先頭）
      const editId = selectedTitles[0] || (generatedTitles[0] && generatedTitles[0].id);
      if (editId) {
        const target = generatedTitles.find((t) => t.id === editId);
        setIsEditing(true);
        setEditingTitleId(editId);
        setEditingValue(target ? target.title : "");
      }
    }
  };

  // 編集中
  const handleTitleEdit = (val: string) => {
    setEditingValue(val);
  };

  return (
    <div className="w-full flex flex-col min-h-0">
        {/* メインカード（flex-1で拡張） */}
        <ScrollArea className="flex-1 pr-2">
          <Card className="flex-1 flex flex-col mb-6">
            <StepIndicator currentStep="theme" />
            <CardContent className="p-6 flex-1 overflow-hidden">
              {generatedTitles.length === 0 ? (
                <div className="h-full flex items-center justify-center text-gray-500">
                  <div className="text-center">
                    <IoSparkles className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                    <p>左側の設定からタイトルを生成してください</p>
                  </div>
                </div>
              ) : (
                <div className="h-full overflow-y-auto">
                  <div className="grid grid-cols-3 gap-4">
                    {generatedTitles.map((title) => (
                      <div
                        key={title.id}
                        className={`p-4 border rounded-lg cursor-pointer transition-all ${
                          title.isSelected
                            ? "border-primary bg-primary/5"
                            : "border-gray-200 hover:border-gray-300"
                        }`}
                        onClick={() => toggleTitleSelection(title.id)}
                      >
                        <div className="flex items-start justify-between gap-3">
                          {isEditing && editingTitleId === title.id ? (
                            <div className="flex-1 space-y-2">
                              <Input
                                value={editingValue}
                                onChange={(e) => handleTitleEdit(e.target.value)}
                                className="w-full"
                                autoFocus
                              />
                            </div>
                          ) : (
                            <p className="flex-1 leading-relaxed">
                              {title.title}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </ScrollArea>

        {/* ボタン集（最下部に配置） */}
        <div className="mt-auto flex justify-between">
          <div className="flex gap-3 w-full">
            <Button
              variant="outline"
              onClick={() => setGeneratedTitles([])}
              className="flex-2"
              disabled={generatedTitles.length === 0}
            >
              <IoRefresh className="w-4 h-4 mr-2" />
              やり直す
            </Button>
            <Button
              variant="outline"
              disabled={selectedTitles.length === 0 && !isEditing}
              className={`flex-2 ${isEditing ? "bg-orange-500 hover:bg-orange-600 text-white" : ""}`}
              onClick={handleEditClick}
            >
              <IoPencil className="w-4 h-4 mr-2" />
              {isEditing ? "修正完了" : "自分で修正"}
            </Button>
            <Button disabled={selectedTitles.length === 0} className="flex-1">
              Next... / 見出し作成
              <IoChevronForward className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </div>
      </div>
    )
}
