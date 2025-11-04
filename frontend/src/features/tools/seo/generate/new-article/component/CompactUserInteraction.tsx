'use client';

import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { 
  BookOpen, 
  Check, 
  ChevronRight,
  Clock,
  Edit3,
  Lightbulb, 
  RotateCcw,
  Save,
  Search, 
  Star,
  Target,
  Users, 
  X, 
  XCircle
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { normalizeOutlineSections } from '@/features/tools/seo/generate/utils/normalize-outline';
import { PersonaOption, ThemeOption } from '@/types/article-generation';
import { getOutlineApprovalMessage, getThemeSelectionMessage } from '@/utils/flow-config';

import type { EditableOutline, EditableOutlineSection } from '../../types/outline';

import MainSectionEditor from './MainSectionEditor';

interface CompactUserInteractionProps {
  type: 'select_persona' | 'select_theme' | 'approve_plan' | 'approve_outline';
  personas?: PersonaOption[];
  themes?: ThemeOption[];
  researchPlan?: any;
  outline?: any;
  onSelect?: (id: number) => void;
  onApprove?: (approved: boolean) => void;
  onRegenerate?: () => void;
  onEditAndProceed?: (editedContent: any) => void;
  isWaiting?: boolean;
  flowType?: 'outline_first' | 'research_first';
}

export default function CompactUserInteraction({
  type,
  personas,
  themes,
  researchPlan,
  outline,
  onSelect,
  onApprove,
  onRegenerate,
  onEditAndProceed,
  isWaiting = false,
  flowType = 'research_first'
}: CompactUserInteractionProps) {
  
  // Debug props
  console.log('🎭 CompactUserInteraction rendering with:', {
    type,
    hasPersonas: !!personas,
    personaCount: personas?.length,
    hasThemes: !!themes,
    themeCount: themes?.length,
    hasResearchPlan: !!researchPlan,
    hasOutline: !!outline,
    outlineType: typeof outline,
    outlineKeys: outline ? Object.keys(outline) : []
  });

  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [editMode, setEditMode] = useState<{
    type: 'persona' | 'theme' | 'plan' | 'outline' | null;
    index?: number;
  }>({ type: null });
  const [editContent, setEditContent] = useState<any>({});

  const handleSelect = (index: number) => {
    setSelectedIndex(index);
    setTimeout(() => {
      onSelect?.(index);
    }, 300);
  };

  const handleApprove = (approved: boolean) => {
    onApprove?.(approved);
  };

  const handleEdit = (type: 'persona' | 'theme' | 'plan' | 'outline', index?: number) => {
    setEditMode({ type, index });
    
    // Initialize edit content based on type
    if (type === 'persona' && personas) {
      if (index !== undefined) {
        // 特定のペルソナを編集
        setEditContent({ description: personas[index].description });
      } else {
        // 選択されたペルソナがある場合はそれを、なければ最初のペルソナを編集
        const targetIndex = selectedIndex !== null ? selectedIndex : 0;
        setEditContent({ description: personas[targetIndex]?.description || '' });
      }
    } else if (type === 'theme' && index !== undefined && themes) {
      setEditContent({
        title: themes[index].title,
        description: themes[index].description,
        keywords: themes[index].keywords.join(', ')
      });
    } else if (type === 'plan' && researchPlan) {
      setEditContent({
        topic: researchPlan.topic || '',
        queries: researchPlan.queries?.map((q: any) => ({
          query: typeof q === 'string' ? q : q.query || '',
          focus: typeof q === 'object' && q.focus ? q.focus : ''
        })) || []
      });
    } else if (type === 'outline' && outline) {
      const determineTopLevel = () => {
        if (typeof outline.top_level_heading === 'number') {
          return outline.top_level_heading >= 2 && outline.top_level_heading <= 6
            ? outline.top_level_heading
            : 2;
        }
        const levelsFromSections = Array.isArray(outline.sections)
          ? outline.sections
              .map((section: any) => (typeof section?.level === 'number' ? section.level : null))
              .filter((lvl: number | null): lvl is number => lvl !== null)
          : [];
        if (levelsFromSections.length === 0) return 2;
        const minimum = Math.min(...levelsFromSections);
        return minimum >= 2 && minimum <= 6 ? minimum : 2;
      };

      const topLevel = determineTopLevel();

      const normalizedSections = normalizeOutlineSections(outline.sections, topLevel);

      const toEditableSection = (section: typeof normalizedSections[number]): EditableOutlineSection => ({
        heading: section.heading,
        level: section.level,
        description: section.description ?? '',
        estimated_chars: section.estimated_chars,
        subsections: section.subsections.map(toEditableSection),
      });

      const editable: EditableOutline = {
        title: outline.title || '',
        suggested_tone: outline.suggested_tone || '',
        topLevel,
        sections: Array.isArray(normalizedSections)
          ? normalizedSections.map(toEditableSection)
          : [],
      };
      setEditContent(editable);
    }
  };

  const handleSaveEdit = () => {
    if (!editMode.type) return;
    
    let finalContent = { ...editContent };
    
    // Process keywords for theme
    if (editMode.type === 'theme' && editContent.keywords) {
      finalContent.keywords = editContent.keywords.split(',').map((k: string) => k.trim()).filter((k: string) => k.length > 0);
    }
    
    onEditAndProceed?.(finalContent);
    setEditMode({ type: null });
    setEditContent({});
  };

  const handleCancelEdit = () => {
    setEditMode({ type: null });
    setEditContent({});
  };

  const updateEditContent = (field: string, value: any) => {
    setEditContent((prev: any) => ({ ...prev, [field]: value }));
  };

  const updateQueryContent = (index: number, field: string, value: string) => {
    setEditContent((prev: any) => ({
      ...prev,
      queries: prev.queries?.map((q: any, i: number) => 
        i === index ? { ...q, [field]: value } : q
      ) || []
    }));
  };

  const updateSectionContent = (index: number, field: string, value: any) => {
    setEditContent((prev: any) => ({
      ...prev,
      sections: prev.sections?.map((s: any, i: number) => 
        i === index ? { ...s, [field]: value } : s
      ) || []
    }));
  };

  const renderOutlineTree = (items: any[], depth = 0): React.ReactElement[] | null => {
    if (!Array.isArray(items) || items.length === 0) return null;
    return items.map((item, index) => {
      const key = `outline-preview-${depth}-${index}`;
      const children = renderOutlineTree(item?.subsections || [], depth + 1);
      return (
        <div
          key={key}
          className={`space-y-1 ${depth > 0 ? 'border-l border-dashed border-gray-200 pl-3' : ''}`}
        >
          <div className="flex items-center gap-2">
            {typeof item?.level === 'number' && (
              <Badge variant="outline" className="bg-white text-blue-700">
                H{item.level}
              </Badge>
            )}
            <span className="text-sm font-medium">{item?.heading || ''}</span>
          </div>
          {item?.description && (
            <p className="ml-6 text-xs text-muted-foreground">{item.description}</p>
          )}
          {item?.estimated_chars && (
            <p className="ml-6 text-xs text-gray-400">約 {item.estimated_chars} 文字</p>
          )}
          {children && <div className="space-y-1">{children}</div>}
        </div>
      );
    });
  };

  // ペルソナ選択 - コンパクトなインライン表示
  if (type === 'select_persona' && personas && personas.length > 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full"
      >
        <Card className="border-2 border-primary/20 shadow-lg bg-gradient-to-br from-white to-primary/5">
          <CardContent className="p-4">
            <div className="flex items-center gap-3 mb-3">
              <motion.div 
                className="w-8 h-8 bg-gradient-to-r from-primary to-secondary rounded-full flex items-center justify-center"
                animate={{ rotate: [0, 10, -10, 0] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <Users className="w-4 h-4 text-white" />
              </motion.div>
              <div className="flex-1">
                <h3 className="text-lg font-bold">ターゲットペルソナを選択</h3>
                <p className="text-sm text-muted-foreground">
                  記事のターゲットとなるペルソナを1つ選択してください
                </p>
              </div>
              <Badge variant="secondary" className="text-xs">
                {personas.length}個の選択肢
              </Badge>
            </div>
            
            {editMode.type === 'persona' ? (
              <div className="space-y-4 mb-4">
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                  <h4 className="font-medium mb-3 flex items-center gap-2">
                    <Edit3 className="w-4 h-4" />
                    ペルソナを編集
                  </h4>
                  <Textarea
                    value={editContent.description || ''}
                    onChange={(e) => updateEditContent('description', e.target.value)}
                    placeholder="ターゲットペルソナの詳細な説明を入力してください..."
                    className="w-full min-h-[120px] resize-none"
                  />
                  <div className="flex justify-end gap-2 mt-3">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleCancelEdit}
                      className="flex items-center gap-1"
                    >
                      <XCircle className="w-4 h-4" />
                      キャンセル
                    </Button>
                    <Button
                      size="sm"
                      onClick={handleSaveEdit}
                      className="flex items-center gap-1"
                      disabled={!editContent.description?.trim()}
                    >
                      <Save className="w-4 h-4" />
                      この内容で進行
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
                {personas.map((persona, index) => (
                  <motion.div
                    key={persona.id}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: index * 0.1 }}
                    whileHover={{ scale: 1.02, y: -2 }}
                    whileTap={{ scale: 0.98 }}
                    className={`
                      relative p-3 pb-8 rounded-lg border-2 cursor-pointer transition-all duration-300 group
                      ${selectedIndex === index 
                        ? 'border-primary bg-primary/10 shadow-lg shadow-primary/20' 
                        : 'border-gray-200 hover:border-primary/40 hover:shadow-md'
                      }
                    `}
                    onClick={() => handleSelect(index)}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`
                        w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
                        ${selectedIndex === index ? 'bg-primary text-white' : 'bg-gray-100 text-gray-600'}
                      `}>
                        <Target className="w-4 h-4" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm text-foreground leading-relaxed">
                          {persona.description}
                        </p>
                      </div>
                    </div>
                    
                    {/* Edit button */}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute bottom-2 right-2 w-6 h-6 p-0 opacity-70 hover:opacity-100 hover:bg-primary/20 bg-white/90 border border-gray-200 shadow-sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEdit('persona', index);
                      }}
                      title="このペルソナを編集"
                    >
                      <Edit3 className="w-3 h-3" />
                    </Button>
                    
                    {selectedIndex === index && (
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="absolute -top-2 -right-2 w-6 h-6 bg-primary rounded-full flex items-center justify-center shadow-lg"
                      >
                        <Check className="w-4 h-4 text-white" />
                      </motion.div>
                    )}
                  </motion.div>
                ))}
              </div>
            )}
            
            {editMode.type !== 'persona' && (
              <div className="flex justify-between items-center">
                <Button
                  variant="outline"
                  onClick={onRegenerate}
                  className="flex items-center gap-2"
                  disabled={isWaiting}
                >
                  <RotateCcw className="w-4 h-4" />
                  新しいペルソナを生成
                </Button>
                
                <div className="text-sm text-muted-foreground">
                  選択後、自動で次のステップに進みます
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  // テーマ選択 - コンパクトなインライン表示
  if (type === 'select_theme' && themes && themes.length > 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full"
      >
        <Card className="border-2 border-secondary/20 shadow-lg bg-gradient-to-br from-white to-secondary/5">
          <CardContent className="p-4">
            <div className="flex items-center gap-3 mb-3">
              <motion.div 
                className="w-8 h-8 bg-gradient-to-r from-secondary to-accent rounded-full flex items-center justify-center"
                animate={{ rotate: [0, 15, -15, 0] }}
                transition={{ duration: 2.5, repeat: Infinity }}
              >
                <Lightbulb className="w-4 h-4 text-white" />
              </motion.div>
              <div className="flex-1">
                <h3 className="text-lg font-bold">記事テーマを選択</h3>
                <p className="text-sm text-muted-foreground">
                  執筆したい記事のテーマを1つ選択してください
                </p>
              </div>
              <Badge variant="secondary" className="text-xs">
                {themes.length}個のテーマ候補
              </Badge>
            </div>
            
            {editMode.type === 'theme' ? (
              <div className="space-y-4 mb-4">
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                  <h4 className="font-medium mb-3 flex items-center gap-2">
                    <Edit3 className="w-4 h-4" />
                    テーマを編集
                  </h4>
                  <div className="space-y-3">
                    <div>
                      <label className="text-sm font-medium block mb-1">タイトル</label>
                      <Input
                        value={editContent.title || ''}
                        onChange={(e) => updateEditContent('title', e.target.value)}
                        placeholder="記事のタイトルを入力..."
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium block mb-1">説明</label>
                      <Textarea
                        value={editContent.description || ''}
                        onChange={(e) => updateEditContent('description', e.target.value)}
                        placeholder="テーマの詳細な説明を入力..."
                        className="min-h-[80px] resize-none"
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium block mb-1">キーワード（カンマ区切り）</label>
                      <Input
                        value={editContent.keywords || ''}
                        onChange={(e) => updateEditContent('keywords', e.target.value)}
                        placeholder="キーワード1, キーワード2, キーワード3..."
                      />
                    </div>
                  </div>
                  <div className="flex justify-end gap-2 mt-3">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleCancelEdit}
                      className="flex items-center gap-1"
                    >
                      <XCircle className="w-4 h-4" />
                      キャンセル
                    </Button>
                    <Button
                      size="sm"
                      onClick={handleSaveEdit}
                      className="flex items-center gap-1"
                      disabled={!editContent.title?.trim() || !editContent.description?.trim()}
                    >
                      <Save className="w-4 h-4" />
                      この内容で進行
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-3 mb-4">
                {themes.map((theme, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                    className={`
                      relative p-4 pb-8 rounded-xl border-2 cursor-pointer transition-all duration-300 group
                      ${selectedIndex === index 
                        ? 'border-secondary bg-secondary/5 shadow-lg ring-4 ring-secondary/20' 
                        : 'border-gray-200 hover:border-secondary/40 hover:shadow-md'
                      }
                    `}
                    onClick={() => handleSelect(index)}
                  >
                    <div className="flex items-start gap-4">
                      <div className={`
                        w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0
                        ${selectedIndex === index ? 'bg-secondary text-white' : 'bg-gray-100 text-gray-600'}
                      `}>
                        <Star className="w-5 h-5" />
                      </div>
                      <div className="flex-1">
                        <h4 className="font-semibold text-lg mb-2 text-foreground">
                          {theme.title}
                        </h4>
                        <p className="text-sm text-muted-foreground mb-3 leading-relaxed">
                          {theme.description}
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {theme.keywords.map((keyword: string, kIndex: number) => (
                            <Badge key={kIndex} variant="outline" className="text-xs">
                              {keyword}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    </div>
                    
                    {/* Edit button */}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="absolute bottom-2 right-2 w-6 h-6 p-0 opacity-70 hover:opacity-100 hover:bg-secondary/20 bg-white/90 border border-gray-200 shadow-sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEdit('theme', index);
                      }}
                      title="このテーマを編集"
                    >
                      <Edit3 className="w-3 h-3" />
                    </Button>
                    
                    {selectedIndex === index && (
                      <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="absolute -top-2 -right-2 w-6 h-6 bg-secondary rounded-full flex items-center justify-center"
                      >
                        <Check className="w-4 h-4 text-white" />
                      </motion.div>
                    )}
                  </motion.div>
                ))}
              </div>
            )}
            
            {editMode.type !== 'theme' && (
              <div className="flex justify-between items-center">
                <Button
                  variant="outline"
                  onClick={onRegenerate}
                  className="flex items-center gap-2"
                  disabled={isWaiting}
                >
                  <RotateCcw className="w-4 h-4" />
                  新しいテーマを生成
                </Button>
                
                <div className="text-sm text-muted-foreground">
                  {getThemeSelectionMessage(flowType)}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  // リサーチ計画承認 - インライン表示
  if (type === 'approve_plan' && researchPlan) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full"
      >
        <Card className="border-2 border-accent/20 shadow-lg bg-gradient-to-br from-white to-accent/5">
          <CardContent className="p-4">
            <div className="flex items-center gap-3 mb-4">
              <motion.div 
                className="w-8 h-8 bg-gradient-to-r from-accent to-primary rounded-full flex items-center justify-center"
                animate={{ scale: [1, 1.1, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <Search className="w-4 h-4 text-white" />
              </motion.div>
              <div className="flex-1">
                <h3 className="text-lg font-bold">リサーチ計画の確認</h3>
                <p className="text-sm text-muted-foreground">
                  記事執筆のためのリサーチ計画をご確認ください
                </p>
              </div>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4 mb-4">
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="text-center">
                  <div className="text-2xl font-bold text-accent">{researchPlan.queries?.length || 0}</div>
                  <div className="text-muted-foreground">リサーチクエリ数</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-accent">2-3分</div>
                  <div className="text-muted-foreground">推定実行時間</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-accent">{researchPlan.keywords?.length || 0}</div>
                  <div className="text-muted-foreground">対象キーワード</div>
                </div>
              </div>
            </div>

            {editMode.type === 'plan' ? (
              <div className="space-y-4 mb-6">
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                  <h4 className="font-medium mb-3 flex items-center gap-2">
                    <Edit3 className="w-4 h-4" />
                    リサーチ計画を編集
                  </h4>
                  <div className="space-y-3">
                    <div>
                      <label className="text-sm font-medium block mb-1">リサーチトピック</label>
                      <Input
                        value={editContent.topic || ''}
                        onChange={(e) => updateEditContent('topic', e.target.value)}
                        placeholder="リサーチのメイントピックを入力..."
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium block mb-2">リサーチクエリ</label>
                      <div className="space-y-2">
                        {editContent.queries?.map((query: any, index: number) => (
                          <div key={index} className="grid grid-cols-2 gap-2">
                            <Input
                              value={query.query || ''}
                              onChange={(e) => updateQueryContent(index, 'query', e.target.value)}
                              placeholder={`クエリ ${index + 1}`}
                            />
                            <Input
                              value={query.focus || ''}
                              onChange={(e) => updateQueryContent(index, 'focus', e.target.value)}
                              placeholder="調査の焦点"
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="flex justify-end gap-2 mt-3">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleCancelEdit}
                      className="flex items-center gap-1"
                    >
                      <XCircle className="w-4 h-4" />
                      キャンセル
                    </Button>
                    <Button
                      size="sm"
                      onClick={handleSaveEdit}
                      className="flex items-center gap-1"
                      disabled={!editContent.topic?.trim()}
                    >
                      <Save className="w-4 h-4" />
                      この内容で進行
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              researchPlan.queries && (
                <div className="space-y-3 mb-6 relative group">
                  <div className="flex items-center justify-between">
                    <h4 className="font-semibold flex items-center gap-2">
                      <Search className="w-4 h-4" />
                      実行予定のリサーチクエリ
                    </h4>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => handleEdit('plan')}
                    >
                      <Edit3 className="w-4 h-4" />
                      編集
                    </Button>
                  </div>
                  {researchPlan.queries.map((queryItem: any, index: number) => {
                    const queryText = typeof queryItem === 'string' ? queryItem : queryItem.query || queryItem;
                    const queryFocus = typeof queryItem === 'object' && queryItem.focus ? queryItem.focus : null;
                    
                    return (
                      <div key={index} className="flex items-start gap-3 p-3 bg-white border border-gray-200 rounded-lg">
                        <Badge variant="outline" className="mt-1">{index + 1}</Badge>
                        <div className="flex-1">
                          <span className="text-sm font-medium">{queryText}</span>
                          {queryFocus && (
                            <p className="text-xs text-muted-foreground mt-1">
                              <strong>焦点:</strong> {queryFocus}
                            </p>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )
            )}

            {editMode.type !== 'plan' && (
              <div className="flex justify-center gap-4">
                <Button
                  variant="outline"
                  onClick={() => handleApprove(false)}
                  className="flex items-center gap-2"
                  disabled={isWaiting}
                >
                  <X className="w-4 h-4" />
                  修正が必要
                </Button>
                
                <Button
                  onClick={() => handleApprove(true)}
                  className="flex items-center gap-2"
                  disabled={isWaiting}
                >
                  <Check className="w-4 h-4" />
                  この計画で開始
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  // アウトライン承認 - インライン表示
  console.log('📝 Checking outline approval condition:', {
    type,
    isApproveOutline: type === 'approve_outline',
    hasOutline: !!outline,
    outlineContent: outline
  });
  
  if (type === 'approve_outline' && outline) {
    console.log('📝 Rendering outline approval UI');
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full"
      >
        <Card className="border-2 border-primary/20 shadow-lg bg-gradient-to-br from-white to-primary/5">
          <CardContent className="p-4">
            <div className="flex items-center gap-3 mb-4">
              <motion.div 
                className="w-8 h-8 bg-gradient-to-r from-primary to-secondary rounded-full flex items-center justify-center"
                animate={{ rotateY: [0, 180, 360] }}
                transition={{ duration: 3, repeat: Infinity }}
              >
                <BookOpen className="w-4 h-4 text-white" />
              </motion.div>
              <div className="flex-1">
                <h3 className="text-lg font-bold">記事構成の確認</h3>
                <p className="text-sm text-muted-foreground">
                  生成された記事のアウトラインをご確認ください
                </p>
              </div>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-4 mb-6">
              <h4 className="font-semibold text-lg mb-2">{outline.title}</h4>
              <p className="text-sm text-muted-foreground mb-4">{outline.description}</p>
              
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm">
                  <Clock className="w-4 h-4 text-primary" />
                  <span><strong>推定読了時間:</strong> {outline.estimated_reading_time || '5-8分'}</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <BookOpen className="w-4 h-4 text-primary" />
                  <span><strong>セクション数:</strong> {outline.sections?.length || 0}個</span>
                </div>
              </div>
            </div>

            {editMode.type === 'outline' ? (
              <div className="space-y-4 mb-6">
                <MainSectionEditor
                  value={editContent as EditableOutline}
                  onChange={(v) => setEditContent(v)}
                  onCancel={handleCancelEdit}
                  onSaveAndStart={(edited) => {
                    // Pass through to higher-level handler (wrapped with edit_and_proceed in caller)
                    onEditAndProceed?.(edited);
                    setEditMode({ type: null });
                    setEditContent({});
                  }}
                />
              </div>
            ) : (
              outline.sections && (
                <div className="space-y-3 mb-6 relative group">
                  <div className="flex items-center justify-between">
                    <h4 className="font-semibold">記事構成</h4>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                      type="button"
                      onClick={() => handleEdit('outline')}
                    >
                      <Edit3 className="w-4 h-4" />
                      編集
                    </Button>
                  </div>
                  {renderOutlineTree(outline.sections)}
                </div>
              )
            )}

            {editMode.type !== 'outline' && (
              <div className="flex justify-center gap-4">
                <Button
                  variant="outline"
                  onClick={() => handleApprove(false)}
                  className="flex items-center gap-2"
                  disabled={isWaiting}
                >
                  <X className="w-4 h-4" />
                  修正が必要
                </Button>
                
                <Button
                  onClick={() => handleApprove(true)}
                  className="flex items-center gap-2"
                  disabled={isWaiting}
                >
                  <Check className="w-4 h-4" />
                  {getOutlineApprovalMessage(flowType)}
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  console.log('🚫 CompactUserInteraction: No matching condition found, returning null', {
    type,
    hasPersonas: !!personas,
    hasThemes: !!themes,
    hasResearchPlan: !!researchPlan,
    hasOutline: !!outline
  });
  
  return null;
} 
