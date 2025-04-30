import SeoHeaderTab from "@/components/seo/seoHeaderTab"
import EditLeftDisplay from "./editLeftDisplay"
import EditRightDisplay from "./editRightDisplay"
import SeoNextButton from "@/components/seo/button/seoNextButton"
import SeoRetryGenerateButton from "@/feature/tools/generate/seo/seoComponents/seoRetryGenerateButton"
import SeoGenerateButton from "@/feature/tools/generate/seo/seoComponents/seoGenerateButton"
// indexページは「配置」することを意識
// 細かいUIは呼び出して使う

// テーマを生成するボタンを押したら、テーマを生成する
// Nextボタンを押したら見出し作成に移る

interface EditDisplayProps {
    onNext: () => void;
}

export default function EditDisplay({ onNext }: EditDisplayProps) {
    return (
        <div className="flex flex-col h-full gap-10">
            <div className="flex gap-10 h-full">
                <div className="w-1/2 flex flex-col gap-10 justify-between h-[calc(100vh-200px)]">
                    <div className="flex-1 min-h-0">
                        <EditLeftDisplay />
                    </div>
                    <div className="flex justify-end gap-2">
                        <SeoGenerateButton generateButtonText="テーマを生成する" />
                    </div>
                </div>  
                <div className="w-1/2 flex flex-col gap-10 justify-between h-[calc(100vh-200px)]">
                    <div className="flex-1 min-h-0">
                        <EditRightDisplay />
                    </div>
                    <div className="flex justify-end gap-2">
                        <SeoRetryGenerateButton />
                        <button className="bg-gray-200 text-black px-4 py-2 rounded-md">
                            自分で修正
                        </button>
                        <SeoNextButton nextButtonText="投稿" onClick={onNext} />
                    </div>
                </div>
            </div>
        </div>
    )
}