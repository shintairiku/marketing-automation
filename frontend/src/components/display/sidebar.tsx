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
  '/home'                 : <IoHome size={24} />,
  '/home/dashboard'            : <IoNewspaper size={24} />,
  '/home/news'         : <IoSettings size={24} />,
  '/home/overview'        : <IoClipboard size={24} />,
  '/home/calendar'        : <IoCalendar size={24} />,
  '/home/performance'     : <IoStatsChart size={24} />,

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

  /* ───────── 3. Generate / Instagram ───────── */
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

  /* ───────── 4. Generate / LINE ───────── */
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

  return undefined;
}

export default function Sidebar() {
  const pathname = usePathname();
  const selectedMenu = findSelectedMenu(pathname);

  return (
    <div className="flex h-[calc(100vh-45px)]">
      <aside className="group w-[64px] hover:w-[250px] h-full bg-primary text-white relative transition-all duration-300 ease-in-out z-20">
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

