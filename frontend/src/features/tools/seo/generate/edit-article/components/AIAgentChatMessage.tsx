'use client';

import React from 'react';
import { Bot, User } from 'lucide-react';

import { cn } from '@/utils/cn';

import ChatMarkdown from './ChatMarkdown';

interface AIAgentChatMessageProps {
  role: 'assistant' | 'user';
  content: string;
}

const roleConfig: Record<
  AIAgentChatMessageProps['role'],
  {
    bubbleClasses: string;
    textClasses: string;
    containerAlignment: string;
    wrapperDirection: string;
    iconWrapperClasses: string;
    icon: React.ReactNode;
    markdown?: boolean;
  }
> = {
  user: {
    bubbleClasses:
      'bg-blue-600 text-white shadow-lg shadow-blue-500/20 border border-blue-500/50',
    textClasses: 'whitespace-pre-wrap break-words text-sm leading-relaxed',
    containerAlignment: 'justify-end',
    wrapperDirection: 'flex-row-reverse',
    iconWrapperClasses: 'bg-blue-600 text-white shadow-sm shadow-blue-500/30',
    icon: <User className="h-4 w-4" />,
    markdown: false,
  },
  assistant: {
    bubbleClasses:
      'bg-slate-50 text-slate-900 border border-slate-200/70 shadow-sm',
    textClasses: 'text-slate-700',
    containerAlignment: 'justify-start',
    wrapperDirection: 'flex-row',
    iconWrapperClasses: 'bg-slate-100 text-blue-700 shadow-inner shadow-slate-200/70',
    icon: <Bot className="h-4 w-4" />,
    markdown: true,
  },
};

export default function AIAgentChatMessage({ role, content }: AIAgentChatMessageProps) {
  const config = roleConfig[role];

  return (
    <div className={cn('flex w-full', config.containerAlignment)}>
      <div className={cn('flex max-w-full gap-3', config.wrapperDirection, 'items-start')}>
        <div
          className={cn(
            'flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full border border-white/60',
            config.iconWrapperClasses
          )}
        >
          {config.icon}
        </div>

        <div
          className={cn(
            'min-w-0 max-w-[min(640px,85vw)] rounded-2xl px-4 py-3 transition-all duration-150',
            config.bubbleClasses
          )}
        >
          {config.markdown ? (
            <ChatMarkdown content={content} className="text-sm leading-relaxed prose-headings:mt-2" />
          ) : (
            <p className={config.textClasses}>{content}</p>
          )}
        </div>
      </div>
    </div>
  );
}
