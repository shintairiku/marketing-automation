import OutputTitle from "@/components/common/outputTitle"

// まだバック繋いでないので仮データ(後で消す)



export default function ThemeRightDisplay() {
    return (
        <div className="flex-1 min-h-0 flex flex-col gap-2 h-full bg-gray-50 rounded-md p-5">
            <OutputTitle />
            <div className="flex-1 flex flex-col gap-1 overflow-y-auto h-full">
                <p>編集するテーマ</p>
            </div>
        </div>
    )
}