'use client';

import { motion } from 'framer-motion';
import { Lightbulb, RefreshCw } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ThemeOption } from '@/types/article-generation';

interface ThemeSelectionProps {
  themes: ThemeOption[];
  onSelect: (themeIndex: number) => void;
  onRegenerate: () => void;
  isWaiting?: boolean;
}

export default function ThemeSelection({ 
  themes, 
  onSelect, 
  onRegenerate, 
  isWaiting = false 
}: ThemeSelectionProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-5xl mx-auto space-y-6"
    >
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-gray-900">記事テーマを選択してください</h2>
        <p className="text-gray-600">
          SEO効果とターゲットペルソナを考慮したテーマ案から選択してください
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {themes.map((theme, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card className="h-full hover:shadow-lg transition-shadow cursor-pointer group">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Lightbulb className="w-5 h-5 text-primary" />
                  {theme.title}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-gray-700">
                  {theme.description}
                </p>
                
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-gray-800">関連キーワード</h4>
                  <div className="flex flex-wrap gap-2">
                    {theme.keywords.map((keyword: string, keywordIndex: number) => (
                      <Badge key={keywordIndex} variant="secondary" className="text-xs">
                        {keyword}
                      </Badge>
                    ))}
                  </div>
                </div>
                
                <Button 
                  onClick={() => onSelect(index)}
                  disabled={isWaiting}
                  className="w-full"
                  variant="outline"
                >
                  {isWaiting ? '選択中...' : 'このテーマを選択'}
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="flex justify-center">
        <Button
          onClick={onRegenerate}
          disabled={isWaiting}
          variant="ghost"
          className="text-gray-600 hover:text-gray-800"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          テーマを再生成
        </Button>
      </div>
    </motion.div>
  );
}