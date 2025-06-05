"use client"

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const PAGE_SIZE = 20;

// ダミーの SEO 記事データ（20件）
const seoDummyArticles = [
    {
      title: "2025年版・SEOトレンド総まとめ",
      shortdescription: "検索順位を左右する最新アルゴリズムと対策ポイントを網羅的に解説。",
      postdate: "2025-05-29"
    },
    {
      title: "AIライティングで差をつけるコンテンツ制作術",
      shortdescription: "生成AIを活用して効率良く質の高い記事を量産する手法を紹介。",
      postdate: "2025-05-27"
    },
    {
      title: "ゼロクリック検索時代のキーワード戦略",
      shortdescription: "クリックされなくても流入を確保するための新しい指標と対策。",
      postdate: "2025-05-25"
    },
    {
      title: "E-E-A-T強化！専門家監修記事の作り方",
      shortdescription: "権威性と信頼性を高めるためのライター選定と構成のコツ。",
      postdate: "2025-05-22"
    },
    {
      title: "検索意図を読み解く4つのプロセス",
      shortdescription: "ユーザー心理を分析し、CVを高める記事構成パターンを大公開。",
      postdate: "2025-05-20"
    },
    {
      title: "BERT完全対応！自然言語最適化ガイド",
      shortdescription: "文脈理解アルゴリズムに合わせた記事リライトの実践例。",
      postdate: "2025-05-18"
    },
    {
      title: "ローカルSEOで地域No.1を獲得する方法",
      shortdescription: "Googleビジネスプロフィール活用とNAP最適化の最新ベストプラクティス。",
      postdate: "2025-05-15"
    },
    {
      title: "画像検索を制するAltテキスト最適化術",
      shortdescription: "クリック率が劇的に向上する画像メタデータの書き方を解説。",
      postdate: "2025-05-13"
    },
    {
      title: "コアウェブバイタル改善で離脱率30%減",
      shortdescription: "LCP・FID・CLSを高速改善した具体的なサイト事例を紹介。",
      postdate: "2025-05-11"
    },
    {
      title: "被リンクではなく“推薦リンク”を獲得せよ",
      shortdescription: "自然にシェアされるコンテンツ企画とアウトリーチの新常識。",
      postdate: "2025-05-09"
    },
    {
      title: "リライト優先度をAIで自動判定する方法",
      shortdescription: "既存記事の潜在価値をスコアリングし更新効率を最大化。",
      postdate: "2025-05-07"
    },
    {
      title: "SEOとSNSを融合したトラフィック爆増戦略",
      shortdescription: "XとTikTokを活用し検索流入を1.8倍にした事例を徹底解剖。",
      postdate: "2025-05-04"
    },
    {
      title: "音声検索最適化：スキーママークアップ完全攻略",
      shortdescription: "話し言葉クエリに対応したFAQ構造化データの実装手順。",
      postdate: "2025-05-02"
    },
    {
      title: "検索順位が落ちたときのリカバリーチェックリスト",
      shortdescription: "ペナルティ診断から改善施策までのロードマップを公開。",
      postdate: "2025-04-28"
    },
    {
      title: "内部リンク設計で回遊率を倍増させるテクニック",
      shortdescription: "クラスター構造とパンくずリストのベストプラクティス。",
      postdate: "2025-04-24"
    },
    {
      title: "ニッチキーワードで月間1万PVを達成した方法",
      shortdescription: "競合0のブルーオーシャンを発見するリサーチ手法を紹介。",
      postdate: "2025-04-20"
    },
    {
      title: "GA4で見るべきSEO指標トップ5",
      shortdescription: "UAとの違いと設定ミスを防ぐチェックポイントを解説。",
      postdate: "2025-04-17"
    },
    {
      title: "エモーショナルライティングがSEOに効く理由",
      shortdescription: "ユーザー共感を誘うストーリーテリングとCTR改善の関係。",
      postdate: "2025-04-13"
    },
    {
      title: "モバイルファースト時代のAMP終了後対応",
      shortdescription: "AMP廃止後に必要な速度＆UX最適化チェックリスト。",
      postdate: "2025-04-10"
    },
    {
      title: "SEO初心者がやりがちな10の失敗",
      shortdescription: "サイト立ち上げ1年目で陥りやすい落とし穴と回避策を整理。",
      postdate: "2025-04-07"
    },
  {
    title: "クリック率を爆上げするリッチリザルト最適化",
    shortdescription: "HowTo と FAQ スキーマで SERP をジャックする方法を具体例とともに解説。",
    postdate: "2025-04-04"
  },
  {
    title: "サーチコンソール新機能の使いこなしガイド",
    shortdescription: "インデックス除外要因の特定と改善フローを最新 UI で紹介。",
    postdate: "2025-04-02"
  },
  {
    title: "“人を動かす”CTA文言100選",
    shortdescription: "クリックを誘発する心理トリガーとテスト設計のコツを徹底解説。",
    postdate: "2025-03-31"
  },
  {
    title: "国際 SEO：hreflang 設定完全マスター",
    shortdescription: "多言語サイトで重複評価を防ぎつつ地域別検索を制覇する方法。",
    postdate: "2025-03-28"
  },
  {
    title: "グロースループ戦略で自然流入を自走化",
    shortdescription: "UX ➜ エンゲージ ➜ シェア ➜ 被リンク の好循環モデルを分解する。",
    postdate: "2025-03-25"
  },
  {
    title: "コンバージョンにつながる記事構成テンプレート",
    shortdescription: "AB テスト 50 本から抽出した“鉄板レイアウト”を公開。",
    postdate: "2025-03-23"
  },
  {
    title: "YMYL ジャンルで信頼性を勝ち取る 7 つの方法",
    shortdescription: "医療・金融サイトが実践する専門性証明と外部評価獲得施策。",
    postdate: "2025-03-20"
  },
  {
    title: "スニペット最適化でスクロールゼロの勝負に勝つ",
    shortdescription: "タイトル・ディスクリプション AB テスト事例 20 選。",
    postdate: "2025-03-18"
  },
  {
    title: "コピペ率 0% にするリサーチライティング術",
    shortdescription: "一次情報と独自データで差別化する記事制作フロー。",
    postdate: "2025-03-15"
  },
  {
    title: "E-A-T を可視化する著者プロフィールの作り方",
    shortdescription: "権威性・経験・信頼性を強調する記載例とチェックリスト。",
    postdate: "2025-03-13"
  },
  {
    title: "成果につながるコンテンツリフレッシュのタイミング",
    shortdescription: "インプレッション下降を察知する 3 つの指標と対応手順。",
    postdate: "2025-03-10"
  },
  {
    title: "内部ランキング要因：サイト階層最適化完全版",
    shortdescription: "クリック深度とリンクジュースを両立させる構造設計。",
    postdate: "2025-03-08"
  },
  {
    title: "検索意図別ライティングチェックリスト",
    shortdescription: "ナビゲーショナル・トランザクショナル・インフォメーショナル別の書き分け術。",
    postdate: "2025-03-05"
  },
  {
    title: "ビジュアルコンテンツ SEO：SVG & WebP 活用術",
    shortdescription: "軽量化と高解像度を両立する画像フォーマット最前線。",
    postdate: "2025-03-03"
  },
  {
    title: "ロングテール戦略で安定流入を作る方法",
    shortdescription: "月間検索 10 回以下キーワードのボリューム拡張テクニック。",
    postdate: "2025-02-28"
  },
  {
    title: "検索ユーザーのフェーズを見極める KPI 設計",
    shortdescription: "TOFU/MOFU/BOFU を数値で追えるダッシュボード設計例。",
    postdate: "2025-02-25"
  },
  {
    title: "クローラビリティ向上のための XML サイトマップ講座",
    shortdescription: "動的 URL とパラメータを最適に整理するベストプラクティス。",
    postdate: "2025-02-22"
  },
  {
    title: "Google Discover に載るためのコンテンツ要件",
    shortdescription: "ニュースフィード表示を狙って PV を爆増させた成功事例。",
    postdate: "2025-02-20"
  },
  {
    title: "セマンティック SEO：エンティティ設計入門",
    shortdescription: "ナレッジグラフに載せるための関連語と構造化手法。",
    postdate: "2025-02-17"
  },
  {
    title: "“検索しない世代”へのリーチ戦略",
    shortdescription: "Z 世代が情報探索に使う SNS × SEO 融合施策を提案。",
    postdate: "2025-02-15"
  },
  {
    title: "スクロール率 80% を超えた記事デザイン",
    shortdescription: "読了率を測定し改善した UX 改修プロセスを公開。",
    postdate: "2025-02-12"
  },
  {
    title: "データドリブンリライトの自動化手順",
    shortdescription: "Low-Hanging-Fruit を AI が抽出するワークフローを解説。",
    postdate: "2025-02-09"
  },
  {
    title: "SEO KPI が動くまでの平均日数を短縮する方法",
    shortdescription: "インデックススピードを上げる技術＆非技術アプローチ。",
    postdate: "2025-02-07"
  },
  {
    title: "検索ボリューム“0”キーワードでも売上 200%UP",
    shortdescription: "機能単語で獲得した CV 事例を深掘り分析。",
    postdate: "2025-02-04"
  },
  {
    title: "LCP 1.8 秒以下を実現したフロント改善術",
    shortdescription: "画像遅延読み込みとコード分割の実装ステップ。",
    postdate: "2025-02-02"
  },
  {
    title: "パラグラフオーダリングで読了率を倍増",
    shortdescription: "行動経済学モデルを応用した記事レイアウト AB テスト。",
    postdate: "2025-01-30"
  },
  {
    title: "被リンク分析ツール徹底比較 2025",
    shortdescription: "Ahrefs・SEMRush・Majestic の精度とコスパを検証。",
    postdate: "2025-01-28"
  },
  {
    title: "SEO 戦略ロードマップ 90 日プラン",
    shortdescription: "キーワード選定から成果検証までの実行チェックリスト。",
    postdate: "2025-01-25"
  },
  {
    title: "Web アクセシビリティと SEO の交差点",
    shortdescription: "WCAG ガイドライン準拠が検索評価にもたらすメリットを整理。",
    postdate: "2025-01-22"
  },
  {
    title: "オウンドメディアの KPI 計画テンプレート",
    shortdescription: "事業フェーズ別に変動する指標の設計図とダッシュボード例。",
    postdate: "2025-01-20"
  },
  {
    title: "競合分析 × ポジショニングマップで隙間を攻める",
    shortdescription: "SimilarWeb & Keywords Everywhere を組み合わせた調査術。",
    postdate: "2025-01-18"
  },
  {
    title: "フィーチャードスニペットを奪取する段落構成",
    shortdescription: "FAQ 形式と定義パラグラフを使った実装プロセス。",
    postdate: "2025-01-15"
  },
  {
    title: "ユーザー生成コンテンツで被リンクを量産する方法",
    shortdescription: "レビュー・Q&A を活用して自然リンクを得た成功パターン。",
    postdate: "2025-01-13"
  },
  {
    title: "ニュース SEO：Google Top Stories 対策の最前線",
    shortdescription: "AMP 廃止後も表示枠を獲る記者・編集フローを公開。",
    postdate: "2025-01-10"
  },
  {
    title: "低品質コンテンツ判定を回避する内部重複対策",
    shortdescription: "カニバリ防止とカノニカル設定のベストプラクティス。",
    postdate: "2025-01-08"
  },
  {
    title: "ストラクチャーデータ自動生成プラグイン 7 選",
    shortdescription: "WordPress & Headless CMS で使える便利ツールを比較。",
    postdate: "2025-01-05"
  },
  {
    title: "画像生成 AI 時代の著作権リスクと SEO",
    shortdescription: "オリジナリティ担保とライセンス表示の最新ガイドライン。",
    postdate: "2025-01-03"
  },
  {
    title: "逆ピラミッド型ライティングで離脱率を下げる",
    shortdescription: "ファーストビューで結論を伝える構成がもたらす効果を検証。",
    postdate: "2024-12-30"
  },
  {
    title: "サイドバー誘導で回遊率を 40% 改善した方法",
    shortdescription: "関連記事ブロックの配置最適化 A/B テスト事例。",
    postdate: "2024-12-27"
  },
  {
    title: "インタラクティブコンテンツが SEO に効く理由",
    shortdescription: "クイズ・計算ツールで平均滞在時間を 2 倍にした施策。",
    postdate: "2024-12-25"
  }
];

