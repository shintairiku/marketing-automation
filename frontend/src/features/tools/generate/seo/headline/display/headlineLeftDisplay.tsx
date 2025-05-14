"use client"

import { useState } from "react";

import CommonTitle from "@/components/seo/commonTitle"
// まだバック繋いでないので仮データ(後で消す)
const themeDummyTitles = [
    "芝生の育て方完全ガイド｜初心者でも失敗しない手順とコツ",
    "自宅の庭に最適な芝生の種類を徹底比較！気候・日当たり別おすすめ一覧",
      "芝生の張り替え費用を節約する方法｜DIYと業者依頼の相場を解説",
      "春の芝生メンテナンスチェックリスト｜新芽を元気に伸ばす秘訣",
      "芝生の水やりタイミングはいつ？季節別ベストプラクティス",
      "害虫に強い芝生の選び方＆防除アイデア10選",
      "芝生の目土入れでふかふかに！失敗しない土選びと撒き方",
      "芝生のエアレーション徹底解説｜道具・頻度・効果をまとめて紹介",
      "冬枯れ芝生を青く戻す！寒冷地でもできるリカバリーテクニック",
      "ペットと暮らす家に最適な芝生の種類とお手入れポイント",
      "芝生にキノコが生える理由と安全な対処法",
      "初心者必見！ロール芝生と種まき芝生のメリット・デメリット比較",
      "芝生が茶色くなる原因トップ5と即効リカバリー方法",
      "おしゃれな芝生エッジングアイデア8選｜庭デザインを格上げ",
      "芝生用自動散水システム導入のメリットと費用比較",
      "マンションのベランダでもOK！人工芝と天然芝の使い分けガイド",
      "芝生の雑草対策まとめ｜薬剤・手取り・防草シートの効果を検証",
      "ゴルフグリーン並みに整える！芝刈り高さと頻度のベストバランス",
      "雨の日に芝生の作業はNG？天候別メンテナンス注意点",
      "芝生の種まきカレンダー｜地域別・気温別の最適時期",
      "芝生の目砂に使えるおすすめ資材とコスト比較",
      "おしゃれガーデンライトで映える夜の芝生コーデ術",
      "子どもが遊んでも痛まない強耐久芝生ランキングTOP7",
      "芝生におすすめの肥料成分と与えるタイミング完全マップ",
      "初心者がやりがちな芝生NG行動10選と改善策",
      "芝生のコアリング後に必ず行うべき5つのステップ",
      "高麗芝 vs. 西洋芝｜特長・価格・メンテナンスの違いを徹底比較",
      "芝生の転圧って必要？ローラーの選び方と作業手順",
      "芝生の水はけを劇的改善！暗渠排水DIY講座",
      "芝生の張り替え時期を見極めるチェックポイント8つ",
      "芝生と相性抜群！ロックガーデンを組み合わせた施工アイデア",
      "芝生育成アプリを使ったスマート管理の始め方",
    "狭小スペースでも映える！ミニガーデン芝生活用事例10選"
]

const characterNumberOptions = [500, 1000, 3000, 5000, 10000, 30000];
export default function ThemeLeftDisplay() {
    const [characterNumberSelected, setCharacterNumberSelected] = useState(characterNumberOptions[0]);
    return (
        <div className="flex-1 flex flex-col gap-10 h-full min-h-0">
            {/* キーワード入力 */}
            <div className="flex-1 h-full flex flex-col min-h-0">
                <CommonTitle title="生成したい記事タイトルを選択" />
                <div className="flex flex-col gap-2 bg-gray-50 rounded-md p-5 mt-5 overflow-y-auto h-full">
                    {themeDummyTitles.map((title, idx) => (
                        <div key={idx} className="text-sm font-bold flex items-center gap-2">
                            <input type="radio" name="theme" value={title} />
                            {title}
                        </div>
                    ))}
                </div>
            </div>
            {/* 文字数入力 */}
            <div>
                <CommonTitle title="生成したい文字数を選択" />
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