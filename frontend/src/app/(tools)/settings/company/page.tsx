"use client";

import { useEffect,useState } from "react";
import { AlertCircle, Building2, Check,ChevronDown, ChevronUp, Pencil, Plus, Star, Trash2 } from "lucide-react";
import { toast } from "sonner";

import Header from "@/components/display/header";
import Sidebar from "@/components/display/sidebar";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription,CardHeader, CardTitle } from "@/components/ui/card";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

// 型定義
interface CompanyInfo {
  id: string;
  name: string;
  website_url: string;
  description: string;
  usp: string;
  target_persona: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
  // 詳細設定（任意項目）
  brand_slogan?: string;
  target_keywords?: string;
  industry_terms?: string;
  avoid_terms?: string;
  popular_articles?: string;
  target_area?: string;
}

interface CompanyFormData {
  name: string;
  website_url: string;
  description: string;
  usp: string;
  target_persona: string;
  is_default?: boolean;
  brand_slogan?: string;
  target_keywords?: string;
  industry_terms?: string;
  avoid_terms?: string;
  popular_articles?: string;
  target_area?: string;
}

export default function CompanySettingsPage() {
  const [companies, setCompanies] = useState<CompanyInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCompany, setSelectedCompany] = useState<CompanyInfo | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // フォームデータ
  const [formData, setFormData] = useState<CompanyFormData>({
    name: "",
    website_url: "",
    description: "",
    usp: "",
    target_persona: "",
    is_default: false,
    brand_slogan: "",
    target_keywords: "",
    industry_terms: "",
    avoid_terms: "",
    popular_articles: "",
    target_area: ""
  });

  // 会社一覧を取得
  const fetchCompanies = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/companies/');
      
      if (!response.ok) {
        throw new Error('Failed to fetch companies');
      }
      const data = await response.json();
      setCompanies(data.companies || []);
    } catch (error) {
      console.error('Error fetching companies:', error);
      toast.error('会社情報の取得に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // 初回読み込み
  useEffect(() => {
    fetchCompanies();
  }, []);

  // フォームリセット
  const resetForm = () => {
    setFormData({
      name: "",
      website_url: "",
      description: "",
      usp: "",
      target_persona: "",
      is_default: false,
      brand_slogan: "",
      target_keywords: "",
      industry_terms: "",
      avoid_terms: "",
      popular_articles: "",
      target_area: ""
    });
    setSelectedCompany(null);
    setIsEditing(false);
    setShowAdvanced(false);
  };

  // 編集開始
  const startEdit = (company: CompanyInfo) => {
    setSelectedCompany(company);
    setFormData({
      name: company.name,
      website_url: company.website_url,
      description: company.description,
      usp: company.usp,
      target_persona: company.target_persona,
      is_default: company.is_default,
      brand_slogan: company.brand_slogan || "",
      target_keywords: company.target_keywords || "",
      industry_terms: company.industry_terms || "",
      avoid_terms: company.avoid_terms || "",
      popular_articles: company.popular_articles || "",
      target_area: company.target_area || ""
    });
    setIsEditing(true);
    setIsDialogOpen(true);
  };

  // 会社情報の保存
  const saveCompany = async () => {
    // バリデーション
    if (!formData.name || !formData.website_url || !formData.description || !formData.usp || !formData.target_persona) {
      toast.error('必須項目をすべて入力してください');
      return;
    }

    // URL形式チェック
    try {
      new URL(formData.website_url);
    } catch {
      toast.error('有効なURL形式を入力してください（例: https://example.com）');
      return;
    }

    try {
      setIsSaving(true);
      let response;
      
      if (isEditing && selectedCompany) {
        // 更新
        response = await fetch(`/api/companies/${selectedCompany.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(formData),
        });
      } else {
        // 新規作成
        response = await fetch('/api/companies/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(formData),
        });
      }

      if (!response.ok) {
        const errorData = await response.json();
        console.error('Complete error response:', errorData);
        
        // より詳細なエラーメッセージを表示
        let errorMessage = 'Failed to save company';
        if (errorData.detail) {
          errorMessage = errorData.detail;
        } else if (errorData.error) {
          errorMessage = errorData.error;
        } else if (errorData.details) {
          errorMessage = errorData.details;
        }
        
        throw new Error(errorMessage);
      }

      const savedCompany = await response.json();
      
      if (isEditing) {
        setCompanies(companies.map(c => c.id === savedCompany.id ? savedCompany : c));
        toast.success('会社情報を更新しました');
      } else {
        await fetchCompanies(); // 一覧を再取得
        toast.success('会社情報を作成しました');
      }

      setIsDialogOpen(false);
      resetForm();
    } catch (error) {
      console.error('Error saving company:', error);
      toast.error(error instanceof Error ? error.message : '保存に失敗しました');
    } finally {
      setIsSaving(false);
    }
  };

  // デフォルト会社の設定
  const setDefaultCompany = async (companyId: string) => {
    try {
      const response = await fetch('/api/companies/set-default', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ company_id: companyId }),
      });

      if (!response.ok) {
        throw new Error('Failed to set default company');
      }

      await fetchCompanies(); // 一覧を再取得
      toast.success('デフォルト会社を設定しました');
    } catch (error) {
      console.error('Error setting default company:', error);
      toast.error('デフォルト設定に失敗しました');
    }
  };

  // 会社削除
  const deleteCompany = async (company: CompanyInfo) => {
    if (companies.length === 1) {
      toast.error('最後の会社情報は削除できません');
      return;
    }

    if (company.is_default && companies.length > 1) {
      toast.error('デフォルト会社は削除できません。先に他の会社をデフォルトに設定してください。');
      return;
    }

    try {
      const response = await fetch(`/api/companies/${company.id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        throw new Error('Failed to delete company');
      }

      await fetchCompanies(); // 一覧を再取得
      toast.success('会社情報を削除しました');
    } catch (error) {
      console.error('Error deleting company:', error);
      toast.error('削除に失敗しました');
    }
  };

  const defaultCompany = companies.find(c => c.is_default);

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <div className="flex mt-[45px]">
        <div className="fixed left-0 top-[45px] h-[calc(100vh-45px)]">
          <Sidebar />
        </div>
        <main className="flex-1 ml-[314px] p-5">
          <div className="container mx-auto p-6 space-y-6">
            <div className="flex justify-between items-center">
              <div className="space-y-2">
                <h1 className="text-3xl font-bold">会社情報設定</h1>
                <p className="text-muted-foreground">
                  SEO記事生成で使用する会社情報を管理します。設定した情報は記事のコンテキストとして自動的に活用されます。
                </p>
              </div>
              
              <Dialog open={isDialogOpen} onOpenChange={(open) => {
                setIsDialogOpen(open);
                if (!open) resetForm();
              }}>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    会社を追加
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                  <DialogHeader>
                    <DialogTitle>
                      {isEditing ? '会社情報を編集' : '新しい会社を追加'}
                    </DialogTitle>
                    <DialogDescription>
                      SEO記事生成で使用する会社情報を設定してください。必須項目を入力後、詳細設定で更に細かく設定できます。
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-6">
                    {/* 必須項目 */}
                    <div className="space-y-4">
                      <h3 className="text-lg font-semibold flex items-center gap-2">
                        <AlertCircle className="h-4 w-4 text-orange-500" />
                        必須項目
                      </h3>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="name">会社名 *</Label>
                          <Input
                            id="name"
                            value={formData.name}
                            onChange={(e) => setFormData({...formData, name: e.target.value})}
                            placeholder="株式会社サンプル"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="website_url">企業HP URL *</Label>
                          <Input
                            id="website_url"
                            value={formData.website_url}
                            onChange={(e) => setFormData({...formData, website_url: e.target.value})}
                            placeholder="https://example.com"
                          />
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="description">会社概要 *</Label>
                        <Textarea
                          id="description"
                          value={formData.description}
                          onChange={(e) => setFormData({...formData, description: e.target.value})}
                          placeholder="どのような事業を行っている会社かを詳しく記載してください"
                          rows={3}
                        />
                        <p className="text-xs text-muted-foreground">
                          事業内容、サービス、会社の特徴などを記載してください
                        </p>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="usp">USP（企業の強み・差別化ポイント） *</Label>
                        <Textarea
                          id="usp"
                          value={formData.usp}
                          onChange={(e) => setFormData({...formData, usp: e.target.value})}
                          placeholder="他社にはない御社独自の強みや差別化ポイントを記載してください"
                          rows={2}
                        />
                        <p className="text-xs text-muted-foreground">
                          競合との差別化要因、独自の技術、サービスの特徴など
                        </p>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="target_persona">ターゲットペルソナ *</Label>
                        <Textarea
                          id="target_persona"
                          value={formData.target_persona}
                          onChange={(e) => setFormData({...formData, target_persona: e.target.value})}
                          placeholder="中小企業の経営者（従業員10-50名、年商1-10億円、デジタル化に課題を感じている40-60代の男性経営者）"
                          rows={3}
                        />
                        <p className="text-xs text-muted-foreground">
                          年齢、性別、職業、収入、興味関心、課題など具体的に記載してください
                        </p>
                      </div>
                    </div>

                    {/* 詳細設定 */}
                    <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced}>
                      <CollapsibleTrigger asChild>
                        <Button variant="ghost" className="w-full justify-between">
                          <span className="flex items-center gap-2">
                            <Check className="h-4 w-4 text-green-500" />
                            詳細設定（任意）
                          </span>
                          {showAdvanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        </Button>
                      </CollapsibleTrigger>
                      <CollapsibleContent className="space-y-4 pt-4">
                        <Alert>
                          <AlertCircle className="h-4 w-4" />
                          <AlertDescription>
                            以下の設定はSEO記事生成でより詳細なコンテキストを提供し、記事の質を向上させます。
                          </AlertDescription>
                        </Alert>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="space-y-2">
                            <Label htmlFor="brand_slogan">ブランドスローガン</Label>
                            <Input
                              id="brand_slogan"
                              value={formData.brand_slogan}
                              onChange={(e) => setFormData({...formData, brand_slogan: e.target.value})}
                              placeholder="未来を創るテクノロジー"
                            />
                          </div>
                          <div className="space-y-2">
                            <Label htmlFor="target_area">対象エリア</Label>
                            <Input
                              id="target_area"
                              value={formData.target_area}
                              onChange={(e) => setFormData({...formData, target_area: e.target.value})}
                              placeholder="東京都、神奈川県、全国"
                            />
                          </div>
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="target_keywords">重要キーワード</Label>
                          <Textarea
                            id="target_keywords"
                            value={formData.target_keywords}
                            onChange={(e) => setFormData({...formData, target_keywords: e.target.value})}
                            placeholder="デジタルマーケティング、SEO対策、SNS運用"
                            rows={2}
                          />
                          <p className="text-xs text-muted-foreground">
                            記事に含めたいキーワードをカンマ区切りで記載
                          </p>
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="industry_terms">業界特有の専門用語</Label>
                          <Textarea
                            id="industry_terms"
                            value={formData.industry_terms}
                            onChange={(e) => setFormData({...formData, industry_terms: e.target.value})}
                            placeholder="リード獲得、コンバージョン率、ROAS、CTR"
                            rows={2}
                          />
                          <p className="text-xs text-muted-foreground">
                            業界でよく使われる専門用語をカンマ区切りで記載
                          </p>
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="avoid_terms">避けたい表現・NGワード</Label>
                          <Textarea
                            id="avoid_terms"
                            value={formData.avoid_terms}
                            onChange={(e) => setFormData({...formData, avoid_terms: e.target.value})}
                            placeholder="安い、格安、簡単すぎる表現"
                            rows={2}
                          />
                          <p className="text-xs text-muted-foreground">
                            記事に含めたくない表現をカンマ区切りで記載
                          </p>
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="popular_articles">人気記事・参考コンテンツ</Label>
                          <Textarea
                            id="popular_articles"
                            value={formData.popular_articles}
                            onChange={(e) => setFormData({...formData, popular_articles: e.target.value})}
                            placeholder="「中小企業のためのDX入門」https://example.com/dx-guide"
                            rows={2}
                          />
                          <p className="text-xs text-muted-foreground">
                            過去の人気記事のタイトルやURLを参考として記載
                          </p>
                        </div>
                      </CollapsibleContent>
                    </Collapsible>

                    <div className="flex justify-end space-x-2 pt-4 border-t">
                      <Button 
                        variant="outline" 
                        onClick={() => setIsDialogOpen(false)}
                        disabled={isSaving}
                      >
                        キャンセル
                      </Button>
                      <Button 
                        onClick={saveCompany}
                        disabled={isSaving}
                      >
                        {isSaving ? '保存中...' : isEditing ? '更新' : '作成'}
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            {/* デフォルト会社の表示 */}
            {defaultCompany && (
              <Alert className="border-primary bg-primary/5">
                <Star className="h-4 w-4 text-primary" />
                <AlertDescription>
                  <strong>{defaultCompany.name}</strong> がデフォルト会社として設定されています。
                  SEO記事生成ではこの会社の情報が自動的に使用されます。
                </AlertDescription>
              </Alert>
            )}

            {/* 会社一覧 */}
            {loading ? (
              <Card>
                <CardContent className="text-center py-8">
                  <p>読み込み中...</p>
                </CardContent>
              </Card>
            ) : companies.length === 0 ? (
              <Card>
                <CardContent className="text-center py-8">
                  <Building2 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-lg font-medium">会社情報が登録されていません</p>
                  <p className="text-muted-foreground mb-4">
                    最初の会社情報を登録して、SEO記事生成を始めましょう
                  </p>
                  <Button onClick={() => setIsDialogOpen(true)}>
                    <Plus className="mr-2 h-4 w-4" />
                    会社を追加
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4">
                {companies.map((company) => (
                  <Card key={company.id} className={company.is_default ? "border-primary" : ""}>
                    <CardHeader>
                      <div className="flex justify-between items-start">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <Building2 className="h-5 w-5 text-primary" />
                            <CardTitle className="text-xl">{company.name}</CardTitle>
                            {company.is_default && (
                              <Badge className="bg-primary">
                                <Star className="h-3 w-3 mr-1" />
                                デフォルト
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground">
                            最終更新: {new Date(company.updated_at).toLocaleDateString('ja-JP')}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          {!company.is_default && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setDefaultCompany(company.id)}
                            >
                              <Star className="h-4 w-4 mr-1" />
                              デフォルトに設定
                            </Button>
                          )}
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => startEdit(company)}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => deleteCompany(company)}
                            disabled={companies.length === 1}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">企業HP URL</p>
                        <a 
                          href={company.website_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-primary hover:underline text-sm"
                        >
                          {company.website_url}
                        </a>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">会社概要</p>
                        <p className="text-sm">{company.description}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">USP・強み</p>
                        <p className="text-sm">{company.usp}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">ターゲットペルソナ</p>
                        <p className="text-sm bg-muted p-2 rounded">{company.target_persona}</p>
                      </div>
                      {(company.target_keywords || company.brand_slogan) && (
                        <div className="pt-2 border-t">
                          <p className="text-sm font-medium text-muted-foreground mb-2">詳細設定</p>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                            {company.brand_slogan && (
                              <div>
                                <span className="font-medium">スローガン:</span> {company.brand_slogan}
                              </div>
                            )}
                            {company.target_keywords && (
                              <div>
                                <span className="font-medium">重要キーワード:</span> {company.target_keywords}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}