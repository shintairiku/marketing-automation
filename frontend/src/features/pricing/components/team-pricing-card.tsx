'use client';

import { useState } from 'react';
import { Check, Minus, Plus,Users } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { calculateTeamPlanArticles,calculateTeamPlanPrice, PRICING_PLANS } from '@/config/pricing-plans';
import { createTeamCheckoutAction } from '@/features/pricing/actions/create-team-checkout-action';
import { useOrganizationContext, useOrganizationRole } from '@/hooks/use-organization-context';
import { useToast } from '@/hooks/use-toast';

interface TeamPricingCardProps {
  organizationId?: string;
  currentSeatCount?: number;
  isUpgrade?: boolean;
}

export function TeamPricingCard({ 
  organizationId, 
  currentSeatCount = 0, 
  isUpgrade = false 
}: TeamPricingCardProps) {
  const [seatCount, setSeatCount] = useState(Math.max(currentSeatCount || PRICING_PLANS.team.minSeats, PRICING_PLANS.team.minSeats));
  const [isLoading, setIsLoading] = useState(false);
  
  const { currentOrganization, isPersonalContext } = useOrganizationContext();
  const { isOwner } = useOrganizationRole();
  const { toast } = useToast();
  
  const teamPlan = PRICING_PLANS.team;
  const totalPrice = calculateTeamPlanPrice(seatCount);
  const totalArticles = calculateTeamPlanArticles(seatCount);
  
  const handleSeatChange = (newCount: number) => {
    const clampedCount = Math.max(teamPlan.minSeats, Math.min(newCount, teamPlan.maxSeats || 1000));
    setSeatCount(clampedCount);
  };

  const handleCheckout = async () => {
    if (isPersonalContext) {
      toast({
        title: 'エラー',
        description: 'Teamプランには組織が必要です。まず組織を作成してください。',
        variant: 'destructive',
      });
      return;
    }

    if (!isOwner) {
      toast({
        title: 'エラー',
        description: 'Teamプランの購入は組織のオーナーのみが可能です。',
        variant: 'destructive',
      });
      return;
    }

    const targetOrgId = organizationId || currentOrganization?.id;
    if (!targetOrgId) {
      toast({
        title: 'エラー',
        description: '組織IDが見つかりません。',
        variant: 'destructive',
      });
      return;
    }

    setIsLoading(true);
    
    try {
      await createTeamCheckoutAction({
        organizationId: targetOrgId,
        seatQuantity: seatCount,
        teamPriceId: teamPlan.priceId,
        organizationName: currentOrganization?.name || '組織',
      });
    } catch (error) {
      console.error('Checkout error:', error);
      toast({
        title: 'エラー',
        description: error instanceof Error ? error.message : 'チェックアウトの作成に失敗しました',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const getActionButtonText = () => {
    if (isLoading) return '処理中...';
    if (isUpgrade) return 'シート数を変更';
    return 'Teamプランを開始';
  };

  return (
    <Card className="relative w-full max-w-sm p-6 bg-gradient-to-br from-green-50 to-blue-50 border-2 border-green-200">
      {/* 人気バッジ */}
      <div className="absolute -top-3 left-1/2 transform -translate-x-1/2">
        <span className="bg-green-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
          チーム向け
        </span>
      </div>
      
      {/* プラン名とアイコン */}
      <div className="text-center mb-4">
        <div className="flex justify-center mb-2">
          <Users className="w-8 h-8 text-green-600" />
        </div>
        <h3 className="text-2xl font-bold text-gray-900">{teamPlan.name}</h3>
        <p className="text-gray-600 mt-1">組織・チーム向けプラン</p>
      </div>

      {/* シート数選択 */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          シート数
        </label>
        <div className="flex items-center space-x-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleSeatChange(seatCount - 1)}
            disabled={seatCount <= teamPlan.minSeats}
          >
            <Minus className="w-4 h-4" />
          </Button>
          
          <Input
            type="number"
            value={seatCount}
            onChange={(e) => handleSeatChange(parseInt(e.target.value) || teamPlan.minSeats)}
            min={teamPlan.minSeats}
            max={teamPlan.maxSeats}
            className="text-center w-20"
          />
          
          <Button
            variant="outline"  
            size="sm"
            onClick={() => handleSeatChange(seatCount + 1)}
            disabled={seatCount >= (teamPlan.maxSeats || 1000)}
          >
            <Plus className="w-4 h-4" />
          </Button>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          最小 {teamPlan.minSeats} シート、最大 {teamPlan.maxSeats} シート
        </p>
      </div>

      {/* 価格表示 */}
      <div className="text-center mb-6">
        <div className="flex items-baseline justify-center">
          <span className="text-3xl font-bold text-gray-900">
            ¥{totalPrice.toLocaleString()}
          </span>
          <span className="text-gray-600 ml-1">/月</span>
        </div>
        <p className="text-sm text-gray-600 mt-1">
          ¥{teamPlan.pricePerSeat.toLocaleString()} × {seatCount} シート
        </p>
        <p className="text-sm text-green-600 font-medium mt-2">
          月間 {totalArticles} 記事まで生成可能
        </p>
      </div>

      {/* 機能リスト */}
      <div className="space-y-3 mb-6">
        {teamPlan.features.features.map((feature, index) => (
          <div key={index} className="flex items-start">
            <Check className="w-5 h-5 text-green-600 mr-2 mt-0.5 flex-shrink-0" />
            <span className="text-sm text-gray-700">{feature}</span>
          </div>
        ))}
      </div>

      {/* アクションボタン */}
      <Button
        onClick={handleCheckout}
        disabled={isLoading || (!isPersonalContext && !isOwner)}
        className="w-full bg-green-600 hover:bg-green-700 text-white"
        size="lg"
      >
        {getActionButtonText()}
      </Button>

      {/* 注意事項 */}
      <div className="mt-4 text-xs text-gray-500 text-center space-y-1">
        {isPersonalContext && (
          <p className="text-orange-600">
            ※ 組織を作成してからご利用ください
          </p>
        )}
        {!isPersonalContext && !isOwner && (
          <p className="text-orange-600">
            ※ 組織のオーナーのみ購入可能です
          </p>
        )}
        <p>ChatGPT Teamと同様の仕組みです</p>
        <p>シート数はいつでも変更できます</p>
      </div>
    </Card>
  );
}