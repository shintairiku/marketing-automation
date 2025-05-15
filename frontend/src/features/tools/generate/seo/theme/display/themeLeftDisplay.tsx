"use client"

import { useState } from "react";

import CommonTitle from "@/components/seo/commonTitle"


const themeNumberOptions = [1, 4, 8, 16, 32, 64];
const personaOptions = ["学生", "主婦", "サラリーマン", "フリーランス", "ビジネスマン", "その他"];

export default function ThemeLeftDisplay() {

    const [numberSelected, setNumberSelected] = useState(themeNumberOptions[0]);
    const [personaSelected, setPersonaSelected] = useState(personaOptions[0]);
    return (
        <div className="flex flex-col gap-10">
            {/* キーワード入力 */}
            <div>
                <CommonTitle title="テーマ作成" />
                <input 
                type="text" 
                className="w-full h-10 bg-[#f9f9f9] rounded-md p-2 mt-5" 
                placeholder="SEOで狙いたいキーワードを入力してください" />
            </div>
            {/* テーマの数の選択 */}
            <div>
                <CommonTitle title="テーマの数" />
                <div className="flex items-center justify-between w-full mt-5 relative">
                    <div className="absolute left-1/2 top-1/2 -translate-y-1/2 -translate-x-1/2 w-full h-1 bg-[#f9f9f9] z-0" />
                    {themeNumberOptions.map((num, idx) => (
                        <button key={num} className={` flex items-center justify-center w-10 h-10 rounded-full font-bold text-lg transition ${numberSelected === num ? "bg-pink-100 text-black" : "bg-gray-50 text-black"} shadow-sm z-10 `}
                            onClick={() => setNumberSelected(num)}
                        >
                            {num}
                        </button>
                    ))}
                </div>
            </div>
            {/* ペルソナの選択 */}
            <div>
                <CommonTitle title="リーチしたいペルソナ" />
                <div className="grid grid-cols-3 gap-5 bg-[#f9f9f9] rounded-md p-5 mt-5">
                    {personaOptions.map((option, idx) => (
                        <button key={idx} className={`flex flex-col items-center justify-center gap-2 min-w-20 h-10 rounded-md font-bold text-sm transition ${personaSelected === option ? "bg-pink-100 text-black" : "bg-gray-50 text-black"} shadow-sm z-10 `}
                            onClick={() => setPersonaSelected(option)}
                        >
                            {/* <img src={`/images/persona/${option}.png`} alt={option} className="w-10 h-10" /> */}
                            <p>{option}</p>
                        </button>
                    ))}
                </div>
            </div>
        </div>
    )
}