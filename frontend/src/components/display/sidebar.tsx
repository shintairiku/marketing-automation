'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import clsx from 'clsx';
import { createPortal } from 'react-dom';
import {
  IoAnalytics, IoCalendar,
  IoCash,
  IoChatbubbles as IoChat,
  IoChatbubbles,
  IoChevronDown,
  IoChevronForward,
  IoClipboard, IoCode, IoDocumentText,
  IoGitBranch,
  IoGlobe,
  IoHelp,
  IoHome, IoImage, IoLinkSharp, IoList,
  IoLogoInstagram, IoMail, IoMegaphone, IoNewspaper, IoPencil, IoPeople, IoPerson,
  IoPricetag, IoSchool, IoSettings, IoSparkles,
  IoStatsChart,
  IoSync, IoText,
} from 'react-icons/io5';
import { LuPanelLeftClose, LuPanelLeftOpen } from 'react-icons/lu';

import { getFilteredGroups, groups } from '@/components/constant/route';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useSidebar } from '@/contexts/SidebarContext';
import { isPrivilegedEmail } from '@/lib/subscription';
import { cn } from '@/utils/cn';
import { useUser } from '@clerk/nextjs';

export const iconMap: Record<string, React.ReactElement<{ size?: number }>> = {
  '/dashboard':                        <IoHome size={20} />,
  '/seo/generate/new-article':         <IoText size={20} />,
  '/seo/manage/list':                  <IoList size={20} />,
  '/seo/manage/status':                <IoSync size={20} />,
  '/seo/manage/schedule':              <IoCalendar size={20} />,
  '/seo/analyze/dashboard':            <IoAnalytics size={20} />,
  '/seo/analyze/report':               <IoDocumentText size={20} />,
  '/seo/analyze/feedback':             <IoChatbubbles size={20} />,
  '/seo/input/persona':                <IoPerson size={20} />,
  '/company-settings/company':         <IoClipboard size={20} />,
  '/company-settings/style-guide':     <IoPencil size={20} />,
  '/instagram/home':                   <IoLogoInstagram size={20} />,
  '/instagram/generate/caption':       <IoText size={20} />,
  '/instagram/generate/hashtags':      <IoPricetag size={20} />,
  '/instagram/generate/image':         <IoImage size={20} />,
  '/instagram/generate/rewrite':       <IoSparkles size={20} />,
  '/instagram/generate/schedule':      <IoCalendar size={20} />,
  '/instagram/manage/list':            <IoList size={20} />,
  '/instagram/manage/status':          <IoSync size={20} />,
  '/instagram/analyze/dashboard':      <IoAnalytics size={20} />,
  '/instagram/analyze/report':         <IoDocumentText size={20} />,
  '/instagram/analyze/feedback':       <IoChatbubbles size={20} />,
  '/instagram/input/persona':          <IoPerson size={20} />,
  '/line/home':                        <IoChat size={20} />,
  '/line/generate/text':               <IoText size={20} />,
  '/line/generate/image':              <IoImage size={20} />,
  '/line/generate/rewrite':            <IoGitBranch size={20} />,
  '/line/generate/schedule':           <IoCalendar size={20} />,
  '/line/manage/list':                 <IoList size={20} />,
  '/line/manage/status':               <IoSync size={20} />,
  '/line/analyze/dashboard':           <IoAnalytics size={20} />,
  '/line/analyze/report':              <IoDocumentText size={20} />,
  '/line/analyze/feedback':            <IoChatbubbles size={20} />,
  '/line/input/persona':               <IoPerson size={20} />,
  '/settings/account':                 <IoPerson size={20} />,
  '/settings/members':                 <IoPeople size={20} />,
  '/settings/billing':                 <IoCash size={20} />,
  '/settings/integrations/wordpress':  <IoLinkSharp size={20} />,
  '/settings/integrations/instagram':  <IoLogoInstagram size={20} />,
  '/settings/integrations/line':       <IoChat size={20} />,
  '/help/home':                        <IoHelp size={20} />,
  '/help/getting-started':             <IoSchool size={20} />,
  '/help/faq':                         <IoChatbubbles size={20} />,
  '/help/contact':                     <IoMail size={20} />,
  '/help/tutorials':                   <IoSchool size={20} />,
  '/help/api-docs':                    <IoCode size={20} />,
  '/help/release-notes':               <IoMegaphone size={20} />,
  '/blog/new':                         <IoNewspaper size={20} />,
  '/blog/history':                     <IoDocumentText size={20} />,
};

