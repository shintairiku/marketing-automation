"use client"

import PageTabs from "@/components/display/pageTabs"
import type { TabOption } from "@/features/tools/generate/seo/types/seoStep"
import { SEO_STEPS, type StepInfo } from "@/features/tools/generate/seo/types/seoStep"

const tabOptions: TabOption[] = [
  { label: "テーマ作成", value: "theme" },
  { label: "見出し作成", value: "headline" },
  { label: "記事作成", value: "description" },
  { label: "記事修正", value: "edit" },
  { label: "記事投稿", value: "post" },
]

interface SeoHeaderTabProps {
  currentStep: StepInfo;
  onStepChange: (step: StepInfo) => void;
}

export default function SeoHeaderTab({ currentStep, onStepChange }: SeoHeaderTabProps) {
  return (
    <PageTabs 
      options={tabOptions} 
      value={currentStep.id} 
      onChange={(value) => {
        const newStep = SEO_STEPS.find(step => step.id === value);
        if (newStep) onStepChange(newStep);
      }} 
    />
  )
}