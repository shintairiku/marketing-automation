import { 
  FlexibleOutline,
  LegacyOutline,
  LegacySection,
  OutlineNode,
  OutlineTree
} from "@/types/outline";

// 簡易UUID生成関数
function generateId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // フォールバック: 簡単なランダムID生成
  return 'node-' + Math.random().toString(36).substr(2, 9) + '-' + Date.now().toString(36);
}

/**
 * 旧形式のアウトラインを新形式（ツリー）に変換
 */
export function legacyToTree(legacy: LegacyOutline): OutlineTree {
  const convertSectionToNode = (section: LegacySection, level: number = 2): OutlineNode => {
    // subsections の処理（string/object両対応）
    const children: OutlineNode[] = [];
    if (section.subsections) {
      for (const sub of section.subsections) {
        if (typeof sub === 'string') {
          // string配列の場合
          children.push({
            id: generateId(),
            title: sub,
            level: level + 1,
            children: []
          });
        } else if (typeof sub === 'object') {
          // オブジェクトの場合
          children.push(convertSectionToNode(sub as LegacySection, level + 1));
        }
      }
    }

    return {
      id: generateId(),
      title: section.title || section.heading || "",
      level: level,
      children
    };
  };

  const nodes: OutlineNode[] = (legacy.sections || []).map(section => 
    convertSectionToNode(section, 2)
  );

  return {
    title: legacy.title,
    description: legacy.description,
    suggested_tone: legacy.suggested_tone,
    nodes
  };
}

/**
 * 新形式（ツリー）を旧形式のアウトラインに変換
 * 後方互換性のため必要
 */
export function treeToLegacy(tree: OutlineTree): LegacyOutline {
  const convertNodeToSection = (node: OutlineNode): LegacySection => {
    return {
      heading: node.title,
      title: node.title, // 両フィールドをサポート
      estimated_chars: 0, // デフォルト値
      // subsectionsはstring[]として返す（後方互換）
      subsections: node.children.length > 0 ? 
        node.children.map(child => child.title) as (string | LegacySection)[] : 
        undefined
    };
  };

  return {
    title: tree.title,
    description: tree.description,
    suggested_tone: tree.suggested_tone,
    sections: tree.nodes.map(node => convertNodeToSection(node))
  };
}

/**
 * FlexibleOutlineが新形式か旧形式かを判定
 */
export function isNewFormat(outline: FlexibleOutline): outline is OutlineTree {
  return 'nodes' in outline && Array.isArray(outline.nodes);
}

/**
 * FlexibleOutlineを新形式に正規化
 */
export function normalizeToTree(outline: FlexibleOutline): OutlineTree {
  if (isNewFormat(outline)) {
    return outline;
  } else {
    return legacyToTree(outline);
  }
}

/**
 * アウトラインノードのフラット化（検索・操作用）
 */
export function flattenNodes(nodes: OutlineNode[]): OutlineNode[] {
  const result: OutlineNode[] = [];
  
  const traverse = (nodeList: OutlineNode[]) => {
    for (const node of nodeList) {
      result.push(node);
      if (node.children.length > 0) {
        traverse(node.children);
      }
    }
  };
  
  traverse(nodes);
  return result;
}

/**
 * 指定したIDのノードを検索
 */
export function findNodeById(nodes: OutlineNode[], id: string): OutlineNode | null {
  const flattened = flattenNodes(nodes);
  return flattened.find(node => node.id === id) || null;
}

/**
 * ノードの親を検索
 */
export function findParentNode(nodes: OutlineNode[], targetId: string): OutlineNode | null {
  const search = (nodeList: OutlineNode[]): OutlineNode | null => {
    for (const node of nodeList) {
      if (node.children.some(child => child.id === targetId)) {
        return node;
      }
      const found = search(node.children);
      if (found) return found;
    }
    return null;
  };
  
  return search(nodes);
}

/**
 * ノードの階層レベルを更新（子ノードも含めて）
 */
export function updateNodeLevels(node: OutlineNode, newLevel: number): OutlineNode {
  const levelDiff = newLevel - node.level;
  
  const updateRecursively = (n: OutlineNode): OutlineNode => ({
    ...n,
    level: Math.max(1, Math.min(6, n.level + levelDiff)), // 1-6の範囲に制限
    children: n.children.map(updateRecursively)
  });
  
  return updateRecursively(node);
}

/**
 * ノードを指定インデックスに挿入
 */
export function insertNodeAt(nodes: OutlineNode[], node: OutlineNode, index: number): OutlineNode[] {
  const newNodes = [...nodes];
  newNodes.splice(index, 0, node);
  return newNodes;
}

/**
 * ノードを削除
 */
export function removeNode(nodes: OutlineNode[], targetId: string): OutlineNode[] {
  return nodes.filter(node => node.id !== targetId).map(node => ({
    ...node,
    children: removeNode(node.children, targetId)
  }));
}

/**
 * ノードの親とインデックスを返すユーティリティ
 */
export function findNodeWithParent(
  nodes: OutlineNode[], 
  id: string, 
  parent: OutlineNode | null = null
): { parent: OutlineNode | null; index: number } | null {
  const arr = parent ? parent.children : nodes;
  const idx = arr.findIndex(n => n.id === id);
  if (idx >= 0) return { parent, index: idx };
  
  for (const n of arr) {
    const found = findNodeWithParent(nodes, id, n);
    if (found) return found;
  }
  return null;
}

/**
 * 新しい空のノードを作成
 */
export function createEmptyNode(level: number = 2): OutlineNode {
  return {
    id: generateId(),
    title: "",
    level: Math.max(1, Math.min(6, level)),
    children: []
  };
}