/** メインアイコンのマップ（グループ代表アイコン） */
const mainIconMap: Record<string, React.ReactElement<{ size?: number }>> = {
  '/dashboard':                  <IoHome size={22} />,
  '/seo/generate/new-article':   <IoText size={22} />,
  '/blog/new':                   <IoNewspaper size={22} />,
  '/company-settings/company':   <IoClipboard size={22} />,
  '/settings/account':           <IoSettings size={22} />,
  '/help/home':                  <IoHelp size={22} />,
};

function isMenuActive(pathname: string, menuHref: string, subLinks?: { title: string; links: { href: string }[] }[]): boolean {
  if (pathname === menuHref) return true;
  if (subLinks) {
    for (const section of subLinks) {
      for (const link of section.links) {
        if (pathname === link.href || pathname.startsWith(link.href + '/')) return true;
      }
    }
  }
  // プラットフォーム別のフォールバック
  if (menuHref.startsWith('/seo/') && pathname.startsWith('/seo/')) return true;
  if (menuHref.startsWith('/blog/') && pathname.startsWith('/blog/')) return true;
  if (menuHref.startsWith('/instagram/') && pathname.startsWith('/instagram/')) return true;
  if (menuHref.startsWith('/line/') && pathname.startsWith('/line/')) return true;
  if (menuHref.startsWith('/company-settings/') && pathname.startsWith('/company-settings/')) return true;
  if (menuHref.startsWith('/settings/') && pathname.startsWith('/settings/')) return true;
  if (menuHref.startsWith('/help/') && pathname.startsWith('/help/')) return true;
  return false;
}

