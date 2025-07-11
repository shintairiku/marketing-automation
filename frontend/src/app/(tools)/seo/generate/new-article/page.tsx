import Header from "@/components/display/header";
import Sidebar from "@/components/display/sidebar";
import NewArticleStartPage from "@/features/tools/seo/generate/new-article/display/NewArticleStartPage";

export default function Page() {
  return (
    <div className="min-h-screen bg-[#eeeeee]">
      <Header />
      <div className="flex mt-[45px]">
        <div className="fixed left-0 top-[45px] h-[calc(100vh-45px)]">
          <Sidebar />
        </div>
        <main className="flex-1 ml-[314px] p-5">
          <NewArticleStartPage />
        </main>
      </div>
    </div>
  );
} 