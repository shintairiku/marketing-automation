# -*- coding: utf-8 -*-
import os
from fastapi import APIRouter

# 各ドメインのエンドポイントをインポート
from app.domains.seo_article.endpoints import router as seo_article_router
from app.domains.organization.endpoints import router as organization_router
from app.domains.company.endpoints import router as company_router
from app.domains.style_template.endpoints import router as style_template_router
from app.domains.image_generation.endpoints import router as image_generation_router

api_router = APIRouter()

# 各ルーターをインクルード
api_router.include_router(seo_article_router, prefix="/articles", tags=["SEO Article"])
# api_router.include_router(article_flow_router, prefix="/article-flows", tags=["Article Flows"]) # article_routerに統合
api_router.include_router(organization_router, prefix="/organizations", tags=["Organizations"])
api_router.include_router(company_router, prefix="/companies", tags=["Companies"])
api_router.include_router(style_template_router, prefix="/style-templates", tags=["Style Templates"])
api_router.include_router(image_generation_router, prefix="/images", tags=["Image Generation"])

# デバッグコンソール（ENABLE_DEBUG_CONSOLE=true のときのみ有効化）
if os.getenv("ENABLE_DEBUG_CONSOLE", "").lower() == "true":
    try:
        from app.api.routes.debug_console import router as debug_console_router
        api_router.include_router(debug_console_router, prefix="/debug", tags=["Debug"])
    except Exception as e:
        print(f"[debug_console] ルーター登録に失敗しました: {e}")

# 今後、Instagram機能などを追加する場合は、ここに一行追加するだけでよい
# from app.domains.instagram.endpoints import router as instagram_router
# api_router.include_router(instagram_router, prefix="/instagram", tags=["Instagram"])
