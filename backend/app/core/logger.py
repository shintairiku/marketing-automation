# -*- coding: utf-8 -*-
"""
アプリケーション用ロガー設定
"""

import logging
import sys
from pathlib import Path
from typing import Optional

def setup_logger(
    name: str = "saas-api",
    level: int = logging.INFO,
    log_file: Optional[str] = None
) -> logging.Logger:
    """ロガーをセットアップする"""
    
    # ロガーを作成
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 既存のハンドラーがある場合はクリア
    if logger.handlers:
        logger.handlers.clear()
    
    # フォーマッターを作成
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # コンソールハンドラーを追加
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラーを追加（指定されている場合）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

# デフォルトロガーを作成
logger = setup_logger()