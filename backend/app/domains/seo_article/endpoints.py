# -*- coding: utf-8 -*-
"""
SEO記事生成ドメイン - APIエンドポイント (統合版)

This module provides:
- Article WebSocket generation endpoints
- Article CRUD operations  
- Article Flow Management API Endpoints
- AI editing capabilities
"""

from fastapi import APIRouter, status, Depends, HTTPException, Query, BackgroundTasks, Request
from typing import List, Optional, Dict, Any
import logging
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
import re
import html
import time
import json

# 新しいインポートパス（修正版）
from .services.generation_service import ArticleGenerationService
from .schemas import GenerateArticleRequest
# from .services.flow_service import (  # 後で実装
#     article_flow_service,
#     ArticleFlowCreate,
#     ArticleFlowRead,
#     GeneratedArticleStateRead,
#     FlowExecutionRequest
# )
from app.common.auth import get_current_user_id_from_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.domains.company.service import CompanyService
from app.domains.seo_article.services.flow_service import get_supabase_client
from app.infrastructure.logging.service import LoggingService

# 静的: 1タグHTMLの出力検疫用設定
SAFE_URL_SCHEMES = {"http", "https", "mailto", "tel"}
_knowledge_cache: Dict[str, Dict[str, Any]] = {}
_knowledge_cache_ttl_sec = 60

security = HTTPBearer(auto_error=False)

# TODO: サービス実装完了後に有効化
# from app.infrastructure.external_apis.article_service import ArticleGenerationService
# from app.infrastructure.external_apis.article_flow_service import (
#     article_flow_service,
#     ArticleFlowCreate,
#     ArticleFlowRead,
#     GeneratedArticleStateRead,
#     FlowExecutionRequest
# )

# 実際のサービスインスタンスを使用
article_service = ArticleGenerationService()

# Define models first
class ArticleFlowCreate(BaseModel):
    name: str = "stub"
    description: Optional[str] = None
    is_template: bool = False
    steps: List[Dict[str, Any]] = []
    
class _StubStep(BaseModel):
    step_order: int = 0
    step_type: str = "stub"
    agent_name: str = "stub"
    prompt_template_id: str = "stub"
    tool_config: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}
    is_interactive: bool = False
    skippable: bool = False
    config: Dict[str, Any] = {}

class ArticleFlowRead(BaseModel):
    id: str = "stub"
    name: str = "stub"
    is_template: bool = False
    steps: List[_StubStep] = []

# Flow service stubs
class ArticleFlowService:
    async def create_flow(self, user_id: str, organization_id: Optional[str], flow_data: Any) -> Dict[str, Any]: return {}
    async def get_user_flows(self, user_id: str, organization_id: Optional[str] = None) -> List[ArticleFlowRead]: return []
    async def get_flow(self, flow_id: str, user_id: str) -> Optional[ArticleFlowRead]: return None
    async def update_flow(self, flow_id: str, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]: return {}
    async def delete_flow(self, flow_id: str, user_id: str) -> bool: return False
    async def start_flow_execution(self, user_id: str, execution_request: Any) -> Optional[str]: return None
    async def get_generation_state(self, process_id: str, user_id: str) -> Optional[Dict[str, Any]]: return None
    async def pause_generation(self, process_id: str, user_id: str) -> bool: return False
    async def cancel_generation(self, process_id: str, user_id: str) -> bool: return False

article_flow_service = ArticleFlowService()
    
class GeneratedArticleStateRead(BaseModel):
    status: str = "stub"
    
class FlowExecutionRequest(BaseModel):
    flow_id: str = "stub"

logger = logging.getLogger(__name__)

router = APIRouter()
# インスタンスは上記で作成済み

# --- Request/Response Models ---

class ArticleUpdateRequest(BaseModel):
    """記事更新リクエスト"""
    title: Optional[str] = None
    content: Optional[str] = None
    shortdescription: Optional[str] = None
    target_audience: Optional[str] = None
    keywords: Optional[List[str]] = None
    status: Optional[str] = Field(None, description="記事の公開状態 (draft, published)")

class ArticleStatusUpdateRequest(BaseModel):
    """記事公開状態更新専用リクエスト"""
    status: str = Field(..., description="記事の公開状態 (draft, published)")

class AIEditRequest(BaseModel):
    """AIによるブロック編集リクエスト"""
    content: str = Field(..., description="元のHTMLブロック内容")
    instruction: str = Field(..., description="編集指示（カジュアルに書き換え等）")
    # 任意: 記事全体HTML（複数ブロック編集時の文脈保持に有効）
    article_html: Optional[str] = Field(None, description="記事全体のHTML（任意、無い場合はDBから取得）")

# --- New Realtime Process Management Models ---

class UserInputRequest(BaseModel):
    """ユーザー入力データ"""
    response_type: str = Field(..., description="応答タイプ")
    payload: Dict[str, Any] = Field(..., description="応答データ")

class ProcessEventResponse(BaseModel):
    """プロセスイベント応答"""
    id: str
    process_id: str
    event_type: str
    event_data: Dict[str, Any]
    event_sequence: int
    created_at: str

# --- AI編集 ヘルパー関数群 ---

