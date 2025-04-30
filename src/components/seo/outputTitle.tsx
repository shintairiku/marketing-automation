// 生成中→生成完了→生成失敗　
// とかの制御のためにコンポーネントに分けています

// あとコピペの制御もここで一括でできたらいいね


import { Copy } from "lucide-react"

export default function OutputTitle() {
    return (
        <div className="gap-5 items-center">
            <div className="flex items-center justify-between gap-2">
                <h1 className="text-base font-bold">生成完了</h1>
                <button className="px-4 py-2">
                    <Copy className="h-5 w-5" />
                </button>
            </div>
            <div className="w-full h-1 rounded-full bg-gray-200"></div>
        </div>
    )
}