"use client"

import Link from 'next/link'; // Next.jsのLinkコンポーネントをインポート
import { ChevronDown } from "lucide-react"
import type { ReactNode } from "react"

import { cn } from "@/utils/tailwind-utils"

interface SubMenuItem {
  id: string;
  label: string;
  href?: string;
}

interface SidebarCategoryProps {
  icon: ReactNode
  label: string
  items: SubMenuItem[]
  isExpanded: boolean // サイドバー全体が展開されているか
  isCategoryActive: boolean // このカテゴリがアクティブ（展開されている）か
  activeSubItem: string | null; // 現在アクティブなサブアイテムのID
  onCategoryClick: () => void
  onSubItemClick: (subItemId: string, href?: string) => void;
  isTransitioning: boolean
  hasSubItems: boolean;
  href?: string; // カテゴリ自体がリンクを持つ場合
}

export default function SidebarCategory({
  icon,
  label,
  items,
  isExpanded,
  isCategoryActive,
  activeSubItem,
  onCategoryClick,
  onSubItemClick,
  isTransitioning,
  hasSubItems,
  href,
}: SidebarCategoryProps) {
  const renderCategoryItem = () => (
    <button
      className={cn(
        "flex w-full items-center px-4 py-3 text-sm transition-colors duration-150 ease-in-out relative",
        "hover:bg-gray-100", // ホバー時の背景色を少し濃く
        isCategoryActive && !hasSubItems ? "text-custom-orange bg-custom-orange-light font-semibold" : "text-sidebar-text-muted",
        isCategoryActive && !hasSubItems && "border-r-4 border-custom-orange" // アクティブなトップレベル項目に右ボーダー
      )}
      onClick={onCategoryClick}
    >
      <div className={cn(
        "flex h-6 w-6 items-center justify-center mr-3 shrink-0",
        isCategoryActive && !hasSubItems ? "text-custom-orange" : "text-sidebar-icon-muted"
      )}>
        {icon}
      </div>
      {isExpanded && !isTransitioning && (
        <>
          <span className="flex-1 text-left truncate">{label}</span>
          {hasSubItems && (
            <ChevronDown
              className={cn(
                "h-4 w-4 transition-transform duration-200",
                isCategoryActive && "rotate-180"
              )}
            />
          )}
        </>
      )}
    </button>
  );

  return (
    <div className="mb-1 border-b border-sidebar-border last:border-b-0">
      {href && !hasSubItems ? ( // カテゴリ自体がリンクで、サブメニューがない場合
        <Link href={href} passHref legacyBehavior>
          <a onClick={(e) => { e.preventDefault(); onCategoryClick(); window.location.href = href; }}>
            {renderCategoryItem()}
          </a>
        </Link>
      ) : (
        renderCategoryItem()
      )}

      {isExpanded && isCategoryActive && hasSubItems && !isTransitioning && (
        <div className="mt-1 mb-2 space-y-1 pl-8 pr-2 bg-white"> {/* サブメニューの背景を白に */}
          {items.map((item) => (
            <Link key={item.id} href={item.href || "#"} passHref legacyBehavior>
              <a
                onClick={(e) => {
                  e.preventDefault(); // Next Link のデフォルト挙動を一旦抑制
                  onSubItemClick(item.id, item.href);
                  if (item.href) {
                    window.location.href = item.href; // 強制的にページ遷移
                  }
                }}
                className={cn(
                  "flex items-center py-2 px-3 text-xs rounded-md transition-colors duration-150 ease-in-out",
                  "hover:bg-gray-100",
                  activeSubItem === item.id ? "text-custom-orange font-semibold" : "text-sidebar-text-muted"
                )}
              >
                <span className="mr-2 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-gray-400 group-hover:bg-custom-orange"></span>
                <span className="truncate">{item.label}</span>
              </a>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
