'use client';

import React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import clsx from 'clsx';
import {
  IoAnalytics, IoBug, IoCalendar, 
  IoCash, 
  IoChatbubbles as IoChat,
  IoChatbubbles, IoClipboard, IoCloudUpload,
  IoCode, IoDocumentText, IoGitBranch,
  IoGlobe, 
  IoHelp, 
  IoHome, IoImage, IoLinkSharp, IoList, 
  IoLogoInstagram, IoMail, IoMegaphone, IoNewspaper, IoPencil, IoPeople, IoPerson,
  IoPricetag, IoSchool, IoSettings, IoSparkles,
  IoStatsChart,
  IoSync, IoText,
  IoChevronBack,
  IoChevronForward,
} from 'react-icons/io5';

import { groups } from '@/components/constant/route';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import { cn } from '@/utils/cn';
import { useSidebar } from '@/contexts/SidebarContext';

export const iconMap: Record<string, React.ReactElement<{ size?: number }>> = {
  /* ───────── 1. Dashboard ───────── */
  '/dashboard'                 : <IoHome size={24} />,
  '/dashboard/news'            : <IoNewspaper size={24} />,
  '/dashboard/overview'        : <IoClipboard size={24} />,
  '/dashboard/calendar'        : <IoCalendar size={24} />,
  '/dashboard/performance'     : <IoStatsChart size={24} />,

  /* ───────── 2. Generate / SEO ───────── */
  '/seo/home'              : <IoGlobe size={24} />,
  '/seo/generate/new-article'        : <IoText size={24} />,

  '/seo/manage/list'           : <IoList size={24} />,
  '/seo/manage/status'         : <IoSync size={24} />,
  '/seo/manage/schedule'       : <IoCalendar size={24} />,

  '/seo/analyze/dashboard'     : <IoAnalytics size={24} />,
  '/seo/analyze/report'        : <IoDocumentText size={24} />,
  '/seo/analyze/feedback'      : <IoChatbubbles size={24} />,

  '/seo/input/persona'         : <IoPerson size={24} />,

  /* ───────── 3. Company Settings ───────── */
  '/company-settings/company'  : <IoClipboard size={24} />,
  '/company-settings/style-guide' : <IoPencil size={24} />,

  /* ───────── 4. Generate / Instagram ───────── */
  '/instagram/home'            : <IoLogoInstagram size={24} />,
  '/instagram/generate/caption'    : <IoText size={24} />,
  '/instagram/generate/hashtags'   : <IoPricetag size={24} />,
  '/instagram/generate/image'      : <IoImage size={24} />,
  '/instagram/generate/rewrite'    : <IoSparkles size={24} />,
  '/instagram/generate/schedule'   : <IoCalendar size={24} />,
  '/instagram/manage/list'       : <IoList size={24} />,
  '/instagram/manage/status'     : <IoSync size={24} />,
  '/instagram/analyze/dashboard'  : <IoAnalytics size={24} />,
  '/instagram/analyze/report'     : <IoDocumentText size={24} />,
  '/instagram/analyze/feedback'   : <IoChatbubbles size={24} />,

  '/instagram/input/persona'    : <IoPerson size={24} />,

  /* ───────── 5. Generate / LINE ───────── */
  '/line/home'                 : <IoChat size={24} />,
  '/line/generate/text'            : <IoText size={24} />,
  '/line/generate/image'           : <IoImage size={24} />,
  '/line/generate/rewrite'         : <IoGitBranch size={24} />,
  '/line/generate/schedule'        : <IoCalendar size={24} />,

  '/line/manage/list'            : <IoList size={24} />,
  '/line/manage/status'          : <IoSync size={24} />,

  '/line/analyze/dashboard'       : <IoAnalytics size={24} />,
  '/line/analyze/report'          : <IoDocumentText size={24} />,
  '/line/analyze/feedback'        : <IoChatbubbles size={24} />,

  '/line/input/persona'         : <IoPerson size={24} />,

  /* ───────── 6. Settings ───────── */
  '/settings/account'           : <IoSettings size={24} />,
  '/settings/account'           : <IoPerson size={24} />,
  '/settings/members'           : <IoPeople size={24} />,
  '/settings/billing'           : <IoCash size={24} />,
  '/settings/integrations/wordpress' : <IoLinkSharp size={24} />,
  '/settings/integrations/instagram' : <IoLogoInstagram size={24} />,
  '/settings/integrations/line'      : <IoChat size={24} />,

  /* ───────── 7. Help ───────── */
  '/help/home'                  : <IoHelp size={24} />,
  '/help/getting-started'       : <IoSchool size={24} />,
  '/help/faq'                   : <IoChatbubbles size={24} />,
  '/help/contact'               : <IoMail size={24} />,
  '/help/tutorials'             : <IoSchool size={24} />,
  '/help/api-docs'              : <IoCode size={24} />,
  '/help/release-notes'         : <IoMegaphone size={24} />,
};

