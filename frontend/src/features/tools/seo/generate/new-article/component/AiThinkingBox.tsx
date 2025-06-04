import { Card, CardContent } from "@/components/ui/card";

export default function AiThinkingBox() {
    return (
      <div className="flex flex-col items-center gap-2 my-10">
        <div className="w-1 h-20 rounded-full bg-primary"></div>
          <Card
            className=" min-w-[600px] max-w-[800px] mx-auto"
          >
            <CardContent className="p-6 flex-1 overflow-hidden">
              <div className="h-full flex items-center justify-center text-gray-500">
                <div className="text-center">
                  <p>思考過程が表示される</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <div className="w-1 h-20 rounded-full bg-primary"></div>
          <Card
            className=" min-w-[600px] max-w-[800px] mx-auto"
          >
            <CardContent className="p-6 flex-1 overflow-hidden">
              <div className="h-full flex items-center justify-center text-gray-500">
                <div className="text-center">
                  <p>思考過程が表示される</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <div className="w-1 h-20 rounded-full bg-primary"></div>
      </div>
    )
}