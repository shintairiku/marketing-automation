# LiteLLM 版 run_agent_streaming 仕様書（SEO記事執筆専用）

## 1. 目的

SEO記事生成プロセスの **writing_sections** ステップのみ、OpenAI Agents
SDK から **LiteLLM** を利用した実装へ置き換える。ただし **OpenAI の
純正モデル（プレフィックスなしで `gpt-` から始まるもの）は従来の
OpenAI Agents ルートをそのまま使う**。\
外部インターフェースは既存の run_agent_streaming と完全互換とし、呼び
出し側では「関数名を差し替えるだけ」で利用できるようにする。

## 2. 変更概要

-   既存の `run_agent_streaming(...)` は削除せず **そのまま残す**。
-   新たに LiteLLM 用の関数 **`run_agent_streaming_litellm(...)`**
    を追加する。
-   `writing_sections` ステップのみ、この新関数を呼び出す。
-   インターフェース（引数順・型）は既存と完全一致させる。
-   内部で `system` / `user` の **messages 形式** を構築し、LiteLLM
    に渡す。
-   **ただし writing_model が `gpt-` で始まる場合は LiteLLM を経由せず、
    従来の OpenAI Agents ルート（openaiResponses）へフォールバックする。**
-   モデルの切り替えは、.envで行う。
-   他ステップ（outline, research, editing）は変更しない。

------------------------------------------------------------------------

## 3. 新規関数：run_agent_streaming_litellm

### 3.1 シグネチャ（既存と完全同一）

``` python
async def run_agent_streaming_litellm(
    self,
    agent: Agent,
    agent_input: str,
    context: ArticleContext,
    run_config: RunConfig,
    section_index: int,
) -> Any:
```

### 3.2 messages の構築

``` python
system_content = getattr(agent, "instructions", "") or default_section_writer_system_prompt(context)
user_content = agent_input

messages = [
    {"role": "system", "content": system_content},
    {"role": "user", "content": user_content},
]
```

### 3.3 LiteLLM によるストリーミング

``` python
from app.externalapi.litellm_client import stream_chat_completion

accumulated = ""

async for chunk in stream_chat_completion(messages):
    accumulated += chunk

    await self.service.utils.send_server_event(
        context,
        SectionChunkPayload(
            section_index=section_index,
            heading=context.generated_outline.sections[section_index].heading,
            html_content_chunk=chunk,
            is_complete=False,
            is_image_mode=context.image_mode,
        )
    )
```

### 3.4 完了イベント

``` python
await self.service.utils.send_server_event(
    context,
    SectionChunkPayload(
        section_index=section_index,
        heading=context.generated_outline.sections[section_index].heading,
        html_content_chunk="",
        is_complete=True,
        section_complete_content=accumulated,
        is_image_mode=context.image_mode,
    )
)

return accumulated
```

### 3.5 OpenAI モデル向けフォールバック

- LiteLLM 実行前に `settings.writing_model`（もしくは渡されたモデル名）を
  判定し、**プレフィックスなしの `gpt-` で始まる場合は LiteLLM を経由せず
  従来の OpenAI Agents SDK 呼び出し（openaiResponses）を使う。**
- それ以外のモデルは従来どおり LiteLLM を利用する。
- フォールバック先も同じシグネチャとイベント送信経路を共有し、
  「リクエストを送るところだけ」を差し替える最小変更とする。

------------------------------------------------------------------------

## 4. LiteLLM クライアント（externalapi）

### 4.1 配置場所

    backend/app/infrastructure/external_apis/litellm_client.py

### 4.2 実装

``` python
from litellm import acompletion
from typing import AsyncIterator, List, Dict, Any
Message = Dict[str, str]

async def stream_chat_completion(messages: List[Message], **kwargs) -> AsyncIterator[str]:
    response = await acompletion(
        model=settings.writing_model,
        messages=messages,
        max_tokens=32768,  # 従来エージェントの上限に合わせた固定値、温度はプロバイダデフォルト
        stream=True,
        **kwargs,
    )
    async for chunk in response:
        delta = chunk["choices"][0]["delta"].get("content", "")
        if delta:
            yield delta
```

------------------------------------------------------------------------

## 5. 呼び出し側の変更（最小限）

### 5.1 変更前

``` python
agent_output = await self.run_agent_streaming(
    current_agent, agent_input, context, run_config, section_index
)
```

### 5.2 変更後

``` python
agent_output = await self.run_agent_streaming_litellm(
    current_agent, agent_input, context, run_config, section_index
)
```

------------------------------------------------------------------------

## 6. TDD（テスト駆動）

### 6.1 テスト項目

1.  **messages 組み立てテスト**
    -   `agent.instructions` → system\
    -   `agent_input` → user\
    -   LiteLLM クライアントに正しい messages が渡ること。
2.  **ストリーミングテスト**
    -   モックで `["foo ", "bar"]` を返す\
    -   完了時の return が `"foo bar"`\
    -   `send_server_event` がチャンク分＋完了分呼ばれる。
3.  **例外テスト**
    -   LiteLLM が例外を投げた場合、例外をそのまま再送出。
4.  **OpenAI フォールバック判定テスト**
    -   writing_model が `gpt-` で始まるとき LiteLLM が呼ばれず、
        従来の OpenAI Agents 呼び出しを使うこと。

------------------------------------------------------------------------

## 7. 非変更点（重要）

-   **editing ステップは既存の run_agent をそのまま使用**。\
-   他ステップ（research, outline）は一切変更しない。\
-   UI 側のイベント形式（section_chunk /
    section_completed）は既存のまま。\
-   画像モード（image_mode=true）でも本文生成は LiteLLM ストリーミングを使用する。
    - 出力はテキストHTMLのみで、従来の `ArticleSectionWithImages`／`image_placeholders` 保存は行わない。
    - プレースホルダーを使いたい場合はプロンプト側で `[image:...]` などのマーカーを自前で埋め込む。

------------------------------------------------------------------------

## 8. まとめ

-   呼び出し側は「関数名の差し替え」のみで LiteLLM に移行可能。
-   messages 分離（system/user）の要求にも完全対応。
-   writing_model が `gpt-` 始まりなら従来の OpenAI Agents を使用し、
    それ以外は LiteLLM を使う二段構成。
-   editor や他フェーズには影響しない安全設計。
