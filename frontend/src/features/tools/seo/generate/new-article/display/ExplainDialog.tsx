import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { IoInformationCircle } from "react-icons/io5";

export default function ExplainDialog() {
    return (
        <div className="mb-6 grid grid-cols-3 gap-2">
            <Dialog>
                <DialogTrigger asChild>
                    <Button variant="outline" className="w-full">
                    <IoInformationCircle className="w-4 h-4 mr-2" />
                    使い方・機能説明
                    </Button>
                </DialogTrigger>
                <DialogContent>
                    <DialogHeader>
                    <DialogTitle>SEOタイトル生成の使い方</DialogTitle>
                    <DialogDescription>
                        効果的なSEOタイトルを生成するための手順をご確認ください。
                    </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 text-sm">
                    <div className="space-y-2">
                        <h4 className="font-medium">1. SEOワードの入力</h4>
                        <p className="text-gray-600">「リーチしたいSEOワード」を入力してください。これが必須項目です。</p>
                    </div>
                    <div className="space-y-2">
                        <h4 className="font-medium">2. 生成設定</h4>
                        <p className="text-gray-600">タイトル数（1〜64件）とペルソナを選択してください。</p>
                    </div>
                    <div className="space-y-2">
                        <h4 className="font-medium">3. タイトル生成</h4>
                        <p className="text-gray-600">「タイトルを生成」ボタンで複数の候補を生成します。</p>
                    </div>
                    <div className="space-y-2">
                        <h4 className="font-medium">4. タイトル選択・編集</h4>
                        <p className="text-gray-600">生成されたタイトルから好みのものを選択し、必要に応じて「自分で修正」で編集できます。</p>
                    </div>
                    <div className="space-y-2">
                        <h4 className="font-medium">5. 次のステップ</h4>
                        <p className="text-gray-600">「Next.../見出し作成」で次のステップに進みます。</p>
                    </div>
                    </div>
                </DialogContent>
            </Dialog>
            <Dialog>
            <DialogTrigger asChild>
                <Button variant="outline" className="w-full">
                <IoInformationCircle className="w-4 h-4 mr-2" />
                SEOとは？
                </Button>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                <DialogTitle>SEOとは？</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 text-sm">
                <p>後でSEOの説明を入れる</p>
                </div>
            </DialogContent>
            </Dialog>
            <Dialog>
            <DialogTrigger asChild>
                <Button variant="outline" className="w-full">
                <IoInformationCircle className="w-4 h-4 mr-2" />
                説明動画
                </Button>
            </DialogTrigger>
            <DialogContent>
                <DialogHeader>
                <DialogTitle>SEOタイトル生成の使い方説明動画</DialogTitle>
                </DialogHeader>
                <div className="space-y-4 text-sm">
                <p>後で動画を挿入</p>
                </div>
            </DialogContent>
            </Dialog>
        </div>
    )
}