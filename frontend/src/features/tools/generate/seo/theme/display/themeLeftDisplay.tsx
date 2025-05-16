"use client"

import { useState } from "react";

import CommonTitle from "@/components/seo/commonTitle";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

const themeNumberOptions = [1, 3, 5];
const personaOptions = ["学生", "主婦", "サラリーマン", "フリーランス", "ビジネスマン", "その他"];

export default function ThemeLeftDisplay() {
    const [keywords, setKeywords] = useState("");
    const [targetLength, setTargetLength] = useState<number | string>("");
    const [numThemeProposals, setNumThemeProposals] = useState(themeNumberOptions[1]);
    const [numResearchQueries, setNumResearchQueries] = useState<number | string>(5);
    const [personaSelected, setPersonaSelected] = useState(personaOptions[0]);
    const [companyName, setCompanyName] = useState("");
    const [companyDescription, setCompanyDescription] = useState("");
    const [companyStyleGuide, setCompanyStyleGuide] = useState("");

    return (
        <div className="flex flex-col gap-8">
            {/* キーワード入力 */}
            <div>
                <CommonTitle title="テーマ作成" />
                <Input 
                    type="text" 
                    value={keywords}
                    onChange={(e) => setKeywords(e.target.value)}
                    className="w-full h-10 bg-[#f9f9f9] rounded-md p-2 mt-3"
                    placeholder="SEOで狙いたいキーワードをカンマ区切りで入力 (例: 札幌, 注文住宅, 自然素材)" 
                />
            </div>

            <div className="grid grid-cols-2 gap-6">
                {/* テーマの数の選択 */}
                <div>
                    <CommonTitle title="テーマ提案数" />
                    <div className="flex items-center justify-between w-full mt-3 relative">
                        <div className="absolute left-1/2 top-1/2 -translate-y-1/2 -translate-x-1/2 w-full h-1 bg-gray-200 z-0" />
                        {themeNumberOptions.map((num) => (
                            <button 
                                key={num} 
                                className={`flex items-center justify-center w-10 h-10 rounded-full font-bold text-lg transition ${numThemeProposals === num ? "bg-pink-100 text-black" : "bg-gray-50 text-black"} shadow-sm z-10 `}
                                onClick={() => setNumThemeProposals(num)}
                            >
                                {num}
                            </button>
                        ))}
                    </div>
                </div>

                {/* リサーチクエリ数 */}
                <div>
                    <Label htmlFor="numResearchQueries" className="text-base font-semibold">リサーチクエリ数</Label>
                    <Input 
                        id="numResearchQueries"
                        type="number" 
                        value={numResearchQueries}
                        onChange={(e) => setNumResearchQueries(e.target.value === '' ? '' : parseInt(e.target.value, 10))}
                        className="w-full h-10 bg-[#f9f9f9] rounded-md p-2 mt-1"
                        placeholder="例: 5"
                        min={1}
                    />
                </div>
            </div>

            {/* 目標文字数 */}
            <div>
                <Label htmlFor="targetLength" className="text-base font-semibold">目標文字数 (任意)</Label>
                <Input 
                    id="targetLength"
                    type="number" 
                    value={targetLength}
                    onChange={(e) => setTargetLength(e.target.value === '' ? '' : parseInt(e.target.value, 10))}
                    className="w-full h-10 bg-[#f9f9f9] rounded-md p-2 mt-1"
                    placeholder="例: 3000"
                />
            </div>
            
            {/* ペルソナの選択 */}
            <div>
                <CommonTitle title="リーチしたいペルソナ (任意)" />
                <div className="grid grid-cols-3 gap-4 bg-[#f9f9f9] rounded-md p-4 mt-3">
                    {personaOptions.map((option) => (
                        <button 
                            key={option} 
                            className={`flex flex-col items-center justify-center gap-1 min-w-20 h-10 rounded-md font-bold text-xs transition ${personaSelected === option ? "bg-pink-100 text-black" : "bg-gray-50 text-black"} shadow-sm z-10 `}
                            onClick={() => setPersonaSelected(option)}
                        >
                            <p>{option}</p>
                        </button>
                    ))}
                </div>
            </div>

            {/* 企業情報 (アコーディオンなどで隠しても良い) */}
            <div className="space-y-4 pt-4 border-t border-gray-200">
                <h3 className="text-lg font-semibold text-gray-700">企業情報 (任意)</h3>
                <div>
                    <Label htmlFor="companyName">企業名</Label>
                    <Input 
                        id="companyName" 
                        type="text" 
                        value={companyName}
                        onChange={(e) => setCompanyName(e.target.value)}
                        className="w-full h-10 bg-[#f9f9f9] rounded-md p-2 mt-1"
                        placeholder="例: 株式会社ナチュラルホームズ札幌"
                    />
                </div>
                <div>
                    <Label htmlFor="companyDescription">企業概要</Label>
                    <Textarea 
                        id="companyDescription"
                        value={companyDescription}
                        onChange={(e) => setCompanyDescription(e.target.value)}
                        className="w-full min-h-[80px] bg-[#f9f9f9] rounded-md p-2 mt-1"
                        placeholder="例: 札幌を拠点に、自然素材を活かした健康で快適な注文住宅を提供しています。"
                    />
                </div>
                <div>
                    <Label htmlFor="companyStyleGuide">文体・トンマナガイド</Label>
                    <Textarea 
                        id="companyStyleGuide"
                        value={companyStyleGuide}
                        onChange={(e) => setCompanyStyleGuide(e.target.value)}
                        className="w-full min-h-[80px] bg-[#f9f9f9] rounded-md p-2 mt-1"
                        placeholder="例: 専門用語を避け、温かみのある丁寧語（ですます調）で。"
                    />
                </div>
            </div>
        </div>
    )
}