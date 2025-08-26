# -*- coding: utf-8 -*-
"""
アウトライン形式変換ユーティリティ
旧形式（sections/subsections）と新形式（OutlineTree）間の変換を提供
"""

import logging
import uuid
from typing import Any, Dict, List, Union, Optional

from app.domains.seo_article.schemas import (
    OutlineData, OutlineSectionData, OutlineTreeData, OutlineNodeData
)

logger = logging.getLogger(__name__)

class OutlineConverter:
    """アウトライン形式変換ユーティリティクラス"""
    
    @staticmethod
    def is_new_format(data: Dict[str, Any]) -> bool:
        """データが新形式（OutlineTree）かどうかを判定"""
        return 'nodes' in data and isinstance(data.get('nodes'), list)
    
    @staticmethod
    def legacy_to_tree(legacy_outline: Union[Dict[str, Any], OutlineData]) -> OutlineTreeData:
        """旧形式を新形式に変換"""
        if isinstance(legacy_outline, OutlineData):
            legacy_dict = legacy_outline.model_dump()
        else:
            legacy_dict = legacy_outline
            
        def convert_section_to_node(section: Dict[str, Any], level: int = 2) -> OutlineNodeData:
            """セクションをノードに変換"""
            return OutlineNodeData(
                id=str(uuid.uuid4()),
                title=section.get('heading', section.get('title', '')),
                level=level,
                children=[
                    convert_section_to_node(subsection, level + 1)
                    for subsection in section.get('subsections', [])
                ]
            )
        
        # セクションをノードに変換
        nodes = []
        for section in legacy_dict.get('sections', []):
            nodes.append(convert_section_to_node(section, 2))
        
        return OutlineTreeData(
            title=legacy_dict.get('title'),
            description=legacy_dict.get('description'),
            suggested_tone=legacy_dict.get('suggested_tone'),
            nodes=nodes
        )
    
    @staticmethod
    def tree_to_legacy(tree_outline: Union[Dict[str, Any], OutlineTreeData]) -> OutlineData:
        """新形式を旧形式に変換（後方互換性のため）"""
        if isinstance(tree_outline, OutlineTreeData):
            tree_dict = tree_outline.model_dump()
        else:
            tree_dict = tree_outline
            
        def convert_node_to_section(node: Dict[str, Any]) -> OutlineSectionData:
            """ノードをセクションに変換"""
            return OutlineSectionData(
                heading=node.get('title', ''),
                estimated_chars=0,  # デフォルト値
                subsections=[
                    convert_node_to_section(child)
                    for child in node.get('children', [])
                ] if node.get('children') else None
            )
        
        # ノードをセクションに変換
        sections = []
        for node in tree_dict.get('nodes', []):
            sections.append(convert_node_to_section(node))
        
        return OutlineData(
            title=tree_dict.get('title', ''),
            suggested_tone=tree_dict.get('suggested_tone', ''),
            sections=sections
        )
    
    @staticmethod
    def normalize_to_tree(outline_data: Dict[str, Any]) -> OutlineTreeData:
        """任意のアウトライン形式を新形式に正規化"""
        try:
            if OutlineConverter.is_new_format(outline_data):
                # 既に新形式
                logger.info("アウトラインは既に新形式です")
                return OutlineTreeData(**outline_data)
            else:
                # 旧形式から変換
                logger.info("旧形式のアウトラインを新形式に変換中")
                return OutlineConverter.legacy_to_tree(outline_data)
        except Exception as e:
            logger.error(f"アウトライン正規化エラー: {e}")
            # エラー時は空のツリーを返す
            return OutlineTreeData(
                title=outline_data.get('title', ''),
                suggested_tone=outline_data.get('suggested_tone', ''),
                nodes=[]
            )
    
    @staticmethod
    def validate_and_convert(edited_content: Dict[str, Any]) -> OutlineData:
        """
        編集されたアウトラインを検証し、標準形式に変換
        edit_and_proceed で受信したデータの処理用
        """
        try:
            # まず新形式に正規化
            tree = OutlineConverter.normalize_to_tree(edited_content)
            
            # 検証: 空のタイトルをチェック
            if not tree.title or not tree.title.strip():
                logger.warning("アウトラインタイトルが空です")
                tree.title = "無題の記事"
            
            # 検証: ノードの妥当性チェック
            def validate_node(node: OutlineNodeData) -> bool:
                if not node.title or not node.title.strip():
                    return False
                if not (1 <= node.level <= 6):
                    return False
                return all(validate_node(child) for child in node.children)
            
            # 無効なノードを除外
            tree.nodes = [node for node in tree.nodes if validate_node(node)]
            
            # 最終的に旧形式に変換して返す（既存システムとの互換性のため）
            return OutlineConverter.tree_to_legacy(tree)
            
        except Exception as e:
            logger.error(f"アウトライン変換・検証エラー: {e}")
            raise ValueError(f"Invalid outline format: {e}")
    
    @staticmethod
    def flatten_nodes(nodes: List[OutlineNodeData]) -> List[OutlineNodeData]:
        """ノードをフラット化（検索・操作用）"""
        result = []
        
        def traverse(node_list: List[OutlineNodeData]):
            for node in node_list:
                result.append(node)
                if node.children:
                    traverse(node.children)
        
        traverse(nodes)
        return result
    
    @staticmethod
    def count_sections(outline: Union[OutlineData, OutlineTreeData]) -> int:
        """セクション数をカウント"""
        if isinstance(outline, OutlineTreeData):
            return len(OutlineConverter.flatten_nodes(outline.nodes))
        else:
            return len(outline.sections) + sum(
                len(section.subsections or []) 
                for section in outline.sections
            )