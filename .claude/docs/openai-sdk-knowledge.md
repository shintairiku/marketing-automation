# OpenAI Responses API / SDK 知見

> **情報ソース**: openai SDK v2.16.0, openai-agents v0.7.0, 実機テスト 2026-02-02

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

## openai-agents v0.7.0 注意点
- `nest_handoff_history` デフォルトが `True`→`False` に変更
- GPT-5.1/5.2 のデフォルト reasoning effort が `'none'` に変更

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
| ブログ生成 | `BLOG_GENERATION_MODEL` | gpt-5.2 |
| 画像生成 | `IMAGEN_MODEL_NAME` | imagen-4.0-generate-preview-06-06 |
| 翻訳 | `reasoning_translate_model` | gpt-5-nano |
