# -*- coding: utf-8 -*-
"""
Gradio ベースのデバッグ/実験用コンソール。
ENABLE_DEBUG_CONSOLE=true で main.py からマウントされます。
外部依存: gradio (pip install gradio)
"""
import json
import uuid
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from app.domains.seo_article.schemas import GenerateArticleRequest
from app.domains.seo_article.services.generation_service import ArticleGenerationService

try:
    import gradio as gr
except ImportError as e:  # pragma: no cover - import guard
    raise RuntimeError("gradio がインストールされていません。`pip install gradio` を実行してください。") from e


def _start_one(service: ArticleGenerationService, req_dict: Dict[str, Any], user_id: str, org_id: Optional[str]) -> Dict[str, str]:
    """1件だけ生成を開始し、process_id/task_idを返す"""
    request_model = GenerateArticleRequest(**req_dict)
    process_id = str(uuid.uuid4())
    coro = service.background_task_manager.start_generation_process(  # type: ignore
        process_id=process_id,
        user_id=user_id,
        organization_id=org_id,
        request_data=request_model,
    )
    import asyncio
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # Gradio はスレッドで実行されるため、実行中ループにスレッドセーフに投げる
        task_id = asyncio.run_coroutine_threadsafe(coro, loop).result()
    else:
        task_id = loop.run_until_complete(coro)
    return {"process_id": process_id, "task_id": task_id}


def _run(
    service: ArticleGenerationService,
    req_json: str,
    overrides_json: str,
    count: int,
    user_id: str,
    org_id: str,
) -> str:
    try:
        req_dict = json.loads(req_json or "{}")
    except json.JSONDecodeError as e:
        return f"❌ request JSON が不正です: {e}"
    try:
        ov = json.loads(overrides_json) if overrides_json else {}
    except json.JSONDecodeError as e:
        return f"❌ overrides JSON が不正です: {e}"

    if ov:
        req_dict["runtime_overrides"] = ov

    try:
        _ = GenerateArticleRequest(**req_dict)
    except ValidationError as e:
        return f"❌ GenerateArticleRequest バリデーションエラー: {e}"

    results: List[Dict[str, str]] = []
    for _i in range(count):
        try:
            results.append(_start_one(service, req_dict, user_id or "debug-user", org_id or None))
        except Exception as e:  # pragma: no cover - runtime guard
            return f"❌ 実行中にエラー: {e}"

    return json.dumps({"runs": results}, ensure_ascii=False, indent=2)


def build_demo(service: Optional[ArticleGenerationService] = None):
    """Gradio Blocks を組み立てて返す"""
    svc = service or ArticleGenerationService()

    with gr.Blocks(title="Agent Debug Console", analytics_enabled=False) as demo:
        gr.Markdown("# Agent Debug Console (Gradio)\n- GenerateArticleRequest を入力して実行\n- runtime_overrides でモデル/温度/プロンプトパッチを上書き\n- auto_mode=true 推奨")

        with gr.Row():
            req = gr.Code(
                label="GenerateArticleRequest (JSON)",
                value=json.dumps(
                    {
                        "initial_keywords": ["札幌", "注文住宅"],
                        "target_age_group": "30代",
                        "num_theme_proposals": 2,
                        "num_research_queries": 2,
                        "num_persona_examples": 2,
                        "auto_mode": True,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                language="json",
                lines=12,
            )
            ov = gr.Code(
                label="runtime_overrides (JSON)",
                value=json.dumps({"global": {"model": "gpt-5.1-mini", "temperature": 0.4}}, ensure_ascii=False, indent=2),
                language="json",
                lines=12,
            )

        with gr.Row():
            count = gr.Slider(label="count", minimum=1, maximum=50, value=1, step=1)
            user_id = gr.Textbox(label="user_id", value="debug-user")
            org_id = gr.Textbox(label="organization_id (任意)", value="")

        run_btn = gr.Button("Run")
        out = gr.Code(label="結果 / エラー", language="json")

        run_btn.click(
            fn=lambda r, o, c, u, g: _run(svc, r, o, int(c), u, g),
            inputs=[req, ov, count, user_id, org_id],
            outputs=out,
        )

    return demo
