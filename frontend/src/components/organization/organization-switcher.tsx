'use client';

import { useState } from 'react';
import { Building2, Check,ChevronDown, Plus, User } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useOrganizationContext, useOrganizationRole } from '@/hooks/use-organization-context';

import { CreateOrganizationDialog } from './create-organization-dialog';

export function OrganizationSwitcher() {
  const {
    currentOrganization,
    isPersonalContext,
    organizationList,
    switchOrganization,
    isLoading,
  } = useOrganizationContext();
  
  const { isOwner } = useOrganizationRole();
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);

  const handleSwitchToPersonal = async () => {
    await switchOrganization(null);
  };

  const handleSwitchToOrganization = async (orgId: string) => {
    await switchOrganization(orgId);
  };

  if (isLoading) {
    return (
      <Button variant="outline" disabled className="w-48">
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 bg-gray-300 rounded animate-pulse" />
          <span>読み込み中...</span>
        </div>
      </Button>
    );
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" className="w-48 justify-between">
            <div className="flex items-center space-x-2">
              {isPersonalContext ? (
                <>
                  <User className="w-4 h-4 text-blue-600" />
                  <span className="truncate">個人アカウント</span>
                </>
              ) : (
                <>
                  <Building2 className="w-4 h-4 text-green-600" />
                  <span className="truncate">{currentOrganization?.name}</span>
                </>
              )}
            </div>
            <ChevronDown className="w-4 h-4" />
          </Button>
        </DropdownMenuTrigger>
        
        <DropdownMenuContent className="w-48" align="start">
          <DropdownMenuLabel>アカウント選択</DropdownMenuLabel>
          <DropdownMenuSeparator />
          
          {/* 個人アカウント */}
          <DropdownMenuItem 
            onClick={handleSwitchToPersonal}
            className="flex items-center space-x-2"
          >
            <User className="w-4 h-4 text-blue-600" />
            <span>個人アカウント</span>
            {isPersonalContext && <Check className="w-4 h-4 ml-auto text-green-600" />}
          </DropdownMenuItem>
          
          <DropdownMenuSeparator />
          
          {/* 組織リスト */}
          <DropdownMenuLabel>組織</DropdownMenuLabel>
          {organizationList?.map((org) => (
            <DropdownMenuItem
              key={org.organization.id}
              onClick={() => handleSwitchToOrganization(org.organization.id)}
              className="flex items-center space-x-2"
            >
              <Building2 className="w-4 h-4 text-green-600" />
              <span className="truncate">{org.organization.name}</span>
              {currentOrganization?.id === org.organization.id && (
                <Check className="w-4 h-4 ml-auto text-green-600" />
              )}
            </DropdownMenuItem>
          ))}
          
          <DropdownMenuSeparator />
          
          {/* 組織作成 */}
          <DropdownMenuItem 
            onClick={() => setIsCreateDialogOpen(true)}
            className="flex items-center space-x-2 text-blue-600"
          >
            <Plus className="w-4 h-4" />
            <span>新しい組織を作成</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <CreateOrganizationDialog
        isOpen={isCreateDialogOpen}
        onClose={() => setIsCreateDialogOpen(false)}
      />
    </>
  );
}

// 組織情報表示用のヘッダーコンポーネント
export function OrganizationHeader() {
  const {
    currentOrganization,
    isPersonalContext,
    organizationData,
    subscriptionData,
  } = useOrganizationContext();
  
  const { role } = useOrganizationRole();

  if (isPersonalContext) {
    return (
      <div className="flex items-center space-x-3 p-4 bg-blue-50 rounded-lg">
        <User className="w-8 h-8 text-blue-600" />
        <div>
          <h2 className="font-semibold text-lg">個人アカウント</h2>
          <p className="text-sm text-gray-600">
            プラン: {subscriptionData?.plan_tier || 'Free'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center space-x-3 p-4 bg-green-50 rounded-lg">
      <Building2 className="w-8 h-8 text-green-600" />
      <div className="flex-1">
        <h2 className="font-semibold text-lg">{currentOrganization?.name}</h2>
        <p className="text-sm text-gray-600">
          あなたの役割: {role === 'owner' ? 'オーナー' : role === 'admin' ? '管理者' : 'メンバー'}
          {organizationData && (
            <span className="ml-2">
              • シート: {organizationData.used_seats}/{organizationData.max_seats}
            </span>
          )}
        </p>
      </div>
      {subscriptionData && (
        <div className="text-right">
          <p className="text-sm font-medium">
            {subscriptionData.plan_tier === 'pro' ? 'Team プラン' : subscriptionData.plan_tier}
          </p>
          <p className="text-xs text-gray-600">
            ステータス: {subscriptionData.status === 'active' ? 'アクティブ' : subscriptionData.status}
          </p>
        </div>
      )}
    </div>
  );
}