async def assemble_edit_knowledge(article_id: str, user_id: str, article_record: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """記事に紐づくコンテキスト、会社情報、スタイルテンプレート等を収集して返す。

    60秒キャッシュにより同一記事の連続呼び出しを最適化。
    """
    cache_key = f"{user_id}:{article_id}"
    cached = _knowledge_cache.get(cache_key)
    if cached and (time.time() - cached.get("cached_at", 0) < _knowledge_cache_ttl_sec):
        return cached

    supabase = get_supabase_client()
    # 1) 記事レコード
    article = article_record
    if not article:
        res = supabase.table("articles").select("*").eq("id", article_id).eq("user_id", user_id).limit(1).execute()
        article = res.data[0] if res.data else None
    process_id = article.get("generation_process_id") if article else None

    # 2) ArticleContext 復元
    context = None
    if process_id:
        try:
            context = await article_service.persistence_service.load_context_from_db(process_id, user_id)
        except Exception as e:
            logger.warning(f"assemble_edit_knowledge: failed to load context for {process_id}: {e}")

    # 3) 会社情報（default）
    try:
        company_obj = await CompanyService.get_default_company(user_id)
        company = company_obj.model_dump() if hasattr(company_obj, "model_dump") else (company_obj.dict() if company_obj else None)
    except Exception as e:
        logger.warning(f"assemble_edit_knowledge: failed to get default company: {e}")
        company = None

    # 4) スタイルガイド（context指定 or ユーザー既定）
    style_template = None
    style_template_id = getattr(context, "style_template_id", None) if context else None
    try:
        if style_template_id:
            r = supabase.table("style_guide_templates").select("*").eq("id", style_template_id).limit(1).execute()
            style_template = r.data[0] if r.data else None
        if not style_template:
            r = supabase.table("style_guide_templates").select("*").eq("user_id", user_id).eq("is_default", True).limit(1).execute()
            style_template = r.data[0] if r.data else None
    except Exception as e:
        logger.warning(f"assemble_edit_knowledge: failed to get style template: {e}")

    # 5) SERP/テーマ/ペルソナ
    serp = getattr(context, "serp_analysis_report", None) if context else None
    persona = getattr(context, "selected_detailed_persona", None) if context else None
    theme = getattr(context, "selected_theme", None) if context else None

    knowledge = {
        "context": context,
        "company": company,
        "style_template": style_template,
        "serp": serp,
        "persona": persona,
        "theme": theme,
        "context_keywords": getattr(context, "initial_keywords", []) if context else []
    }

    knowledge["cached_at"] = time.time()
    _knowledge_cache[cache_key] = knowledge
    return knowledge


def _summarize_style_guide(style_template: Optional[Dict[str, Any]], context_obj: Optional[Any]) -> str:
    if not style_template and not (getattr(context_obj, "style_template_settings", None) or {}):
        return "(未設定)"
    settings = {}
    if style_template:
        settings = style_template.get("settings", {}) or {}
    # context側に設定があればマージ（context優先）
    if context_obj and getattr(context_obj, "style_template_settings", None):
        settings = {**settings, **(context_obj.style_template_settings or {})}
    if not settings:
        return "(未設定)"
    # 日本語の短い要約
    parts = []
    tone = settings.get("tone")
    if tone: parts.append(f"口調={tone}")
    formality = settings.get("formality")
    if formality: parts.append(f"文体={formality}")
    sentence_len = settings.get("sentence_length")
    if sentence_len: parts.append(f"文長={sentence_len}")
    heading = settings.get("heading_style")
    if heading: parts.append(f"見出し={heading}")
    list_style = settings.get("list_style")
    if list_style: parts.append(f"箇条書き={list_style}")
    num_style = settings.get("number_style")
    if num_style: parts.append(f"英数字表記={num_style}")
    return ", ".join(parts) if parts else "(設定あり)"


def _summarize_company(company: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not company:
        return {
            "name": "(未設定)",
            "usp": "",
            "avoid_terms": "",
            "target_area": "",
        }
    return {
        "name": company.get("name") or "(未設定)",
        "usp": company.get("usp") or "",
        "avoid_terms": company.get("avoid_terms") or "",
        "target_area": company.get("target_area") or "",
    }


def _summarize_serp(serp_obj: Optional[Any]) -> Dict[str, Any]:
    if not serp_obj:
        return {
            "keyword": "",
            "user_intent": "",
            "common_headings": [],
            "content_gaps": [],
            "recommended_length": "",
        }
    try:
        serp = serp_obj.model_dump() if hasattr(serp_obj, "model_dump") else dict(serp_obj)
    except Exception:
        serp = {}
    keyword = serp.get("keyword") or serp.get("search_query") or ""
    return {
        "keyword": keyword,
        "user_intent": serp.get("user_intent_analysis", ""),
        "common_headings": serp.get("common_headings", []) or [],
        "content_gaps": serp.get("content_gaps", []) or [],
        "recommended_length": serp.get("recommended_target_length") or serp.get("average_article_length") or "",
    }


def build_edit_system_prompt(knowledge: Dict[str, Any], tag: str, attrs: Dict[str, Any], article_excerpt: str) -> str:
    ctx = knowledge.get("context")
    company_info = _summarize_company(knowledge.get("company"))
    style_summary = _summarize_style_guide(knowledge.get("style_template"), ctx)
    serp_summary = _summarize_serp(knowledge.get("serp"))

    # テーマ要約
    theme = knowledge.get("theme")
    theme_summary = ""
    try:
        if theme:
            data = theme.model_dump() if hasattr(theme, "model_dump") else dict(theme)
            title = data.get("title")
            desc = data.get("description")
            kws = ", ".join(data.get("keywords", [])[:6]) if data.get("keywords") else ""
            theme_summary = ", ".join(filter(None, [title, desc, f"KW:{kws}" if kws else None]))
    except Exception:
        theme_summary = ""

    persona = knowledge.get("persona") or (ctx.custom_persona if ctx and getattr(ctx, "custom_persona", None) else "")

    # 編集ガードレール（属性一覧の可視化）
    preserved_attrs = " ".join([f"{k}='{html.escape(' '.join(v) if isinstance(v, list) else str(v))}'" for k, v in attrs.items()])

    system_prompt = (
        "あなたはSEO編集専門のシニアエディタ。以下の「知識パック」を厳守し、指定ブロックだけを修正する。\n\n"
        "[知識パック]\n"
        f"- テーマ: {theme_summary or '(未設定)'}\n"
        f"- 対象ペルソナ: {persona or '(未設定)'}\n"
        f"- 会社情報: {company_info['name']}, USP={company_info['usp']}, NGワード={company_info['avoid_terms']}, ターゲットエリア={company_info['target_area']}\n"
        f"- スタイルガイド設定: {style_summary}\n"
        f"- SERP要約: keyword={serp_summary['keyword']}, user_intent={serp_summary['user_intent']}, 共通見出し={', '.join(serp_summary['common_headings'][:8])}, content_gaps={', '.join(serp_summary['content_gaps'][:8])}, 推奨文量={serp_summary['recommended_length']}\n"
        f"- 記事本文の抜粋（参照用。編集対象外）:\n{article_excerpt}\n\n"
        "[HTML構造ガードレール - 絶対遵守]\n"
        "- 全てのHTMLタグは適切に開始・終了する（例: <strong>テキスト</strong>）\n"
        "- 入れ子構造は正しい階層を維持する（ul > li, strong内にulは不可）\n"
        "- p要素内にp要素を入れ子にしない（<p><p>...</p></p>は禁止）\n"
        "- ul要素の直下にはli要素のみを配置する\n"
        "- 出力HTMLはW3C標準に準拠する\n"
        "- 構造的に無効なHTMLは絶対に出力しない\n\n"
        "[編集ガードレール]\n"
        f"- 編集対象: <{tag}{(' ' + preserved_attrs) if preserved_attrs else ''}>…</{tag}> の内側のみ。他ブロックには一切触れない。\n"
        "- タグ名・既存 attributes(id/class/data-*) を維持。リンク/画像/src/alt も壊さない。\n"
        "- 出力はそのタグ1つだけ（前後テキストや説明文、バッククォート禁止）。\n"
        "- 事実は知識パックと元記事からのみ。推測や新規URLを捏造しない。\n"
        "- 日本語。冗長回避。スタイルガイドを最優先。\n\n"
        "[出力フォーマット]\n"
        f"- 1タグのHTML断片のみ（例：<{tag} …>…</{tag}>）"
    )
    return system_prompt


def build_edit_user_prompt(tag: str, attrs: Dict[str, Any], inner_html: str, instruction_text: str) -> str:
    # attrs を HTML の文字列に
    attr_str = " ".join([f"{k}='{html.escape(' '.join(v) if isinstance(v, list) else str(v))}'" for k, v in attrs.items()])
    opening = f"<{tag}{(' ' + attr_str) if attr_str else ''}>"
    closing = f"</{tag}>"
    original_html = f"{opening}{inner_html}{closing}"

    prompt = (
        "[編集対象ブロック]\n"
        f"original_html:\n{original_html}\n\n"
        "[編集指示]\n"
        f"{instruction_text}"
    )
    return prompt


def strip_code_fences(text: str) -> str:
    if not text:
        return text
    # ```lang ... ``` を除去
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```\s*$", "", text)
    # 先頭末尾のバッククォートを粗く除去
    text = text.strip("`")
    return text


def validate_and_fix_html_structure(html_content: str) -> str:
    """HTMLの構造的整合性を検証・修正"""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 1. 不適切に閉じられていないタグの検出と修正
        _fix_unclosed_tags(soup)
        
        # 2. 不適切な入れ子構造の修正
        _fix_invalid_nesting(soup)
        
        # 3. 空の要素の除去
        _remove_empty_elements(soup)
        
        return str(soup)
    except Exception as e:
        logger.error(f"HTML validation failed: {e}")
        return html_content


def _fix_unclosed_tags(soup):
    """未閉じタグの修正"""
    # BeautifulSoupが自動的にタグを閉じるが、明示的にチェック
    for tag in soup.find_all(True):
        # 自己完結タグ以外でテキストが空の場合は削除候補
        if tag.name not in ['br', 'img', 'hr', 'input', 'area', 'base', 'col', 'embed', 'link', 'meta', 'source', 'track', 'wbr']:
            if not tag.get_text(strip=True) and not tag.find_all():
                tag.decompose()


def _fix_invalid_nesting(soup):
    """不適切な入れ子構造の修正"""
    # p要素内のp要素を修正
    for p in soup.find_all('p'):
        nested_ps = p.find_all('p')
        for nested_p in nested_ps:
            # 内側のpの内容を外側のpに移動
            contents = list(nested_p.contents)
            for content in contents:
                p.insert_before(content)
            nested_p.decompose()
    
    # ul要素の直下にstrong等のブロック要素が来る場合の修正
    for ul in soup.find_all('ul'):
        direct_children = [child for child in ul.children if hasattr(child, 'name')]
        for child in direct_children:
            if child.name and child.name not in ['li']:
                # li要素でない直接の子要素をli要素で囲む
                li_wrapper = soup.new_tag('li')
                child.wrap(li_wrapper)


def _remove_empty_elements(soup):
    """空要素の除去"""
    # 空のp, div, span要素を削除
    for tag_name in ['p', 'div', 'span', 'strong', 'em']:
        for tag in soup.find_all(tag_name):
            if not tag.get_text(strip=True) and not tag.find_all(['img', 'br', 'hr']):
                tag.decompose()


def sanitize_dom(frag) -> None:
    """script/style除去、on*属性除去、javascript:リンク除去などの簡易サニタイズ"""
    try:
        # 危険タグ除去
        for bad in frag.find_all(["script", "style"]):
            bad.decompose()
        # 属性検疫
        for el in frag.find_all(True):
            # on* 属性除去
            for attr in list(el.attrs.keys()):
                if attr.lower().startswith("on"):
                    del el.attrs[attr]
            # URL属性の検査
            for url_attr in ["href", "src"]:
                if url_attr in el.attrs:
                    val = " ".join(el.attrs.get(url_attr)) if isinstance(el.attrs.get(url_attr), list) else str(el.attrs.get(url_attr))
                    if not val:
                        continue
                    low = val.strip().lower()
                    if low.startswith("javascript:"):
                        del el.attrs[url_attr]
                        continue
                    # スキーム付きのものはホワイトリストに限定（相対URLは許可）
                    if "://" in low:
                        scheme = low.split(":", 1)[0]
                        if scheme not in SAFE_URL_SCHEMES:
                            del el.attrs[url_attr]
    except Exception as e:
        logger.warning(f"sanitize_dom failed: {e}")


def enhanced_sanitize_dom(frag) -> None:
    """強化されたHTMLサニタイズ（構造整合性を含む）"""
    try:
        # 既存のセキュリティ処理
        sanitize_dom(frag)
        
        # 構造整合性チェック
        # 1. 不適切な入れ子構造の修正
        _fix_invalid_nesting(frag)
        
        # 2. 未閉じタグの検出・修正
        _fix_unclosed_tags(frag)
        
        # 3. 空要素の除去
        _remove_empty_elements(frag)
        
    except Exception as e:
        logger.warning(f"Enhanced sanitization failed: {e}")

# --- Article CRUD Endpoints ---

@router.get("/", response_model=List[dict], status_code=status.HTTP_200_OK)
async def get_articles(
    user_id: str = Depends(get_current_user_id_from_token),
    status_filter: Optional[str] = Query(None, description="Filter by generation status (completed, error, etc.)"),
    limit: int = Query(20, description="Number of articles to return"),
    offset: int = Query(0, description="Number of articles to skip")
):
    """
    Get articles for the specified user.
    
    **Parameters:**
    - user_id: User ID (from authentication)
    - status_filter: Filter articles by status (optional)
    - limit: Maximum number of articles to return (default: 20)
    - offset: Number of articles to skip for pagination (default: 0)
    
    **Returns:**
    - List of articles with basic information
    """
    try:
        articles = await article_service.get_user_articles(
            user_id=user_id,
            status_filter=status_filter,
            limit=limit,
            offset=offset
        )
        return articles
    except Exception as e:
        logger.error(f"Error getting articles for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve articles"
        )

@router.get("/all-processes", response_model=List[dict], status_code=status.HTTP_200_OK)
async def get_all_processes(
    user_id: str = Depends(get_current_user_id_from_token),
    status_filter: Optional[str] = Query(None, description="Filter by status (completed, in_progress, error, etc.)"),
    limit: int = Query(20, description="Number of items to return"),
    offset: int = Query(0, description="Number of items to skip")
):
    """
    Get all processes (completed articles + in-progress/failed generation processes) for the user.
    
    **Parameters:**
    - user_id: User ID (from authentication)
    - status_filter: Filter by status (optional)
    - limit: Maximum number of items to return (default: 20)
    - offset: Number of items to skip for pagination (default: 0)
    
    **Returns:**
    - List of articles and generation processes with unified format
    """
    try:
        processes = await article_service.get_all_user_processes(
            user_id=user_id,
            status_filter=status_filter,
            limit=limit,
            offset=offset
        )
        return processes
    except Exception as e:
        logger.error(f"Error getting all processes for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve processes"
        )

@router.get("/recoverable-processes", response_model=List[dict], status_code=status.HTTP_200_OK)
async def get_recoverable_processes(
    user_id: str = Depends(get_current_user_id_from_token),
    limit: int = Query(10, description="Number of recoverable processes to return"),
):
    """
    Get recoverable processes for the user that can be resumed.
    
    **Parameters:**
    - user_id: User ID (from authentication)
    - limit: Maximum number of processes to return (default: 10)
    
    **Returns:**
    - List of recoverable generation processes with recovery metadata
    """
    try:
        processes = await article_service.get_recoverable_processes(
            user_id=user_id,
            limit=limit
        )
        return processes
    except Exception as e:
        logger.error(f"Error getting recoverable processes for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recoverable processes"
        )

@router.get("/generation/{process_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def get_generation_process(
    request: Request,
    process_id: str,
    user_id: str = Depends(get_current_user_id_from_token),
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
):
    """
    Get generation process state by ID.
    
    **Parameters:**
    - process_id: Generation process ID
    - user_id: User ID (from authentication)
    
    **Returns:**
    - Generation process state including image_mode and other context data
    """
    try:
        # Debug raw request headers
        auth_header_raw = request.headers.get("Authorization")
        logger.info(f"🔐 [ENDPOINT] Raw Authorization header: {auth_header_raw[:30] if auth_header_raw else 'None'}...")
        logger.info(f"🔐 [ENDPOINT] All headers: {dict(request.headers)}")
        
        # Extract JWT token for RLS enforcement
        user_jwt = authorization.credentials if authorization else None
        logger.info(f"🔐 [ENDPOINT] Getting process {process_id} for user {user_id} with JWT: {user_jwt is not None}")
        
        process_state = await article_service.get_generation_process_state(process_id, user_id, user_jwt)
        if not process_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation process not found or access denied"
            )
        return process_state
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting generation process {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve generation process"
        )

@router.get("/{article_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def get_article(
    article_id: str,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Get detailed article information by ID.
    
    **Parameters:**
    - article_id: Article ID
    - user_id: User ID (from authentication)
    
    **Returns:**
    - Detailed article information including content
    """
    try:
        article = await article_service.get_article(article_id, user_id)
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found or access denied"
            )
        return article
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting article {article_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve article"
        )

@router.patch("/{article_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def update_article(
    article_id: str,
    update_data: ArticleUpdateRequest,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    記事を更新します。
    
    **Parameters:**
    - article_id: 記事ID
    - update_data: 更新するデータ
    - user_id: ユーザーID（認証から取得）
    
    **Returns:**
    - 更新された記事情報
    """
    try:
        # まず記事が存在し、ユーザーがアクセス権限を持つことを確認
        existing_article = await article_service.get_article(article_id, user_id)
        if not existing_article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found or access denied"
            )
        
        # 記事を更新
        updated_article = await article_service.update_article(
            article_id=article_id,
            user_id=user_id,
            update_data=update_data.dict(exclude_unset=True)
        )
        
        return updated_article
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating article {article_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update article"
        )

@router.patch("/{article_id}/status", response_model=dict, status_code=status.HTTP_200_OK)
async def update_article_status(
    article_id: str,
    status_data: ArticleStatusUpdateRequest,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    記事の公開状態を更新します。
    
    **Parameters:**
    - article_id: 記事ID
    - status_data: 公開状態データ (draft または published)
    - user_id: ユーザーID（認証から取得）
    
    **Returns:**
    - 更新された記事情報
    """
    try:
        # ステータス値の検証
        valid_statuses = ['draft', 'published']
        if status_data.status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # まず記事が存在し、ユーザーがアクセス権限を持つことを確認
        existing_article = await article_service.get_article(article_id, user_id)
        if not existing_article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found or access denied"
            )
        
        # 記事の公開状態を更新
        updated_article = await article_service.update_article(
            article_id=article_id,
            user_id=user_id,
            update_data={"status": status_data.status}
        )
        
        return {
            "id": article_id,
            "status": status_data.status,
            "message": f"記事の状態を「{status_data.status}」に更新しました",
            "updated_at": updated_article.get("updated_at") if updated_article else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating article status {article_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update article status"
        )

@router.post("/{article_id}/ai-edit", response_model=dict, status_code=status.HTTP_200_OK)
async def ai_edit_block(
    article_id: str,
    req: AIEditRequest,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    ブロック内容を OpenAI で編集して返す。
    
    **Parameters**
    - article_id: 記事ID（アクセス制御用）
    - req: AIEditRequest (content, instruction)
    - user_id: Clerk認証ユーザーID
    """
    try:
        # 0) 記事アクセス権チェック & 本文取得
        article = await article_service.get_article(article_id, user_id)
        if not article:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found or access denied")

        # 1) ナレッジ収集（キャッシュ付き）
        knowledge = await assemble_edit_knowledge(article_id, user_id, article)

        # 2) 入力HTMLの解析（1タグ保証 & 属性保持）
        soup = BeautifulSoup(req.content, "html.parser")
        target = soup.find(True)
        if not target:
            raise HTTPException(status_code=400, detail="content は1つのタグでラップしてください")
        tag_name = target.name
        attrs = dict(target.attrs)
        inner_html = "".join(str(c) for c in target.contents)

        # 3) プロンプト構築（記事全体の抜粋は instructions 側へ、input は編集対象のみ）
        article_excerpt = (req.article_html or article.get("content") or "")[:4000]
        system_prompt = build_edit_system_prompt(knowledge, tag_name, attrs, article_excerpt)
        user_prompt = build_edit_user_prompt(tag_name, attrs, inner_html, req.instruction)

        # 4) OpenAI 呼び出し
        from app.core.config import settings
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        start_time = time.time()
        # Responses API で instructions/input を厳密に分離
        response = await client.responses.create(
            model=settings.editing_model,
            instructions=system_prompt,
            input=user_prompt,
            temperature=0.3,
        )
        duration_ms = int((time.time() - start_time) * 1000)

        raw = (getattr(response, "output_text", None) or "")
        clean = strip_code_fences(raw.strip())

        # 5) 出力検疫：1タグ抽出/属性復元/危険除去
        out_soup = BeautifulSoup(clean, "html.parser")
        frag = out_soup.find(tag_name)
        if not frag:
            # タグ欠落時は強制リラップ
            new_frag = BeautifulSoup("", "html.parser").new_tag(tag_name, **attrs)
            new_frag.append(BeautifulSoup(clean, "html.parser"))
            frag = new_frag
        # 属性は元を優先して復元
        for k_attr, v in attrs.items():
            frag[k_attr] = v
        enhanced_sanitize_dom(frag)
        
        # HTMLバリデーション処理を追加
        validated_html = validate_and_fix_html_structure(str(frag))
        edited = validated_html

        # 6) ログ保存（system_prompt/user_prompt/usage等）
        try:
            logging_service = LoggingService()
            session_id = logging_service.create_log_session(
                article_uuid=str(article.get("id")),
                user_id=user_id,
                initial_input={"article_id": article_id, "edit_type": "block"},
                seo_keywords=knowledge.get("context_keywords", []),
                article_style_info=knowledge.get("style_template", {}) or {},
                persona_settings={"persona": knowledge.get("persona")},
                company_info=knowledge.get("company") or {},
                session_metadata={"workflow_type": "seo_article_ai_edit"}
            )
            execution_id = logging_service.create_execution_log(
                session_id=session_id,
                agent_name="ai_edit_block",
                agent_type="editor",
                step_number=1,
                input_data={"tag": tag_name, "attrs": attrs, "instruction": req.instruction},
                llm_model=settings.editing_model,
            )
            usage = getattr(response, "usage", None)
            prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
            total_tokens = getattr(usage, "total_tokens", 0) if usage else 0
            logging_service.create_llm_call_log(
                execution_id=execution_id,
                call_sequence=1,
                api_type="responses",
                model_name=settings.editing_model,
                provider="openai",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                full_prompt_data={"instructions": system_prompt, "input": user_prompt},
                response_content=raw,
                response_data=json.loads(response.model_dump_json()),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                response_time_ms=duration_ms,
            )
        except Exception as log_e:
            logger.warning(f"Failed to log AI edit call: {log_e}")

        return {"edited_content": edited}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI edit error for article {article_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI edit failed")

# --- WebSocket Generation Endpoint (DEPRECATED) ---
# NOTE: WebSocket endpoint has been removed in favor of Supabase Realtime.
# Use the new HTTP endpoints for generation management: /generation/start, /generation/{id}/user-input, etc.

# --- NEW: Supabase Realtime Process Management Endpoints ---

@router.post("/generation/start", response_model=dict, status_code=status.HTTP_201_CREATED)
async def start_generation_process(
    request: GenerateArticleRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id_from_token),
    organization_id: Optional[str] = Query(None, description="Organization ID for multi-tenant support")
):
    """
    Start a new article generation process using background tasks and Supabase Realtime.
    
    **Parameters:**
    - request: Article generation request parameters
    - user_id: User ID (from authentication)
    - organization_id: Optional organization ID for multi-tenant support
    
    **Returns:**
    - process_id: Unique process identifier
    - realtime_channel: Supabase Realtime channel name for subscription
    - status: Initial process status
    """
    try:
        logger.info(f"🎯 [ENDPOINT] Starting generation process for user: {user_id}")
        
        # Create process in database
        logger.info("📝 [ENDPOINT] Creating process in database")
        process_id = await article_service.create_generation_process(
            user_id=user_id,
            organization_id=organization_id,
            request_data=request
        )
        logger.info(f"✅ [ENDPOINT] Process created with ID: {process_id}")
        
        # Start background task
        logger.info("🚀 [ENDPOINT] Adding background task to FastAPI BackgroundTasks")
        background_tasks.add_task(
            article_service.run_generation_background_task,
            process_id=process_id,
            user_id=user_id,
            organization_id=organization_id,
            request_data=request
        )
        logger.info(f"✅ [ENDPOINT] Background task added successfully for process {process_id}")
        
        response_data = {
            "process_id": process_id,
            "realtime_channel": f"process_{process_id}",
            "status": "started",
            "message": "Generation process started successfully",
            "subscription_info": {
                "table": "process_events",
                "filter": f"process_id=eq.{process_id}",
                "channel": f"process_events:process_id=eq.{process_id}"
            }
        }
        logger.info(f"🏁 [ENDPOINT] Returning response for process {process_id}")
        return response_data
        
    except Exception as e:
        logger.error(f"Error starting generation process: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start generation process"
        )

@router.post("/generation/{process_id}/resume", response_model=dict, status_code=status.HTTP_200_OK)
async def resume_generation_process(
    process_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Resume a paused or failed generation process.
    
    **Parameters:**
    - process_id: Generation process ID to resume
    - user_id: User ID (from authentication)
    
    **Returns:**
    - process_id: Process identifier
    - status: Updated process status
    """
    try:
        # Validate process ownership and resumability
        process_state = await article_service.get_generation_process_state(process_id, user_id)
        if not process_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Process not found or access denied"
            )
        
        # Check if process can be resumed
        resumable_statuses = ['user_input_required', 'paused', 'error']
        if process_state.get("status") not in resumable_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Process cannot be resumed from status: {process_state.get('status')}"
            )
        
        # Start resume background task
        background_tasks.add_task(
            article_service.resume_generation_background_task,
            process_id=process_id,
            user_id=user_id
        )
        
        return {
            "process_id": process_id,
            "status": "resuming",
            "message": "Generation process resume initiated",
            "realtime_channel": f"process_{process_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming generation {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume generation process"
        )

@router.post("/generation/{process_id}/user-input", response_model=dict, status_code=status.HTTP_200_OK)
async def submit_user_input(
    process_id: str,
    input_data: UserInputRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Submit user input for a process waiting for user interaction.
    
    **Parameters:**
    - process_id: Generation process ID
    - input_data: User input data (response_type and payload)
    - user_id: User ID (from authentication)
    
    **Returns:**
    - process_id: Process identifier
    - status: Updated process status
    """
    try:
        logger.info(f"🔍 [SUBMIT_INPUT] Processing user input for process {process_id}, user {user_id}")
        logger.info(f"📝 [SUBMIT_INPUT] Input data: {input_data.dict()}")
        
        # Validate process state
        process_state = await article_service.get_generation_process_state(process_id, user_id)
        if not process_state:
            logger.error(f"❌ [SUBMIT_INPUT] Process {process_id} not found for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process not found or access denied"
            )
        
        logger.info(f"📊 [SUBMIT_INPUT] Process state: {process_state}")
        
        if not process_state.get("is_waiting_for_input"):
            logger.error(f"❌ [SUBMIT_INPUT] Process {process_id} is not waiting for input: {process_state.get('is_waiting_for_input')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Process is not waiting for user input"
            )
        
        # Validate input type matches expected (skip validation for special request types)
        expected_input_type = process_state.get("input_type")
        special_request_types = ["regenerate", "edit_and_proceed"]
        
        if (expected_input_type and 
            expected_input_type != input_data.response_type and 
            input_data.response_type not in special_request_types):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Expected input type '{expected_input_type}', got '{input_data.response_type}'"
            )
        
        # Store user input and update process state
        await article_service.process_user_input(
            process_id=process_id,
            user_id=user_id,
            input_data=input_data.dict()
        )
        
        # Continue processing in background
        background_tasks.add_task(
            article_service.continue_generation_after_input,
            process_id=process_id,
            user_id=user_id
        )
        
        return {
            "process_id": process_id,
            "status": "input_received",
            "message": "User input received, continuing generation",
            "input_type": input_data.response_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"💥 [SUBMIT_INPUT] Error processing user input for {process_id}: {e}")
        logger.exception(f"[SUBMIT_INPUT] Full exception details for process {process_id}:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process user input: {str(e)}"
        )

@router.post("/generation/{process_id}/pause", response_model=dict, status_code=status.HTTP_200_OK)
async def pause_generation_process(
    process_id: str,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Pause a running generation process.
    
    **Parameters:**
    - process_id: Generation process ID to pause
    - user_id: User ID (from authentication)
    
    **Returns:**
    - process_id: Process identifier
    - status: Updated process status
    """
    try:
        success = await article_service.pause_generation_process(process_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process not found, access denied, or cannot be paused"
            )
        
        return {
            "process_id": process_id,
            "status": "paused",
            "message": "Generation process paused successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing generation {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pause generation process"
        )

@router.delete("/generation/{process_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def cancel_generation_process(
    process_id: str,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Cancel a generation process.
    
    **Parameters:**
    - process_id: Generation process ID to cancel
    - user_id: User ID (from authentication)
    
    **Returns:**
    - process_id: Process identifier
    - status: Updated process status
    """
    try:
        success = await article_service.cancel_generation_process(process_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process not found, access denied, or cannot be cancelled"
            )
        
        return {
            "process_id": process_id,
            "status": "cancelled",
            "message": "Generation process cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling generation {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel generation process"
        )

@router.get("/generation/{process_id}/events", response_model=List[ProcessEventResponse], status_code=status.HTTP_200_OK)
async def get_process_events(
    process_id: str,
    user_id: str = Depends(get_current_user_id_from_token),
    since_sequence: Optional[int] = Query(None, description="Get events after this sequence number"),
    limit: int = Query(50, description="Maximum events to return"),
    event_types: Optional[str] = Query(None, description="Comma-separated list of event types to filter")
):
    """
    Get process events for real-time synchronization and event history.
    
    **Parameters:**
    - process_id: Generation process ID
    - user_id: User ID (from authentication)
    - since_sequence: Get events after this sequence number (for incremental updates)
    - limit: Maximum number of events to return
    - event_types: Comma-separated list of event types to filter (optional)
    
    **Returns:**
    - List of process events ordered by sequence number
    """
    try:
        # Parse event types filter
        event_type_list = None
        if event_types:
            event_type_list = [t.strip() for t in event_types.split(",") if t.strip()]
        
        events = await article_service.get_process_events(
            process_id=process_id,
            user_id=user_id,
            since_sequence=since_sequence,
            limit=limit,
            event_types=event_type_list
        )
        
        return events
        
    except Exception as e:
        logger.error(f"Error getting process events for {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve process events"
        )

@router.post("/generation/{process_id}/events/{event_id}/acknowledge", response_model=dict, status_code=status.HTTP_200_OK)
async def acknowledge_event(
    process_id: str,
    event_id: str,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Acknowledge receipt of a specific event (for reliable delivery tracking).
    
    **Parameters:**
    - process_id: Generation process ID
    - event_id: Event ID to acknowledge
    - user_id: User ID (from authentication)
    
    **Returns:**
    - status: Acknowledgment status
    """
    try:
        success = await article_service.acknowledge_process_event(
            process_id=process_id,
            event_id=event_id,
            user_id=user_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found or access denied"
            )
        
        return {
            "status": "acknowledged",
            "event_id": event_id,
            "process_id": process_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to acknowledge event"
        )

@router.get("/generation/{process_id}/realtime-info", response_model=dict, status_code=status.HTTP_200_OK)
async def get_realtime_subscription_info(
    process_id: str,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Get Supabase Realtime subscription information for a process.
    
    **Parameters:**
    - process_id: Generation process ID
    - user_id: User ID (from authentication)
    
    **Returns:**
    - Subscription configuration for Supabase Realtime client
    """
    try:
        # Validate process access
        process_state = await article_service.get_generation_process_state(process_id, user_id)
        if not process_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process not found or access denied"
            )
        
        return {
            "process_id": process_id,
            "subscription_config": {
                "channel_name": f"process_events:process_id=eq.{process_id}",
                "table": "process_events",
                "filter": f"process_id=eq.{process_id}",
                "event": "INSERT",
                "schema": "public"
            },
            "process_state_subscription": {
                "channel_name": f"process_state:{process_id}",
                "table": "generated_articles_state",
                "filter": f"id=eq.{process_id}",
                "event": "UPDATE",
                "schema": "public"
            },
            "current_status": process_state.get("status"),
            "last_updated": process_state.get("updated_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting realtime info for {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve realtime subscription info"
        )

# --- Article Flow Management Endpoints ---

# Flow CRUD操作用の認証（フロー管理専用）
# Use proper Clerk JWT authentication for flows
from app.common.auth import get_current_user_id_from_token as get_current_user_id_for_flows

@router.post("/flows/", response_model=ArticleFlowRead, status_code=status.HTTP_201_CREATED)
async def create_flow(
    flow_data: ArticleFlowCreate,
    organization_id: Optional[str] = Query(None, description="Organization ID for organization-level flows"),
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Create a new article generation flow"""
    try:
        flow = await article_flow_service.create_flow(current_user_id, organization_id, flow_data)
        return flow
    except Exception as e:
        logger.error(f"Error creating flow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create flow"
        )

@router.get("/flows/", response_model=List[ArticleFlowRead])
async def get_flows(
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    include_templates: bool = Query(True, description="Include template flows"),
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Get flows accessible to the current user"""
    try:
        flows = await article_flow_service.get_user_flows(current_user_id, organization_id)
        
        # Filter templates if requested
        if not include_templates:
            flows = [flow for flow in flows if not flow.is_template]
        
        return flows
    except Exception as e:
        logger.error(f"Error getting flows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve flows"
        )

@router.get("/flows/{flow_id}", response_model=ArticleFlowRead)
async def get_flow(
    flow_id: str,
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Get flow by ID"""
    try:
        flow = await article_flow_service.get_flow(flow_id, current_user_id)
        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flow not found or access denied"
            )
        return flow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting flow {flow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve flow"
        )

@router.put("/flows/{flow_id}", response_model=ArticleFlowRead)
async def update_flow(
    flow_id: str,
    update_data: dict,
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Update flow (only owner or organization admin can update)"""
    try:
        flow = await article_flow_service.update_flow(flow_id, current_user_id, update_data)
        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flow not found or access denied"
            )
        return flow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating flow {flow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update flow"
        )

@router.delete("/flows/{flow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flow(
    flow_id: str,
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Delete flow (only owner or organization admin can delete)"""
    try:
        success = await article_flow_service.delete_flow(flow_id, current_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flow not found or access denied"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting flow {flow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete flow"
        )

# Flow execution endpoints
@router.post("/flows/{flow_id}/execute")
async def execute_flow(
    flow_id: str,
    execution_request: FlowExecutionRequest,
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Start executing a flow"""
    try:
        # Set the flow_id from the path parameter
        execution_request.flow_id = flow_id
        
        process_id = await article_flow_service.start_flow_execution(current_user_id, execution_request)
        if not process_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flow not found or access denied"
            )
        
        return {
            "process_id": process_id,
            "message": "Flow execution started",
            "status": "in_progress"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing flow {flow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start flow execution"
        )

# Generation state management endpoints
@router.get("/flows/generations/{process_id}", response_model=GeneratedArticleStateRead)
async def get_generation_state(
    process_id: str,
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Get generation process state"""
    try:
        state = await article_flow_service.get_generation_state(process_id, current_user_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation process not found or access denied"
            )
        return state
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting generation state {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve generation state"
        )

@router.post("/flows/generations/{process_id}/pause")
async def pause_generation(
    process_id: str,
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Pause generation process"""
    try:
        success = await article_flow_service.pause_generation(process_id, current_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation process not found or access denied"
            )
        
        return {"message": "Generation process paused"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing generation {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pause generation"
        )

@router.post("/flows/generations/{process_id}/cancel")
async def cancel_generation(
    process_id: str,
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Cancel generation process"""
    try:
        success = await article_flow_service.cancel_generation(process_id, current_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation process not found or access denied"
            )
        
        return {"message": "Generation process cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling generation {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel generation"
        )

# Template flow endpoints
@router.get("/flows/templates/", response_model=List[ArticleFlowRead])
async def get_template_flows(
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Get all template flows available for copying"""
    try:
        flows = await article_flow_service.get_user_flows(current_user_id)
        template_flows = [flow for flow in flows if flow.is_template]
        return template_flows
    except Exception as e:
        logger.error(f"Error getting template flows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template flows"
        )

@router.post("/flows/templates/{template_id}/copy", response_model=ArticleFlowRead)
async def copy_template_flow(
    template_id: str,
    name: str = Query(..., description="Name for the new flow"),
    organization_id: Optional[str] = Query(None, description="Organization ID for organization-level flow"),
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Copy a template flow to create a new customizable flow"""
    try:
        # Get template flow
        template = await article_flow_service.get_flow(template_id, current_user_id)
        if not template or not template.is_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template flow not found"
            )
        
        # Create flow data from template
        flow_data = ArticleFlowCreate(
            name=name,
            description=f"Copied from template: {template.name}",
            is_template=False,
            steps=[
                {
                    "step_order": step.step_order,
                    "step_type": step.step_type,
                    "agent_name": step.agent_name,
                    "prompt_template_id": step.prompt_template_id,
                    "tool_config": step.tool_config,
                    "output_schema": step.output_schema,
                    "is_interactive": step.is_interactive,
                    "skippable": step.skippable,
                    "config": step.config
                }
                for step in template.steps
            ]
        )
        
        # Create new flow
        new_flow = await article_flow_service.create_flow(current_user_id, organization_id, flow_data)
        return new_flow
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error copying template flow {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to copy template flow"
        )

# --- AI Content Generation Endpoints ---

from .services.ai_content_generation_service import AIContentGenerationService
from .schemas import AIContentGenerationRequest, AIContentGenerationResponse
from fastapi import UploadFile, File, Form

@router.post("/ai-content-generation", response_model=AIContentGenerationResponse)
async def generate_ai_content(
    request: AIContentGenerationRequest,
    current_user_id: str = Depends(get_current_user_id_from_token)
):
    """
    AIコンテンツ生成エンドポイント
    ユーザー入力（テキスト、画像、URL）からコンテンツブロックを生成
    """
    try:
        ai_service = AIContentGenerationService()

        # 入力データを構築
        input_data = {
            "type": request.input_type,
            "content": request.content,
            "include_heading": request.include_heading,
            "article_id": request.article_id,
            "insert_position": request.insert_position,
            "article_html": request.article_html
        }

        if request.image_data:
            input_data["image_data"] = request.image_data

        if request.additional_text:
            input_data["additional_text"] = request.additional_text

        # コンテンツ生成
        result = await ai_service.generate_content_blocks(
            input_data=input_data,
            user_instruction=request.user_instruction,
            user_id=current_user_id
        )

        return AIContentGenerationResponse(**result)

    except Exception as e:
        logger.error(f"AI content generation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI content generation failed: {str(e)}"
        )

@router.post("/ai-content-generation/upload", response_model=AIContentGenerationResponse)
async def generate_ai_content_from_upload(
    file: UploadFile = File(...),
    include_heading: bool = Form(False),
    user_instruction: Optional[str] = Form(None),
    article_id: Optional[str] = Form(None),
    insert_position: Optional[int] = Form(None),
    article_html: Optional[str] = Form(None),
    current_user_id: str = Depends(get_current_user_id_from_token)
):
    """
    ファイルアップロードからAIコンテンツ生成
    """
    try:
        ai_service = AIContentGenerationService()

        # ファイルを一時保存
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # コンテンツ生成
            result = await ai_service.generate_content_from_file(
                file_path=temp_file_path,
                file_type=file.content_type or "application/octet-stream",
                user_instruction=user_instruction,
                include_heading=include_heading,
                user_id=current_user_id,
                article_id=article_id,
                insert_position=insert_position,
                article_html=article_html
            )

            return AIContentGenerationResponse(**result)

        finally:
            # 一時ファイル削除
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except Exception as e:
        logger.error(f"AI content generation from upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI content generation from upload failed: {str(e)}"
        )

# --- Step Snapshot Management Endpoints ---

class SnapshotResponse(BaseModel):
    """Step snapshot response model"""
    snapshot_id: str
    step_name: str
    step_index: int
    step_category: Optional[str] = None
    step_description: str
    created_at: str
    can_restore: bool
    # Branch management fields
    branch_id: Optional[str] = None
    branch_name: Optional[str] = None
    is_active_branch: bool = False
    parent_snapshot_id: Optional[str] = None
    is_current: bool = False

class RestoreSnapshotResponse(BaseModel):
    """Snapshot restoration response model"""
    success: bool
    process_id: str
    restored_step: str
    snapshot_id: str
    message: str

@router.get("/generation/{process_id}/snapshots", response_model=List[SnapshotResponse], status_code=status.HTTP_200_OK)
async def get_process_snapshots(
    process_id: str,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Get all available step snapshots for a generation process.

    This endpoint returns a chronological list of snapshots representing
    each step completion in the generation process. Users can restore
    to any of these snapshots to retry from that step.

    **Parameters:**
    - process_id: Generation process ID
    - user_id: User ID (from authentication)

    **Returns:**
    - List of snapshots ordered chronologically (oldest to newest)
    """
    try:
        # Validate process access
        process_state = await article_service.get_generation_process_state(process_id, user_id)
        if not process_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process not found or access denied"
            )

        # Get snapshots
        snapshots = await article_service.persistence_service.get_snapshots_for_process(
            process_id=process_id,
            user_id=user_id
        )

        return [SnapshotResponse(**snapshot) for snapshot in snapshots]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving snapshots for process {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve process snapshots"
        )

@router.post("/generation/{process_id}/snapshots/{snapshot_id}/restore", response_model=RestoreSnapshotResponse, status_code=status.HTTP_200_OK)
async def restore_process_from_snapshot(
    process_id: str,
    snapshot_id: str,
    background_tasks: BackgroundTasks,
    create_new_branch: bool = False,  # Changed: restoration just moves HEAD (like git checkout)
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Restore a generation process to a previous step from a snapshot (like git checkout).

    This moves the current position (HEAD) to the specified snapshot.
    Branching happens automatically when progressing forward from a restored position.

    **Parameters:**
    - process_id: Generation process ID
    - snapshot_id: Snapshot ID to restore from
    - create_new_branch: Deprecated (kept for API compatibility, ignored)
    - user_id: User ID (from authentication)

    **Returns:**
    - Restoration result with success status, restored step information, and branch info
    """
    try:
        # Validate process access
        process_state = await article_service.get_generation_process_state(process_id, user_id)
        if not process_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process not found or access denied"
            )

        # Check if process is in a state that allows restoration
        non_restorable_statuses = ['in_progress', 'resuming', 'auto_progressing']
        if process_state.get("status") in non_restorable_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot restore process in status: {process_state.get('status')}. Please pause the process first."
            )

        # Restore from snapshot with branch option
        result = await article_service.persistence_service.restore_from_snapshot(
            snapshot_id=snapshot_id,
            user_id=user_id,
            create_new_branch=create_new_branch
        )

        # If restoration was successful and the restored step requires user input,
        # the process will automatically be set to user_input_required status
        # No need to start background task here

        # If the restored step is an autonomous step, we can optionally continue processing
        restored_step = result.get("restored_step")
        autonomous_steps = {
            'keyword_analyzing', 'keyword_analyzed', 'persona_generating', 'theme_generating',
            'research_planning', 'researching', 'research_synthesizing', 'research_report_generated',
            'outline_generating', 'writing_sections', 'editing'
        }
        # 注意(legacy-flow): 上記には旧リサーチステップも含めており、
        # 過去のスナップショットを復元した際に自動処理対象とするために残しています。

        if restored_step in autonomous_steps:
            # Optionally auto-continue for autonomous steps
            # For now, we'll let the user manually resume
            pass

        return RestoreSnapshotResponse(**result)

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error restoring process {process_id} from snapshot {snapshot_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore process from snapshot"
        )
