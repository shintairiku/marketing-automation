'use client';

import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import React from 'react';

interface StepIndicatorProps {
  currentStep: string;
}

 
function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
} 

const PROFILE_STEPS = [
  { id: 'theme', number: 1, title: 'テーマ' },
  { id: 'outline', number: 2, title: 'アウトライン' },
  { id: 'body', number: 3, title: '本文' },
  { id: 'title', number: 4, title: 'タイトル' },
  { id: 'edit', number: 5, title: '編集' },
];

export const StepIndicator = ({ currentStep }: StepIndicatorProps) => {
  return (
    <div className="flex items-center justify-center p-10">
      {PROFILE_STEPS.map((step, index) => (
        <React.Fragment key={step.id}>
          {/* ステップサークルとラベル */}
          <div className="flex justify-center gap-2 items-center">
            <div
              className={cn(
                'w-6 h-6 rounded-full flex items-center justify-center text-xs font-semibold relative',
                currentStep === step.id
                  ? 'bg-primary text-white'
                  : 'bg-gray-300 text-white'
              )}
            >
              {step.number}
            </div>
            <span className={cn(
              'text-sm font-bold whitespace-nowrap',
              currentStep === step.id ? 'text-primary' : 'text-gray-300'
            )}>
              {step.title}
            </span>
          </div>
          {/* 接続線（最後以外） */}
          {index < PROFILE_STEPS.length - 1 && (
            <div
              className={cn(
                'h-[2px] flex-1 mx-4',
                currentStep === PROFILE_STEPS[index + 1].id || currentStep === step.id
                  ? 'bg-primary'
                  : 'bg-gray-300'
              )}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );
};
