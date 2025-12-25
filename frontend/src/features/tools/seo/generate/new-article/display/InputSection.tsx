"use client";

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Bot, ChevronDown, ChevronUp, ImageIcon, ListTree, Palette, Plus, Settings, X, Zap } from 'lucide-react';
import { IoRefresh, IoSparkles } from 'react-icons/io5';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { useDefaultCompany } from '@/hooks/useDefaultCompany';
import { cn } from '@/utils/cn';
import { FLOW_METADATA, FlowType } from '@/utils/flow-config';
import { useAuth } from '@clerk/nextjs';

interface InputSectionProps {
  onStartGeneration: (data: any) => void;
  isConnected: boolean;
  isGenerating: boolean;
}

const AGE_OPTIONS = ["10代", "20代", "30代", "40代", "50代", "60代", "70代以上"] as const;
const PERSONA_OPTIONS = ["主婦", "学生", "社会人", "自営業", "経営者・役員", "退職者", "その他"] as const;

export default function InputSection({ onStartGeneration, isConnected, isGenerating }: InputSectionProps) {
    const { getToken } = useAuth();
    const [seoKeywords, setSeoKeywords] = useState<string[]>([]);
    const [currentKeyword, setCurrentKeyword] = useState('');
    const [themeCount, setThemeCount] = useState(3);
    const [targetAgeGroups, setTargetAgeGroups] = useState<string[]>([]);
    const [selectedPersonaTypes, setSelectedPersonaTypes] = useState<string[]>([]);
    const [customPersona, setCustomPersona] = useState('');
    const [targetLength, setTargetLength] = useState(3000);
    const [researchQueries, setResearchQueries] = useState(3);
    const [personaExamples, setPersonaExamples] = useState(3);
    const [showAdvanced, setShowAdvanced] = useState(false);
    
    // 画像モード関連の状態
    const [imageMode, setImageMode] = useState(true);
    const [imageSettings, setImageSettings] = useState({});

    // 高度アウトラインモード関連の状態
    const [advancedOutlineMode, setAdvancedOutlineMode] = useState(false);
    const [topLevelHeading, setTopLevelHeading] = useState<'h2' | 'h3'>('h2');
    const [enableFinalEditing, setEnableFinalEditing] = useState(false);
    const [autoMode, setAutoMode] = useState(true);
    const [autoSelectionStrategy, setAutoSelectionStrategy] = useState<'first' | 'best_match'>('best_match');
    
    // スタイルテンプレート関連の状態
    const [styleTemplates, setStyleTemplates] = useState([]);
    const [selectedStyleTemplate, setSelectedStyleTemplate] = useState('');
    
    // フロー設定関連の状態
    const [selectedFlowType, setSelectedFlowType] = useState<FlowType>('outline_first');
    
    // デフォルト会社情報を取得
    const { company, loading: companyLoading, hasCompany } = useDefaultCompany();

    // 会社のペルソナをデフォルト選択として設定
    useEffect(() => {
        if (company?.target_persona && selectedPersonaTypes.length === 0) {
            setSelectedPersonaTypes(['会社設定']);
        }
    }, [company?.target_persona, selectedPersonaTypes.length]);

    useEffect(() => {
        if (!company?.target_persona) {
            setSelectedPersonaTypes((prev) => prev.filter((type) => type !== '会社設定'));
        }
    }, [company?.target_persona]);


    // スタイルテンプレートを取得
    useEffect(() => {
        const fetchStyleTemplates = async () => {
            try {
                const token = await getToken();
                const headers: Record<string, string> = {
                    'Content-Type': 'application/json',
                };
                
                if (token) {
                    headers.Authorization = `Bearer ${token}`;
                }
                
                const response = await fetch('/api/proxy/style-templates', {
                    headers,
                });
                if (response.ok) {
                    const templates = await response.json();
                    setStyleTemplates(templates);
                    // デフォルトテンプレートがあれば自動選択
                    const defaultTemplate = templates.find((t: any) => t.is_default);
                    if (defaultTemplate) {
                        setSelectedStyleTemplate(defaultTemplate.id);
                    }
                }
            } catch (error) {
                console.error('スタイルテンプレートの取得に失敗しました:', error);
            }
        };
        
        fetchStyleTemplates();
    }, [getToken]);

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

        // ペルソナ設定の処理
        const companyPersonaSelected =
          selectedPersonaTypes.includes('会社設定') && company?.target_persona ? company.target_persona : null;
        const primaryPersonaCandidates = selectedPersonaTypes.filter(
          (type) => type !== '会社設定' && type !== 'その他'
        );
        const includesOtherPersona = selectedPersonaTypes.includes('その他');

        let effectivePersonaType: string | null = primaryPersonaCandidates[0] || null;
        let effectiveCustomPersona = customPersona.trim() ? customPersona.trim() : null;

        if (companyPersonaSelected) {
            effectiveCustomPersona = [companyPersonaSelected, effectiveCustomPersona]
              .filter(Boolean)
              .join('\n\n') || companyPersonaSelected;
        }

        if (!effectivePersonaType && (includesOtherPersona || companyPersonaSelected)) {
            effectivePersonaType = 'その他';
        }

        const requestData = {
            initial_keywords: seoKeywords,
            target_age_group: targetAgeGroups[0] ?? null,
            target_age_groups: targetAgeGroups,
            num_theme_proposals: themeCount,
            num_research_queries: researchQueries,
            num_persona_examples: personaExamples,
            persona_type: effectivePersonaType || null,
            persona_types: selectedPersonaTypes,
            custom_persona: effectiveCustomPersona || null,
            target_length: targetLength,
            // 会社情報をデフォルト会社から自動設定
            company_name: company?.name || null,
            company_description: company?.description || null,
            company_usp: company?.usp || null,
            company_website_url: company?.website_url || null,
            company_target_persona: company?.target_persona || null,
            company_brand_slogan: company?.brand_slogan || null,
            company_target_keywords: company?.target_keywords || null,
            company_industry_terms: company?.industry_terms || null,
            company_avoid_terms: company?.avoid_terms || null,
            company_popular_articles: company?.popular_articles || null,
            company_target_area: company?.target_area || null,
            // 画像モード設定を追加
            image_mode: imageMode,
            image_settings: imageSettings,
            // スタイルテンプレート設定を追加
            style_template_id: (selectedStyleTemplate && selectedStyleTemplate !== 'default') ? selectedStyleTemplate : null,
            // 高度アウトライン設定を追加
            advanced_outline_mode: advancedOutlineMode,
            outline_top_level_heading: advancedOutlineMode ? (topLevelHeading === 'h3' ? 3 : 2) : 2,
            // フロー設定を追加
            flow_type: selectedFlowType,
            // 最終編集ステップ実行可否
            enable_final_editing: enableFinalEditing,
            // オートモード
            auto_mode: autoMode,
            auto_selection_strategy: autoSelectionStrategy,
        };

        console.log('📦 Request data being sent:', requestData);
        console.log('🖼️ Image mode in request data:', imageMode);
        onStartGeneration(requestData);
    };

    const themeCountOptions = [1, 3, 5, 8, 10];
    
    return (
      <div className="w-full flex flex-col min-h-0 max-h-full overflow-hidden">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6">
          {/* Card1: SEOワード */}
          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle className="text-lg">記事を上位表示したい検索ワード *</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* キーワード入力欄 */}
                <div className="flex gap-2">
                  <Input
                    value={currentKeyword}
                    onChange={(e) => setCurrentKeyword(e.target.value)}
                    onKeyPress={handleKeywordKeyPress}
                    placeholder="例: リフォーム"
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
                「大阪 リフォーム」のような検索ワードで上位表示をしたい場合は、「大阪」を一度＋ボタンで追加してから、次に「リフォーム」を入力してください
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Card3: オートモード（位置を入れ替え） */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Bot className="h-5 w-5" />
                オートモード
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                ペルソナ/記事タイトル/アウトラインの承認を自動で進めます。フローはそのまま、確認なしで完走させたいときに。
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-sm">オートモードを有効にする</p>
                  <p className="text-xs text-muted-foreground">ユーザー入力ステップをスキップし自動選択します。</p>
                </div>
                <Switch
                  checked={autoMode}
                  onCheckedChange={setAutoMode}
                  aria-label="オートモードを有効にする"
                />
              </div>

              {/* <div className="space-y-2">
                <Label className="text-sm">自動選択の戦略</Label>
                <Select
                  value={autoSelectionStrategy}
                  onValueChange={(value) => setAutoSelectionStrategy(value as 'first' | 'best_match')}
                  disabled={!autoMode}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="戦略を選択" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="best_match">コンテキストに最適（推奨）</SelectItem>
                    <SelectItem value="first">先頭を常に選ぶ</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  best_match: キーワード・会社情報・SERP傾向に最も合う候補を選択 / first: 生成順で固定
                </p>
              </div> */}
            </CardContent>
          </Card>

        </div>

        {/* 会社情報ステータス */}
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <Settings className="h-5 w-5 text-gray-500" />
                <div>
                  <h3 className="font-medium">会社情報・マーケティング戦略設定</h3>
                  {companyLoading ? (
                    <p className="text-sm text-gray-500">読み込み中...</p>
                  ) : hasCompany ? (
                    <p className="text-sm text-gray-500">
                      {company?.name} の情報を使用します
                    </p>
                  ) : (
                    <p className="text-sm text-yellow-600">
                      会社情報が未設定です。設定することでより適切な記事が生成されます。
                    </p>
                  )}
                </div>
              </div>
              <Link href="/company-settings/company">
                <Button variant="outline" size="sm">
                  {hasCompany ? '編集' : '設定'}
                </Button>
              </Link>
            </div>
            {hasCompany && company && (
              <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div><span className="font-medium">企業名:</span> {company.name}</div>
                  <div><span className="font-medium">ターゲット:</span> {company.target_persona}</div>
                  <div className="col-span-2"><span className="font-medium">概要:</span> {company.description.substring(0, 100)}{company.description.length > 100 ? '...' : ''}</div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 高度な設定 */}
        <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced}>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" className="w-full justify-between mb-4">
              <span>高度な設定</span>
              {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </Button>
          </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-5 mb-6">
            {/* 画像モード */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <ImageIcon className="h-5 w-5" aria-hidden="true" />
                  画像生成・挿入機能
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label className="text-sm font-medium">有効にする</Label>
                      <p className="text-sm text-muted-foreground">
                        記事に画像プレースホルダーを挿入し、後から画像生成や画像アップロードができます
                      </p>
                    </div>
                    <Switch
                      checked={imageMode}
                      onCheckedChange={(value) => {
                        console.log('🖼️ Image mode toggle changed:', value);
                        setImageMode(value);
                      }}
                    />
                  </div>

                  {imageMode && (
                    <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="flex items-start gap-3">
                        <IoSparkles className="h-5 w-5 text-blue-600 mt-0.5" />
                        <div className="space-y-2">
                          <h4 className="text-sm font-medium text-blue-900">画像モードが有効です</h4>
                          <p className="text-sm text-blue-800">
                            AIが記事の適切な箇所に画像プレースホルダーを配置します。生成後の編集画面で：
                          </p>
                          <ul className="text-sm text-blue-800 list-disc list-inside ml-2 space-y-1">
                            <li>Imagen 4.0で自動画像生成</li>
                            <li>手動での画像アップロード</li>
                          </ul>
                          <p className="text-sm text-blue-800">
                            などが可能です。
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* 記事スタイル設定 */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Palette className="h-5 w-5" />
                  記事スタイル設定
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <Select value={selectedStyleTemplate} onValueChange={setSelectedStyleTemplate}>
                    <SelectTrigger>
                      <SelectValue placeholder="スタイルテンプレートを選択" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="default">デフォルトスタイル</SelectItem>
                      {styleTemplates.map((template: any) => (
                        <SelectItem key={template.id} value={template.id}>
                          {template.name}
                          {template.is_default && " (デフォルト)"}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  {selectedStyleTemplate && selectedStyleTemplate !== 'default' && (
                    <div className="p-3 bg-purple-50 border border-purple-200 rounded-lg">
                      {(() => {
                        const template: any = styleTemplates.find((t: any) => t.id === selectedStyleTemplate);
                        return template ? (
                          <div className="space-y-2">
                            <div className="text-sm font-medium text-purple-900">{template.name}</div>
                            {template.description && (
                              <div className="text-sm text-purple-800">{template.description}</div>
                            )}
                            <div className="text-xs text-purple-700 space-y-1">
                              {template.settings?.tone && <div>トーン: {template.settings.tone}</div>}
                              {template.settings?.style && <div>文体: {template.settings.style}</div>}
                              {template.settings?.approach && <div>アプローチ: {template.settings.approach}</div>}
                            </div>
                          </div>
                        ) : null;
                      })()}
                    </div>
                  )}

                  {(!selectedStyleTemplate || selectedStyleTemplate === 'default') && (
                    <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
                      <div className="text-sm text-gray-800">
                        デフォルトスタイル: 親しみやすく分かりやすい文章で、読者に寄り添うトーン
                      </div>
                    </div>
                  )}

                  <div className="text-xs text-gray-500">
                    <Link href="/company-settings/style-guide" className="text-blue-600 hover:text-blue-800 underline">
                      記事スタイルのテンプレートを管理
                    </Link>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 記事タイトル候補数 */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">記事タイトル候補数</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  ※オートモードの場合、タイトル候補は1つのみ作られます
                </p>
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

            {/* ターゲット年代層 */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">ターゲット年代層（任意）</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground">複数年代をまとめて指定できます。未選択の場合は年代指定なしで生成します。</p>
                  {targetAgeGroups.length > 0 && (
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">選択中 ({targetAgeGroups.length}件)</Label>
                      <div className="flex flex-wrap gap-2">
                        {targetAgeGroups.map((age) => (
                          <span
                            key={age}
                            className="flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-medium text-primary"
                          >
                            {age}
                            <button
                              type="button"
                              aria-label={`${age} を削除`}
                              className="rounded-full p-1 text-primary transition hover:bg-primary/20"
                              onClick={() =>
                                setTargetAgeGroups((prev) => prev.filter((item) => item !== age))
                              }
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-3">
                    {AGE_OPTIONS.map((age) => {
                      const selected = targetAgeGroups.includes(age);
                      return (
                        <label
                          key={age}
                          className={cn(
                            "flex items-center space-x-2 rounded-lg border p-2 text-sm cursor-pointer transition",
                            selected
                              ? "border-primary bg-primary/10 text-primary shadow-sm"
                              : "border-border hover:bg-muted"
                          )}
                        >
                          <Checkbox
                            checked={selected}
                            onCheckedChange={() =>
                              setTargetAgeGroups((prev) =>
                                prev.includes(age) ? prev.filter((item) => item !== age) : [...prev, age]
                              )
                            }
                          />
                          <span>{age}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* ペルソナ設定 */}
            <Card className="md:col-span-2">
              <CardHeader>
                <CardTitle className="text-lg">ペルソナ設定</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <p className="text-sm text-muted-foreground">複数の想定読者像を組み合わせて指定できます。</p>
                  {selectedPersonaTypes.length > 0 && (
                    <div className="space-y-2">
                      <Label className="text-sm font-medium">選択中 ({selectedPersonaTypes.length}件)</Label>
                      <div className="flex flex-wrap gap-2">
                        {selectedPersonaTypes.map((persona) => {
                          const chipLabel =
                            persona === '会社設定' && company?.target_persona
                              ? `会社設定: ${company.target_persona}`
                              : persona === 'その他' && customPersona.trim()
                                ? `その他: ${customPersona.trim()}`
                                : persona;
                          return (
                            <span
                              key={persona}
                              className="flex items-center gap-1 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs font-medium text-primary"
                              title={chipLabel}
                            >
                              {chipLabel}
                              <button
                                type="button"
                                aria-label={`${persona} を削除`}
                                className="rounded-full p-1 text-primary transition hover:bg-primary/20"
                                onClick={() =>
                                  setSelectedPersonaTypes((prev) => prev.filter((item) => item !== persona))
                                }
                              >
                                <X className="h-3 w-3" />
                              </button>
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}
                  <div className="grid grid-cols-2 gap-3">
                    {(hasCompany && company?.target_persona ? ['会社設定'] : []).concat(PERSONA_OPTIONS).map((persona) => {
                      const selected = selectedPersonaTypes.includes(persona);
                      const isCompanyOption = persona === '会社設定';
                      const isDisabled = isCompanyOption && !company?.target_persona;
                      return (
                        <label
                          key={persona}
                          className={cn(
                            "flex items-start space-x-2 rounded-lg border p-3 text-sm cursor-pointer transition",
                            selected
                              ? "border-primary bg-primary/10 text-primary shadow-sm"
                              : "border-border hover:bg-muted",
                            isDisabled && "cursor-not-allowed opacity-50"
                          )}
                        >
                          <Checkbox
                            checked={selected}
                            disabled={isDisabled}
                            onCheckedChange={() => {
                              if (isDisabled) return;
                              setSelectedPersonaTypes((prev) =>
                                prev.includes(persona)
                                  ? prev.filter((item) => item !== persona)
                                  : [...prev, persona]
                              );
                            }}
                          />
                          <div className="space-y-1">
                            <span className="font-medium">
                              {isCompanyOption ? '事前設定済みのペルソナ（推奨）' : persona}
                            </span>
                            {isCompanyOption && company?.target_persona && (
                              <p className="text-xs text-muted-foreground line-clamp-2">
                                {company.target_persona}
                              </p>
                            )}
                          </div>
                        </label>
                      );
                    })}
                  </div>
                  {selectedPersonaTypes.includes('会社設定') && hasCompany && company?.target_persona && (
                    <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
                      <div className="text-sm font-medium text-gray-900 mb-2">会社設定のペルソナ:</div>
                      <div className="text-sm text-gray-800">{company.target_persona}</div>
                    </div>
                  )}
                  {selectedPersonaTypes.includes('その他') && (
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

            {/* 目標文字数 */}
            {/* <Card>
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
            </Card> */}

            {/* 最終編集ステップ */}
            {/* <Card>
              <CardHeader>
                <CardTitle className="text-lg">最終編集ステップ</CardTitle>
                <p className="text-sm text-muted-foreground">ONにすると記事生成後に編集エージェントで仕上げます。OFFならセクション執筆で完了し高速化します。</p>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm">最終編集を実行する</p>
                    <p className="text-xs text-muted-foreground">従来挙動: ON / 高速完了: OFF</p>
                  </div>
                  <Switch
                    checked={enableFinalEditing}
                    onCheckedChange={setEnableFinalEditing}
                    aria-label="最終編集を実行する"
                  />
                </div>
              </CardContent>
            </Card> */}

            {/* リサーチクエリ数 */}
            {/* <Card>
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
            </Card> */}

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

            {/* 高度アウトラインモード */}
            {/* <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <ListTree className="h-5 w-5" />
                  高度アウトラインモード
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  大見出しと小見出しを同時に生成し、階層構造を維持したままセクションライティングを行います。
                </p>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label className="text-sm font-medium">有効にする</Label>
                      <p className="text-sm text-muted-foreground">
                        階層化されたアウトラインを自動生成し、その構造を保持したまま執筆します。
                      </p>
                    </div>
                    <Switch
                      checked={advancedOutlineMode}
                      onCheckedChange={(value) => setAdvancedOutlineMode(value)}
                      aria-label="高度アウトラインモードを有効にする"
                    />
                  </div>

                  {advancedOutlineMode && (
                    <div className="space-y-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
                      <div className="space-y-2">
                        <Label className="text-sm font-medium">大見出しのレベルを選択</Label>
                        <Select
                          value={topLevelHeading}
                          onValueChange={(value) => setTopLevelHeading(value as 'h2' | 'h3')}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="トップレベル見出しを選択" />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="h2">H2</SelectItem>
                            <SelectItem value="h3">H3</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1 text-xs text-blue-800">
                        <p>
                          大見出しをH2にするかH3にするかを選択できます。生成後のアウトライン編集でも、この階層構造に沿って各見出しを調整できます。
                        </p>
                      </div>
                    </div>
                  )}

                  {!advancedOutlineMode && (
                    <p className="text-xs text-muted-foreground">
                      標準モードでは H2 を大見出しとした構成案が生成されます。必要に応じてアウトライン編集で小見出しを追加できます。
                    </p>
                  )}
                </div>
              </CardContent>
            </Card> */}

            {/* 記事生成フロー設定 */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  記事生成フロー
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Select value={selectedFlowType} onValueChange={(value) => setSelectedFlowType(value as FlowType)}>
                  <SelectTrigger>
                    <SelectValue placeholder="生成フローを選択" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(FLOW_METADATA).map(([key, meta]) => (
                      <SelectItem key={key} value={key}>
                        {meta.displayName}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>

                {selectedFlowType && (
                  <div className="rounded-md border border-blue-200 bg-blue-50 p-3 text-sm leading-relaxed text-blue-900">
                    <div className="font-medium">{FLOW_METADATA[selectedFlowType].displayName}</div>
                    <div className="text-blue-800">{FLOW_METADATA[selectedFlowType].description}</div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </CollapsibleContent>
        </Collapsible>
        {/* ボタン（最下部に配置） */}
        <div className="mt-auto flex justify-center">
          <Button
            onClick={handleStartGeneration}
            disabled={!isConnected || isGenerating || seoKeywords.length === 0}
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
