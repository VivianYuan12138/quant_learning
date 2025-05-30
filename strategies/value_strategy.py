#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
价值策略 - value_strategy.py
基于价值因子的选股策略
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from strategy_base import BaseStrategy


class ValueStrategy(BaseStrategy):
    """价值策略"""
    
    def __init__(self, **kwargs):
        super().__init__("价值策略", **kwargs)
        
        # 策略特定参数 - 支持自定义覆盖
        self.max_rsi = kwargs.get('max_rsi', 70)          # RSI不能太高
        self.min_price_position = kwargs.get('min_price_position', 0.1)   # 价格相对位置较低
        self.max_price_position = kwargs.get('max_price_position', 0.6)   # 价格相对位置不能太高
        self.min_bb_position = kwargs.get('min_bb_position', 0.1)      # 布林带下轨附近
        self.max_bb_position = kwargs.get('max_bb_position', 0.5)      # 不在布林带上轨
        self.max_volatility = kwargs.get('max_volatility', 0.4)       # 波动率相对较低
        
    def is_qualified_stock(self, indicators, stock_info=None):
        """判断股票是否符合价值策略条件"""
        return (
            # 价格相对便宜
            self.min_price_position <= indicators['price_position'] <= self.max_price_position and
            
            # RSI不能过热
            indicators['rsi'] <= self.max_rsi and
            
            # 布林带位置相对较低
            self.min_bb_position <= indicators['bb_position'] <= self.max_bb_position and
            
            # 基本趋势条件（放宽）
            indicators['price'] > indicators['ma60'] and           # 价格高于长期均线
            
            # 波动率不太高
            indicators['volatility'] <= self.max_volatility and
            
            # 成交量有一定活跃度
            indicators['volume_ratio'] > 0.3
        )
    
    def calculate_score(self, indicators, stock_info=None):
        """计算价值策略评分"""
        score = (
            # 价值因子权重 50%
            (1 - indicators['price_position']) * 30 +        # 价格位置越低越好
            (1 - indicators['bb_position']) * 20 +           # 布林带位置越低越好
            
            # 安全边际权重 25%
            max(0, 70 - indicators['rsi']) * 0.5 +           # RSI越低越好
            (1 - indicators['volatility']) * 10 +            # 波动率越低越好
            
            # 基本面权重 25%
            (indicators['price'] / indicators['ma60'] - 1) * 15 +  # 相对长期均线的强度
            indicators['volume_ratio'] * 10                  # 成交量活跃度
        )
        return score
    
    def get_strategy_description(self):
        """获取策略描述"""
        return f"""
价值策略 - 寻找被低估的优质股票

选股条件:
1. 价格位置: {self.min_price_position} - {self.max_price_position} (相对低位)
2. RSI < {self.max_rsi} (不过热)
3. 布林带位置: {self.min_bb_position} - {self.max_bb_position} (相对低位)
4. 价格 > 60日均线 (基本趋势)
5. 波动率 < {self.max_volatility:.1%}
6. 成交量比率 > 0.3

评分权重:
- 价值因子: 50% (价格位置30%, 布林带位置20%)
- 安全边际: 25% (RSI15%, 波动率10%)
- 基本面: 25% (趋势强度15%, 成交量10%)
        """ 