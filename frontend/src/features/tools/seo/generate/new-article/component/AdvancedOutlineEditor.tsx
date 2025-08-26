'use client';

import { useCallback,useState } from 'react';
import { AnimatePresence,motion } from 'framer-motion';
import {
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  Edit3,
  GripVertical,
  Plus,
  Trash2,
  X
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { 
  FlexibleOutline,
  OutlineNode, 
  OutlineTree} from '@/types/outline';
import {
  createEmptyNode,
  findNodeById,
  findNodeWithParent,
  insertNodeAt,
  normalizeToTree,
  removeNode,
  treeToLegacy,
  updateNodeLevels} from '@/utils/outline-convert';

interface AdvancedOutlineEditorProps {
  outline: FlexibleOutline;
  onSave: (editedOutline: any) => void;
  onCancel: () => void;
}

interface NodeEditState {
  nodeId: string | null;
  value: string;
}

export default function AdvancedOutlineEditor({
  outline,
  onSave,
  onCancel
}: AdvancedOutlineEditorProps) {
  // 新形式に正規化
  const [tree, setTree] = useState<OutlineTree>(() => normalizeToTree(outline));
  const [editState, setEditState] = useState<NodeEditState>({ nodeId: null, value: '' });

  // ノードの移動処理
  const moveNode = useCallback((nodeId: string, direction: 'up' | 'down') => {
    setTree(prevTree => {
      const findAndMoveInArray = (nodes: OutlineNode[], parentArray: OutlineNode[]): OutlineNode[] => {
        const index = nodes.findIndex(n => n.id === nodeId);
        if (index >= 0) {
          const newNodes = [...nodes];
          const targetIndex = direction === 'up' ? index - 1 : index + 1;
          
          if (targetIndex >= 0 && targetIndex < newNodes.length) {
            // 要素を交換
            [newNodes[index], newNodes[targetIndex]] = [newNodes[targetIndex], newNodes[index]];
          }
          return newNodes;
        }
        
        // 子ノードを再帰的に検索
        return nodes.map(node => ({
          ...node,
          children: findAndMoveInArray(node.children, nodes)
        }));
      };

      return {
        ...prevTree,
        nodes: findAndMoveInArray(prevTree.nodes, prevTree.nodes)
      };
    });
  }, []);

  // ノードのインデント処理（実構造変更）
  const indentNode = useCallback((nodeId: string, direction: 'left' | 'right') => {
    setTree(prevTree => {
      // 構造を変更可能にするため deep clone
      const cloned = JSON.parse(JSON.stringify(prevTree)) as OutlineTree;
      const loc = findNodeWithParent(cloned.nodes, nodeId);
      if (!loc) return prevTree;

      const parentArr = loc.parent ? loc.parent.children : cloned.nodes;
      const node = parentArr.splice(loc.index, 1)[0];

      if (direction === 'right') {
        // 右インデント：直前の兄弟の子にする
        if (loc.index === 0) { 
          // 最初のノードは右インデントできない
          parentArr.splice(loc.index, 0, node); 
          return prevTree; 
        }
        const prevSibling = parentArr[loc.index - 1];
        prevSibling.children.push(updateNodeLevels(node, prevSibling.level + 1));
      } else {
        // 左インデント：親の兄弟にする
        if (!loc.parent) { 
          // ルートレベルは左インデントできない
          parentArr.splice(loc.index, 0, node); 
          return prevTree; 
        }
        const grandLoc = findNodeWithParent(cloned.nodes, loc.parent.id);
        const grandArr = grandLoc?.parent ? grandLoc.parent.children : cloned.nodes;
        const insertAt = (grandLoc ? grandLoc.index : cloned.nodes.indexOf(loc.parent)) + 1;
        grandArr.splice(insertAt, 0, updateNodeLevels(node, (grandLoc?.parent ? grandLoc.parent.level : 0) + 1));
      }
      return cloned;
    });
  }, []);

  // ノード追加
  const addNode = useCallback((afterNodeId?: string, asChild: boolean = false) => {
    const newNode = createEmptyNode();
    
    setTree(prevTree => {
      if (!afterNodeId) {
        // ルートレベルに追加
        return {
          ...prevTree,
          nodes: [...prevTree.nodes, newNode]
        };
      }

      const addNodeRecursively = (nodes: OutlineNode[]): OutlineNode[] => {
        return nodes.map(node => {
          if (node.id === afterNodeId) {
            if (asChild) {
              // 子として追加
              return {
                ...node,
                children: [...node.children, { ...newNode, level: node.level + 1 }]
              };
            } else {
              // 兄弟として追加（同レベル）
              return node;
            }
          }
          return {
            ...node,
            children: addNodeRecursively(node.children)
          };
        });
      };

      if (asChild) {
        return {
          ...prevTree,
          nodes: addNodeRecursively(prevTree.nodes)
        };
      } else {
        // 兄弟として追加する場合、配列レベルで処理
        const insertAt = (nodeList: OutlineNode[]): OutlineNode[] => {
          const index = nodeList.findIndex(n => n.id === afterNodeId);
          if (index >= 0) {
            const referenceNode = nodeList[index];
            return insertNodeAt(nodeList, { ...newNode, level: referenceNode.level }, index + 1);
          }
          return nodeList.map(node => ({
            ...node,
            children: insertAt(node.children)
          }));
        };

        return {
          ...prevTree,
          nodes: insertAt(prevTree.nodes)
        };
      }
    });

    // 新しいノードを編集状態にする
    setEditState({ nodeId: newNode.id, value: '' });
  }, []);

  // ノード削除
  const deleteNode = useCallback((nodeId: string) => {
    setTree(prevTree => ({
      ...prevTree,
      nodes: removeNode(prevTree.nodes, nodeId)
    }));
  }, []);

  // ノード編集開始
  const startEditNode = useCallback((node: OutlineNode) => {
    setEditState({ nodeId: node.id, value: node.title });
  }, []);

  // ノード編集キャンセル
  const cancelEditNode = useCallback(() => {
    if (editState.nodeId) {
      // 空のノードだった場合は削除
      const node = findNodeById(tree.nodes, editState.nodeId);
      if (node && !node.title.trim()) {
        deleteNode(editState.nodeId);
      }
    }
    setEditState({ nodeId: null, value: '' });
  }, [editState.nodeId, tree.nodes, deleteNode]);

  // ノード編集完了
  const finishEditNode = useCallback(() => {
    if (!editState.nodeId || !editState.value.trim()) {
      cancelEditNode();
      return;
    }

    setTree(prevTree => {
      const updateNodeTitle = (nodes: OutlineNode[]): OutlineNode[] => {
        return nodes.map(node => {
          if (node.id === editState.nodeId) {
            return { ...node, title: editState.value.trim() };
          }
          return {
            ...node,
            children: updateNodeTitle(node.children)
          };
        });
      };

      return {
        ...prevTree,
        nodes: updateNodeTitle(prevTree.nodes)
      };
    });

    setEditState({ nodeId: null, value: '' });
  }, [editState, cancelEditNode]);

  // ノード描画（再帰）
  const renderNode = useCallback((node: OutlineNode, index: number, siblings: OutlineNode[]) => {
    const isEditing = editState.nodeId === node.id;
    const canMoveUp = index > 0;
    const canMoveDown = index < siblings.length - 1;
    const canIndentLeft = node.level > 1;
    const canIndentRight = node.level < 6;

    return (
      <motion.div
        key={node.id}
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
        className="group"
      >
        <div 
          className="flex items-center gap-2 p-2 rounded-lg border border-gray-200 bg-white hover:shadow-sm transition-all"
          style={{ marginLeft: `${(node.level - 1) * 20}px` }}
        >
          {/* ドラッグハンドル */}
          <div className="opacity-0 group-hover:opacity-100 transition-opacity">
            <GripVertical className="w-4 h-4 text-gray-400" />
          </div>

          {/* レベル表示 */}
          <Badge variant="outline" className="text-xs px-1 py-0">
            H{node.level}
          </Badge>

          {/* タイトル編集 */}
          <div className="flex-1">
            {isEditing ? (
              <div className="flex items-center gap-2">
                <Input
                  value={editState.value}
                  onChange={(e) => setEditState(prev => ({ ...prev, value: e.target.value }))}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') finishEditNode();
                    if (e.key === 'Escape') cancelEditNode();
                  }}
                  className="text-sm h-7"
                  autoFocus
                  placeholder="見出しを入力..."
                />
                <Button size="sm" variant="ghost" onClick={finishEditNode} className="h-6 w-6 p-0">
                  <Check className="w-3 h-3" />
                </Button>
                <Button size="sm" variant="ghost" onClick={cancelEditNode} className="h-6 w-6 p-0">
                  <X className="w-3 h-3" />
                </Button>
              </div>
            ) : (
              <div 
                className="text-sm cursor-pointer hover:bg-gray-50 px-2 py-1 rounded"
                onClick={() => startEditNode(node)}
              >
                {node.title || '(空の見出し)'}
              </div>
            )}
          </div>

          {/* 操作ボタン群 */}
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            {/* 上下移動 */}
            <Button
              size="sm"
              variant="ghost"
              onClick={() => moveNode(node.id, 'up')}
              disabled={!canMoveUp}
              className="h-6 w-6 p-0"
            >
              <ChevronUp className="w-3 h-3" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => moveNode(node.id, 'down')}
              disabled={!canMoveDown}
              className="h-6 w-6 p-0"
            >
              <ChevronDown className="w-3 h-3" />
            </Button>

            {/* インデント */}
            <Button
              size="sm"
              variant="ghost"
              onClick={() => indentNode(node.id, 'left')}
              disabled={!canIndentLeft}
              className="h-6 w-6 p-0"
            >
              <ChevronLeft className="w-3 h-3" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => indentNode(node.id, 'right')}
              disabled={!canIndentRight}
              className="h-6 w-6 p-0"
            >
              <ChevronRight className="w-3 h-3" />
            </Button>

            {/* 追加・削除 */}
            <Button
              size="sm"
              variant="ghost"
              onClick={() => addNode(node.id, false)}
              className="h-6 w-6 p-0"
            >
              <Plus className="w-3 h-3" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => addNode(node.id, true)}
              className="h-6 w-6 p-0"
              title="子見出しを追加"
            >
              <Plus className="w-3 h-3" />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => deleteNode(node.id)}
              className="h-6 w-6 p-0 text-red-500 hover:text-red-700"
            >
              <Trash2 className="w-3 h-3" />
            </Button>
          </div>
        </div>

        {/* 子ノード */}
        <AnimatePresence>
          {node.children.length > 0 && (
            <div className="mt-1">
              {node.children.map((child, childIndex) => 
                renderNode(child, childIndex, node.children)
              )}
            </div>
          )}
        </AnimatePresence>
      </motion.div>
    );
  }, [editState, moveNode, indentNode, addNode, deleteNode, startEditNode, finishEditNode, cancelEditNode]);

  const handleSave = () => {
    // 後方互換はサーバ側のconverterが担保するため、ツリー形式で送信
    onSave(tree);
  };

  return (
    <Card>
      <CardContent className="p-4">
        <div className="mb-4">
          <h3 className="text-lg font-semibold mb-2">アウトライン編集</h3>
          <p className="text-sm text-gray-600">
            見出しをクリックして編集、ボタンで構造を変更できます
          </p>
        </div>

        {/* タイトル編集 */}
        <div className="mb-4">
          <label className="text-sm font-medium block mb-1">記事タイトル</label>
          <Input
            value={tree.title || ''}
            onChange={(e) => setTree(prev => ({ ...prev, title: e.target.value }))}
            placeholder="記事のタイトルを入力..."
          />
        </div>

        {/* 推奨トーン編集 */}
        <div className="mb-4">
          <label className="text-sm font-medium block mb-1">推奨トーン</label>
          <Input
            value={tree.suggested_tone || ''}
            onChange={(e) => setTree(prev => ({ ...prev, suggested_tone: e.target.value }))}
            placeholder="記事のトーンを入力（例：丁寧な解説調）..."
          />
        </div>

        {/* トップレベル（執筆基準） */}
        <div className="mb-4">
          <label className="text-sm font-medium block mb-1">トップレベル見出し（執筆の基準）</label>
          <select
            className="w-full border border-gray-300 rounded-md p-2 text-sm"
            value={tree.base_level ?? 2}
            onChange={(e) => setTree(prev => ({ ...prev, base_level: parseInt(e.target.value, 10) }))}
          >
            <option value={1}>H1</option>
            <option value={2}>H2（推奨）</option>
            <option value={3}>H3</option>
            <option value={4}>H4</option>
            <option value={5}>H5</option>
            <option value={6}>H6</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            未指定でも可（既定=H2 / サーバで自動判定）。H1は記事タイトル用を推奨。
          </p>
        </div>

        {/* アウトラインツリー */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium">セクション構成</label>
            <Button size="sm" onClick={() => addNode()} variant="outline">
              <Plus className="w-4 h-4 mr-1" />
              セクション追加
            </Button>
          </div>
          
          <div className="space-y-1 max-h-96 overflow-y-auto">
            <AnimatePresence>
              {tree.nodes.map((node, index) => 
                renderNode(node, index, tree.nodes)
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* 操作ガイド */}
        <div className="mb-4 p-3 bg-gray-50 rounded-lg text-xs text-gray-600">
          <p><strong>操作方法:</strong></p>
          <ul className="mt-1 space-y-1">
            <li>• 見出しをクリックして編集</li>
            <li>• ↑↓で順序変更、←→で階層変更</li>
            <li>• +で同レベル追加、++で子レベル追加</li>
            <li>• 🗑️で削除</li>
          </ul>
        </div>

        {/* 保存・キャンセルボタン */}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onCancel}>
            キャンセル
          </Button>
          <Button onClick={handleSave}>
            保存して進む
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}