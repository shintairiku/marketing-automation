import { CaseStudySection } from '@/features/landing/sections/case-study-section';
import { FaqSection } from '@/features/landing/sections/faq-section';
import { FlowSection } from '@/features/landing/sections/flow-section';
import { PricingSection } from '@/features/landing/sections/pricing-section';
import { ProblemSection } from '@/features/landing/sections/problem-section';
import { SolutionSection } from '@/features/landing/sections/solution-section';
import { TopSection } from '@/features/landing/sections/top-section';
import { VideoSection } from '@/features/landing/sections/video-section';
import { WhySeoSection } from '@/features/landing/sections/why-seo-section';

export default function HomePage() {
  return (
    <>
      <TopSection />
      <VideoSection />
      <WhySeoSection />
      <ProblemSection />
      <SolutionSection />
      <CaseStudySection />
      <PricingSection />
      <FlowSection />
      <FaqSection />
    </>
  );
}
