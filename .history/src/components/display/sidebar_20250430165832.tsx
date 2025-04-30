"use client"

import { useState, useEffect } from "react"
import { Clock, Settings, BarChart3, Database } from "lucide-react"
import { cn } from "@/utils/tailwind-utils"
import SidebarCategory from "@/components/display/sidebarCategory"

interface SidebarProps {
  isExpanded: boolean
  setIsExpanded: (value: boolean) => void
}

export default function Sidebar({ isExpanded, setIsExpanded }: SidebarProps) {
  const [activeCategories, setActiveCategories] = useState<string[]>([])
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
    }
  }, [isExpanded])

  const handleCategoryClick = (categoryId: string) => {
    setActiveCategories(prev => {
      if (prev.includes(categoryId)) {
        return prev.filter(id => id !== categoryId)
      } else {
        return [...prev, categoryId]
      }
    })
  }

  // 日本語のメニューデータ
  const menuData = [
    {
      id: "dashboard",
      icon: <Clock className="h-5 w-5" />,
      label: "ダッシュボード",
      items: [],
    },
    {
      id: "generation",
      icon: <Settings className="h-5 w-5" />,
      label: "生成機能",
      items: [
        { id: "seo", label: "SEO記事生成" },
        { id: "ig-caption", label: "IGキャプション生成" },
        { id: "ig-content", label: "IGコンテンツ生成" },
        { id: "line", label: "LINE配信生成" },
      ],
    },
    {
      id: "analytics",
      icon: <BarChart3 className="h-5 w-5" />,
      label: "分析機能",
      items: [
        { id: "blog", label: "ブログ" },
        { id: "instagram", label: "インスタグラム" },
        { id: "line-analytics", label: "LINE" },
        { id: "ads", label: "広告" },
      ],
    },
    {
      id: "input",
      icon: <Database className="h-5 w-5" />,
      label: "入力スペース",
      items: [
        { id: "persona", label: "ペルソナの設定" },
        { id: "blog-domain", label: "ブログドメインの設定" },
        { id: "instagram-template", label: "インスタグラムテンプレート" },
        { id: "line-template", label: "LINEテンプレート" },
      ],
    },
  ]

  return (
    <div
      className={cn(
        "relative flex h-full flex-col shadow-lg bg-[#F9F9F9] transition-all duration-300 ease-in-out",
        isExpanded ? "w-[220px]" : "w-[60px]",
      )}
      onMouseEnter={() => setIsExpanded(true)}
      onMouseLeave={() => setIsExpanded(false)}
    >
      <div className="flex flex-col py-2">
        {menuData.map((category) => (
          <SidebarCategory
            key={category.id}
            icon={category.icon}
            label={category.label}
            items={category.items}
            isExpanded={isExpanded}
            isActive={activeCategories.includes(category.id)}
            onClick={() => handleCategoryClick(category.id)}
            isTransitioning={isTransitioning}
          />
        ))}
      </div>
    </div>
  )
}
