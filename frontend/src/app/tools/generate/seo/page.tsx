"use client"

import { useState } from "react"

import Header from "@/components/display/header"
import Sidebar from "@/components/display/sidebar"
import SeoHeaderTab from "@/components/seo/seoHeaderTab"
import DescriptionIndex from "@/features/tools/generate/seo/description/display/index"
import EditIndex from "@/features/tools/generate/seo/edit/display/index"
import HeadlineIndex from "@/features/tools/generate/seo/headline/display/index"
import PostIndex from "@/features/tools/generate/seo/post/display/index"
import ThemeIndex from "@/features/tools/generate/seo/theme/display/index"
import { SEO_STEPS, type StepInfo } from "@/features/tools/generate/seo/types/seoStep"

export default function SeoPage() {
    const [currentStep, setCurrentStep] = useState<StepInfo>(SEO_STEPS[0]);
    const handleNextStep = () => {
        const currentIndex = SEO_STEPS.findIndex(step => step.id === currentStep.id);
        if (currentIndex < SEO_STEPS.length - 1) {
            setCurrentStep(SEO_STEPS[currentIndex + 1]);
        }
    };

    return (
        <div className="flex flex-col h-screen overflow-hidden">
            <Header />
            <div className="flex flex-1">
                <Sidebar />
                <main className="flex-1 py-5 px-10">
                    <div className="flex flex-col h-full">
                        <div className="p-4">
                            <SeoHeaderTab currentStep={currentStep} onStepChange={setCurrentStep} />
                        </div>
                        <div className="mt-8 flex-1">
                            {currentStep.id === 'theme' && <ThemeIndex onNext={handleNextStep} />}
                            {currentStep.id === 'headline' && <HeadlineIndex onNext={handleNextStep} />}
                            {currentStep.id === 'description' && <DescriptionIndex onNext={handleNextStep} />}
                            {currentStep.id === 'edit' && <EditIndex onNext={handleNextStep} />}
                            {currentStep.id === 'post' && <PostIndex />}
                        </div>
                    </div>
                </main>
            </div>
        </div>
        
    );
}