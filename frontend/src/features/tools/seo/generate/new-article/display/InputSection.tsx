"use client";
import { useState } from 'react';
import { ChevronDown, ChevronUp, Plus, X } from "lucide-react";
import { IoRefresh, IoSparkles } from "react-icons/io5";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Textarea } from "@/components/ui/textarea";

interface InputSectionProps {
  onStartGeneration: (data: any) => void;
  isConnected: boolean;
  isGenerating: boolean;
}

export default function InputSection({ onStartGeneration, isConnected, isGenerating }: InputSectionProps) {
    const [seoKeywords, setSeoKeywords] = useState<string[]>([]);
    const [currentKeyword, setCurrentKeyword] = useState('');
    const [themeCount, setThemeCount] = useState(3);
    const [targetAgeGroup, setTargetAgeGroup] = useState('');
    const [personaType, setPersonaType] = useState('');
    const [customPersona, setCustomPersona] = useState('');
    const [targetLength, setTargetLength] = useState(3000);
    const [researchQueries, setResearchQueries] = useState(3);
    const [personaExamples, setPersonaExamples] = useState(3);
    const [companyName, setCompanyName] = useState('');
    const [companyDescription, setCompanyDescription] = useState('');
    const [companyStyleGuide, setCompanyStyleGuide] = useState('');
    const [showAdvanced, setShowAdvanced] = useState(false);

    // キーワード追加関数
    const addKeyword = () => {
        const trimmedKeyword = currentKeyword.trim();
        if (trimmedKeyword && !seoKeywords.includes(trimmedKeyword)) {
            setSeoKeywords([...seoKeywords, trimmedKeyword]);
            setCurrentKeyword('');
        }
    };

    // キーワード削除関数
    const removeKeyword = (indexToRemove: number) => {
        setSeoKeywords(seoKeywords.filter((_, index) => index !== indexToRemove));
    };

    // Enterキーでキーワード追加
    const handleKeywordKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addKeyword();
        }
    };

    const handleStartGeneration = () => {
        if (seoKeywords.length === 0) {
            alert('SEOキーワードを最低1つ入力してください');
            return;
        }

        if (!targetAgeGroup) {
            alert('ターゲット年代層を選択してください');
            return;
        }

        const requestData = {
            initial_keywords: seoKeywords,
            target_age_group: targetAgeGroup,
            num_theme_proposals: themeCount,
            num_research_queries: researchQueries,
            num_persona_examples: personaExamples,
            persona_type: personaType || null,
            custom_persona: customPersona || null,
            target_length: targetLength,
            company_name: companyName || null,
            company_description: companyDescription || null,
            company_style_guide: companyStyleGuide || null,
        };

        onStartGeneration(requestData);
    };

    const themeCountOptions = [1, 3, 5, 8, 10];
    
    return (
      <div className="w-full flex flex-col min-h-0 max-h-full overflow-hidden">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6">
          {/* Card1: SEOワード */}
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="text-lg">リーチしたいSEOワード *</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* キーワード入力欄 */}
                <div className="flex gap-2">
                  <Input
                    value={currentKeyword}
                    onChange={(e) => setCurrentKeyword(e.target.value)}
                    onKeyPress={handleKeywordKeyPress}
                    placeholder="例: Webマーケティング"
                    className="flex-1"
                  />
                  <Button
                    type="button"
                    onClick={addKeyword}
                    disabled={!currentKeyword.trim() || seoKeywords.includes(currentKeyword.trim())}
                    size="sm"
                    className="px-3"
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
                
                {/* 追加されたキーワード一覧 */}
                {seoKeywords.length > 0 && (
                  <div className="space-y-2">
                    <Label className="text-sm font-medium">追加されたキーワード ({seoKeywords.length}個)</Label>
                    <div className="flex flex-wrap gap-2">
                      {seoKeywords.map((keyword, index) => (
                        <Badge
                          key={index}
                          variant="secondary"
                          className="flex items-center gap-1 py-1 px-2"
                        >
                          {keyword}
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="h-4 w-4 p-0 hover:bg-destructive hover:text-destructive-foreground"
                            onClick={() => removeKeyword(index)}
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* ヘルプテキスト */}
                <div className="text-sm text-muted-foreground">
                  キーワードを入力してプラスボタンをクリックするか、Enterキーを押して追加してください
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Card2: テーマ数 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">生成テーマ数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="space-y-3">
                  <div className="text-center text-2xl font-bold text-primary">{themeCount}</div>
                  <Slider
                    value={[themeCount]}
                    onValueChange={(value) => setThemeCount(value[0])}
                    min={1}
                    max={10}
                    step={1}
                    className="w-full"
                  />
                  <div className="flex justify-between text-sm text-gray-500">
                    <span>1</span>
                    <span>5</span>
                    <span>10</span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Card3: ターゲット年代層 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">ターゲット年代層 *</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Select value={targetAgeGroup} onValueChange={setTargetAgeGroup} required>
                  <SelectTrigger>
                    <SelectValue placeholder="年代層を選択" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="10代">10代</SelectItem>
                    <SelectItem value="20代">20代</SelectItem>
                    <SelectItem value="30代">30代</SelectItem>
                    <SelectItem value="40代">40代</SelectItem>
                    <SelectItem value="50代">50代</SelectItem>
                    <SelectItem value="60代">60代</SelectItem>
                    <SelectItem value="70代以上">70代以上</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Card4: ペルソナ */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">ペルソナ設定</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Select value={personaType} onValueChange={setPersonaType}>
                  <SelectTrigger>
                    <SelectValue placeholder="ペルソナを選択" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="主婦">主婦</SelectItem>
                    <SelectItem value="学生">学生</SelectItem>
                    <SelectItem value="社会人">社会人</SelectItem>
                    <SelectItem value="自営業">自営業</SelectItem>
                    <SelectItem value="経営者・役員">経営者・役員</SelectItem>
                    <SelectItem value="退職者">退職者</SelectItem>
                    <SelectItem value="その他">その他</SelectItem>
                  </SelectContent>
                </Select>
                {personaType === 'その他' && (
                  <Textarea
                    value={customPersona}
                    onChange={(e) => setCustomPersona(e.target.value)}
                    placeholder="独自のペルソナを詳しく入力してください（例: 札幌近郊で自然素材を使った家づくりに関心がある、小さな子供を持つ30代夫婦）"
                    rows={3}
                  />
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 高度な設定 */}
        <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced}>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" className="w-full justify-between mb-4">
              <span>高度な設定</span>
              {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mb-6">
              {/* 目標文字数 */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">目標文字数</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="text-center text-xl font-bold text-primary">{targetLength.toLocaleString()}文字</div>
                    <Slider
                      value={[targetLength]}
                      onValueChange={(value) => setTargetLength(value[0])}
                      min={1000}
                      max={10000}
                      step={500}
                      className="w-full"
                    />
                    <div className="flex justify-between text-sm text-gray-500">
                      <span>1,000</span>
                      <span>5,000</span>
                      <span>10,000</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* リサーチクエリ数 */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">リサーチクエリ数</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="text-center text-2xl font-bold text-primary">{researchQueries}</div>
                    <Slider
                      value={[researchQueries]}
                      onValueChange={(value) => setResearchQueries(value[0])}
                      min={1}
                      max={10}
                      step={1}
                      className="w-full"
                    />
                    <div className="flex justify-between text-sm text-gray-500">
                      <span>1</span>
                      <span>5</span>
                      <span>10</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* 具体的なペルソナ生成数 */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">ペルソナ生成数</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="text-center text-2xl font-bold text-primary">{personaExamples}</div>
                    <Slider
                      value={[personaExamples]}
                      onValueChange={(value) => setPersonaExamples(value[0])}
                      min={1}
                      max={8}
                      step={1}
                      className="w-full"
                    />
                    <div className="flex justify-between text-sm text-gray-500">
                      <span>1</span>
                      <span>4</span>
                      <span>8</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* 企業情報 */}
              <Card className="md:col-span-2 lg:col-span-3">
                <CardHeader>
                  <CardTitle className="text-lg">企業情報</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <Label htmlFor="company-name">企業名</Label>
                      <Input
                        id="company-name"
                        value={companyName}
                        onChange={(e) => setCompanyName(e.target.value)}
                        placeholder="株式会社サンプル"
                      />
                    </div>
                    <div>
                      <Label htmlFor="company-description">企業概要</Label>
                      <Textarea
                        id="company-description"
                        value={companyDescription}
                        onChange={(e) => setCompanyDescription(e.target.value)}
                        placeholder="企業の事業内容や特徴を入力してください"
                        rows={2}
                      />
                    </div>
                    <div>
                      <Label htmlFor="company-style">文体・トンマナガイド</Label>
                      <Textarea
                        id="company-style"
                        value={companyStyleGuide}
                        onChange={(e) => setCompanyStyleGuide(e.target.value)}
                        placeholder="記事の文体やトーンについての指示"
                        rows={2}
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </CollapsibleContent>
        </Collapsible>
        {/* ボタン（最下部に配置） */}
        <div className="mt-auto flex justify-center">
          <Button
            onClick={handleStartGeneration}
            disabled={!isConnected || isGenerating || seoKeywords.length === 0 || !targetAgeGroup}
            className="w-full max-w-md"
            size="lg"
          >
            <IoSparkles className="mr-2 h-5 w-5" />
            {isGenerating ? '生成中...' : '記事生成を開始'}
          </Button>
        </div>
      </div>
    )
}