'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';

interface SelectionBox {
  left: number;
  top: number;
  width: number;
  height: number;
}

interface SelectionManagerProps {
  onSelectionChange?: (selectedIds: Set<string>) => void;
  blockRefs: Record<string, HTMLElement | null>;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export default function SelectionManager({
  onSelectionChange,
  blockRefs,
  children,
  className,
  style
}: SelectionManagerProps) {
  const [selectionBox, setSelectionBox] = useState<SelectionBox | null>(null);
  const [isSelecting, setIsSelecting] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const selectionOrigin = useRef<{ x: number; y: number } | null>(null);
  const selectedBaseRef = useRef<Set<string>>(new Set());
  const selectionModeRef = useRef<'replace' | 'add'>('replace');

  const handleMouseDown = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;

    const target = event.target as HTMLElement;

    // Skip if clicking on interactive elements
    if (target.closest('button, input, textarea, select, a[href], [role="button"]')) {
      return;
    }

    // Skip drag handles and interactive elements unless explicitly allowed
    if (target.closest('[data-interactive="true"]') && !target.closest('[data-allow-selection="true"]')) {
      return;
    }

    // Skip if clicking inside editable content areas
    if (target.closest('[contenteditable="true"]')) {
      return;
    }

    // Allow selection on most content areas
    console.log('Starting selection at:', { x: event.clientX, y: event.clientY });

    const container = containerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const originX = event.clientX - rect.left;
    const originY = event.clientY - rect.top;

    selectionOrigin.current = { x: originX, y: originY };
    const isAddMode = event.metaKey || event.ctrlKey || event.shiftKey;
    selectionModeRef.current = isAddMode ? 'add' : 'replace';

    // For add mode, preserve current selection
    if (isAddMode) {
      // Get currently selected blocks from DOM
      const currentlySelected = new Set<string>();
      Object.entries(blockRefs).forEach(([id, element]) => {
        if (element && element.closest('[data-selected="true"]')) {
          currentlySelected.add(id);
        }
      });
      selectedBaseRef.current = currentlySelected;
    } else {
      selectedBaseRef.current = new Set();
      // Clear selection immediately for replace mode
      onSelectionChange?.(new Set());
    }

    setIsSelecting(true);
    setSelectionBox({ left: originX, top: originY, width: 0, height: 0 });

    const handleMouseMove = (moveEvent: MouseEvent) => {
      if (!selectionOrigin.current || !container) return;

      moveEvent.preventDefault();
      moveEvent.stopPropagation();

      const containerRect = container.getBoundingClientRect();
      const currentX = moveEvent.clientX - containerRect.left;
      const currentY = moveEvent.clientY - containerRect.top;
      const origin = selectionOrigin.current;

      const left = Math.min(origin.x, currentX);
      const top = Math.min(origin.y, currentY);
      const width = Math.abs(currentX - origin.x);
      const height = Math.abs(currentY - origin.y);

      const newBox = { left, top, width, height };
      setSelectionBox(newBox);

      // Use global coordinates for intersection detection
      const startX = containerRect.left + origin.x;
      const startY = containerRect.top + origin.y;
      const selectionRect = {
        left: Math.min(startX, moveEvent.clientX),
        right: Math.max(startX, moveEvent.clientX),
        top: Math.min(startY, moveEvent.clientY),
        bottom: Math.max(startY, moveEvent.clientY),
      };

      const nextSelection = new Set(selectedBaseRef.current);

      Object.entries(blockRefs).forEach(([id, element]) => {
        if (!element) return;

        const blockRect = element.getBoundingClientRect();
        const intersects =
          selectionRect.left <= blockRect.right &&
          selectionRect.right >= blockRect.left &&
          selectionRect.top <= blockRect.bottom &&
          selectionRect.bottom >= blockRect.top;

        if (intersects) {
          nextSelection.add(id);
        }
      });

      onSelectionChange?.(nextSelection);
    };

    const handleMouseUp = (upEvent: MouseEvent) => {
      upEvent.preventDefault();
      upEvent.stopPropagation();

      setIsSelecting(false);
      setSelectionBox(null);
      selectionOrigin.current = null;
      selectedBaseRef.current = new Set();

      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    event.preventDefault();
    event.stopPropagation();
  }, [blockRefs, onSelectionChange]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      setSelectionBox(null);
      setIsSelecting(false);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      className={className}
      style={style}
      onMouseDown={handleMouseDown}
    >
      {/* Selection box overlay */}
      {selectionBox && isSelecting && (
        <div
          className="pointer-events-none absolute z-50 border-2 border-blue-600 bg-blue-300/40 shadow-md"
          style={{
            left: selectionBox.left,
            top: selectionBox.top,
            width: Math.max(selectionBox.width, 1),
            height: Math.max(selectionBox.height, 1),
          }}
        />
      )}

      {children}
    </div>
  );
}