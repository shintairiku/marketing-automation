'use client';

import React,
{ createContext, PropsWithChildren, useCallback, useContext, useEffect, useState } from 'react';

interface SidebarContextType {
  isSidebarOpen: boolean;
  setIsSidebarOpen: (value: boolean) => void;
  toggleSidebar: () => void;
  expandedMenu: string | null;
  setExpandedMenu: (href: string | null) => void;
  toggleMenu: (href: string) => void;
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

const SIDEBAR_OPEN_KEY = 'sidebar-open';
const SIDEBAR_EXPANDED_KEY = 'sidebar-expanded-menu';

export function SidebarProvider({ children }: PropsWithChildren) {
  const [isSidebarOpen, setIsSidebarOpenState] = useState(true);
  const [expandedMenu, setExpandedMenuState] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    try {
      const savedOpen = localStorage.getItem(SIDEBAR_OPEN_KEY);
      if (savedOpen !== null) {
        setIsSidebarOpenState(JSON.parse(savedOpen));
      }
      const savedExpanded = localStorage.getItem(SIDEBAR_EXPANDED_KEY);
      if (savedExpanded) {
        setExpandedMenuState(savedExpanded);
      }
    } catch (error) {
      console.warn('Failed to load sidebar state:', error);
    }
    setIsInitialized(true);
  }, []);

  const setIsSidebarOpen = useCallback((value: boolean) => {
    setIsSidebarOpenState(value);
    try {
      localStorage.setItem(SIDEBAR_OPEN_KEY, JSON.stringify(value));
    } catch (error) {
      console.warn('Failed to save sidebar state:', error);
    }
  }, []);

  const toggleSidebar = useCallback(() => {
    setIsSidebarOpen(!isSidebarOpen);
  }, [isSidebarOpen, setIsSidebarOpen]);

  const setExpandedMenu = useCallback((href: string | null) => {
    setExpandedMenuState(href);
    try {
      if (href) {
        localStorage.setItem(SIDEBAR_EXPANDED_KEY, href);
      } else {
        localStorage.removeItem(SIDEBAR_EXPANDED_KEY);
      }
    } catch (error) {
      console.warn('Failed to save sidebar expanded state:', error);
    }
  }, []);

  const toggleMenu = useCallback((href: string) => {
    setExpandedMenu(expandedMenu === href ? null : href);
  }, [expandedMenu, setExpandedMenu]);

  if (!isInitialized) {
    return <div className="min-h-screen bg-background" />;
  }

  return (
    <SidebarContext.Provider value={{
      isSidebarOpen,
      setIsSidebarOpen,
      toggleSidebar,
      expandedMenu,
      setExpandedMenu,
      toggleMenu,
    }}>
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
