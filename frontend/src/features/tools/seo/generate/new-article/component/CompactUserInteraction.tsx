'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Users, 
  Lightbulb, 
  Search, 
  BookOpen, 
  Check, 
  X, 
  RotateCcw,
  ChevronRight,
  Star,
  Target,
  Clock,
  Edit3,
  Save,
  XCircle
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { PersonaOption, ThemeOption } from '../hooks/useArticleGeneration';

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
  isWaiting = false
}: CompactUserInteractionProps) {

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
    if (type === 'persona' && index !== undefined && personas) {
      setEditContent({ description: personas[index].description });
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
      setEditContent({
        title: outline.title || '',
        suggested_tone: outline.suggested_tone || '',
        sections: outline.sections?.map((s: any) => ({
          heading: s.heading || '',
          estimated_chars: s.estimated_chars || 0
        })) || []
      });
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

  // ペルソナ選択 - コンパクトなインライン表示
  if (type === 'select_persona' && personas) {
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
                      relative p-3 rounded-lg border-2 cursor-pointer transition-all duration-300
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
                      className="absolute top-2 right-2 w-6 h-6 p-0 opacity-0 group-hover:opacity-100 hover:bg-primary/10"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEdit('persona', index);
                      }}
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
  if (type === 'select_theme' && themes) {
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
                      relative p-4 rounded-xl border-2 cursor-pointer transition-all duration-300 group
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
                          {theme.keywords.map((keyword, kIndex) => (
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
                      className="absolute top-2 right-2 w-6 h-6 p-0 opacity-0 group-hover:opacity-100 hover:bg-secondary/10"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleEdit('theme', index);
                      }}
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
                  選択後、自動でリサーチを開始します
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
  if (type === 'approve_outline' && outline) {
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
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                  <h4 className="font-medium mb-3 flex items-center gap-2">
                    <Edit3 className="w-4 h-4" />
                    アウトラインを編集
                  </h4>
                  <div className="space-y-3">
                    <div>
                      <label className="text-sm font-medium block mb-1">記事タイトル</label>
                      <Input
                        value={editContent.title || ''}
                        onChange={(e) => updateEditContent('title', e.target.value)}
                        placeholder="記事のタイトルを入力..."
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium block mb-1">推奨トーン</label>
                      <Input
                        value={editContent.suggested_tone || ''}
                        onChange={(e) => updateEditContent('suggested_tone', e.target.value)}
                        placeholder="記事のトーンを入力（例：丁寧な解説調）..."
                      />
                    </div>
                    <div>
                      <label className="text-sm font-medium block mb-2">セクション構成</label>
                      <div className="space-y-2">
                        {editContent.sections?.map((section: any, index: number) => (
                          <div key={index} className="grid grid-cols-3 gap-2">
                            <div className="col-span-2">
                              <Input
                                value={section.heading || ''}
                                onChange={(e) => updateSectionContent(index, 'heading', e.target.value)}
                                placeholder={`セクション ${index + 1} の見出し`}
                              />
                            </div>
                            <Input
                              type="number"
                              value={section.estimated_chars || ''}
                              onChange={(e) => updateSectionContent(index, 'estimated_chars', parseInt(e.target.value) || 0)}
                              placeholder="文字数"
                              min="0"
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
                      disabled={!editContent.title?.trim()}
                    >
                      <Save className="w-4 h-4" />
                      この内容で進行
                    </Button>
                  </div>
                </div>
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
                      onClick={() => handleEdit('outline')}
                    >
                      <Edit3 className="w-4 h-4" />
                      編集
                    </Button>
                  </div>
                  {outline.sections.map((section: any, index: number) => (
                    <div key={index} className="flex items-start gap-3 p-4 bg-white border border-gray-200 rounded-lg">
                      <Badge variant="outline" className="mt-1">{index + 1}</Badge>
                      <div className="flex-1">
                        <h5 className="font-medium mb-1">{section.heading}</h5>
                        <p className="text-sm text-muted-foreground">{section.description}</p>
                      </div>
                    </div>
                  ))}
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
                  この構成で執筆開始
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  return null;
} 