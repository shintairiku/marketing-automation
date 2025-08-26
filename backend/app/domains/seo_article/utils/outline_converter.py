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
        """旧形式を新形式に変換（string配列対応）"""
        if isinstance(legacy_outline, OutlineData):
            legacy_dict = legacy_outline.model_dump()
        else:
            legacy_dict = legacy_outline
            
        def convert_section_to_node(section: Dict[str, Any], level: int = 2) -> OutlineNodeData:
            """セクションをノードに変換（string/dict両対応）"""
            subs = section.get('subsections', []) or []
            children = []
            for sub in subs:
                if isinstance(sub, str):
                    # string配列の場合
                    children.append(OutlineNodeData(
                        id=str(uuid.uuid4()),
                        title=sub,
                        level=level + 1,
                        children=[]
                    ))
                elif isinstance(sub, dict):
                    # オブジェクトの場合
                    children.append(convert_section_to_node(sub, level + 1))
            
            return OutlineNodeData(
                id=str(uuid.uuid4()),
                title=section.get('heading', section.get('title', '')),
                level=level,
                children=children
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
    def decide_base_level(tree: OutlineTreeData) -> int:
        """
        ツリーから執筆基準レベルを決定する。
        - base_level が指定されていればそれを優先
        - ルートに level==1 が1つだけ && 子が存在 → H1 は記事タイトルとみなし H2 起点
        - それ以外は ルートノードの最小 level を採用
        - 最終的に [1..6] にクリップし、デフォルトは 2
        """
        if getattr(tree, "base_level", None):
            return max(1, min(6, int(tree.base_level)))  # 明示優先
        
        levels = [n.level for n in tree.nodes] or [2]
        has_single_h1 = sum(1 for n in tree.nodes if n.level == 1) == 1
        
        if has_single_h1:
            # 単一 H1 はタイトルと推定。子がいれば H2 起点
            return 2
        
        return max(1, min(6, min(levels)))

    @staticmethod
    def tree_to_legacy(tree_outline: Union[Dict[str, Any], OutlineTreeData]) -> OutlineData:
        """新形式を旧形式に変換（subsectionsをstring[]で返す）"""
        if isinstance(tree_outline, OutlineTreeData):
            tree_dict = tree_outline.model_dump()
        else:
            tree_dict = tree_outline
            
        def convert_node_to_section(node: Dict[str, Any]) -> OutlineSectionData:
            """ノードをセクションに変換（subsectionsはOutlineSectionData[]）"""
            # 子ノードをOutlineSectionDataオブジェクトとして変換
            child_sections = []
            for child in node.get('children', []):
                if child:
                    child_sections.append(OutlineSectionData(
                        heading=child.get('title', ''),
                        estimated_chars=0,
                        subsections=None  # 深い階層は一旦無視
                    ))
            
            return OutlineSectionData(
                heading=node.get('title', ''),
                estimated_chars=0,  # デフォルト値
                subsections=child_sections if child_sections else None
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
    def tree_to_legacy_for_writing(tree_outline: Union[Dict[str, Any], OutlineTreeData],
                                   prefer_base_level: Optional[int] = None) -> OutlineData:
        """執筆都合に合わせて新形式→旧形式に安全変換（トップレベルを決定して sections を構築）"""
        if isinstance(tree_outline, OutlineTreeData):
            tree_dict = tree_outline.model_dump()
        else:
            tree_dict = tree_outline

        # 決定的にトップレベルを選ぶ
        tree = OutlineTreeData(**tree_dict)
        base_level = prefer_base_level or OutlineConverter.decide_base_level(tree)

        def is_top(node: Dict[str, Any]) -> bool:
            return int(node.get("level", 2)) == base_level

        def to_section(node: Dict[str, Any]) -> OutlineSectionData:
            # 直下の子（base_level+1）を subsections に、それより深いものは本文プロンプト側に委譲
            child_sections = []
            for child in node.get("children", []):
                lvl = int(child.get("level", base_level + 1))
                if lvl == base_level + 1:
                    # OutlineSectionDataオブジェクトとして作成
                    child_sections.append(OutlineSectionData(
                        heading=child.get("title", ""),
                        estimated_chars=0,
                        subsections=None  # さらに深い階層は一旦無視
                    ))
                # さらに深い場合は一旦無視（本文生成プロンプトで対応）
            
            return OutlineSectionData(
                heading=node.get("title", ""),
                estimated_chars=0,
                subsections=child_sections if child_sections else None
            )

        top_nodes = [n for n in tree_dict.get("nodes", []) if is_top(n)]
        
        # H1 only で子が H2 のときなど、トップ候補が空なら子を昇格
        if not top_nodes and tree_dict.get("nodes"):
            for n in tree_dict["nodes"]:
                for c in n.get("children", []):
                    if int(c.get("level", 9)) == base_level:
                        top_nodes.append(c)

        sections = [to_section(n) for n in top_nodes]
        
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
    def validate_and_convert(edited_content: Dict[str, Any], prefer_base_level: Optional[int] = None) -> OutlineData:
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
            
            # 最終的に legacy へ（執筆用ポリシーを反映）
            return OutlineConverter.tree_to_legacy_for_writing(tree, prefer_base_level)
            
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