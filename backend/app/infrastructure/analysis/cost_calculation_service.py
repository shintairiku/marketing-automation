# -*- coding: utf-8 -*-
"""
OpenAI モデル別コスト計算サービス
異なるOpenAIモデルの詳細な価格情報に基づいてコストを計算する
"""
import logging
from typing import Dict, Any, List
from decimal import Decimal

logger = logging.getLogger(__name__)

class CostCalculationService:
    """OpenAI モデル別コスト計算サービス"""
    
    # OpenAI 料金表 (2025年1月時点)
    # 価格は1Mトークンあたりの料金 (USD)
    MODEL_PRICING = {
        # GPT-4o models
        "gpt-4o": {
            "input_tokens": 2.50,
            "output_tokens": 10.00,
            "cached_tokens": 1.25,  # 50% discount
            "reasoning_tokens": 60.00,
            "supports_cache": True,
            "supports_reasoning": True
        },
        "gpt-4o-mini": {
            "input_tokens": 0.15,
            "output_tokens": 0.60,
            "cached_tokens": 0.075,  # 50% discount
            "reasoning_tokens": 3.60,
            "supports_cache": True,
            "supports_reasoning": True
        },
        "gpt-4o-2024-11-20": {
            "input_tokens": 2.50,
            "output_tokens": 10.00,
            "cached_tokens": 1.25,
            "reasoning_tokens": 60.00,
            "supports_cache": True,
            "supports_reasoning": True
        },
        "gpt-4o-2024-08-06": {
            "input_tokens": 2.50,
            "output_tokens": 10.00,
            "cached_tokens": 1.25,
            "reasoning_tokens": 60.00,
            "supports_cache": True,
            "supports_reasoning": True
        },
        "gpt-4o-2024-05-13": {
            "input_tokens": 5.00,
            "output_tokens": 15.00,
            "cached_tokens": 2.50,
            "reasoning_tokens": 90.00,
            "supports_cache": True,
            "supports_reasoning": True
        },
        "gpt-4o-mini-2024-07-18": {
            "input_tokens": 0.15,
            "output_tokens": 0.60,
            "cached_tokens": 0.075,
            "reasoning_tokens": 3.60,
            "supports_cache": True,
            "supports_reasoning": True
        },
        
        # o1 models
        "o1-preview": {
            "input_tokens": 15.00,
            "output_tokens": 60.00,
            "cached_tokens": 7.50,
            "reasoning_tokens": 60.00,
            "supports_cache": True,
            "supports_reasoning": True
        },
        "o1-mini": {
            "input_tokens": 3.00,
            "output_tokens": 12.00,
            "cached_tokens": 1.50,
            "reasoning_tokens": 12.00,
            "supports_cache": True,
            "supports_reasoning": True
        },
        "o1-2024-12-17": {
            "input_tokens": 15.00,
            "output_tokens": 60.00,
            "cached_tokens": 7.50,
            "reasoning_tokens": 60.00,
            "supports_cache": True,
            "supports_reasoning": True
        },
        "o1-mini-2024-09-12": {
            "input_tokens": 3.00,
            "output_tokens": 12.00,
            "cached_tokens": 1.50,
            "reasoning_tokens": 12.00,
            "supports_cache": True,
            "supports_reasoning": True
        },
        
        # GPT-4 Turbo models
        "gpt-4-turbo": {
            "input_tokens": 10.00,
            "output_tokens": 30.00,
            "cached_tokens": 5.00,
            "reasoning_tokens": 30.00,
            "supports_cache": True,
            "supports_reasoning": False
        },
        "gpt-4-turbo-2024-04-09": {
            "input_tokens": 10.00,
            "output_tokens": 30.00,
            "cached_tokens": 5.00,
            "reasoning_tokens": 30.00,
            "supports_cache": True,
            "supports_reasoning": False
        },
        "gpt-4-turbo-preview": {
            "input_tokens": 10.00,
            "output_tokens": 30.00,
            "cached_tokens": 5.00,
            "reasoning_tokens": 30.00,
            "supports_cache": True,
            "supports_reasoning": False
        },
        "gpt-4-0125-preview": {
            "input_tokens": 10.00,
            "output_tokens": 30.00,
            "cached_tokens": 5.00,
            "reasoning_tokens": 30.00,
            "supports_cache": True,
            "supports_reasoning": False
        },
        "gpt-4-1106-preview": {
            "input_tokens": 10.00,
            "output_tokens": 30.00,
            "cached_tokens": 5.00,
            "reasoning_tokens": 30.00,
            "supports_cache": True,
            "supports_reasoning": False
        },
        
        # Legacy GPT-4 models
        "gpt-4": {
            "input_tokens": 30.00,
            "output_tokens": 60.00,
            "cached_tokens": 15.00,
            "reasoning_tokens": 60.00,
            "supports_cache": False,
            "supports_reasoning": False
        },
        "gpt-4-0613": {
            "input_tokens": 30.00,
            "output_tokens": 60.00,
            "cached_tokens": 15.00,
            "reasoning_tokens": 60.00,
            "supports_cache": False,
            "supports_reasoning": False
        },
        "gpt-4-32k": {
            "input_tokens": 60.00,
            "output_tokens": 120.00,
            "cached_tokens": 30.00,
            "reasoning_tokens": 120.00,
            "supports_cache": False,
            "supports_reasoning": False
        },
        "gpt-4-32k-0613": {
            "input_tokens": 60.00,
            "output_tokens": 120.00,
            "cached_tokens": 30.00,
            "reasoning_tokens": 120.00,
            "supports_cache": False,
            "supports_reasoning": False
        },
        
        # GPT-3.5 models
        "gpt-3.5-turbo": {
            "input_tokens": 0.50,
            "output_tokens": 1.50,
            "cached_tokens": 0.25,
            "reasoning_tokens": 1.50,
            "supports_cache": False,
            "supports_reasoning": False
        },
        "gpt-3.5-turbo-0125": {
            "input_tokens": 0.50,
            "output_tokens": 1.50,
            "cached_tokens": 0.25,
            "reasoning_tokens": 1.50,
            "supports_cache": False,
            "supports_reasoning": False
        },
        "gpt-3.5-turbo-1106": {
            "input_tokens": 1.00,
            "output_tokens": 2.00,
            "cached_tokens": 0.50,
            "reasoning_tokens": 2.00,
            "supports_cache": False,
            "supports_reasoning": False
        },
        "gpt-3.5-turbo-16k": {
            "input_tokens": 3.00,
            "output_tokens": 4.00,
            "cached_tokens": 1.50,
            "reasoning_tokens": 4.00,
            "supports_cache": False,
            "supports_reasoning": False
        },
        
        # Default fallback
        "unknown": {
            "input_tokens": 2.50,
            "output_tokens": 10.00,
            "cached_tokens": 1.25,
            "reasoning_tokens": 60.00,
            "supports_cache": True,
            "supports_reasoning": True
        }
    }
    
    @classmethod
    def calculate_cost(
        cls,
        model_name: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cached_tokens: int = 0,
        reasoning_tokens: int = 0,
        total_tokens: int = 0
    ) -> Dict[str, Any]:
        """
        モデル別にコストを計算する
        
        Args:
            model_name: OpenAIモデル名
            prompt_tokens: 入力トークン数
            completion_tokens: 出力トークン数
            cached_tokens: キャッシュトークン数
            reasoning_tokens: 推論トークン数 (o1モデルなど)
            total_tokens: 総トークン数 (検証用)
            
        Returns:
            Dict: コスト詳細情報
        """
        try:
            # モデル情報を取得
            model_info = cls.MODEL_PRICING.get(model_name, cls.MODEL_PRICING["unknown"])
            
            # 1M トークンあたりの単価を1トークンあたりの単価に変換
            input_rate = Decimal(str(model_info["input_tokens"])) / Decimal("1000000")
            output_rate = Decimal(str(model_info["output_tokens"])) / Decimal("1000000")
            cache_rate = Decimal(str(model_info["cached_tokens"])) / Decimal("1000000")
            reasoning_rate = Decimal(str(model_info["reasoning_tokens"])) / Decimal("1000000")
            
            # 実際のトークン数を使用してコストを計算
            # キャッシュトークンは入力トークンから差し引く
            actual_input_tokens = max(0, prompt_tokens - cached_tokens)
            
            input_cost = Decimal(str(actual_input_tokens)) * input_rate
            output_cost = Decimal(str(completion_tokens)) * output_rate
            cache_cost = Decimal(str(cached_tokens)) * cache_rate
            reasoning_cost = Decimal(str(reasoning_tokens)) * reasoning_rate
            
            total_cost = input_cost + output_cost + cache_cost + reasoning_cost
            
            # 結果を構築
            result = {
                "model_name": model_name,
                "model_supports_cache": model_info["supports_cache"],
                "model_supports_reasoning": model_info["supports_reasoning"],
                "token_usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "cached_tokens": cached_tokens,
                    "reasoning_tokens": reasoning_tokens,
                    "total_tokens": total_tokens or (prompt_tokens + completion_tokens)
                },
                "cost_breakdown": {
                    "input_cost_usd": float(input_cost),
                    "output_cost_usd": float(output_cost),
                    "cache_cost_usd": float(cache_cost),
                    "reasoning_cost_usd": float(reasoning_cost),
                    "total_cost_usd": float(total_cost)
                },
                "pricing_rates": {
                    "input_rate_per_1m": model_info["input_tokens"],
                    "output_rate_per_1m": model_info["output_tokens"],
                    "cache_rate_per_1m": model_info["cached_tokens"],
                    "reasoning_rate_per_1m": model_info["reasoning_tokens"]
                },
                "cost_savings": {
                    "cache_savings_usd": float((input_rate - cache_rate) * Decimal(str(cached_tokens))),
                    "cache_savings_percentage": 50.0 if cached_tokens > 0 else 0.0
                }
            }
            
            logger.info(f"Cost calculated for {model_name}: ${float(total_cost):.6f}")
            return result
            
        except Exception as e:
            logger.error(f"Cost calculation error for {model_name}: {e}")
            # フォールバック計算
            fallback_cost = (prompt_tokens + completion_tokens) * 0.000005  # 概算
            return {
                "model_name": model_name,
                "model_supports_cache": False,
                "model_supports_reasoning": False,
                "token_usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "cached_tokens": cached_tokens,
                    "reasoning_tokens": reasoning_tokens,
                    "total_tokens": total_tokens or (prompt_tokens + completion_tokens)
                },
                "cost_breakdown": {
                    "input_cost_usd": 0.0,
                    "output_cost_usd": 0.0,
                    "cache_cost_usd": 0.0,
                    "reasoning_cost_usd": 0.0,
                    "total_cost_usd": fallback_cost
                },
                "pricing_rates": {
                    "input_rate_per_1m": 0.0,
                    "output_rate_per_1m": 0.0,
                    "cache_rate_per_1m": 0.0,
                    "reasoning_rate_per_1m": 0.0
                },
                "cost_savings": {
                    "cache_savings_usd": 0.0,
                    "cache_savings_percentage": 0.0
                },
                "error": str(e)
            }
    
    @classmethod
    def get_model_pricing_info(cls, model_name: str) -> Dict[str, Any]:
        """指定されたモデルの料金情報を取得"""
        return cls.MODEL_PRICING.get(model_name, cls.MODEL_PRICING["unknown"])
    
    @classmethod
    def get_all_supported_models(cls) -> List[str]:
        """サポートされているすべてのモデル名を取得"""
        return list(cls.MODEL_PRICING.keys())
    
    @classmethod
    def is_model_supported(cls, model_name: str) -> bool:
        """指定されたモデルがサポートされているかチェック"""
        return model_name in cls.MODEL_PRICING
    
    @classmethod
    def calculate_session_total_cost(cls, llm_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """セッション全体のコストを計算"""
        total_cost = 0.0
        total_tokens = 0
        total_input_tokens = 0
        total_output_tokens = 0
        total_cache_tokens = 0
        total_reasoning_tokens = 0
        
        model_breakdown = {}
        
        for call in llm_calls:
            model_name = call.get("model_name", "unknown")
            cost_info = cls.calculate_cost(
                model_name=model_name,
                prompt_tokens=call.get("prompt_tokens", 0),
                completion_tokens=call.get("completion_tokens", 0),
                cached_tokens=call.get("cached_tokens", 0),
                reasoning_tokens=call.get("reasoning_tokens", 0),
                total_tokens=call.get("total_tokens", 0)
            )
            
            call_cost = cost_info["cost_breakdown"]["total_cost_usd"]
            total_cost += call_cost
            
            total_tokens += cost_info["token_usage"]["total_tokens"]
            total_input_tokens += cost_info["token_usage"]["prompt_tokens"]
            total_output_tokens += cost_info["token_usage"]["completion_tokens"]
            total_cache_tokens += cost_info["token_usage"]["cached_tokens"]
            total_reasoning_tokens += cost_info["token_usage"]["reasoning_tokens"]
            
            # モデル別の集計
            if model_name not in model_breakdown:
                model_breakdown[model_name] = {
                    "calls": 0,
                    "total_cost": 0.0,
                    "total_tokens": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_tokens": 0,
                    "reasoning_tokens": 0
                }
            
            model_breakdown[model_name]["calls"] += 1
            model_breakdown[model_name]["total_cost"] += call_cost
            model_breakdown[model_name]["total_tokens"] += cost_info["token_usage"]["total_tokens"]
            model_breakdown[model_name]["input_tokens"] += cost_info["token_usage"]["prompt_tokens"]
            model_breakdown[model_name]["output_tokens"] += cost_info["token_usage"]["completion_tokens"]
            model_breakdown[model_name]["cache_tokens"] += cost_info["token_usage"]["cached_tokens"]
            model_breakdown[model_name]["reasoning_tokens"] += cost_info["token_usage"]["reasoning_tokens"]
        
        return {
            "session_summary": {
                "total_cost_usd": total_cost,
                "total_tokens": total_tokens,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
                "total_cache_tokens": total_cache_tokens,
                "total_reasoning_tokens": total_reasoning_tokens,
                "total_llm_calls": len(llm_calls)
            },
            "model_breakdown": model_breakdown,
            "cost_efficiency": {
                "cost_per_token": total_cost / total_tokens if total_tokens > 0 else 0.0,
                "cache_utilization_percentage": (total_cache_tokens / total_input_tokens * 100) if total_input_tokens > 0 else 0.0,
                "total_cache_savings": sum(
                    cls.calculate_cost(
                        call.get("model_name", "unknown"),
                        call.get("prompt_tokens", 0),
                        call.get("completion_tokens", 0),
                        call.get("cached_tokens", 0),
                        call.get("reasoning_tokens", 0)
                    )["cost_savings"]["cache_savings_usd"] for call in llm_calls
                )
            }
        }