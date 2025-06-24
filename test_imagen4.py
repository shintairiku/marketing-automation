#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Imagen-4.0テスト用スクリプト
"""

import asyncio
import json
import aiohttp
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_imagen_models():
    """Imagen-4.0とImagen-3.0の両方をテストする"""
    
    # テスト用認証トークン（実際の環境では適切なトークンを使用）
    test_token = "test-token"
    
    # テスト用データ
    test_data = {
        "placeholder_id": "test_placeholder_" + str(asyncio.get_event_loop().time()),
        "description_jp": "テスト画像",
        "prompt_en": "A beautiful mountain landscape with snow-capped peaks and clear blue sky, professional photography",
        "alt_text": "Mountain landscape"
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {test_token}"
    }
    
    base_url = "http://localhost:8008/api/images"
    
    async with aiohttp.ClientSession() as session:
        
        # 1. 設定テスト
        logger.info("=== 設定テスト ===")
        async with session.get(f"{base_url}/test-config") as response:
            config_result = await response.json()
            logger.info(f"設定: {json.dumps(config_result, indent=2, ensure_ascii=False)}")
        
        # 2. Imagen-4.0テスト
        logger.info("=== Imagen-4.0テスト ===")
        try:
            async with session.post(f"{base_url}/test-imagen4", headers=headers, json=test_data) as response:
                if response.status == 200:
                    imagen4_result = await response.json()
                    logger.info(f"Imagen-4.0成功: {json.dumps(imagen4_result, indent=2, ensure_ascii=False)}")
                else:
                    error_text = await response.text()
                    logger.error(f"Imagen-4.0失敗 (status: {response.status}): {error_text}")
        except Exception as e:
            logger.error(f"Imagen-4.0エラー: {e}")
        
        # 3. Imagen-3.0テスト
        logger.info("=== Imagen-3.0テスト ===")
        try:
            async with session.post(f"{base_url}/test-imagen3", headers=headers, json=test_data) as response:
                if response.status == 200:
                    imagen3_result = await response.json()
                    logger.info(f"Imagen-3.0成功: {json.dumps(imagen3_result, indent=2, ensure_ascii=False)}")
                else:
                    error_text = await response.text()
                    logger.error(f"Imagen-3.0失敗 (status: {response.status}): {error_text}")
        except Exception as e:
            logger.error(f"Imagen-3.0エラー: {e}")
        
        # 4. デフォルト（フォールバック付き）テスト
        logger.info("=== デフォルト（フォールバック付き）テスト ===")
        try:
            async with session.post(f"{base_url}/generate", headers=headers, json=test_data) as response:
                if response.status == 200:
                    default_result = await response.json()
                    logger.info(f"デフォルト成功: {json.dumps(default_result, indent=2, ensure_ascii=False)}")
                else:
                    error_text = await response.text()
                    logger.error(f"デフォルト失敗 (status: {response.status}): {error_text}")
        except Exception as e:
            logger.error(f"デフォルトエラー: {e}")

if __name__ == "__main__":
    asyncio.run(test_imagen_models())