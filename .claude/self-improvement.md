# Self-Improvement Log (自己改善ログ)

> This file consolidates all self-improvement entries from CLAUDE.md into a single chronologically-sorted reference.
> These are lessons learned from mistakes, inefficiencies, and judgment errors pointed out by the user, recorded to prevent repeating the same mistakes.
>
> Source: `/home/als0028/study/shintairiku/marketing-automation/CLAUDE.md`

---

## 2026-02-01

- **Next.js キャッシュ問題**: フォント変更後に `.next` キャッシュが古いビルドを参照し `montserrat is not defined` エラーが発生。ファイル内容は正しかったが `.next` 削除+再起動が必要だった。コード変更後にランタイムエラーが出た場合は、まずキャッシュクリアを確認すべき。
- **Stripe 設計の初期実装ミス**: 個人と組織で別々の Stripe Customer を作成する設計は、Stripe 公式の推奨に反していた。日割りクレジットが別 Customer に滞留し実質機能しない問題があった。**外部 API 連携の設計時は、必ず公式ドキュメントの推奨パターンを先に調査すべき。**
- **Stripe `pending_if_incomplete` の制限見落とし**: `payment_behavior: 'pending_if_incomplete'` と `metadata` を同時に渡して `StripeInvalidRequestError` が発生。**Stripe APIパラメータの組み合わせ制限は公式ドキュメント (pending-updates-reference) で事前に確認すべき。**
- **環境変数フォールバック不足**: `NEXT_PUBLIC_APP_URL` 未設定で Portal の `return_url` が空文字列になりStripeエラー。**環境変数を使うURLは必ずフォールバック値を設定すべき。**
- **即時決済のUX問題**: アップグレードボタン押下で即座に決済が走る実装は、ユーザーに確認の余地がなかった。**課金を伴うアクションは必ず確認ステップを挟むべき。** `invoices.createPreview()` でプレビューを見せてから実行する設計が適切。
- **ビルドコマンド**: フロントエンドのビルドは `bun run build` を使う。`npx next build` ではなく。`.next` キャッシュの削除は通常不要（ルートグループ変更時等の特殊ケースのみ）。
- **記憶の更新忘れ**: 作業完了後は必ず CLAUDE.md を更新する。ユーザーに言われる前に自主的に行うべき。
- **tailwind-merge v3 非互換**: `tailwind-merge` v3 は Tailwind CSS v4 専用。Tailwind CSS v3 プロジェクトでは v2.6.x を使うこと。`bg-gradient-to-*` 等の競合解決が壊れる。**メジャーバージョンアップ時は、同じエコシステム内の他パッケージとの互換性も必ず確認すべき。**
- **openai-agents 0.7.0 注意点**: `nest_handoff_history` デフォルトが `True`→`False` に変更。ハンドオフ使用時は明示的に `True` を渡す必要がある可能性。GPT-5.1/5.2 のデフォルト reasoning effort が `'none'` に変更されたためブログ生成品質に影響する可能性あり（要テスト）。
- **ハードコード問題の見落とし**: プラン管理機能の設計時、最初の調査が浅く `plan_tier_id` が5箇所でハードコードされている問題を見逃した。ユーザーに「ちゃんとデータの整合性とれてる？」と指摘されて初めて深い調査を実施。**新機能の設計時は、関連する全データフロー（Webhook → DB → API → UI）を最初に網羅的に調査すべき。**
- **Supabase 型定義未生成による連鎖的ビルドエラー**: `plan_tiers`, `usage_tracking` テーブルが型に含まれていないため、`(supabase as any)` キャストが大量に必要になった。**新テーブル追加後は早期に `bun run generate-types` を実行し、型安全性を確保すべき。**
- **使用量表示の調査不足**: ユーザーに「使用量が全く表示されていない」と指摘されるまで、新規サブスクリプション時に `usage_tracking` が作成されない問題に気づかなかった。最初は特権ユーザーの条件のみ疑ったが、実際は全ユーザーに影響する根本的なデータフロー問題だった。**機能を実装したら、新規ユーザーが初めて使うフロー（契約直後の状態）を必ず検証すべき。UPDATE のみで INSERT がないのは典型的な初期化漏れ。**

---

## 2026-02-02

- **記憶の即時更新**: コード変更を完了した直後に CLAUDE.md を更新せず、ユーザーに「また記憶してないでしょ」と指摘された。**変更を加えたら、次のユーザー応答の前に必ず CLAUDE.md を更新する。これは最優先の義務。**
- **Framer Motion `transition` の `exit` キー**: `transition={{ exit: { duration: 0.35 } }}` は型エラー。正しくは `exit={{ ..., transition: { duration: 0.35 } }}` — exit prop 内に transition を入れる。ビルドで初めて気付くのではなく、書く時点で型を意識すべき。
- **`bun run build` を使う**: ユーザーに指摘されたとおり、`npx next build` ではなく `bun run build` を使用すること。

