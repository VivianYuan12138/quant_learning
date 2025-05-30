#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
动量策略 - momentum_strategy.py
基于动量因子的选股策略
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from strategy_base import BaseStrategy


class MomentumStrategy(BaseStrategy):
    """动量策略"""
    
    def __init__(self, **kwargs):
        super().__init__("动量策略", **kwargs)
        
        # 策略特定参数 - 支持自定义覆盖
        self.min_rsi = kwargs.get('min_rsi', 20)
        self.max_rsi = kwargs.get('max_rsi', 75)
        self.min_momentum_5d = kwargs.get('min_momentum_5d', -0.05)
        self.min_momentum_20d = kwargs.get('min_momentum_20d', -0.15)
        self.max_volatility = kwargs.get('max_volatility', 0.5)
        self.min_volume_ratio = kwargs.get('min_volume_ratio', 0.5)
        self.min_price_position = kwargs.get('min_price_position', 0.3)
        self.min_bb_position = kwargs.get('min_bb_position', 0.2)
        self.max_bb_position = kwargs.get('max_bb_position', 0.8)
    
    def is_qualified_stock(self, indicators, stock_info=None):
        """判断股票是否符合动量策略条件"""
        return (
            # 趋势条件
            indicators['price'] > indicators['ma20'] and          # 价格 > 20日均线
            indicators['ma5'] > indicators['ma10'] and            # 5日 > 10日均线
            indicators['ma10'] > indicators['ma20'] and           # 10日 > 20日均线
            indicators['ma20'] > indicators['ma60'] and           # 20日 > 60日均线
            
            # RSI条件
            self.min_rsi <= indicators['rsi'] <= self.max_rsi and # RSI在合理区间
            
            # 动量条件
            indicators['momentum_5d'] > self.min_momentum_5d and  # 短期动量不太差
            indicators['momentum_20d'] > self.min_momentum_20d and # 中期动量不太差
            
            # MACD条件
            indicators['macd'] > indicators['macd_signal'] and     # MACD金叉
            indicators['macd_hist'] > 0 and                       # MACD柱状线为正
            
            # 布林带条件
            self.min_bb_position <= indicators['bb_position'] <= self.max_bb_position and # 价格在布林带合理位置
            
            # 波动率和成交量条件
            indicators['volatility'] < self.max_volatility and    # 波动率不太高
            indicators['volume_ratio'] > self.min_volume_ratio and # 成交量不太低
            
            # 价格位置
            indicators['price_position'] > self.min_price_position # 价格相对位置不太低
        )
    
    def calculate_score(self, indicators, stock_info=None):
        """计算动量策略评分"""
        score = (
            # 动量指标权重 40%
            indicators['momentum_5d'] * 20 +
            indicators['momentum_10d'] * 15 +
            indicators['momentum_20d'] * 5 +
            
            # 相对强度权重 25%
            (indicators['price'] / indicators['ma20'] - 1) * 25 +
            
            # RSI评分权重 15%
            (80 - abs(indicators['rsi'] - 50)) * 0.3 +
            
            # MACD评分权重 10%
            indicators['macd_hist'] * 100 +
            
            # 价格位置权重 10%
            indicators['price_position'] * 10
        )
        return score
    
    def get_strategy_description(self):
        """获取策略描述"""
        return f"""
动量策略 - 追踪市场趋势，选择具有强劲上升动量的股票

选股条件:
1. 趋势条件: 价格高于各均线，均线多头排列
2. RSI范围: {self.min_rsi} - {self.max_rsi}
3. 动量要求: 5日动量 > {self.min_momentum_5d:.1%}, 20日动量 > {self.min_momentum_20d:.1%}
4. MACD金叉: MACD > Signal且柱状线为正
5. 布林带位置: {self.min_bb_position} - {self.max_bb_position}
6. 波动率 < {self.max_volatility:.1%}
7. 成交量比率 > {self.min_volume_ratio}
8. 价格相对位置 > {self.min_price_position}

评分权重:
- 动量指标: 40% (5日20%, 10日15%, 20日5%)
- 相对强度: 25%
- RSI评分: 15%
- MACD强度: 10%
- 价格位置: 10%
        """ 