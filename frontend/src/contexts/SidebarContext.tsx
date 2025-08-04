'use client';

import React,
{ createContext, useContext, useState, PropsWithChildren } from 'react';

interface SidebarContextType {
  isSubSidebarOpen: boolean;
  setIsSubSidebarOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

export function SidebarProvider({ children }: PropsWithChildren) {
  const [isSubSidebarOpen, setIsSubSidebarOpen] = useState(true);

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
