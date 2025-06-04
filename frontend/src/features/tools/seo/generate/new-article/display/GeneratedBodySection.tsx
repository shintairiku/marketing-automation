'use client';
import { useState } from "react";
import React from 'react';
import { FaEdit, FaPlus, FaRobot, FaTrash } from "react-icons/fa";
import { IoChevronForward, IoRefresh } from "react-icons/io5";
import { IoInformationCircle } from "react-icons/io5";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Textarea } from "@/components/ui/textarea";

interface ArticleBlock {
  id: string;
  type: "h1" | "h2" | "h3" | "p";
  content: string;
}

interface EditResult {
  blockId: string;
  before: string;
  after: string;
}

export default function GeneratedBodySection() {
  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const [hoveredBlockId, setHoveredBlockId] = useState<string | null>(null);
  const [editRequest, setEditRequest] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [currentEditResult, setCurrentEditResult] = useState<EditResult | null>(
    null,
  );
  const [editMode, setEditMode] = useState<"ai" | "manual" | null>(null);
  const [manualEditValue, setManualEditValue] = useState("");
  const [isManualEditing, setIsManualEditing] = useState(false);
  const [manualEditingBlockId, setManualEditingBlockId] = useState<
    string | null
  >(null);
  const [selectedPreset, setSelectedPreset] = useState<
    "rewrite" | "double" | "casual" | null
  >(null);
  const [selectedAddPreset, setSelectedAddPreset] = useState<
    "seamless" | "paragraph" | null
  >(null);
  const [addPosition, setAddPosition] = useState<number | null>(null);
  const [isManualAdding, setIsManualAdding] = useState(false);
  const [manualAddValue, setManualAddValue] = useState("");

  // ダミー記事データ
  const [articleBlocks, setArticleBlocks] = useState<ArticleBlock[]>([
    {
      id: "1",
      type: "h1",
      content: "デジタルマーケティングの成功戦略：2024年版完全ガイド",
    },
    {
      id: "2",
      type: "h2",
      content: "1. データ分析の重要性",
    },
    {
      id: "3",
      type: "p",
      content:
        "現代のデジタルマーケティングにおいて、データ分析は欠かせない要素となっています。顧客の行動パターンや購買傾向を詳細に分析することで、より効果的なマーケティング戦略を立案することができます。",
    },
    {
      id: "4",
      type: "h2",
      content: "2. コンテンツマーケティングの効果的な活用",
    },
    {
      id: "5",
      type: "p",
      content:
        "質の高いコンテンツを継続的に配信することは、ブランドの信頼性向上と顧客エンゲージメントの増加に直結します。ターゲットオーディエンスのニーズに合わせたコンテンツ戦略を構築することが重要です。",
    },
    {
      id: "6",
      type: "h2",
      content: "3. まとめ",
    },
    {
      id: "7",
      type: "p",
      content:
        "デジタルマーケティングで成功するためには、明確な目標設定とKPIの定義、ターゲットオーディエンスの詳細な分析、データに基づいた継続的な改善、複数のチャネルを組み合わせた統合的なアプローチが重要です。",
    },
  ]);

  const handleBlockClick = (blockId: string) => {
    setSelectedBlockId(blockId);
    setEditMode(null);
    setManualEditValue("");
    setEditRequest("");
    setSelectedPreset(null);
    setAddPosition(null);
    setSelectedAddPreset(null);
    setManualAddValue("");
    // 選択されたブロックの内容を手動編集の初期値に設定
    const selectedBlock = articleBlocks.find((block) => block.id === blockId);
    if (selectedBlock) {
      setManualEditValue(selectedBlock.content);
    }
  };

  const handleAddClick = (position: number) => {
    setAddPosition(position);
    setSelectedBlockId(null);
    setEditMode(null);
    setManualEditValue("");
    setEditRequest("");
    setSelectedPreset(null);
    setSelectedAddPreset(null);
    setManualAddValue("");
  };

  const handlePresetSelect = (type: "rewrite" | "double" | "casual") => {
    setSelectedPreset(type);
  };

  const handleAddPresetSelect = (type: "seamless" | "paragraph") => {
    setSelectedAddPreset(type);
  };

  const handleAIEditStart = () => {
    if (!selectedBlockId) return;

    setIsEditing(true);

    // ダミー編集結果を生成
    setTimeout(() => {
      const selectedBlock = articleBlocks.find(
        (block) => block.id === selectedBlockId,
      );
      if (selectedBlock) {
        let afterContent = "";

        if (selectedPreset) {
          switch (selectedPreset) {
            case "rewrite":
              afterContent = `${selectedBlock.content}（全て作り替えられたバージョン）`;
              break;
            case "double":
              afterContent = `${selectedBlock.content} さらに詳しく説明すると、この概念は様々な側面から理解することができます。具体的な事例や実践的な応用方法についても考慮する必要があります。`;
              break;
            case "casual":
              afterContent = selectedBlock.content
                .replace(/です。/g, "だよ。")
                .replace(/ます。/g, "るよ。")
                .replace(/である/g, "なんだ");
              break;
          }
        } else if (editRequest.trim()) {
          afterContent = `${selectedBlock.content}（${editRequest}に基づいて修正されたバージョン）`;
        }

        setCurrentEditResult({
          blockId: selectedBlockId,
          before: selectedBlock.content,
          after: afterContent,
        });

        setIsEditing(false);
        setSheetOpen(true);
        setSelectedBlockId(null);
        setEditRequest("");
        setEditMode(null);
        setSelectedPreset(null);
      }
    }, 2000);
  };

  const handleAIAddStart = () => {
    if (addPosition === null) return;

    setIsEditing(true);

    // ダミー追加結果を生成
    setTimeout(() => {
      let newContent = "";

      if (selectedAddPreset) {
        switch (selectedAddPreset) {
          case "seamless":
            newContent =
              "このように、前述の内容から自然に続く文章として、さらなる詳細や関連情報を提供することで、読者の理解を深めることができます。";
            break;
          case "paragraph":
            newContent =
              "また、この分野における最新の動向として、テクノロジーの進歩により新たな可能性が広がっています。具体的には、AI技術の活用により効率化が図られ、従来では困難だった課題の解決が可能となっています。これにより、業界全体のパフォーマンス向上が期待されており、今後の発展に注目が集まっています。さらに、持続可能性の観点からも重要な意味を持つこの取り組みは、長期的な成長戦略の一環として位置づけられています。";
            break;
        }
      } else if (editRequest.trim()) {
        newContent = `${editRequest}に基づいて生成された新しい段落です。この内容は指定された要求に応じて作成されました。`;
      }

      // 新しいブロックIDを生成
      const newBlockId = `block_${Date.now()}`;

      setCurrentEditResult({
        blockId: newBlockId,
        before: "",
        after: newContent,
      });

      setIsEditing(false);
      setSheetOpen(true);
      setAddPosition(null);
      setEditRequest("");
      setEditMode(null);
      setSelectedAddPreset(null);
    }, 2000);
  };

  const handleStartManualEdit = () => {
    if (!selectedBlockId) return;

    const selectedBlock = articleBlocks.find(
      (block) => block.id === selectedBlockId,
    );
    if (selectedBlock) {
      setIsManualEditing(true);
      setManualEditingBlockId(selectedBlockId);
      setManualEditValue(selectedBlock.content);
      setSelectedBlockId(null);
      setEditMode(null);
    }
  };

  const handleSaveManualEdit = () => {
    if (!manualEditingBlockId || !manualEditValue.trim()) return;

    // 直接記事を更新
    setArticleBlocks((blocks) =>
      blocks.map((block) =>
        block.id === manualEditingBlockId
          ? { ...block, content: manualEditValue.trim() }
          : block,
      ),
    );

    setIsManualEditing(false);
    setManualEditingBlockId(null);
    setManualEditValue("");
  };

  const handleCancelManualEdit = () => {
    setIsManualEditing(false);
    setManualEditingBlockId(null);
    setManualEditValue("");
  };

  const handleStartManualAdd = () => {
    if (addPosition === null) return;

    setIsManualAdding(true);
    setManualAddValue("");
    setAddPosition(addPosition);
    setEditMode(null);
  };

  const handleSaveManualAdd = () => {
    if (addPosition === null || !manualAddValue.trim()) return;

    // 新しいブロックを生成
    const newBlock: ArticleBlock = {
      id: `block_${Date.now()}`,
      type: "p",
      content: manualAddValue.trim(),
    };

    // 直接記事に追加
    setArticleBlocks((blocks) => {
      const newBlocks = [...blocks];
      newBlocks.splice(addPosition, 0, newBlock);
      return newBlocks;
    });

    setIsManualAdding(false);
    setAddPosition(null);
    setManualAddValue("");
  };

  const handleCancelManualAdd = () => {
    setIsManualAdding(false);
    setAddPosition(null);
    setManualAddValue("");
  };

  const handleDeleteBlock = (blockId: string) => {
    setArticleBlocks((blocks) =>
      blocks.filter((block) => block.id !== blockId),
    );
    setSelectedBlockId(null);
  };

  const handleAccept = () => {
    if (currentEditResult) {
      if (currentEditResult.before === "") {
        // 新しいブロックを追加
        const newBlock: ArticleBlock = {
          id: currentEditResult.blockId,
          type: "p",
          content: currentEditResult.after,
        };

        setArticleBlocks((blocks) => {
          const newBlocks = [...blocks];
          if (addPosition !== null) {
            newBlocks.splice(addPosition, 0, newBlock);
          } else {
            newBlocks.push(newBlock);
          }
          return newBlocks;
        });
      } else {
        // 既存のブロックを修正
        setArticleBlocks((blocks) =>
          blocks.map((block) =>
            block.id === currentEditResult.blockId
              ? { ...block, content: currentEditResult.after }
              : block,
          ),
        );
      }
      setSheetOpen(false);
      setCurrentEditResult(null);
    }
  };

  const handleReject = () => {
    setSheetOpen(false);
    setCurrentEditResult(null);
  };

  const getBlockStyles = (type: string) => {
    switch (type) {
      case "h1":
        return "text-3xl font-bold mb-4";
      case "h2":
        return "text-2xl font-semibold mb-3";
      case "h3":
        return "text-xl font-medium mb-2";
      default:
        return "text-base mb-3 leading-relaxed";
    }
  };

  return (
    <div className="w-full space-y-6">
      <div className="mb-6">
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline" className="w-full">
              <IoInformationCircle className="w-4 h-4 mr-2" />
              使い方・機能説明
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>SEO本文生成の使い方</DialogTitle>
              <DialogDescription>
                効果的なSEO記事本文を生成するための手順をご確認ください。
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 text-sm">
              <div className="space-y-2">
                <h4 className="font-medium">1. 文字数の設定</h4>
                <p className="text-gray-600">
                  生成したい記事の文字数を選択してください。SEO効果を考慮すると3000文字以上が推奨されます。
                </p>
              </div>
              <div className="space-y-2">
                <h4 className="font-medium">2. 本文生成</h4>
                <p className="text-gray-600">
                  「本文を生成」ボタンで構造化された記事を自動生成します。
                </p>
              </div>
              <div className="space-y-2">
                <h4 className="font-medium">3. 内容確認・編集</h4>
                <p className="text-gray-600">
                  生成された本文を確認し、必要に応じて「自分で修正」で編集できます。
                </p>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
      {/* メイン記事エリア */}
      <Card className="flex-1">
        <CardContent className="p-6">
          <div className="prose prose-lg max-w-none">
            {/* 最初の追加エリア */}
            {!isManualAdding && (
              <Popover>
                <PopoverTrigger asChild>
                  <div
                    className={`py-2 cursor-pointer rounded transition-all ${
                      addPosition === 0 ? "bg-blue-50" : "hover:bg-gray-50"
                    } ${isManualEditing ? "opacity-50 pointer-events-none" : ""}`}
                    onClick={() => !isManualEditing && handleAddClick(0)}
                  >
                    <div className="flex items-center gap-2">
                      <div className="h-1 flex-1 bg-gray-50"></div>
                      <FaPlus className="text-gray-100" />
                      <div className="h-1 flex-1 bg-gray-50"></div>
                    </div>
                  </div>
                </PopoverTrigger>
                {addPosition === 0 && (
                  <PopoverContent className="w-80">
                    <div className="space-y-4">
                      <h4 className="font-medium">ブロックを追加</h4>

                      {editMode === null && (
                        <div className="space-y-2">
                          <Button
                            variant="outline"
                            className="w-full"
                            onClick={handleStartManualAdd}
                          >
                            自分で追加
                          </Button>
                          <Button
                            variant="outline"
                            className="w-full"
                            onClick={() => setEditMode("ai")}
                          >
                            AI追加を開始
                          </Button>
                        </div>
                      )}

                      {editMode === "ai" && (
                        <div className="space-y-4">
                          {/* プリセットボタン */}
                          <div className="space-y-2">
                            <Button
                              variant={
                                selectedAddPreset === "seamless"
                                  ? "default"
                                  : "outline"
                              }
                              className="w-full"
                              onClick={() => handleAddPresetSelect("seamless")}
                              disabled={isEditing}
                            >
                              シームレスに繋ぐ文章を追加
                            </Button>
                            <Button
                              variant={
                                selectedAddPreset === "paragraph"
                                  ? "default"
                                  : "outline"
                              }
                              className="w-full"
                              onClick={() => handleAddPresetSelect("paragraph")}
                              disabled={isEditing}
                            >
                              300文字の文章を追加
                            </Button>
                          </div>

                          {/* 自由記述エリア */}
                          <div className="space-y-2">
                            <label className="text-sm font-medium">
                              追加依頼（自由記述）
                            </label>
                            <Textarea
                              value={editRequest}
                              onChange={(e) => setEditRequest(e.target.value)}
                              placeholder="追加したい内容を記述してください..."
                              rows={3}
                              className="text-sm"
                            />
                          </div>

                          <div className="flex gap-2">
                            <Button
                              variant="outline"
                              className="flex-1"
                              onClick={() => setEditMode(null)}
                            >
                              戻る
                            </Button>
                            <Button
                              className="flex-1"
                              onClick={handleAIAddStart}
                              disabled={
                                isEditing ||
                                (!selectedAddPreset && !editRequest.trim())
                              }
                            >
                              {isEditing ? (
                                <>
                                  <IoRefresh className="w-4 h-4 mr-2 animate-spin" />
                                  追加中...
                                </>
                              ) : (
                                "追加開始"
                              )}
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  </PopoverContent>
                )}
              </Popover>
            )}

            {/* 手動追加エリア（最初の位置） */}
            {isManualAdding && addPosition === 0 && (
              <div className="space-y-3 p-4 border-2 border-primary rounded-lg bg-primary/5 mb-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-medium">内容を追加中</h4>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleCancelManualAdd}
                    >
                      キャンセル
                    </Button>
                    <Button
                      size="sm"
                      onClick={handleSaveManualAdd}
                      disabled={!manualAddValue.trim()}
                    >
                      保存
                    </Button>
                  </div>
                </div>
                <Textarea
                  value={manualAddValue}
                  onChange={(e) => setManualAddValue(e.target.value)}
                  placeholder="マークダウン記法も使用できます..."
                  rows={6}
                  className="text-sm"
                />
              </div>
            )}

            {articleBlocks.map((block, index) => {
              const isHovered = hoveredBlockId === block.id;
              const isSelected = selectedBlockId === block.id;
              const isManualEditingThisBlock = isManualEditing && manualEditingBlockId === block.id;

              const renderBlock = () => {
                const blockProps = {
                  className: `${getBlockStyles(block.type)} transition-all cursor-pointer border-2 border-transparent rounded p-2 mb-2 ${
                    isHovered ? "bg-gray-100" : ""
                  } ${isSelected ? "border-primary bg-primary/5" : ""} ${
                    isManualEditing || isManualAdding ? "opacity-50 pointer-events-none" : ""
                  }`,
                  onMouseEnter: () => !(isManualEditing || isManualAdding) && setHoveredBlockId(block.id),
                  onMouseLeave: () => setHoveredBlockId(null),
                  onClick: () => !(isManualEditing || isManualAdding) && handleBlockClick(block.id),
                };

                switch (block.type) {
                  case "h1":
                    return <h1 {...blockProps}>{block.content}</h1>;
                  case "h2":
                    return <h2 {...blockProps}>{block.content}</h2>;
                  case "h3":
                    return <h3 {...blockProps}>{block.content}</h3>;
                  case "p":
                    return <p {...blockProps}>{block.content}</p>;
                  default:
                    return <p {...blockProps}>{block.content}</p>;
                }
              };

              return (
                <div key={block.id}>
                  {isManualEditingThisBlock ? (
                    <div className="space-y-3 p-4 border-2 border-primary rounded-lg bg-primary/5 mb-4">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium">内容を編集中</h4>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={handleCancelManualEdit}
                          >
                            キャンセル
                          </Button>
                          <Button
                            size="sm"
                            onClick={handleSaveManualEdit}
                            disabled={!manualEditValue.trim()}
                          >
                            保存
                          </Button>
                        </div>
                      </div>
                      <Textarea
                        value={manualEditValue}
                        onChange={(e) => setManualEditValue(e.target.value)}
                        rows={6}
                        className="text-sm"
                      />
                    </div>
                  ) : (
                    <Popover>
                      <PopoverTrigger asChild>
                        {renderBlock()}
                      </PopoverTrigger>
                      {isSelected && (
                        <PopoverContent className="w-80">
                          <div className="space-y-4">
                            <h4 className="font-medium">ブロックを修正</h4>

                            {editMode === null && (
                              <div className="space-y-2">
                                <Button
                                  className="w-full"
                                  onClick={() => setEditMode("ai")}
                                >
                                  <FaRobot className="w-4 h-4 mr-2" />
                                  AI修正を開始
                                </Button>
                                <Button
                                  variant="outline"
                                  className="w-full"
                                  onClick={handleStartManualEdit}
                                >
                                  <FaEdit className="w-4 h-4 mr-2" />
                                  自分で修正
                                </Button>
                                <AlertDialog>
                                  <AlertDialogTrigger asChild>
                                    <Button
                                      variant="outline"
                                      className="w-full text-red-600 hover:text-red-700 hover:bg-red-50"
                                    >
                                      <FaTrash className="w-4 h-4 mr-2" />
                                      ブロックを消去
                                    </Button>
                                  </AlertDialogTrigger>
                                  <AlertDialogContent>
                                    <AlertDialogHeader>
                                      <AlertDialogTitle>
                                        ブロックを削除しますか？
                                      </AlertDialogTitle>
                                      <AlertDialogDescription>
                                        この操作は取り消すことができません。選択したブロックが完全に削除されます。
                                      </AlertDialogDescription>
                                    </AlertDialogHeader>
                                    <AlertDialogFooter>
                                      <AlertDialogCancel>
                                        キャンセル
                                      </AlertDialogCancel>
                                      <AlertDialogAction
                                        className="bg-red-600 hover:bg-red-700"
                                        onClick={() =>
                                          selectedBlockId &&
                                          handleDeleteBlock(selectedBlockId)
                                        }
                                      >
                                        削除
                                      </AlertDialogAction>
                                    </AlertDialogFooter>
                                  </AlertDialogContent>
                                </AlertDialog>
                              </div>
                            )}

                            {editMode === "ai" && (
                              <div className="space-y-4">
                                {/* プリセットボタン */}
                                <div className="space-y-2">
                                  <Button
                                    variant={
                                      selectedPreset === "rewrite"
                                        ? "default"
                                        : "outline"
                                    }
                                    className="w-full"
                                    onClick={() =>
                                      handlePresetSelect("rewrite")
                                    }
                                    disabled={isEditing}
                                  >
                                    全て作り替える
                                  </Button>
                                  <Button
                                    variant={
                                      selectedPreset === "double"
                                        ? "default"
                                        : "outline"
                                    }
                                    className="w-full"
                                    onClick={() => handlePresetSelect("double")}
                                    disabled={isEditing}
                                  >
                                    分量を倍に
                                  </Button>
                                  <Button
                                    variant={
                                      selectedPreset === "casual"
                                        ? "default"
                                        : "outline"
                                    }
                                    className="w-full"
                                    onClick={() => handlePresetSelect("casual")}
                                    disabled={isEditing}
                                  >
                                    もっとカジュアルに
                                  </Button>
                                </div>

                                {/* 自由記述エリア */}
                                <div className="space-y-2">
                                  <label className="text-sm font-medium">
                                    修正依頼（自由記述）
                                  </label>
                                  <Textarea
                                    value={editRequest}
                                    onChange={(e) =>
                                      setEditRequest(e.target.value)
                                    }
                                    placeholder="修正したい内容を記述してください..."
                                    rows={3}
                                    className="text-sm"
                                  />
                                </div>

                                <div className="flex gap-2">
                                  <Button
                                    variant="outline"
                                    className="flex-1"
                                    onClick={() => setEditMode(null)}
                                  >
                                    戻る
                                  </Button>
                                  <Button
                                    className="flex-1"
                                    onClick={handleAIEditStart}
                                    disabled={
                                      isEditing ||
                                      (!selectedPreset && !editRequest.trim())
                                    }
                                  >
                                    {isEditing ? (
                                      <>
                                        <IoRefresh className="w-4 h-4 mr-2 animate-spin" />
                                        修正中...
                                      </>
                                    ) : (
                                      "修正開始"
                                    )}
                                  </Button>
                                </div>
                              </div>
                            )}
                          </div>
                        </PopoverContent>
                      )}
                    </Popover>
                  )}

                  {/* ブロック間の追加エリア */}
                  {!isManualAdding && (
                    <Popover>
                      <PopoverTrigger asChild>
                        <div
                          className={`py-2 cursor-pointer rounded transition-all ${
                            addPosition === index + 1
                              ? "bg-blue-50"
                              : "hover:bg-gray-50"
                          } ${isManualEditing ? "opacity-50 pointer-events-none" : ""}`}
                          onClick={() =>
                            !isManualEditing && handleAddClick(index + 1)
                          }
                        >
                          <div className="flex items-center gap-2">
                            <div className="h-1 flex-1 bg-gray-50"></div>
                            <FaPlus className="text-gray-100" />
                            <div className="h-1 flex-1 bg-gray-50"></div>
                          </div>
                        </div>
                      </PopoverTrigger>
                      {addPosition === index + 1 && (
                        <PopoverContent className="w-80">
                          <div className="space-y-4">
                            <h4 className="font-medium">ブロックを追加</h4>

                            {editMode === null && (
                              <div className="space-y-2">
                                <Button
                                  variant="outline"
                                  className="w-full"
                                  onClick={handleStartManualAdd}
                                >
                                  自分で追加
                                </Button>
                                <Button
                                  variant="outline"
                                  className="w-full"
                                  onClick={() => setEditMode("ai")}
                                >
                                  AI追加を開始
                                </Button>
                              </div>
                            )}

                            {editMode === "ai" && (
                              <div className="space-y-4">
                                {/* プリセットボタン */}
                                <div className="space-y-2">
                                  <Button
                                    variant={
                                      selectedAddPreset === "seamless"
                                        ? "default"
                                        : "outline"
                                    }
                                    className="w-full"
                                    onClick={() =>
                                      handleAddPresetSelect("seamless")
                                    }
                                    disabled={isEditing}
                                  >
                                    シームレスに繋ぐ文章を追加
                                  </Button>
                                  <Button
                                    variant={
                                      selectedAddPreset === "paragraph"
                                        ? "default"
                                        : "outline"
                                    }
                                    className="w-full"
                                    onClick={() =>
                                      handleAddPresetSelect("paragraph")
                                    }
                                    disabled={isEditing}
                                  >
                                    300文字の文章を追加
                                  </Button>
                                </div>

                                {/* 自由記述エリア */}
                                <div className="space-y-2">
                                  <label className="text-sm font-medium">
                                    追加依頼（自由記述）
                                  </label>
                                  <Textarea
                                    value={editRequest}
                                    onChange={(e) =>
                                      setEditRequest(e.target.value)
                                    }
                                    placeholder="追加したい内容を記述してください..."
                                    rows={3}
                                    className="text-sm"
                                  />
                                </div>

                                <div className="flex gap-2">
                                  <Button
                                    variant="outline"
                                    className="flex-1"
                                    onClick={() => setEditMode(null)}
                                  >
                                    戻る
                                  </Button>
                                  <Button
                                    className="flex-1"
                                    onClick={handleAIAddStart}
                                    disabled={
                                      isEditing ||
                                      (!selectedAddPreset &&
                                        !editRequest.trim())
                                    }
                                  >
                                    {isEditing ? (
                                      <>
                                        <IoRefresh className="w-4 h-4 mr-2 animate-spin" />
                                        追加中...
                                      </>
                                    ) : (
                                      "追加開始"
                                    )}
                                  </Button>
                                </div>
                              </div>
                            )}
                          </div>
                        </PopoverContent>
                      )}
                    </Popover>
                  )}

                  {/* 手動追加エリア */}
                  {isManualAdding && addPosition === index + 1 && (
                    <div className="space-y-3 p-4 border-2 border-primary rounded-lg bg-primary/5 mt-2">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium">内容を追加中</h4>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={handleCancelManualAdd}
                          >
                            キャンセル
                          </Button>
                          <Button
                            size="sm"
                            onClick={handleSaveManualAdd}
                            disabled={!manualAddValue.trim()}
                          >
                            保存
                          </Button>
                        </div>
                      </div>
                      <Textarea
                        value={manualAddValue}
                        onChange={(e) => setManualAddValue(e.target.value)}
                        placeholder="マークダウン記法も使用できます..."
                        rows={6}
                        className="text-sm"
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* 最下部ボタン */}
      <div className="w-full">
        <Button className="w-full" size="lg">
          Next.../公開設定
          <IoChevronForward className="w-4 h-4 mr-2" />
        </Button>
      </div>

      {/* Before/After シート */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="bottom" className="max-h-[60vh] p-5 bg-white">
          {currentEditResult && (
            <div className="mt-6 space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-full">
                {/* Before */}
                <div className="space-y-3">
                  <h3 className="font-medium text-gray-600">変更前</h3>
                  <div className="p-4 bg-red-50 border border-red-200 rounded-lg h-40 overflow-y-auto">
                    <p className="text-sm text-gray-700">
                      {currentEditResult.before || "（新規追加）"}
                    </p>
                  </div>
                </div>

                {/* After */}
                <div className="space-y-3">
                  <h3 className="font-medium text-gray-600">変更後</h3>
                  <div className="p-4 bg-green-50 border border-green-200 rounded-lg h-40 overflow-y-auto">
                    <p className="text-sm text-gray-700">
                      {currentEditResult.after}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex gap-3 justify-center">
                <Button variant="outline" onClick={handleReject}>
                  変更を破棄
                </Button>
                <Button onClick={handleAccept}>変更を適用</Button>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
