# -*- coding: utf-8 -*-
"""
デバッグ/実験用の軽量コンソールと API
- 単一HTML（/debug/console）
- エージェント定義の一覧（/debug/agents）
- オーバーライド付き記事生成の起動（/debug/run）
"""
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.domains.seo_article.schemas import GenerateArticleRequest
from app.domains.seo_article.services.generation_service import ArticleGenerationService
from app.domains.seo_article.agents import definitions as agent_defs

DEBUG_ENABLED = os.getenv("ENABLE_DEBUG_CONSOLE", "").lower() == "true"

router = APIRouter()

# 単一サービスインスタンス（軽量用途）
_article_service = ArticleGenerationService()


class DebugRunPayload(BaseModel):
    """デバッグ実行用リクエスト"""
    request: GenerateArticleRequest = Field(..., description="通常のGenerateArticleRequest。auto_mode=True推奨。")
    count: int = Field(1, ge=1, le=50, description="同一設定で何本実行するか")
    concurrency: int = Field(1, ge=1, le=10, description="並列実行数（簡易版、現状は順次実行）")
    user_id: Optional[str] = Field(default="debug-user", description="紐づけるユーザーID（デフォルトはダミー）")
    organization_id: Optional[str] = Field(default=None, description="組織ID（必要な場合のみ）")
    overrides: Optional[Dict[str, Any]] = Field(default=None, description="runtime_overrides の糖衣シンタックス。指定時 request.runtime_overrides を上書き")


def _ensure_enabled():
    if not DEBUG_ENABLED:
        raise HTTPException(status_code=404, detail="Debug console is disabled. Set ENABLE_DEBUG_CONSOLE=true to enable.")


@router.get("/console-html", response_class=HTMLResponse, include_in_schema=False)
async def debug_console_html():
    _ensure_enabled()
    html = """
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <title>Debug Console</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; margin: 24px; line-height: 1.6; }
    textarea { width: 100%; min-height: 160px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { border: 1px solid #ddd; padding: 6px 8px; font-size: 12px; }
    th { background: #f7f7f7; }
    button { padding: 8px 12px; }
  </style>
</head>
<body>
  <h1>Agent Debug Console</h1>
  <div class="grid">
    <div>
      <h2>GenerateArticleRequest</h2>
      <textarea id="request">{ "initial_keywords": ["札幌","注文住宅"], "target_age_group": "30代", "num_theme_proposals": 2, "num_research_queries": 2, "num_persona_examples": 2, "auto_mode": true }</textarea>
    </div>
    <div>
      <h2>Overrides (runtime_overrides)</h2>
      <textarea id="overrides">{ "global": { "model": "gpt-5.1-mini", "temperature": 0.4 } }</textarea>
    </div>
  </div>
  <div style="margin-top:12px;">
    count: <input id="count" type="number" value="1" min="1" max="50" style="width:80px;">
    concurrency: <input id="concurrency" type="number" value="1" min="1" max="10" style="width:80px;">
    <button id="run">Run</button>
    <button id="loadAgents">Load agents</button>
  </div>
  <pre id="log" style="background:#f5f5f5; padding:12px; min-height:120px;"></pre>
  <table id="agentTable"></table>

  <script>
    const log = (msg) => { document.getElementById('log').textContent = msg; };
    document.getElementById('run').onclick = async () => {
      try {
        const req = JSON.parse(document.getElementById('request').value);
        const ov = JSON.parse(document.getElementById('overrides').value || "{}");
        const body = {
          request: req,
          count: Number(document.getElementById('count').value || 1),
          concurrency: Number(document.getElementById('concurrency').value || 1),
          overrides: ov
        };
        const res = await fetch('/debug/run', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
        const json = await res.json();
        log(JSON.stringify(json, null, 2));
      } catch (e) { log(e.toString()); }
    };

    document.getElementById('loadAgents').onclick = async () => {
      const res = await fetch('/debug/agents');
      const data = await res.json();
      const rows = data.map(a => `<tr><td>${a.name}</td><td>${a.model||''}</td><td>${(a.tools||[]).join(',')}</td></tr>`).join('');
      document.getElementById('agentTable').innerHTML = '<tr><th>Agent</th><th>Model</th><th>Tools</th></tr>' + rows;
    };
  </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@router.get("/agents", include_in_schema=False)
async def list_agents():
    _ensure_enabled()
    agents = [
        agent_defs.persona_generator_agent,
        agent_defs.theme_agent,
        agent_defs.research_agent,
        agent_defs.outline_agent,
        agent_defs.section_writer_agent,
        agent_defs.section_writer_with_images_agent,
        agent_defs.editor_agent,
        agent_defs.serp_keyword_analysis_agent,
    ]
    data = []
    for ag in agents:
        tools = []
        for t in getattr(ag, "tools", []) or []:
            name = getattr(t, "name", None) or getattr(t, "__name__", None) or str(t)
            tools.append(name)
        data.append({
            "name": ag.name,
            "model": getattr(ag, "model", None),
            "tools": tools,
        })
    return data


@router.post("/run", include_in_schema=False)
async def debug_run(payload: DebugRunPayload):
    _ensure_enabled()
    runs: List[Dict[str, Any]] = []
    base_request_dict = payload.request.model_dump()
    if payload.overrides:
        base_request_dict["runtime_overrides"] = payload.overrides
    base_request = GenerateArticleRequest(**base_request_dict)

    for _ in range(payload.count):
        request_model = GenerateArticleRequest(**base_request.model_dump())
        process_id = str(uuid.uuid4())
        task_id = await _article_service.background_task_manager.start_generation_process(
            process_id=process_id,
            user_id=payload.user_id or "debug-user",
            organization_id=payload.organization_id,
            request_data=request_model,
        )
        runs.append({"process_id": process_id, "task_id": task_id})
    return {"runs": runs}
