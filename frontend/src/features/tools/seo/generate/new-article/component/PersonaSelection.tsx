'use client';

import { motion } from 'framer-motion';
import { RefreshCw,User } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PersonaOption } from '@/types/article-generation';

interface PersonaSelectionProps {
  personas: PersonaOption[];
  onSelect: (personaId: number) => void;
  onRegenerate: () => void;
  isWaiting?: boolean;
}

export default function PersonaSelection({ 
  personas, 
  onSelect, 
  onRegenerate, 
  isWaiting = false 
}: PersonaSelectionProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-4xl mx-auto space-y-6"
    >
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-gray-900">ペルソナを選択してください</h2>
        <p className="text-gray-600">
          生成されたペルソナの中から、最も適切なものを選択してください
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {personas.map((persona, index) => (
          <motion.div
            key={persona.id}
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card className="h-full hover:shadow-lg transition-shadow cursor-pointer group">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <User className="w-5 h-5 text-primary" />
                  ペルソナ {persona.id + 1}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-700 mb-4 line-clamp-4">
                  {persona.description}
                </p>
                <Button 
                  onClick={() => onSelect(persona.id)}
                  disabled={isWaiting}
                  className="w-full"
                  variant="outline"
                >
                  {isWaiting ? '選択中...' : 'このペルソナを選択'}
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
          ペルソナを再生成
        </Button>
      </div>
    </motion.div>
  );
}