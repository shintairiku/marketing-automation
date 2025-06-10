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
  TrendingUp
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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
  isWaiting = false
}: CompactUserInteractionProps) {

  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);

  const handleSelect = (index: number) => {
    setSelectedIndex(index);
    setTimeout(() => {
      onSelect?.(index);
    }, 300);
  };

  const handleApprove = (approved: boolean) => {
    onApprove?.(approved);
  };

  // ペルソナ選択
  if (type === 'select_persona' && personas) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-5xl mx-auto"
      >
        <Card className="border-2 border-primary/20 shadow-lg">
          <CardHeader className="bg-gradient-to-r from-primary/5 to-secondary/5">
            <CardTitle className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-r from-primary to-secondary rounded-full flex items-center justify-center">
                <Users className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-xl font-bold">ターゲットペルソナを選択</h3>
                <p className="text-sm text-muted-foreground font-normal">
                  記事のターゲットとなるペルソナを1つ選択してください
                </p>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
              {personas.map((persona, index) => (
                <motion.div
                  key={persona.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className={`
                    relative p-4 rounded-xl border-2 cursor-pointer transition-all duration-300
                    ${selectedIndex === index 
                      ? 'border-primary bg-primary/5 shadow-lg ring-4 ring-primary/20' 
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
                  
                  {selectedIndex === index && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="absolute -top-2 -right-2 w-6 h-6 bg-primary rounded-full flex items-center justify-center"
                    >
                      <Check className="w-4 h-4 text-white" />
                    </motion.div>
                  )}
                </motion.div>
              ))}
            </div>
            
            <div className="flex justify-between">
              <Button
                variant="outline"
                onClick={onRegenerate}
                className="flex items-center gap-2"
                disabled={isWaiting}
              >
                <RotateCcw className="w-4 h-4" />
                新しいペルソナを生成
              </Button>
              
              <Badge variant="secondary" className="self-center">
                {personas.length}つのペルソナから選択
              </Badge>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  // テーマ選択
  if (type === 'select_theme' && themes) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-5xl mx-auto"
      >
        <Card className="border-2 border-secondary/20 shadow-lg">
          <CardHeader className="bg-gradient-to-r from-secondary/5 to-accent/5">
            <CardTitle className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-r from-secondary to-accent rounded-full flex items-center justify-center">
                <Lightbulb className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-xl font-bold">記事テーマを選択</h3>
                <p className="text-sm text-muted-foreground font-normal">
                  執筆したい記事のテーマを1つ選択してください
                </p>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="space-y-4 mb-6">
              {themes.map((theme, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.99 }}
                  className={`
                    relative p-5 rounded-xl border-2 cursor-pointer transition-all duration-300
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
            
            <div className="flex justify-between">
              <Button
                variant="outline"
                onClick={onRegenerate}
                className="flex items-center gap-2"
                disabled={isWaiting}
              >
                <RotateCcw className="w-4 h-4" />
                新しいテーマを生成
              </Button>
              
              <Badge variant="secondary" className="self-center">
                {themes.length}つのテーマから選択
              </Badge>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  // リサーチ計画承認
  if (type === 'approve_plan' && researchPlan) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-5xl mx-auto"
      >
        <Card className="border-2 border-accent/20 shadow-lg">
          <CardHeader className="bg-gradient-to-r from-accent/5 to-primary/5">
            <CardTitle className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-r from-accent to-primary rounded-full flex items-center justify-center">
                <Search className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-xl font-bold">リサーチ計画の確認</h3>
                <p className="text-sm text-muted-foreground font-normal">
                  記事執筆のためのリサーチ計画をご確認ください
                </p>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="bg-gray-50 rounded-lg p-4 mb-6">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="w-5 h-5 text-accent" />
                <h4 className="font-semibold">リサーチ概要</h4>
              </div>
              <div className="space-y-2 text-sm text-muted-foreground">
                <p><strong>対象キーワード:</strong> {researchPlan.keywords?.join(', ')}</p>
                <p><strong>リサーチクエリ数:</strong> {researchPlan.queries?.length || 0}件</p>
                <p><strong>推定実行時間:</strong> 約2-3分</p>
              </div>
            </div>

            {researchPlan.queries && (
              <div className="space-y-3 mb-6">
                <h4 className="font-semibold flex items-center gap-2">
                  <Search className="w-4 h-4" />
                  実行予定のリサーチクエリ
                </h4>
                {researchPlan.queries.map((query: string, index: number) => (
                  <div key={index} className="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-lg">
                    <Badge variant="outline">{index + 1}</Badge>
                    <span className="text-sm">{query}</span>
                  </div>
                ))}
              </div>
            )}

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
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  // アウトライン承認
  if (type === 'approve_outline' && outline) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-5xl mx-auto"
      >
        <Card className="border-2 border-primary/20 shadow-lg">
          <CardHeader className="bg-gradient-to-r from-primary/5 to-secondary/5">
            <CardTitle className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-r from-primary to-secondary rounded-full flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-white" />
              </div>
              <div>
                <h3 className="text-xl font-bold">記事構成の確認</h3>
                <p className="text-sm text-muted-foreground font-normal">
                  生成された記事のアウトラインをご確認ください
                </p>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
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

            {outline.sections && (
              <div className="space-y-3 mb-6">
                <h4 className="font-semibold">記事構成</h4>
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
            )}

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
          </CardContent>
        </Card>
      </motion.div>
    );
  }

  return null;
} 