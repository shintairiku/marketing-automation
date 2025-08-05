import { IoInformationCircle } from "react-icons/io5";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

export default function ExplainDialog() {
    return (
        <div className="mb-6 flex justify-center">
            <Dialog>
            <DialogTrigger asChild>
                <Button variant="outline">
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