function findSelectedMenu(pathname: string) {
  // 1. 親リンクで一致するものを探す
  let menu = groups.flatMap(g => g.links).find(l => pathname === l.href);
  if (menu) return menu;

  // 2. subLinksの中に一致するものがあれば、その親リンクを返す
  menu = groups
    .flatMap(g => g.links)
    .find(l => l.subLinks && l.subLinks.some(section => section.links.some(sub => pathname === sub.href)));
  if (menu) return menu;

  // 3. さらにサブリンクが階層的に深い場合はstartsWithで判定
  menu = groups
    .flatMap(g => g.links)
    .find(l => l.subLinks && l.subLinks.some(section => section.links.some(sub => pathname.startsWith(sub.href))));
  if (menu) return menu;

  // 4. パス階層で判定（/seo/で始まる場合はSEOメニューを返す）
  if (pathname.startsWith('/seo/')) {
    menu = groups.flatMap(g => g.links).find(l => l.href === '/seo/generate/new-article');
    if (menu) return menu;
  }
  
  // 5. 他のプラットフォームも同様に判定
  if (pathname.startsWith('/instagram/')) {
    menu = groups.flatMap(g => g.links).find(l => l.href === '/instagram/home');
    if (menu) return menu;
  }
  
  if (pathname.startsWith('/line/')) {
    menu = groups.flatMap(g => g.links).find(l => l.href === '/line/home');
    if (menu) return menu;
  }

  // 5.5. 会社設定ページの判定
  if (pathname.startsWith('/company-settings/')) {
    menu = groups.flatMap(g => g.links).find(l => l.href === '/company-settings/company');
    if (menu) return menu;
  }

  // 6. 設定ページの判定
  if (pathname.startsWith('/settings/')) {
    menu = groups.flatMap(g => g.links).find(l => l.href === '/settings/account');
    if (menu) return menu;
  }

  // 7. ヘルプページの判定
  if (pathname.startsWith('/help/')) {
    menu = groups.flatMap(g => g.links).find(l => l.href === '/help/home');
    if (menu) return menu;
  }

  return undefined;
}

