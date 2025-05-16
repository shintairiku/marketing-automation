"use client"

import { ReactNode,useEffect, useState } from "react"
import { BarChart3, ChevronRight,Clock, Database, Settings } from "lucide-react"

import SidebarCategory from "@/components/display/sidebarCategory"
import { cn } from "@/utils/tailwind-utils"

interface SidebarProps {
  className?: string;
  isExpanded: boolean
  setIsExpanded: (value: boolean) => void
}

// アイコンコンポーネントの型定義
interface IconProps {
  className?: string;
}

// 各メニューアイテムの型定義
interface MenuItem {
  id: string;
  icon: ReactNode; // ReactNode を使用して柔軟性を確保
  label: string;
  items: SubMenuItem[];
  href?: string; // トップレベルのリンク用
}

interface SubMenuItem {
  id: string;
  label: string;
  href?: string; // サブアイテムのリンク用
}

export default function Sidebar({ className, isExpanded, setIsExpanded }: SidebarProps) {
  // 日本語のメニューデータとアイコンの割り当て
  const menuData: MenuItem[] = [
    {
      id: "dashboard",
      icon: <Clock className="h-5 w-5" />,
      label: "ダッシュボード",
      items: [],
      href: "/dashboard", // ダッシュボードへの直接リンク
    },
    {
      id: "generation",
      icon: <Settings className="h-5 w-5" />,
      label: "生成機能",
      items: [
        { id: "seo", label: "SEO記事生成", href: "/tools/generate/seo" },
        { id: "ig-caption", label: "IGキャプション生成", href: "/tools/generate/ig-caption" },
        { id: "ig-content", label: "IGコンテンツ生成", href: "/tools/generate/ig-content" },
        { id: "line", label: "LINE配信生成", href: "/tools/generate/line" },
      ],
    },
    {
      id: "analytics",
      icon: <BarChart3 className="h-5 w-5" />,
      label: "分析機能",
      items: [
        { id: "blog-analytics", label: "ブログ", href: "/analytics/blog" },
        { id: "instagram-analytics", label: "インスタグラム", href: "/analytics/instagram" },
        { id: "line-analytics", label: "LINE", href: "/analytics/line" },
        { id: "ads-analytics", label: "広告", href: "/analytics/ads" },
      ],
    },
    {
      id: "input-space",
      icon: <Database className="h-5 w-5" />,
      label: "入力スペース",
      items: [
        { id: "persona-settings", label: "ペルソナの設定", href: "/input-space/persona" },
        { id: "blog-domain-settings", label: "ブログドメインの設定", href: "/input-space/blog-domain" },
        { id: "instagram-template-settings", label: "インスタグラムテンプレート", href: "/input-space/instagram-template" },
        { id: "line-template-settings", label: "LINEテンプレート", href: "/input-space/line-template" },
      ],
    },
  ];

  const [activeCategories, setActiveCategories] = useState<string[]>(menuData.filter(category => category.items.length > 0).map(category => category.id));
  // activeSubItem は選択されたサブメニューアイテムのIDを保持します。
  // 例: 'seo', 'ig-caption' など
  const [activeSubItem, setActiveSubItem] = useState<string | null>(null);
  const [isTransitioning, setIsTransitioning] = useState(false)

  useEffect(() => {
    if (isExpanded) {
      setIsTransitioning(true)
      const timer = setTimeout(() => {
        setIsTransitioning(false)
      }, 300) // アニメーション時間と同じ
      return () => clearTimeout(timer)
    } else {
      setIsTransitioning(false)
      // サイドバーが閉じられたらアクティブなカテゴリもリセット（デザインによる）
      // setActiveCategories([]);
    }
  }, [isExpanded])

  const handleCategoryClick = (categoryId: string, href?: string) => {
    if (href) { // トップレベルのアイテムが直接リンクを持つ場合
      // router.push(href); // Next.jsのルーターを使用する場合
      console.log(`Navigating to ${href}`);
      setActiveCategories([categoryId]); // クリックされたカテゴリをアクティブにする
      setActiveSubItem(null); // サブアイテムの選択は解除
      return;
    }

    setActiveCategories(prev => {
      if (prev.includes(categoryId)) {
        return prev.filter(id => id !== categoryId) // カテゴリを閉じる
      } else {
        // 他のカテゴリが展開されている場合、それを閉じて新しいカテゴリのみ展開する（アコーディオン動作）
        return [categoryId] // カテゴリを開く
      }
    })
    setActiveSubItem(null); // カテゴリ変更時はサブアイテムの選択を解除
  }

  const handleSubItemClick = (subItemId: string, href?: string) => {
    if (href) {
      // router.push(href); // Next.jsのルーターを使用する場合
      console.log(`Navigating to ${href}`);
    }
    setActiveSubItem(subItemId);
    // サブアイテムがクリックされたときに親カテゴリもアクティブにする
    const parentCategory = menuData.find(category => category.items.some(item => item.id === subItemId));
    if (parentCategory && !activeCategories.includes(parentCategory.id)) {
      setActiveCategories(prev => [...prev, parentCategory.id]);
    }
  };

  return (
    <div
      className={cn(
        "relative flex h-full flex-col bg-sidebar-bg shadow-md transition-all duration-300 ease-in-out",
        isExpanded ? "w-[250px]" : "w-[70px]", // 幅を少し調整
        className // 渡された className を適用
      )}
      onMouseEnter={() => setIsExpanded(true)}
      onMouseLeave={() => setIsExpanded(false)}
    >
      <nav className="flex-grow overflow-y-auto py-4">
        {menuData.map((category) => (
          <SidebarCategory
            key={category.id}
            icon={category.icon}
            label={category.label}
            items={category.items}
            isExpanded={isExpanded}
            isCategoryActive={activeCategories.includes(category.id)}
            activeSubItem={activeSubItem}
            onCategoryClick={() => handleCategoryClick(category.id, category.href)}
            onSubItemClick={handleSubItemClick}
            isTransitioning={isTransitioning}
            hasSubItems={category.items.length > 0}
            href={category.href}
          />
        ))}
      </nav>
      {/* フッターや追加情報などが必要な場合はここに */}
    </div>
  )
}
