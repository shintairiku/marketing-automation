# OpenAI Responses API / SDK 知見

> **情報ソース**: openai SDK v2.25.0, openai-agents v0.10.5, 実機テスト 2026-02-02

## SDK 型定義の確認方法
```bash
source backend/.env 2>/dev/null; export OPENAI_API_KEY; cd backend && uv run python -c "
from openai import AsyncOpenAI
import inspect
sig = inspect.signature(AsyncOpenAI().responses.create)
for name, param in sig.parameters.items():
    print(f'  {name}: {param.annotation}')
"
```

## `responses.create()` 主要パラメータ
```python
client.responses.create(
    model="gpt-5-nano",
    instructions="...",
    input="...",
    reasoning={"effort": "minimal", "summary": None},
    text={"verbosity": "low"},
    store=False,
)
```

## reasoning.effort 別トークン消費 (gpt-5-nano)
| effort | reasoning_tokens | output_tokens | total_tokens |
|--------|-----------------|--------------|-------------|
| `"low"` | 192 | 284 | 338 |
| `"minimal"` | 0 | 57 | 111 |

翻訳など単純タスクは `"minimal"` が最適。reasoning_tokens がゼロで 1/3 のコスト。

## Prompt Caching 重要知見
| 項目 | 詳細 |
|------|------|
| `instructions` vs `developer` | キャッシュ的に同一。同じプレフィックスを共有 |
| gpt-5.2 自動キャッシュ | **されない**。`prompt_cache_key` 必須 |
| gpt-5-mini 自動キャッシュ | される。`prompt_cache_key` なしでも95%+ |
| `prompt_cache_key` 隔離 | 異なるキー = 異なるバケット。内容同一でもキャッシュミス |
| 最小閾値 | 1024 トークン以下はキャッシュされない |
| 増分単位 | 128 トークン刻みでプレフィックス一致 |
| 料金割引 | gpt-5系: 90%, gpt-4.1系: 75%, gpt-4o系: 50% |
| `prompt_cache_key` 上限 | 64文字。超えると 400 エラー |

## Agents SDK ストリーミング知見
- `RunItemStreamEvent`: tool_called, tool_output, reasoning 等
- `RawResponsesStreamEvent`: response.completed, response.output_item.done 等
- `ResponseFunctionWebSearch` は `name` 属性がなく `type` ("web_search_call") で識別
- `ToolCallOutputItem.raw_item` が dict の場合があり `getattr` ではなく dict アクセスが必要
- `to_input_list()` は元入力 + 新規アイテム。`previous_response_id` 運用時は履歴マージ必要

## openai-agents v0.10.4/v0.10.5 注意点
- v0.7.0: `nest_handoff_history` デフォルトが `True`→`False` に変更
- v0.7.0: GPT-5.1/5.2 のデフォルト reasoning effort が `'none'` に変更
- v0.10.4: Python 3.9 サポート終了（3.10+ 必須）
- v0.10.4: WebSocket トランスポートサポート追加
- v0.10.4: HostedMCPTool, ShellTool, ApplyPatchTool, ImageGenerationTool, CodeInterpreterTool 追加
- v0.10.4: `ModelSettings.verbosity` フィールド追加（`Literal['low', 'medium', 'high'] | None`）
- v0.10.5: MultiProvider prefix modes、MCP エラーをクラッシュではなく構造化エラー結果として返すように改善
- v0.10.5: `ToolOutputTrimmer` 追加（`agents.extensions`）— 古いターンの大きなツール出力を自動トリミング
- v0.10.5: `FunctionTool` にタイムアウト設定 (`timeout_seconds`, `timeout_behavior`) 追加
- v0.10.5: トレースメタデータをスパンに伝搬するよう修正
- v0.10.5: **Tool Search/Namespace は依然未対応** — `Tool` union に ToolSearchTool/NamespaceTool がない
- v0.10.5: `FunctionTool` に `defer_loading` フィールドなし、`_convert_tool()` も未対応

