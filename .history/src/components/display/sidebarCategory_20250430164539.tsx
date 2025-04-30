"use client"

import type { ReactNode } from "react"
import { ChevronDown, Link } from "lucide-react"
import { cn } from "@/lib/utils"

interface SidebarCategoryProps {
  icon: ReactNode
  label: string
  items: { id: string; label: string }[]
  isExpanded: boolean
  isActive: boolean
  onClick: () => void
  isTransitioning: boolean
}

export default function SidebarCategory({
  icon,
  label,
  items,
  isExpanded,
  isActive,
  onClick,
  isTransitioning,
}: SidebarCategoryProps) {
  return (
    <div className="mb-4">
      <button
        className={cn("flex w-full items-center px-4 py-2 hover:bg-gray-100", isActive && "font-medium")}
        onClick={onClick}
      >
        <div className="flex h-6 w-6 items-center justify-center">{icon}</div>
        {isExpanded && !isTransitioning && (
          <>
            <span className="ml-3 flex-1 text-left">{label}</span>
            {items.length > 0 && (
              <ChevronDown className={cn("h-4 w-4 transition-transform", isActive && "rotate-180")} />
            )}
          </>
        )}
      </button>

      {isExpanded && isActive && items.length > 0 && !isTransitioning && (
        <div className="mt-1 space-y-1 pl-10">
          {items.map((item) => (
            <div key={item.id} className="flex items-center py-2 text-sm text-gray-700 hover:text-gray-900">
              {/* <div className="mr-2 h-1.5 w-1.5 rounded-full bg-gray-400"></div> */}
              <span>{item.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
