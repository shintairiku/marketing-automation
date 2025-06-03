import Sidebar from "@/components/display/sidebar";
import Header from "@/components/display/header";
import IndexPage from "@/features/generate/seo/new-article/display/indexPage";

export default function Page() {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="flex mt-[45px]">
        <div className="fixed left-0 top-[45px] h-[calc(100vh-45px)]">
          <Sidebar />
        </div>
        <main className="flex-1 ml-[314px] p-5">
          <IndexPage />
        </main>
      </div>
    </div>
  );
} 