// ダミー用のHTML
export function seoDummyHtml() {
  return `
  <h2 style="font-size:1.5rem;font-weight:bold;margin-bottom:1rem;">ダミー記事タイトル</h2>
  <p>これはダミーのHTMLコンテンツです。<br>記事詳細のプレビューや本文などをここに表示できます。</p>
  <ul style="margin-top:1rem;list-style:disc;padding-left:1.5rem;">
    <li>ポイント1</li>
    <li>ポイント2</li>
    <li>ポイント3</li>
  </ul>
  `;
}


export default function IndexPage() {
  const [page, setPage] = useState(1);
  const [sheetOpen, setSheetOpen] = useState(false);

  // ページごとの記事を取得
  const pagedArticles = seoDummyArticles.slice(
    (page - 1) * PAGE_SIZE,
    page * PAGE_SIZE
  );

  const totalPages = Math.ceil(seoDummyArticles.length / PAGE_SIZE);

  return (
    <div className="space-y-6">
      {/* 上部：ボタン群 */}
      <div className="flex items-center gap-2">
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline">フィルター</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>期間で絞り込む</DialogTitle>
            </DialogHeader>
            <div className="flex flex-col gap-4 py-2">
              <div>
                <label className="block text-sm mb-1">開始日</label>
                <input type="date" className="border rounded px-2 py-1 w-full" />
              </div>
              <div>
                <label className="block text-sm mb-1">終了日</label>
                <input type="date" className="border rounded px-2 py-1 w-full" />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline">クリア</Button>
              <Button>適用</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
        <Button variant="outline">表示設定</Button>
      </div>

      {/* 中部：カードで囲まれたテーブル */}
      <Card className="p-4">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="py-2 px-2">タイトル</TableHead>
              <TableHead className="py-2 px-2">概要</TableHead>
              <TableHead className="py-2 px-2">投稿日</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {pagedArticles.map((article, idx) => (
              <TableRow
                key={idx}
                className="cursor-pointer hover:bg-muted"
                onClick={() => setSheetOpen(true)}
              >
                <TableCell className="py-2 px-2 font-medium">{article.title}</TableCell>
                <TableCell className="py-2 px-2">{article.shortdescription}</TableCell>
                <TableCell className="py-2 px-2">{article.postdate}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* 下部：ページネーション */}
      <div className="flex justify-center items-center gap-2">
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                aria-disabled={page === 1}
                className={page === 1 ? "pointer-events-none opacity-50" : ""}
              />
            </PaginationItem>
            <span>
              {page} / {totalPages}
            </span>
            <PaginationItem>
              <PaginationNext
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                aria-disabled={page === totalPages}
                className={page === totalPages ? "pointer-events-none opacity-50" : ""}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      </div>
      {/* サイドシート（記事プレビュー） */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="right" className="max-w-xl w-full">
          <SheetHeader>
            <SheetTitle>記事プレビュー</SheetTitle>
          </SheetHeader>
          <div className="mt-4" dangerouslySetInnerHTML={{ __html: seoDummyHtml() }} />
          <SheetClose asChild>
            <Button className="mt-6 w-full" variant="outline">
              閉じる
            </Button>
          </SheetClose>
        </SheetContent>
      </Sheet>
    </div>
  );
}
