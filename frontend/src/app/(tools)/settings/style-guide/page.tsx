"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Plus, Edit, Trash2, Star, Copy, Settings } from "lucide-react";
import Header from "@/components/display/header";
import Sidebar from "@/components/display/sidebar";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@clerk/nextjs";

interface StyleTemplate {
  id: string;
  name: string;
  description?: string;
  template_type: string;
  settings: Record<string, any>;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

const TEMPLATE_TYPES = [
  { value: "writing_tone", label: "文体・トーン" },
  { value: "vocabulary", label: "語彙・表現" },
  { value: "structure", label: "記事構成" },
  { value: "branding", label: "ブランディング" },
  { value: "seo_focus", label: "SEO重視" },
  { value: "custom", label: "カスタム" }
];

const DEFAULT_SETTINGS = {
  tone: "",
  style: "",
  approach: "",
  vocabulary: "",
  structure: "",
  special_instructions: ""
};

export default function StyleGuideSettingsPage() {
  const { toast } = useToast();
  const { getToken } = useAuth();
  const [templates, setTemplates] = useState<StyleTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState<StyleTemplate | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    template_type: "custom",
    settings: DEFAULT_SETTINGS
  });

  const fetchTemplates = async () => {
    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }
      
      const response = await fetch('/api/proxy/style-templates', {
        headers,
      });
      if (response.ok) {
        const data = await response.json();
        setTemplates(data);
      } else {
        throw new Error('テンプレートの取得に失敗しました');
      }
    } catch (error) {
      toast({
        title: "エラー",
        description: error instanceof Error ? error.message : "テンプレートの取得に失敗しました",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  const handleCreateTemplate = async () => {
    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }
      
      const response = await fetch('/api/proxy/style-templates', {
        method: 'POST',
        headers,
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        toast({
          title: "成功",
          description: "スタイルテンプレートを作成しました",
        });
        setDialogOpen(false);
        resetForm();
        fetchTemplates();
      } else {
        throw new Error('テンプレートの作成に失敗しました');
      }
    } catch (error) {
      toast({
        title: "エラー",
        description: error instanceof Error ? error.message : "テンプレートの作成に失敗しました",
        variant: "destructive",
      });
    }
  };

  const handleUpdateTemplate = async () => {
    if (!editingTemplate) return;

    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }
      
      const response = await fetch(`/api/proxy/style-templates/${editingTemplate.id}`, {
        method: 'PUT',
        headers,
        body: JSON.stringify(formData),
      });

      if (response.ok) {
        toast({
          title: "成功",
          description: "スタイルテンプレートを更新しました",
        });
        setDialogOpen(false);
        setEditingTemplate(null);
        resetForm();
        fetchTemplates();
      } else {
        throw new Error('テンプレートの更新に失敗しました');
      }
    } catch (error) {
      toast({
        title: "エラー",
        description: error instanceof Error ? error.message : "テンプレートの更新に失敗しました",
        variant: "destructive",
      });
    }
  };

  const handleDeleteTemplate = async (templateId: string) => {
    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }
      
      const response = await fetch(`/api/proxy/style-templates/${templateId}`, {
        method: 'DELETE',
        headers,
      });

      if (response.ok) {
        toast({
          title: "成功",
          description: "スタイルテンプレートを削除しました",
        });
        fetchTemplates();
      } else {
        throw new Error('テンプレートの削除に失敗しました');
      }
    } catch (error) {
      toast({
        title: "エラー",
        description: error instanceof Error ? error.message : "テンプレートの削除に失敗しました",
        variant: "destructive",
      });
    }
  };

  const handleSetDefault = async (templateId: string) => {
    try {
      const token = await getToken();
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }
      
      const response = await fetch(`/api/proxy/style-templates/${templateId}/set-default`, {
        method: 'POST',
        headers,
      });

      if (response.ok) {
        toast({
          title: "成功",
          description: "デフォルトテンプレートを設定しました",
        });
        fetchTemplates();
      } else {
        throw new Error('デフォルト設定に失敗しました');
      }
    } catch (error) {
      toast({
        title: "エラー",
        description: error instanceof Error ? error.message : "デフォルト設定に失敗しました",
        variant: "destructive",
      });
    }
  };

  const openCreateDialog = () => {
    resetForm();
    setEditingTemplate(null);
    setDialogOpen(true);
  };

  const openEditDialog = (template: StyleTemplate) => {
    setFormData({
      name: template.name,
      description: template.description || "",
      template_type: template.template_type,
      settings: { ...DEFAULT_SETTINGS, ...template.settings }
    });
    setEditingTemplate(template);
    setDialogOpen(true);
  };

  const resetForm = () => {
    setFormData({
      name: "",
      description: "",
      template_type: "custom",
      settings: DEFAULT_SETTINGS
    });
  };

  const getTypeLabel = (type: string) => {
    return TEMPLATE_TYPES.find(t => t.value === type)?.label || type;
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="flex mt-[45px]">
        <div className="fixed left-0 top-[45px] h-[calc(100vh-45px)]">
          <Sidebar />
        </div>
        <main className="flex-1 ml-[314px] p-5">
          <div className="container mx-auto p-6 space-y-6">
            <div className="flex justify-between items-start">
              <div className="space-y-2">
                <h1 className="text-3xl font-bold">スタイルガイド設定</h1>
                <p className="text-muted-foreground">
                  SEO記事生成で使用するスタイルガイドテンプレートを管理します。
                </p>
              </div>
              <Button onClick={openCreateDialog}>
                <Plus className="h-4 w-4 mr-2" />
                新規作成
              </Button>
            </div>

            <Alert>
              <Settings className="h-4 w-4" />
              <AlertDescription>
                スタイルテンプレートを設定すると、SEO記事生成時にカスタムスタイルを適用できます。
                デフォルト設定では従来のプロンプトが使用されます。
              </AlertDescription>
            </Alert>

            {loading ? (
              <div className="flex justify-center items-center py-16">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
                  <p className="mt-4 text-lg text-gray-600">テンプレートを読み込み中...</p>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {templates.map((template) => (
                  <Card key={template.id} className="overflow-hidden">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <CardTitle className="text-lg">{template.name}</CardTitle>
                            {template.is_default && (
                              <Star className="h-4 w-4 text-yellow-500 fill-yellow-500" />
                            )}
                          </div>
                          <Badge variant="secondary" className="text-xs">
                            {getTypeLabel(template.template_type)}
                          </Badge>
                        </div>
                      </div>
                      {template.description && (
                        <p className="text-sm text-muted-foreground mt-2">
                          {template.description}
                        </p>
                      )}
                    </CardHeader>
                    <CardContent className="pt-0">
                      <div className="space-y-2 mb-4">
                        {template.settings.tone && (
                          <div className="text-xs">
                            <span className="font-medium">トーン:</span> {template.settings.tone}
                          </div>
                        )}
                        {template.settings.style && (
                          <div className="text-xs">
                            <span className="font-medium">文体:</span> {template.settings.style}
                          </div>
                        )}
                        {template.settings.approach && (
                          <div className="text-xs">
                            <span className="font-medium">アプローチ:</span> {template.settings.approach}
                          </div>
                        )}
                      </div>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => openEditDialog(template)}
                          className="flex-1"
                        >
                          <Edit className="h-3 w-3 mr-1" />
                          編集
                        </Button>
                        {!template.is_default && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleSetDefault(template.id)}
                          >
                            <Star className="h-3 w-3" />
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleDeleteTemplate(template.id)}
                          className="text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
                
                {templates.length === 0 && (
                  <div className="col-span-full text-center py-16">
                    <div className="max-w-md mx-auto">
                      <div className="bg-gray-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                        <Settings className="w-8 h-8 text-gray-600" />
                      </div>
                      <h3 className="text-xl font-semibold text-gray-900 mb-2">テンプレートがありません</h3>
                      <p className="text-gray-600">
                        まだスタイルガイドテンプレートが作成されていません。
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </main>
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingTemplate ? 'スタイルテンプレートを編集' : 'スタイルテンプレートを作成'}
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">テンプレート名</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="例: カジュアルトーン"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="template_type">テンプレートタイプ</Label>
                <Select
                  value={formData.template_type}
                  onValueChange={(value) => setFormData({ ...formData, template_type: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TEMPLATE_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="description">説明</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="このテンプレートの説明"
                rows={2}
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="tone">トーン・調子</Label>
                <Input
                  id="tone"
                  value={formData.settings.tone}
                  onChange={(e) => setFormData({ 
                    ...formData, 
                    settings: { ...formData.settings, tone: e.target.value }
                  })}
                  placeholder="例: 親しみやすく分かりやすい"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="style">文体</Label>
                <Input
                  id="style"
                  value={formData.settings.style}
                  onChange={(e) => setFormData({ 
                    ...formData, 
                    settings: { ...formData.settings, style: e.target.value }
                  })}
                  placeholder="例: ですます調"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="approach">アプローチ・方針</Label>
              <Input
                id="approach"
                value={formData.settings.approach}
                onChange={(e) => setFormData({ 
                  ...formData, 
                  settings: { ...formData.settings, approach: e.target.value }
                })}
                placeholder="例: 読者に寄り添う"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="vocabulary">語彙・表現の指針</Label>
              <Textarea
                id="vocabulary"
                value={formData.settings.vocabulary}
                onChange={(e) => setFormData({ 
                  ...formData, 
                  settings: { ...formData.settings, vocabulary: e.target.value }
                })}
                placeholder="例: 専門用語を避け、簡単な言葉で説明"
                rows={2}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="structure">記事構成の指針</Label>
              <Textarea
                id="structure"
                value={formData.settings.structure}
                onChange={(e) => setFormData({ 
                  ...formData, 
                  settings: { ...formData.settings, structure: e.target.value }
                })}
                placeholder="例: 見出しを使って情報を整理"
                rows={2}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="special_instructions">特別な指示</Label>
              <Textarea
                id="special_instructions"
                value={formData.settings.special_instructions}
                onChange={(e) => setFormData({ 
                  ...formData, 
                  settings: { ...formData.settings, special_instructions: e.target.value }
                })}
                placeholder="例: 具体例や体験談を交えて説得力を持たせる"
                rows={3}
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              キャンセル
            </Button>
            <Button onClick={editingTemplate ? handleUpdateTemplate : handleCreateTemplate}>
              {editingTemplate ? '更新' : '作成'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}