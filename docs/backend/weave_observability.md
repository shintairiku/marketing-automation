# Weave Observability & Evaluation Guide

本ドキュメントでは、最新の W&B **Weave** を OpenAI Agents SDK 製の SEO 記事生成フローに組み込み、計測・評価・実験を 1 クリックで回す手順をまとめます。

---

## 1. トレーシングの有効化

1. `.env`（またはデプロイ環境）に以下を追記します。

   ```env
   WEAVE_ENABLED=true
   WEAVE_PROJECT_NAME=seo-article-generation
   WEAVE_ENTITY=<your-wandb-entity>
   WANDB_API_KEY=<wandb api key>  # 未設定なら WEAVE_API_KEY でも可
   ```

2. `backend/app/core/observability/weave_integration.py` が `weave.init()` を呼び出し、`WeaveTracingProcessor` を OpenAI Agents SDK の trace processor へ追加します。OpenAI Traces を無効化せず、同じイベントを Weave 側にもストリームできます。

3. `ArticleGenerationService` → `GenerationFlowManager` で `safe_trace_context()` をラップし、`ArticleContext.observability["weave"]` に `trace_url`, `trace_id`, `project_url` を保存します。Supabase Realtime 側からも `article_context.observability` 経由で参照可能です。

---

## 2. フロントエンドでの可視化

* `frontend/src/hooks/useArticleGenerationRealtime.ts` が `article_context.observability.weave` を取り込み、`GenerationState.observability` に保持します。
* `CompactGenerationFlow`（リアルタイム進捗 UI）に「Weave Trace」ボタンを追加。`trace_url` が存在すれば 1 クリックで該当トレースを Weave UI で開けます。

---

## 3. 評価セットアップ (`backend/app/evals`)

| ファイル | 役割 |
| --- | --- |
| `datasets.py` | 難易度別のキーワード＋ペルソナ入力例を定義 |
| `scorers.py` | `length_budget_score` などのプログラム系評価 + `IntentCoverageJudge`（LLM-as-judge） |
| `model.py` | `ArticleFlowModel(weave.Model)` が既存フローを 1 API にラップ |
| `run_eval.py` | `weave.Evaluation` を CLI から実行するエントリーポイント |

### 実行例

```bash
cd backend
uv run python -m app.evals.run_eval \
  --project seo-article-generation \
  --variant prompt-v2 \
  --limit 3
```

実行すると Weave Evaluations UI にリーダーボードが生成され、各 Run のトレースツリーへドリルダウンできます。Scorer は追加・差し替え自由です。

---

## 4. オートパイロット設定

評価やバッチ実行時にユーザー操作を省くため、`ArticleContext.auto_decision_mode=True` を指定すると以下が自動化されます。

* ペルソナ / テーマの最初の候補を自動選択
* アウトライン承認やリサーチプラン承認を自動で `approved=True`
* `disable_realtime_events=True` を併用すると Supabase RPC/イベントを発火せず、Weave トレースだけを収集可能

この設定は通常プロダクション環境では **False** のままにしてください。

---

## 5. 参考リンク

* [Weave × OpenAI Agents SDK Integration](https://docs.wandb.ai/weave/guides/integrations/openai_agents)
* [Weave Tracing Quickstart](https://docs.wandb.ai/weave/guides/tracking/tracing)
* [Weave Evaluations & Playground](https://docs.wandb.ai/weave/guides/core-types/evaluations)

---

以上で Weave を “計測・評価・実験” の中核に組み込み、SEO 記事生成フローを数値で改善できるようになります。
