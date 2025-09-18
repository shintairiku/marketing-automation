'use client';

import React from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical } from 'lucide-react';
import { cn } from '@/utils/cn';

interface SortableBlockProps {
  id: string;
  children: React.ReactNode;
  isDragging?: boolean;
}

export default function SortableBlock({ id, children, isDragging }: SortableBlockProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging: isLocalDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        'relative group',
        isLocalDragging && 'opacity-50',
        isDragging && 'invisible'
      )}
    >
      {/* ドラッグハンドル */}
      <div
        className={cn(
          'absolute -left-8 top-1/2 -translate-y-1/2 p-1 rounded cursor-grab hover:bg-gray-100',
          'opacity-0 group-hover:opacity-100 transition-opacity',
          'touch-none', // タッチデバイスでの誤動作防止
        )}
        {...attributes}
        {...listeners}
      >
        <GripVertical className="h-5 w-5 text-gray-400" />
      </div>
      {children}
    </div>
  );
}