export default function Sidebar() {
  const pathname = usePathname();
  const { user } = useUser();
  const { isSidebarOpen, toggleSidebar, expandedMenu, setExpandedMenu, toggleMenu, isMobile } = useSidebar();

  // モバイル時はSheet内で常に展開表示
  const effectiveOpen = isMobile ? true : isSidebarOpen;

  // ユーザー権限に基づいてグループをフィルタリング
  const isPrivileged = isPrivilegedEmail(user?.primaryEmailAddress?.emailAddress);
  const filteredGroups = useMemo(() => getFilteredGroups(isPrivileged), [isPrivileged]);

  // パス変更時に対応するメニューを自動展開
  useEffect(() => {
    const allLinks = filteredGroups.flatMap(g => g.links);
    const activeMenu = allLinks.find(l => isMenuActive(pathname, l.href, l.subLinks));
    if (activeMenu && expandedMenu !== activeMenu.href) {
      setExpandedMenu(activeMenu.href);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  return (
    <TooltipProvider delayDuration={200}>
      <aside
        className={cn(
          'flex flex-col h-screen bg-white border-r border-stone-200 transition-all duration-300 ease-in-out overflow-hidden',
          effectiveOpen ? 'w-[240px]' : 'w-[64px]'
        )}
      >
        {/* Logo + Toggle */}
        <div className={cn(
          'flex items-center h-14 border-b border-stone-100 shrink-0',
          effectiveOpen ? 'px-3 justify-between' : 'justify-center'
        )}>
          {effectiveOpen ? (
            <>
              <div className="flex items-center gap-2">
                <Image src="/logo.png" alt="ブログAI" width={113} height={32} className="shrink-0" />
              </div>
              {!isMobile && (
                <button
                  onClick={toggleSidebar}
                  className="p-1.5 rounded-md text-stone-400 hover:text-stone-600 hover:bg-stone-100 transition-colors"
                >
                  <LuPanelLeftClose size={18} />
                </button>
              )}
            </>
          ) : (
            <button
              onClick={toggleSidebar}
              className="p-1 rounded-md hover:bg-stone-100 transition-colors"
            >
              <Image src="/icon.png" alt="ブログAI" width={28} height={28} />
            </button>
          )}
        </div>

        {/* Navigation */}
        <ScrollArea className="flex-1">
          <nav className="py-2">
            {filteredGroups.map((group) => (
              <div key={group.title} className="mb-1">
                {group.links.map((link) => {
                  const active = isMenuActive(pathname, link.href, link.subLinks);
                  const isExpanded = expandedMenu === link.href;
                  const hasSubLinks = link.subLinks && link.subLinks.length > 0;
                  const mainIcon = mainIconMap[link.href] || iconMap[link.href];

                  // サイドバー折り畳み時: アイコン + ホバーでサブメニューをフライアウト表示
                  if (!effectiveOpen) {
                    if (!hasSubLinks) {
                      return (
                        <Tooltip key={link.href}>
                          <TooltipTrigger asChild>
                            <Link
                              href={link.href}
                              className={clsx(
                                'flex items-center justify-center h-11 mx-2 my-0.5 rounded-lg transition-colors',
                                active
                                  ? 'bg-primary/10 text-primary'
                                  : 'text-stone-500 hover:bg-stone-100 hover:text-stone-700'
                              )}
                            >
                              <span className={active ? 'text-primary' : ''}>{mainIcon}</span>
                            </Link>
                          </TooltipTrigger>
                          <TooltipContent side="right" sideOffset={8}>
                            <p className="font-medium">{link.label}</p>
                          </TooltipContent>
                        </Tooltip>
                      );
                    }

                    // サブリンク付き: ホバーでフライアウトメニュー表示
                    return (
                      <CollapsedMenuFlyout
                        key={link.href}
                        link={link}
                        active={active}
                        mainIcon={mainIcon}
                        pathname={pathname}
                      />
                    );
                  }

                  // サイドバー展開時: アコーディオン式
                  if (!hasSubLinks) {
                    return (
                      <Link
                        key={link.href}
                        href={link.href}
                        className={clsx(
                          'flex items-center gap-3 h-10 mx-2 my-0.5 px-3 rounded-lg text-sm font-medium transition-colors',
                          active
                            ? 'bg-primary/10 text-primary'
                            : 'text-stone-600 hover:bg-stone-50 hover:text-stone-800'
                        )}
                      >
                        <span className="shrink-0">{mainIcon}</span>
                        <span className="truncate">{link.label}</span>
                      </Link>
                    );
                  }

                  return (
                    <Collapsible
                      key={link.href}
                      open={isExpanded}
                      onOpenChange={() => toggleMenu(link.href)}
                    >
                      <CollapsibleTrigger asChild>
                        <button
                          className={clsx(
                            'flex items-center gap-3 w-full h-10 mx-2 pr-3 pl-3 my-0.5 rounded-lg text-sm font-medium transition-colors text-left',
                            active
                              ? 'bg-primary/10 text-primary'
                              : 'text-stone-600 hover:bg-stone-50 hover:text-stone-800',
                            // w-full + mx-2 だと幅がはみ出るので計算
                          )}
                          style={{ width: 'calc(100% - 16px)' }}
                        >
                          <span className="shrink-0">{mainIcon}</span>
                          <span className="truncate flex-1">{link.label}</span>
                          <IoChevronDown
                            size={14}
                            className={cn(
                              'shrink-0 text-stone-400 transition-transform duration-200',
                              isExpanded && 'rotate-180'
                            )}
                          />
                        </button>
                      </CollapsibleTrigger>

                      <CollapsibleContent className="overflow-hidden data-[state=open]:animate-collapsible-down data-[state=closed]:animate-collapsible-up">
                        <div className="ml-4 mr-2 mt-0.5 mb-1 border-l-2 border-stone-100">
                          {link.subLinks.map((section) => (
                            <div key={section.title} className="py-1">
                              <p className="px-4 py-1 text-[11px] font-semibold text-stone-400 uppercase tracking-wider">
                                {section.title}
                              </p>
                              {section.links.map((subLink) => {
                                const isDisabled = subLink.disabled;
                                const isSubActive = pathname === subLink.href;

                                if (isDisabled) {
                                  return (
                                    <div
                                      key={subLink.href || subLink.label}
                                      className="flex items-center gap-2.5 px-4 py-1.5 text-sm text-stone-300 cursor-not-allowed"
                                    >
                                      <span className="shrink-0 opacity-50">
                                        {iconMap[subLink.href]}
                                      </span>
                                      <span className="truncate">{subLink.label}</span>
                                      <span className="ml-auto text-[10px] bg-stone-100 text-stone-400 px-1.5 py-0.5 rounded">
                                        開発中
                                      </span>
                                    </div>
                                  );
                                }

                                return (
                                  <Link
                                    key={subLink.href}
                                    href={subLink.href}
                                    className={clsx(
                                      'flex items-center gap-2.5 px-4 py-1.5 text-sm rounded-r-md transition-colors',
                                      isSubActive
                                        ? 'text-primary font-medium bg-primary/5 border-l-2 border-primary -ml-[2px]'
                                        : 'text-stone-500 hover:text-stone-700 hover:bg-stone-50'
                                    )}
                                  >
                                    <span className="shrink-0">{iconMap[subLink.href]}</span>
                                    <span className="truncate">{subLink.label}</span>
                                  </Link>
                                );
                              })}
                            </div>
                          ))}
                        </div>
                      </CollapsibleContent>
                    </Collapsible>
                  );
                })}
              </div>
            ))}
          </nav>
        </ScrollArea>

      </aside>
    </TooltipProvider>
  );
}

/**
 * 縮小サイドバー用フライアウトメニュー
 * アイコンホバーで右側にサブメニューを Portal 経由でポップアウト表示
 * （aside の overflow-hidden を回避するため body 直下に描画）
 */
function CollapsedMenuFlyout({
  link,
  active,
  mainIcon,
  pathname,
}: {
  link: { href: string; label: string; subLinks: { title: string; links: { href: string; label: string; disabled?: boolean }[] }[] };
  active: boolean;
  mainIcon: React.ReactNode;
  pathname: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [panelPos, setPanelPos] = useState<{ top: number; left: number } | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const triggerRef = useRef<HTMLAnchorElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const open = useCallback(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    // アイコンの位置を取得してパネル座標を計算
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setPanelPos({ top: rect.top, left: rect.right + 6 });
    }
    setIsOpen(true);
  }, []);

  const close = useCallback(() => {
    timeoutRef.current = setTimeout(() => setIsOpen(false), 150);
  }, []);

  const cancelClose = useCallback(() => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
  }, []);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  return (
    <>
      {/* アイコンボタン */}
      <Link
        ref={triggerRef}
        href={link.href}
        className={clsx(
          'flex items-center justify-center h-11 mx-2 my-0.5 rounded-lg transition-colors',
          active
            ? 'bg-primary/10 text-primary'
            : 'text-stone-500 hover:bg-stone-100 hover:text-stone-700'
        )}
        onMouseEnter={open}
        onMouseLeave={close}
      >
        <span className={active ? 'text-primary' : ''}>{mainIcon}</span>
      </Link>

      {/* フライアウトパネル — Portal で body 直下に描画 */}
      {isOpen && panelPos && createPortal(
        <div
          ref={panelRef}
          className="fixed z-[9999] min-w-[210px] py-2 bg-white rounded-xl border border-stone-200 shadow-xl animate-in fade-in slide-in-from-left-2 duration-150"
          style={{ top: panelPos.top, left: panelPos.left }}
          onMouseEnter={cancelClose}
          onMouseLeave={close}
        >
          <p className="px-3 pb-1.5 text-xs font-semibold text-stone-500 border-b border-stone-100 mb-1">
            {link.label}
          </p>
          {link.subLinks.map((section) => (
            <div key={section.title} className="py-1">
              {link.subLinks.length > 1 && (
                <p className="px-3 py-1 text-[10px] font-semibold text-stone-400 uppercase tracking-wider">
                  {section.title}
                </p>
              )}
              {section.links.map((subLink) => {
                if (subLink.disabled) {
                  return (
                    <div
                      key={subLink.href || subLink.label}
                      className="flex items-center gap-2 px-3 py-1.5 text-sm text-stone-300 cursor-not-allowed"
                    >
                      <span className="shrink-0 opacity-50">{iconMap[subLink.href]}</span>
                      <span className="truncate">{subLink.label}</span>
                    </div>
                  );
                }
                const isSubActive = pathname === subLink.href;
                return (
                  <Link
                    key={subLink.href}
                    href={subLink.href}
                    className={clsx(
                      'flex items-center gap-2 px-3 py-1.5 text-sm transition-colors rounded-md mx-1',
                      isSubActive
                        ? 'text-primary font-medium bg-primary/5'
                        : 'text-stone-600 hover:bg-stone-50 hover:text-stone-800'
                    )}
                    onClick={() => setIsOpen(false)}
                  >
                    <span className="shrink-0">{iconMap[subLink.href]}</span>
                    <span className="truncate">{subLink.label}</span>
                  </Link>
                );
              })}
            </div>
          ))}
        </div>,
        document.body,
      )}
    </>
  );
}
