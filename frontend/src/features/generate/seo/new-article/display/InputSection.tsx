"use client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { IoRefresh, IoSparkles } from "react-icons/io5";

export default function InputSection() {
    const titleCountOptions = [1, 4, 8, 16, 32, 64];
    return (
      <div className="w-full flex flex-col min-h-0 max-h-full overflow-hidden">
        <div className="grid grid-cols-2 gap-5 mb-6">
          {/* Card1: SEOワード */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">リーチしたいSEOワード</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Input
                  id="seo-keyword"
                  placeholder="例: Webマーケティング"
                />
              </div>
            </CardContent>
          </Card>

          {/* Card2: タイトル数 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">生成タイトル数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="space-y-3">
                  <Slider
                    id="title-count"
                    min={0}
                    max={5}
                    step={1}
                    className="w-full"
                  />
                  <div className="flex justify-between text-sm text-gray-500">
                    {titleCountOptions.map((count, index) => (
                      <span
                        key={count}
                      >
                        {count}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Card3: ペルソナ */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">ペルソナ設定</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Select>
                  <SelectTrigger>
                    <SelectValue placeholder="ペルソナを選択" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="beginner">初心者・入門者</SelectItem>
                    <SelectItem value="intermediate">中級者・実践者</SelectItem>
                    <SelectItem value="expert">上級者・専門家</SelectItem>
                    <SelectItem value="business">ビジネス担当者</SelectItem>
                    <SelectItem value="student">学生・研究者</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>
        </div>
        {/* ボタン（最下部に配置） */}
        <div className="mt-auto flex justify-between">
          <Button
            className="w-full"
            size="lg"
          >
            記事生成を開始
          </Button>
        </div>
      </div>
    )
}