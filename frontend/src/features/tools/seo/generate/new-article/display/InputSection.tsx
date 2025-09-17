"use client";
import { useEffect,useState } from 'react';
import Link from 'next/link';
import { ChevronDown, ChevronUp, Image, ListTree, Palette,Plus, Settings, X } from "lucide-react";
import { IoRefresh, IoSparkles } from "react-icons/io5";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useDefaultCompany } from '@/hooks/useDefaultCompany';
import { useAuth } from '@clerk/nextjs';

interface InputSectionProps {
  onStartGeneration: (data: any) => void;
  isConnected: boolean;
  isGenerating: boolean;
}

export default function InputSection({ onStartGeneration, isConnected, isGenerating }: InputSectionProps) {
    const { getToken } = useAuth();
    const [seoKeywords, setSeoKeywords] = useState<string[]>([]);
    const [currentKeyword, setCurrentKeyword] = useState('');
    const [themeCount, setThemeCount] = useState(3);
    const [targetAgeGroup, setTargetAgeGroup] = useState('');
    const [personaType, setPersonaType] = useState('');
    const [customPersona, setCustomPersona] = useState('');
    const [targetLength, setTargetLength] = useState(3000);
    const [researchQueries, setResearchQueries] = useState(3);
    const [personaExamples, setPersonaExamples] = useState(3);
    const [showAdvanced, setShowAdvanced] = useState(false);
    
    // 画像モード関連の状態
    const [imageMode, setImageMode] = useState(false);
    const [imageSettings, setImageSettings] = useState({});

    // 高度アウトラインモード関連の状態
    const [advancedOutlineMode, setAdvancedOutlineMode] = useState(false);
    const [topLevelHeading, setTopLevelHeading] = useState<'h2' | 'h3'>('h2');
    
    // スタイルテンプレート関連の状態
    const [styleTemplates, setStyleTemplates] = useState([]);
    const [selectedStyleTemplate, setSelectedStyleTemplate] = useState('');
    
    // デフォルト会社情報を取得
    const { company, loading: companyLoading, hasCompany } = useDefaultCompany();

    // 会社のペルソナをデフォルト選択として設定
    useEffect(() => {
        if (company?.target_persona && !personaType) {
            setPersonaType('会社設定');
        }
    }, [company?.target_persona, personaType]);

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

        if (!targetAgeGroup) {
            alert('ターゲット年代層を選択してください');
            return;
        }

        // ペルソナ設定の処理
        let effectivePersonaType = personaType;
        let effectiveCustomPersona = customPersona;
        
        // 会社設定のペルソナが選択されている場合
        if (personaType === '会社設定' && company?.target_persona) {
            effectivePersonaType = 'その他'; // バックエンドでは「その他」として扱う
            effectiveCustomPersona = company.target_persona; // 会社のペルソナをカスタムペルソナとして使用
        }

        const requestData = {
            initial_keywords: seoKeywords,
            target_age_group: targetAgeGroup,
            num_theme_proposals: themeCount,
            num_research_queries: researchQueries,
            num_persona_examples: personaExamples,
            persona_type: effectivePersonaType || null,
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
                  キーワードを入力し、Enterを押す（＋ボタンを押す）と追加されます。キーワードを複数使用する際は、1キーワード入力ごとに追加してください。
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Card2: 画像モード */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Image className="h-5 w-5" />
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

          {/* Card3: 高度アウトラインモード */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <ListTree className="h-5 w-5" />
                高度アウトラインモード
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <Label className="text-sm font-medium">有効にする</Label>
                    <p className="text-sm text-muted-foreground">
                      大見出しと小見出しを同時に生成し、階層構造を維持したままセクションライティングを行います
                    </p>
                  </div>
                  <Switch
                    checked={advancedOutlineMode}
                    onCheckedChange={(value) => setAdvancedOutlineMode(value)}
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
                          <SelectItem value="h2">H2（標準的な構成）</SelectItem>
                          <SelectItem value="h3">H3（細かく分類された構成）</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1 text-xs text-blue-800">
                      <p>
                        H2 を大見出しにすると小見出しは H3 で生成されます。H3 を選ぶと小見出しは H4 となり、より細かな単位でライティングを行います。
                      </p>
                      <p>
                        生成後のアウトライン編集でも、この階層構造に沿って各見出しを調整できます。
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
          </Card>

          {/* Card4: スタイルテンプレート */}
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

          {/* Card4: テーマ数 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">生成する記事テーマ数</CardTitle>
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

          {/* Card5: ターゲット年代層 */}
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

          {/* Card6: ペルソナ */}
          <Card className="md:col-span-2">
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
                    {hasCompany && company?.target_persona && (
                      <SelectItem value="会社設定">
                        事前設定済みのペルソナ（推奨）
                      </SelectItem>
                    )}
                    <SelectItem value="主婦">主婦</SelectItem>
                    <SelectItem value="学生">学生</SelectItem>
                    <SelectItem value="社会人">社会人</SelectItem>
                    <SelectItem value="自営業">自営業</SelectItem>
                    <SelectItem value="経営者・役員">経営者・役員</SelectItem>
                    <SelectItem value="退職者">退職者</SelectItem>
                    <SelectItem value="その他">その他</SelectItem>
                  </SelectContent>
                </Select>
                {personaType === '会社設定' && hasCompany && company?.target_persona && (
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="text-sm font-medium text-blue-900 mb-2">会社設定のペルソナ:</div>
                    <div className="text-sm text-blue-800">{company.target_persona}</div>
                  </div>
                )}
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
