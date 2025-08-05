import GenerationProcessPage from "@/features/tools/seo/generate/new-article/display/GenerationProcessPage";

interface PageProps {
  params: Promise<{
    jobId: string;
  }>;
}

export default async function Page({ params }: PageProps) {
  const { jobId } = await params;
  
  return <GenerationProcessPage jobId={jobId} />;
}