export default function Sidebar() {
  const pathname = usePathname();
  const selectedMenu = findSelectedMenu(pathname);
  const { isSubSidebarOpen, setIsSubSidebarOpen } = useSidebar();

  return (
    <div className="flex h-[calc(100vh-45px)]">
      {/* Main Sidebar */}
      <aside className="group absolute left-0 top-0 w-[64px] hover:w-[250px] h-full bg-primary text-white transition-all duration-300 ease-in-out z-30">
        <ScrollArea className="h-full py-10">
          <nav className="flex flex-col gap-2">
            {groups.map((g) => (
              <div key={g.title} className="border-b border-white/20 p-[8px]">
                {g.links.map((l) => (
                  <Link
                    key={l.href}
                    href={l.href}
                    className={clsx(
                      'flex items-center p-[8px] rounded-lg text-sm',
                      pathname.startsWith(l.href)
                        ? 'bg-primary text-white hover:bg-primary/80'
                        : 'hover:bg-primary/80'
                    )}
                  >
                    <div className="text-white">
                      {iconMap[l.href]}
                    </div>
                    <span className="opacity-0 group-hover:opacity-100 transition-opacity delay-100 ml-3 text-[15px] text-white font-semibold whitespace-nowrap">
                      {l.label}
                    </span>
                  </Link>
                ))}
              </div>
            ))}
          </nav>
        </ScrollArea>
      </aside>

      {/* Sub Sidebar */}
      <aside className={cn(
        "ml-[64px] h-full bg-white text-black shadow-[10px_0_10px_rgba(0,0,0,0.1)] z-10 transition-all duration-300 ease-in-out",
        isSubSidebarOpen ? "w-[250px]" : "w-[64px]"
      )}>
        <div className={cn("flex flex-col gap-2 p-5 transition-opacity duration-300", !isSubSidebarOpen && "opacity-0 pointer-events-none")}>
          <div className="flex items-center justify-center gap-2">
            {selectedMenu?.imageurl && (
              <div className="relative w-6 h-6">
                <Image 
                  src={selectedMenu.imageurl} 
                  alt={selectedMenu.sublabel || ''} 
                  fill
                  style={{ objectFit: 'contain' }}
                  priority
                />
              </div>
            )}
            <p className="text-lg font-bold whitespace-nowrap text-center">{selectedMenu?.sublabel}</p>
          </div>
        </div>
        
        {/* 縮小時のヘッダー */}
        <div className={cn("flex items-center justify-center pt-4 pb-2 transition-opacity duration-300", isSubSidebarOpen && "opacity-0 pointer-events-none absolute")}>
          {selectedMenu?.imageurl && (
            <div className="relative w-5 h-5">
              <Image 
                src={selectedMenu.imageurl} 
                alt={selectedMenu.sublabel || ''} 
                fill
                style={{ objectFit: 'contain' }}
                priority
              />
            </div>
          )}
        </div>
        <ScrollArea className={cn("h-[calc(100%-80px)] transition-all duration-300", !isSubSidebarOpen && "h-[calc(100%-50px)]")}>
          {selectedMenu?.subLinks?.map((section) => (
            <div key={section.title} className={cn(
              "flex flex-col gap-2 p-[8px]",
              isSubSidebarOpen ? "py-5" : "py-1"
            )}>
              <div className={cn("flex items-center justify-between gap-2", !isSubSidebarOpen && "justify-center")}>
                <p className={cn("font-bold text-primary transition-opacity duration-200", !isSubSidebarOpen && "opacity-0 hidden")}>{section.title}</p>
                <div className={cn('h-[1px] bg-primary flex-1 transition-opacity duration-200', !isSubSidebarOpen && "opacity-0 hidden")}></div>
              </div>
              <div className="flex flex-col">
                {section.links.map((link) => {
                  const isDisabled = link.disabled;
                  const linkContent = (
                    <>
                      <div className={cn(
                        "text-foreground transition-all duration-200",
                        {"text-gray-400": isDisabled},
                        !isSubSidebarOpen && "scale-90"
                      )}>
                        {iconMap[link.href]}
                      </div>
                      <span className={cn(
                        "text-sm whitespace-nowrap text-foreground transition-opacity duration-200 ml-2",
                        !isSubSidebarOpen && "opacity-0 hidden",
                        {"text-gray-400": isDisabled}
                      )}>
                        {link.label}
                      </span>
                      {isDisabled && (
                        <span className={cn(
                          "ml-auto text-xs text-gray-400 bg-gray-200 px-2 py-1 rounded transition-opacity duration-200",
                          !isSubSidebarOpen && "opacity-0 hidden"
                        )}>
                          開発中
                        </span>
                      )}
                    </>
                  );

                  if (isDisabled) {
                    return (
                      <div
                        key={link.href || link.label}
                        className={clsx(
                          "flex items-center gap-2 rounded-lg transition-all duration-200",
                          "opacity-50 cursor-not-allowed",
                          isSubSidebarOpen ? "p-[8px]" : "p-[6px] justify-center mx-1"
                        )}
                      >
                        {linkContent}
                      </div>
                    );
                  }
                  
                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      className={clsx(
                        "flex items-center gap-2 rounded-lg transition-all duration-200",
                        pathname === link.href
                          ? "bg-primary/10 text-primary"
                          : "hover:bg-gray-100 cursor-pointer",
                        isSubSidebarOpen 
                          ? "p-[8px]" 
                          : "p-[6px] justify-center mx-1 hover:bg-primary/5"
                      )}
                    >
                      {linkContent}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </ScrollArea>
        <Button
          onClick={() => setIsSubSidebarOpen(!isSubSidebarOpen)}
          className={cn(
            "absolute bg-primary hover:bg-primary/80 text-white rounded-full flex items-center justify-center z-30 transition-all duration-300",
            isSubSidebarOpen 
              ? "top-4 right-4 h-8 w-8" 
              : "top-4 right-2 h-6 w-6"
          )}
        >
          {isSubSidebarOpen ? <IoChevronBack size={20} /> : <IoChevronForward size={16} />}
        </Button>
      </aside>
    </div>
  );
}

