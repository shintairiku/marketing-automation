import Header from "@/components/display/header";
import Sidebar from "@/components/display/sidebar";
import GenerationProcessPage from "@/features/tools/seo/generate/new-article/display/GenerationProcessPage";

interface PageProps {
  params: Promise<{
    jobId: string;
  }>;
}

export default async function Page({ params }: PageProps) {
  const { jobId } = await params;
  
  return (
    <div className="min-h-screen bg-[#eeeeee]">
      <Header />
      <div className="flex mt-[45px]">
        <div className="fixed left-0 top-[45px] h-[calc(100vh-45px)]">
          <Sidebar />
        </div>
        <main className="flex-1 ml-[314px] p-5">
          <GenerationProcessPage jobId={jobId} />
        </main>
      </div>
    </div>
  );
}