---

## 2026-02-10

- **再検証の重要性**: 実装完了後のユーザー再検証要求で、`useArticles.ts` と `admin/plans/page.tsx` に `USE_PROXY` パターンが欠けているバグを発見した。最初の実装時にサーバーサイドAPI Routes (9ファイル) のみに注力し、クライアントサイドhooksの直接fetch呼び出しを見落としていた。**サーバーサイド→バックエンド通信だけでなく、ブラウザ→バックエンド通信パスも全て確認すべき。**
- **FastAPI末尾スラッシュ + Cloud Run scheme 変換の複合問題**: `frontend/src/app/api/proxy/[...path]/route.ts` の `ensureTrailingSlash()` が `/blog/sites` を `/blog/sites/` に変換し、FastAPI (`redirect_slashes=True`) が 307 で `/blog/sites` へ戻す。さらに Cloud Run の `Location` が `http://...run.app/...` になり、プロキシがそれを手動追従すると Cloud Run 側で 302/307 が連鎖する。**手動リダイレクト追従を使う場合は、(1) 末尾スラッシュ強制をしない、(2) `Location` が `http://` でも `https://` に正規化する、の両方を実施すべき。**
- **リダイレクト処理の不完全実装**: これまでの実装は「1回だけ追従」だったため、Cloud Run の多段リダイレクト（FastAPI 307 + Cloud Run 302）で取りこぼしが起きた。**手動追従ロジックは最初から最大ホップ数を持つループ実装にするべき。**

---

## 2026-02-18

- **記憶の即時更新（再び）**: コード変更後、ユーザーに「CLAUDE.mdだけ更新しといてね」と言われた。変更完了→コミット前のCLAUDE.md更新を忘れるパターンが繰り返されている。**コミットメッセージを書く前に必ずCLAUDE.mdを更新するルーチンを確立すべき。**
- **pg_dumpベースのベースライン生成は複数パスが必要**: 最初のフィルタリングで行単位→statement残骸が残る→statement単位で再パース、という3段階が必要だった。**最初からstatement単位パーサーで処理すべきだった。**
- **Supabase接続のIPv6問題 (WSL2)**: `db.xxx.supabase.co` はIPv6で解決されるがWSL2はIPv6非対応。pooler (`aws-0-*.pooler.supabase.com`) はIPv4だがリージョン不一致で `Tenant not found`。**WSL2環境ではREST API経由が最も確実。**

---

## 2026-02-19

- **Supabase CLIの既知バグを事前調査すべきだった**: `99-roles.sql` エラーに対して、config.toml修正→Docker掃除→ボリューム削除と試行錯誤を繰り返したが、最初からGitHub Issuesを検索すべきだった。**ツールのエラーが不可解な場合は、まずGitHub Issuesで同一エラーメッセージを検索する。**
- **PowerShell と WSL2 の Docker 共有の罠**: `docker system prune -a --volumes -f` をPowerShellで実行しても、WSL2側のSupabaseコンテナ/ボリュームが残る場合がある。**Docker操作はWSL2側で統一すべき。**

---

## 2026-02-20

- **クラウドサンドボックスでの `bun install` 忘れ**: サンドボックス環境では `node_modules` が存在しない。ユーザーに「毎回ビルドエラー起きてる」と指摘された。**サンドボックスでは作業開始時に必ず `bun install` を実行すること。**
- **プッシュ前のlint/build検証忘れ**: ローカルCLIでは実行していたが、サンドボックスでは省略していた。**環境に関係なく、プッシュ前に `bun run lint` + `bun run build` を必ず実行すること。**
- **`next/font/google` のビルド時ネットワーク依存**: Google Fonts に依存する `next/font/google` はネットワーク制限環境（CI、サンドボックス等）でビルドが失敗する。**`@fontsource-variable` でセルフホストすればビルド時の外部依存を排除できる。**

---

## 2026-02-21

- **Webhook → API の実行順序を考慮すべきだった**: Clerk Webhook が `user.created` で `status: 'none'` のレコードを先に作成するため、Status API の「レコード未存在時のみ」のフリープラン作成ロジックが発火しなかった。**外部サービスの Webhook とアプリ内 API の実行順序・競合を設計時に必ず考慮すべき。特に「レコードが存在しない場合のみ INSERT」のパターンは、別の経路で先に INSERT されるケースを見落としやすい。**
