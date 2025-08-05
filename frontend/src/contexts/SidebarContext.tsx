'use client';

import React,
{ createContext, useContext, useState, useEffect, PropsWithChildren } from 'react';

interface SidebarContextType {
  isSubSidebarOpen: boolean;
  setIsSubSidebarOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

const SIDEBAR_STORAGE_KEY = 'sub-sidebar-open';

export function SidebarProvider({ children }: PropsWithChildren) {
  const [isSubSidebarOpen, setIsSubSidebarOpenState] = useState(true);
  const [isInitialized, setIsInitialized] = useState(false);

  // ローカルストレージから初期状態を読み込み
  useEffect(() => {
    try {
      const savedState = localStorage.getItem(SIDEBAR_STORAGE_KEY);
      if (savedState !== null) {
        setIsSubSidebarOpenState(JSON.parse(savedState));
      }
    } catch (error) {
      console.warn('Failed to load sidebar state from localStorage:', error);
    }
    setIsInitialized(true);
  }, []);

  // 状態変更時にローカルストレージに保存
  const setIsSubSidebarOpen = (value: boolean | ((prev: boolean) => boolean)) => {
    setIsSubSidebarOpenState(prevState => {
      const newState = typeof value === 'function' ? value(prevState) : value;
      try {
        localStorage.setItem(SIDEBAR_STORAGE_KEY, JSON.stringify(newState));
      } catch (error) {
        console.warn('Failed to save sidebar state to localStorage:', error);
      }
      return newState;
    });
  };

  // 初期化が完了するまでは空のdivを返す
  if (!isInitialized) {
    return <div className="min-h-screen bg-background" />;
  }

  return (
    <SidebarContext.Provider value={{ isSubSidebarOpen, setIsSubSidebarOpen }}>
      {children}
    </SidebarContext.Provider>
  );
}

export function useSidebar() {
  const context = useContext(SidebarContext);
  if (context === undefined) {
    throw new Error('useSidebar must be used within a SidebarProvider');
  }
  return context;
}
