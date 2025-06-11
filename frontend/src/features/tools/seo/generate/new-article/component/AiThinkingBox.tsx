'use client';

import { motion } from 'framer-motion';
import { Brain, Sparkles, Zap } from 'lucide-react';

import { Card, CardContent } from "@/components/ui/card";

interface AiThinkingBoxProps {
  messages: string[];
  isActive?: boolean;
}

export default function AiThinkingBox({ messages, isActive = false }: AiThinkingBoxProps) {
  if (!isActive && messages.length === 0) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center gap-4 my-10"
    >
      {/* 接続線 */}
      <motion.div 
        className="w-1 h-12 rounded-full bg-gradient-to-b from-primary to-primary/50"
        animate={isActive ? { opacity: [0.5, 1, 0.5] } : {}}
        transition={{ duration: 2, repeat: Infinity }}
      />
      
      {messages.map((message, index) => (
        <motion.div
          key={index}
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: index * 0.2 }}
        >
          <Card className="min-w-[600px] max-w-[800px] mx-auto border-2 border-primary/20 bg-gradient-to-r from-blue-50 to-purple-50">
            <CardContent className="p-6">
              <div className="flex items-center gap-3">
                <motion.div
                  animate={isActive ? { rotate: 360 } : {}}
                  transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                  className="flex-shrink-0"
                >
                  <Brain className="w-6 h-6 text-primary" />
                </motion.div>
                <div className="flex-1">
                  <motion.p 
                    className="text-gray-700 font-medium"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.5 }}
                  >
                    {message}
                  </motion.p>
                </div>
                {isActive && (
                  <motion.div
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 1, repeat: Infinity }}
                  >
                    <Sparkles className="w-5 h-5 text-yellow-500" />
                  </motion.div>
                )}
              </div>
            </CardContent>
          </Card>
          
          {index < messages.length - 1 && (
            <motion.div 
              className="w-1 h-8 rounded-full bg-gradient-to-b from-primary/50 to-primary/30 mx-auto mt-4"
              animate={{ opacity: [0.3, 0.7, 0.3] }}
              transition={{ duration: 1.5, repeat: Infinity, delay: index * 0.3 }}
            />
          )}
        </motion.div>
      ))}
      
      {isActive && (
        <motion.div 
          className="w-1 h-12 rounded-full bg-gradient-to-b from-primary/50 to-transparent"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      )}
    </motion.div>
  );
}