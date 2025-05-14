"use client"

import { useState } from "react";

import CommonTitle from "@/components/seo/commonTitle"

// まだバック繋いでないので仮データ(後で消す)
const headlineDummyData = {
    "title": "芝生の育て方完全ガイド｜初心者でも失敗しない手順とコツ",
    "sections": [
      {
        "title": "芝生を始める前に知っておきたい基礎知識",
        "subsections": [
          "芝生の主な種類と特徴",
          "気候・日当たり・用途別の選び方",
          "天然芝と人工芝のコスト＆メンテ比較"
        ]
      },
      {
        "title": "施工準備編：土づくりと道具のチェックリスト",
        "subsections": [
          "土壌診断と pH 調整のやり方",
          "排水性を高める整地・暗渠対策",
          "初心者でも揃えやすい必須ツール"
        ]
      },
      {
        "title": "張り方別の具体的手順",
        "subsections": [
          "種まき芝の播種ステップ",
          "ロール芝（切り芝）の敷設方法",
          "目土・転圧で定着率を上げるコツ"
        ]
      },
      {
        "title": "日常メンテナンスの基本",
        "subsections": [
          "水やり頻度と時間帯のベストプラクティス",
          "芝刈り高さと刈り込み頻度の目安",
          "施肥・目土入れ・雑草管理の年間サイクル"
        ]
      },
      {
        "title": "季節別ケア：四季を通じて青さを保つ",
        "subsections": [
          "春：更新作業とエアレーション",
          "夏：高温・乾燥対策と病害虫チェック",
          "秋：生育促進と冬越し準備",
          "冬：休眠期のダメージ軽減"
        ]
      },
      {
        "title": "よくあるトラブルと解決策",
        "subsections": [
          "茶色く枯れる・禿げる原因とリカバリー",
          "キノコ・コケの発生対策",
          "害虫＆病気の早期発見と安全な駆除方法"
        ]
      },
      {
        "title": "維持コスト＆時間管理の現実",
        "subsections": [
          "年間スケジュールと作業工数の目安",
          "DIY vs. プロ依頼：費用シミュレーション",
          "作業を楽にするスマート管理アイテム"
        ]
      },
      {
        "title": "まとめ：挫折しないための Q&A と次のステップ",
        "subsections": [
          "初心者が悩みやすい Q&A 集",
          "維持を楽しむコツとモチベーション維持法",
          "さらに映える庭づくりの応用アイデア"
        ]
      }
    ]
  }
  

const characterNumberOptions = [500, 1000, 3000, 5000, 10000, 30000];
export default function ThemeLeftDisplay() {
    const [characterNumberSelected, setCharacterNumberSelected] = useState(characterNumberOptions[0]);
    return (
        <div className="flex-1 flex flex-col gap-10 h-full min-h-0">
            {/* キーワード入力 */}
            <div className="flex-1 h-full flex flex-col min-h-0">
                <CommonTitle title="生成した記事の最終確認" />
                <div className="flex flex-col gap-2 bg-gray-50 rounded-md p-5 mt-5 overflow-y-auto h-full">
                    {headlineDummyData.sections.map((section, idx) => (
                        <div key={idx}>
                            <h3 className="text-lg font-bold">{section.title}</h3>
                            <ul className="list-disc pl-5">
                                {section.subsections.map((subsection, subIdx) => (
                                    <li key={subIdx} className="text-sm">{subsection}</li>
                                ))}
                            </ul>
                        </div>
                    ))}
                </div>
            </div>
            {/* 文字数入力 */}
            <div>
                <CommonTitle title="生成したい文字数の確認" />
                <div className="flex gap-2 mt-5">
                    {characterNumberOptions.map((num, idx) => (
                        <button key={num} className={`flex-1 flex items-center justify-center w-10 h-10 rounded-full font-bold text-lg transition ${characterNumberSelected === num ? "bg-pink-100 text-black" : "bg-gray-50 text-black"} shadow-sm z-10 `}
                            onClick={() => setCharacterNumberSelected(num)}
                        >
                            {num}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    )
}