## ToolOutputTrimmer（v0.10.5 新機能）
```python
from agents.extensions import ToolOutputTrimmer
from agents import RunConfig

trimmer = ToolOutputTrimmer(
    recent_turns=2,        # 直近2ターンは対象外
    max_output_chars=800,  # 800文字超のツール出力をトリミング
    preview_chars=300,     # 先頭300文字をプレビューとして残す
)
run_config = RunConfig(call_model_input_filter=trimmer)
```
- `CallModelInputFilter` プロトコルを実装。`RunConfig.call_model_input_filter` に渡す
- 古いターンの `function_call_output` を `[Trimmed: tool_name output — N chars → M char preview]` に置換
- 元データは変更しない（shallow copy）
- Blog AI で WordPress ツール出力（数千文字）のトークン削減に有効

## GPT-5.4 新機能 (2026-03-05 移行)

| 機能 | 詳細 |
|------|------|
| コンテキスト | 1M+ トークン（GPT-5.2の400Kから大幅拡張） |
| 料金 | input=$2.50/M, cached=$0.25/M (90%割引), output=$15.00/M |
| 長文料金 | 入力272K超で2倍料金（input=$5.00/M, cached=$0.50/M） |
| コンパクション | `context_management=[{"type":"compaction","compact_threshold":400000}]` でサーバーサイド自動圧縮 |
| allowed_tools | `tool_choice={"type":"allowed_tools","mode":"auto","tools":[...]}` でフェーズ別ツール制限 |
| ツール検索 (API) | `{"type":"tool_search"}` + `defer_loading=True` で関連ツールのみロード（47%トークン削減） |
| ツール検索 (SDK) | **openai-agents v0.10.4 では未対応**。SDK の Tool union に含まれない |
| namespace | `{"type":"namespace","name":"...","tools":[...]}` でツールグループ化 |
| reasoning effort | none(デフォルト), low, medium, high, xhigh |
| verbosity | text.verbosity: low/medium/high で出力長制御 |
| `prompt_cache_key` | GPT-5.4でも必須（自動キャッシュなし） |
| コンパクションとキャッシュ | compaction後もtools+instructionsプレフィックスはキャッシュ対象 |

## Tool Search API 詳細（openai SDK v2.25.0）

```python
# Responses API レベルでの Tool Search 使用方法
# ※ openai-agents SDK v0.10.4 では未対応
client.responses.create(
    model="gpt-5.4",
    tools=[
        {"type": "tool_search"},  # ツール検索を有効化
        {"type": "function", "name": "tool_a", "defer_loading": True, ...},
        {"type": "function", "name": "tool_b", "defer_loading": True, ...},
    ],
    ...
)
```

- `defer_loading=True`: 初期ロードせず、ツール検索で必要になった時のみロード
- 効果: ツール数が多い場合に入力トークンを最大47%削減
- **Agents SDK 制限**: `Agent.tools` は `list[Tool]` 型で、ToolSearchTool/NamespaceTool が union に含まれない。`FunctionTool` dataclass にも `defer_loading` フィールドがない。`_convert_tool()` は `defer_loading` を出力しない。将来の agents SDK アップデートで対応予定

## AI Models Configuration
| 用途 | 環境変数 | デフォルト値 |
|------|---------|------------|
| リサーチ | `RESEARCH_MODEL` | gpt-5-mini |
| 執筆 | `WRITING_MODEL` | gpt-4o-mini |
| アウトライン | `OUTLINE_MODEL` | WRITING_MODEL |
| 編集 | `EDITING_MODEL` | gpt-4o-mini |
| SERP分析 | `SERP_ANALYSIS_MODEL` | RESEARCH_MODEL |
| Agents SDK | `MODEL_FOR_AGENTS` | gpt-4o-mini |
| AI記事編集 | `ARTICLE_EDIT_AGENT_MODEL` | gpt-5-mini |
| AIコンテンツ生成 | `AI_CONTENT_GENERATION_MODEL` | gpt-5-mini |
| ブログ生成 | `BLOG_GENERATION_MODEL` | gpt-5.4 |
| 画像生成 | `IMAGEN_MODEL_NAME` | imagen-4.0-generate-preview-06-06 |
| 翻訳 | `reasoning_translate_model` | gpt-5-nano |
