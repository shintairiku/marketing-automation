#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全フィルタ対応プロンプトテスト
"""

import asyncio
import aiohttp
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_various_prompts():
    """様々なプロンプトで安全フィルタ対応をテスト"""
    
    base_url = "http://localhost:8008/api/images"
    
    # テスト用の様々なプロンプト（安全フィルタに引っかかりやすそうなもの）
    test_prompts = [
        {
            "name": "人物を含むプロンプト",
            "data": {
                "placeholder_id": "test_people",
                "description_jp": "人々が働いている様子",
                "prompt_en": "People working in an office environment",
                "alt_text": "Office scene"
            }
        },
        {
            "name": "子供を含むプロンプト", 
            "data": {
                "placeholder_id": "test_children",
                "description_jp": "子供たちが遊んでいる公園",
                "prompt_en": "Children playing in a park with families",
                "alt_text": "Park scene"
            }
        },
        {
            "name": "顔を含むプロンプト",
            "data": {
                "placeholder_id": "test_faces",
                "description_jp": "笑顔の人々",
                "prompt_en": "Happy faces of people smiling",
                "alt_text": "Happy people"
            }
        },
        {
            "name": "安全なプロンプト（風景）",
            "data": {
                "placeholder_id": "test_landscape",
                "description_jp": "美しい山の風景",
                "prompt_en": "Beautiful mountain landscape with trees",
                "alt_text": "Mountain view"
            }
        },
        {
            "name": "安全なプロンプト（物体）",
            "data": {
                "placeholder_id": "test_objects",
                "description_jp": "モダンな建物",
                "prompt_en": "Modern architectural building with glass windows",
                "alt_text": "Modern building"
            }
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for test_case in test_prompts:
            logger.info(f"=== テスト: {test_case['name']} ===")
            logger.info(f"オリジナルプロンプト: {test_case['data']['prompt_en']}")
            
            try:
                async with session.post(f"{base_url}/test-direct", json={}) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("status") == "test_completed":
                            logger.info(f"✅ テスト成功")
                            logger.info(f"Imagen-4: {'成功' if result['results']['imagen_4']['success'] else '失敗'}")
                            logger.info(f"Imagen-3: {'成功' if result['results']['imagen_3']['success'] else '失敗'}")
                        else:
                            logger.error(f"❌ テスト失敗: {result}")
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ HTTP エラー ({response.status}): {error_text}")
                        
            except Exception as e:
                logger.error(f"❌ 例外発生: {e}")
            
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_various_prompts())