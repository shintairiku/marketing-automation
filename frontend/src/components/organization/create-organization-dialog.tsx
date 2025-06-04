'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { useOrganizationList } from '@clerk/nextjs';

interface CreateOrganizationDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CreateOrganizationDialog({ isOpen, onClose }: CreateOrganizationDialogProps) {
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [description, setDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  
  const { createOrganization } = useOrganizationList();
  const { toast } = useToast();
  const router = useRouter();

  // 組織名からスラッグを自動生成
  const handleNameChange = (value: string) => {
    setName(value);
    // 簡単なスラッグ生成（英数字とハイフンのみ）
    const autoSlug = value
      .toLowerCase()
      .replace(/[^\w\s-]/g, '') // 特殊文字を除去
      .replace(/\s+/g, '-') // スペースをハイフンに
      .replace(/-+/g, '-') // 連続ハイフンを1つに
      .trim();
    setSlug(autoSlug);
  };

  const handleCreate = async () => {
    if (!name.trim()) {
      toast({
        title: 'エラー',
        description: '組織名を入力してください',
        variant: 'destructive',
      });
      return;
    }

    if (!slug.trim()) {
      toast({
        title: 'エラー', 
        description: 'スラッグを入力してください',
        variant: 'destructive',
      });
      return;
    }

    if (!createOrganization) {
      toast({
        title: 'エラー',
        description: '組織作成機能が利用できません',
        variant: 'destructive',
      });
      return;
    }

    setIsCreating(true);
    
    try {
      // Clerkで組織を作成
      const organization = await createOrganization({
        name: name.trim(),
        slug: slug.trim(),
      });

      if (organization) {
        // Supabaseに組織データを保存する処理はClerkのWebhookで行う
        // または、ここで直接APIを呼び出す
        
        toast({
          title: '成功',
          description: '組織が作成されました',
        });

        // 組織作成後、Teamプラン購入ページにリダイレクト
        router.push(`/pricing?organization_id=${organization.id}&action=setup`);
        onClose();
      }
    } catch (error) {
      console.error('Organization creation error:', error);
      toast({
        title: 'エラー',
        description: '組織の作成に失敗しました',
        variant: 'destructive',
      });
    } finally {
      setIsCreating(false);
    }
  };

  const handleClose = () => {
    if (!isCreating) {
      setName('');
      setSlug('');
      setDescription('');
      onClose();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>新しい組織を作成</DialogTitle>
          <DialogDescription>
            チームで記事生成サービスを利用するための組織を作成します。
            作成後、Teamプランの設定を行います。
          </DialogDescription>
        </DialogHeader>
        
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="name">組織名 *</Label>
            <Input
              id="name"
              placeholder="株式会社〇〇"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              disabled={isCreating}
            />
          </div>
          
          <div className="grid gap-2">
            <Label htmlFor="slug">スラッグ *</Label>
            <Input
              id="slug"
              placeholder="my-company"
              value={slug}
              onChange={(e) => setSlug(e.target.value)}
              disabled={isCreating}
            />
            <p className="text-xs text-gray-600">
              URLで使用されます。英数字とハイフンのみ使用可能です。
            </p>
          </div>
          
          <div className="grid gap-2">
            <Label htmlFor="description">説明（任意）</Label>
            <Textarea
              id="description"
              placeholder="組織の簡単な説明..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={isCreating}
              rows={3}
            />
          </div>
        </div>

        <DialogFooter>
          <Button 
            variant="outline" 
            onClick={handleClose}
            disabled={isCreating}
          >
            キャンセル
          </Button>
          <Button 
            onClick={handleCreate}
            disabled={isCreating || !name.trim() || !slug.trim() || !createOrganization}
          >
            {isCreating ? '作成中...' : '組織を作成'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}