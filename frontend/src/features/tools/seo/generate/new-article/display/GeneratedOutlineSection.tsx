'use client';

import React, { useEffect, useMemo,useState } from "react";
import { IoChevronForward,IoList, IoPencil, IoRefresh } from 'react-icons/io5';

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";

interface GeneratedOutline {
  id: string;
  title: string;
  level: number;
  isSelected: boolean;
}

export default function GenerateSeoOutline() {
  const [displayMode, setDisplayMode] = useState<"current" | "html" | "markdown">("current");
  const [generatedOutlines, setGeneratedOutlines] = useState<GeneratedOutline[]>([]);
  const [isEditing, setIsEditing] = useState(false);
  const [editingOutlineId, setEditingOutlineId] = useState<string | null>(null);
  const [editingValue, setEditingValue] = useState("");

  const dummyOutlineData = useMemo(() => ({
    "1000": [
      { title: "はじめに", level: 1 },
      { title: "問題提起", level: 2 },
      { title: "本記事で解決できること", level: 2 },
      { title: "SEO対策の重要性", level: 1 },
      { title: "検索エンジンの仕組み", level: 2 },
      { title: "SEOの基本原則", level: 2 },
      { title: "キーワード選定のポイント", level: 2 },
      { title: "コンテンツ最適化の方法", level: 1 },
      { title: "タイトルとメタディスクリプション", level: 2 },
      { title: "見出し構造の最適化", level: 2 },
      { title: "内部リンクの活用", level: 2 },
      { title: "まとめ", level: 1 },
      { title: "次のステップ", level: 2 }
    ]
  }), []);

  // スライダー用の値とラベルのマッピング
  const wordCountOptions = [500, 1000, 3000, 5000, 10000];
  const getWordCountFromSliderValue = (value: number) => {
    return wordCountOptions[value] || wordCountOptions[1];
  };

  // 初期ダミーデータ投入
  useEffect(() => {
    // デフォルトは1000ワードのアウトライン
    const template = dummyOutlineData["1000"];
    const mockOutlines: GeneratedOutline[] = template.map((item, index) => ({
      id: `${index + 1}`,
      title: item.title,
      level: item.level,
      isSelected: false
    }));
    setGeneratedOutlines(mockOutlines);
  }, [dummyOutlineData]);

  const toggleOutlineSelection = (id: string) => {
    if (isEditing) return;
    setGeneratedOutlines((outlines) =>
      outlines.map((outline) =>
        outline.id === id ? { ...outline, isSelected: !outline.isSelected } : outline,
      ),
    );
  };

  const handleEditClick = () => {
    if (isEditing) {
      // 修正完了
      if (editingOutlineId && editingValue.trim()) {
        setGeneratedOutlines(outlines =>
          outlines.map(outline =>
            outline.id === editingOutlineId
              ? { ...outline, title: editingValue.trim() }
              : outline
          )
        );
      }
      setIsEditing(false);
      setEditingOutlineId(null);
      setEditingValue("");
    } else {
      // 修正開始
      const selectedOutline = generatedOutlines.find(outline => outline.isSelected);
      if (selectedOutline) {
        setIsEditing(true);
        setEditingOutlineId(selectedOutline.id);
        setEditingValue(selectedOutline.title);
      }
    }
  };

  const handleOutlineEdit = (value: string) => {
    setEditingValue(value);
  };

  const cancelEdit = () => {
    setIsEditing(false);
    setEditingOutlineId(null);
    setEditingValue("");
  };

  const selectedOutlines = generatedOutlines.filter((outline) => outline.isSelected);

  const getIndentClass = (level: number) => {
    switch (level) {
      case 1: return "ml-0";
      case 2: return "ml-4";
      case 3: return "ml-8";
      default: return "ml-0";
    }
  };

  const getLevelPrefix = (level: number) => {
    switch (level) {
      case 1: return "■";
      case 2: return "▼";
      case 3: return "●";
      default: return "■";
    }
  };

  const getHtmlTag = (level: number) => {
    return `h${level}`;
  };

  const getMarkdownPrefix = (level: number) => {
    return "#".repeat(level);
  };

  const formatOutlineForDisplay = (outline: GeneratedOutline) => {
    switch (displayMode) {
      case "html":
        return `<${getHtmlTag(outline.level)}>${outline.title}</${getHtmlTag(outline.level)}>`;
      case "markdown":
        return `${getMarkdownPrefix(outline.level)} ${outline.title}`;
      default:
        return outline.title;
    }
  };

  return (
      <div className="w-full flex flex-col">
        {/* メインカード */}
        <Card className="flex-1 flex flex-col mb-6">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Button
                  variant={displayMode === "current" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setDisplayMode("current")}
                >
                  今の状態
                </Button>
                <Button
                  variant={displayMode === "html" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setDisplayMode("html")}
                >
                  HTML
                </Button>
                <Button
                  variant={displayMode === "markdown" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setDisplayMode("markdown")}
                >
                  Markdown
                </Button>
              </div>
            </div>
            <Separator />
          </CardHeader>
          <CardContent className="p-6 pt-0 flex-1 overflow-hidden">
            {generatedOutlines.length === 0 ? (
              <div className="h-full flex items-center justify-center text-gray-500">
                <div className="text-center">
                  <IoList className="w-12 h-12 mx-auto mb-3 text-gray-400" />
                  <p>上側の設定から見出しを生成してください</p>
                </div>
              </div>
            ) : (
              <div className="space-y-2 h-full overflow-y-auto">
                {displayMode === "current" ? (
                  // 今の状態表示（クリック可能）
                  generatedOutlines.map((outline) => (
                    <div
                      key={outline.id}
                      className={`p-3 border rounded-lg transition-all ${
                        outline.isSelected
                          ? "border-primary bg-primary/5"
                          : "border-gray-200 hover:border-gray-300"
                      } ${isEditing && editingOutlineId !== outline.id ? 'opacity-50' : 'cursor-pointer'}`}
                      onClick={() => isEditing && editingOutlineId === outline.id ? null : toggleOutlineSelection(outline.id)}
                    >
                      <div className={`flex items-center gap-3 ${getIndentClass(outline.level)}`}>
                        <span className="text-primary font-semibold">
                          {getLevelPrefix(outline.level)}
                        </span>
                        {isEditing && editingOutlineId === outline.id ? (
                          <div className="flex-1 flex items-center gap-2">
                            <Input
                              value={editingValue}
                              onChange={(e) => handleOutlineEdit(e.target.value)}
                              className="flex-1"
                              autoFocus
                            />
                            <Button size="sm" onClick={handleEditClick} className="bg-orange-500 hover:bg-orange-600 text-white">
                              完了
                            </Button>
                            <Button size="sm" variant="outline" onClick={cancelEdit}>
                              キャンセル
                            </Button>
                          </div>
                        ) : (
                          <p className="flex-1 leading-relaxed">{outline.title}</p>
                        )}
                        <Badge variant="outline" className="shrink-0 text-xs">
                          H{outline.level}
                        </Badge>
                      </div>
                    </div>
                  ))
                ) : (
                  // HTML/Markdown表示（コピー用テキスト形式）
                  <div className="bg-gray-50 p-4 rounded-lg border">
                    <pre className="whitespace-pre-wrap text-sm font-mono leading-relaxed">
                      {generatedOutlines.map((outline) => formatOutlineForDisplay(outline)).join('\n')}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* ボタン集（最下部に配置） */}
        <div className="mt-auto flex justify-between">
          <div className="flex gap-3 w-full">
            <Button 
              variant="outline" 
              onClick={() => setGeneratedOutlines([])}
              className="flex-1"
              disabled={generatedOutlines.length === 0}
            >
              <IoRefresh className="w-4 h-4 mr-2" />
              やり直す
            </Button>
            <Button 
              variant="outline" 
              disabled={selectedOutlines.length === 0 && !isEditing}
              className={`flex-1 ${isEditing ? 'bg-orange-500 hover:bg-orange-600 text-white' : ''}`}
              onClick={handleEditClick}
            >
              <IoPencil className="w-4 h-4 mr-2" />
              {isEditing ? '修正完了' : '自分で修正'}
            </Button>
            <Button 
              disabled={selectedOutlines.length === 0}
              className="flex-1"
            >
              Next... / 本文作成
              <IoChevronForward className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </div>
      </div>
  );
}
