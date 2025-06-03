'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { groups } from '@/components/constant/route';
import clsx from 'clsx';
import { ScrollArea } from '@/components/ui/scroll-area';
import Image from 'next/image';
import {
  /* Home / Dashboard */
  IoHome, IoNewspaper, IoSettings, IoClipboard, IoCalendar, IoStatsChart,

  /* SEO */
  IoGlobe, IoText, IoList, IoDocumentText, IoPencil, IoCloudUpload,
  IoSync, IoAnalytics, IoChatbubbles, IoPerson,

  /* Instagram */
  IoLogoInstagram, IoPricetag, IoImage, IoSparkles,

  /* LINE */
  IoChatbubbles as IoChat,  /* ←重複を避けるためエイリアス */
  IoGitBranch
} from 'react-icons/io5';

export const iconMap: Record<string, React.ReactElement<{ size?: number }>> = {
  /* ───────── 1. Home (Dashboard) ───────── */
  '/dashboard'                 : <IoHome size={24} />,
  '/dashboard/news'            : <IoNewspaper size={24} />,
  '/dashboard/setting'         : <IoSettings size={24} />,
  '/dashboard/overview'        : <IoClipboard size={24} />,
  '/dashboard/calendar'        : <IoCalendar size={24} />,
  '/dashboard/performance'     : <IoStatsChart size={24} />,

  /* ───────── 2. Generate / SEO ───────── */
  '/generate/seo/home'              : <IoGlobe size={24} />,
  '/generate/seo/new-article'        : <IoText size={24} />,

  '/manage/seo/list'           : <IoList size={24} />,
  '/manage/seo/status'         : <IoSync size={24} />,
  '/manage/seo/schedule'       : <IoCalendar size={24} />,

  '/analyze/seo/dashboard'     : <IoAnalytics size={24} />,
  '/analyze/seo/report'        : <IoDocumentText size={24} />,
  '/analyze/seo/feedback'      : <IoChatbubbles size={24} />,

  '/input/seo/persona'         : <IoPerson size={24} />,

  /* ───────── 3. Generate / Instagram ───────── */
  '/generate/instagram'            : <IoLogoInstagram size={24} />,
  '/generate/instagram/caption'    : <IoText size={24} />,
  '/generate/instagram/hashtags'   : <IoPricetag size={24} />,
  '/generate/instagram/image'      : <IoImage size={24} />,
  '/generate/instagram/rewrite'    : <IoSparkles size={24} />,
  '/generate/instagram/schedule'   : <IoCalendar size={24} />,
  '/generate/instagram/list'       : <IoList size={24} />,
  '/generate/instagram/status'     : <IoSync size={24} />,
  '/generate/instagram/dashboard'  : <IoAnalytics size={24} />,
  '/generate/instagram/report'     : <IoDocumentText size={24} />,
  '/generate/instagram/feedback'   : <IoChatbubbles size={24} />,

  '/generate/instagram/persona'    : <IoPerson size={24} />,

  /* ───────── 4. Generate / LINE ───────── */
  '/generate/line'                 : <IoChat size={24} />,
  '/generate/line/text'            : <IoText size={24} />,
  '/generate/line/image'           : <IoImage size={24} />,
  '/generate/line/rewrite'         : <IoGitBranch size={24} />,
  '/generate/line/schedule'        : <IoCalendar size={24} />,

  '/generate/line/list'            : <IoList size={24} />,
  '/generate/line/status'          : <IoSync size={24} />,

  '/generate/line/dashboard'       : <IoAnalytics size={24} />,
  '/generate/line/report'          : <IoDocumentText size={24} />,
  '/generate/line/feedback'        : <IoChatbubbles size={24} />,

  '/generate/line/persona'         : <IoPerson size={24} />,
};

export default function Sidebar() {
  const pathname = usePathname();
  
  // 現在のパスに基づいて選択されたメニュー項目を取得
  const selectedMenu = groups
    .flatMap(g => g.links)
    .find(l => pathname.startsWith(l.href));

  return (
    <div className="flex h-[calc(100vh-45px)]">
      <aside className="group w-[64px] hover:w-[250px] h-full bg-primary text-white relative transition-all duration-300 ease-in-out z-20">
        <ScrollArea className="h-full">
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
        <div className='absolute right-0 top-0 size-[36px] translate-x-full bg-primary'>
          <div className='size-[36px] bg-white' style={{ clipPath: 'circle(100% at 100% 100%)' }}></div>
        </div>
        <div className='absolute right-0 bottom-0 size-[36px] translate-x-full bg-primary'>
          <div className='size-[36px] bg-white' style={{ clipPath: 'circle(100% at 100% 0%)' }}></div>
        </div>
      </aside>

      <aside className="absolute left-[64px] w-[250px] h-full bg-white text-black shadow-[10px_0_10px_rgba(0,0,0,0.1)] z-10">
        <div className="flex flex-col gap-2 p-5">
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
        <ScrollArea className="h-[calc(100%-80px)]">
          {selectedMenu?.subLinks?.map((section) => (
            <div key={section.title} className="flex flex-col gap-2 p-[8px] py-5">
              <div className="flex items-center justify-between gap-2">
                <p className="font-bold text-primary">{section.title}</p>
                <div className='h-[1px] bg-primary flex-1'></div>
              </div>
              <div className="flex flex-col">
                {section.links.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={clsx(
                      "flex items-center gap-2 p-[8px] rounded-lg",
                      pathname === link.href
                        ? "bg-primary/10 text-primary"
                        : "hover:bg-gray-100"
                    )}
                  >
                    <div className="text-foreground">
                      {iconMap[link.href]}
                    </div>
                    <span className="text-sm text-foreground whitespace-nowrap transition-opacity duration-300 group-hover:opacity-0">
                      {link.label}
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </ScrollArea>
      </aside>
    </div>
  );
}

