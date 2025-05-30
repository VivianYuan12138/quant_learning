#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
成长策略 - growth_strategy.py
基于成长因子的选股策略
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from strategy_base import MultiFactorStrategy


class GrowthStrategy(MultiFactorStrategy):
    """成长策略"""
    
    def __init__(self, **kwargs):
        # 定义成长因子
        factors = ['momentum_20d', 'momentum_60d', 'rsi', 'volume_ratio', 'price_position']
        weights = {
            'momentum_20d': 0.3,     # 中期动量
            'momentum_60d': 0.25,    # 长期动量  
            'rsi': 0.2,              # 相对强弱
            'volume_ratio': 0.15,    # 成交量
            'price_position': 0.1    # 价格位置
        }
        
        super().__init__("成长策略", factors=factors, weights=weights, **kwargs)
        
        # 策略特定参数 - 支持自定义覆盖
        self.min_momentum_20d = kwargs.get('min_momentum_20d', 0.05)    # 20日动量至少5%
        self.min_momentum_60d = kwargs.get('min_momentum_60d', 0.10)    # 60日动量至少10% 
        self.min_rsi = kwargs.get('min_rsi', 45)               # RSI有一定强度
        self.max_rsi = kwargs.get('max_rsi', 80)               # RSI不能过热
        self.min_volume_ratio = kwargs.get('min_volume_ratio', 1.2)     # 成交量放大
        self.min_price_position = kwargs.get('min_price_position', 0.4)   # 价格相对较高位置
        self.max_volatility = kwargs.get('max_volatility', 0.6)       # 允许较高波动率
        
    def is_qualified_stock(self, indicators, stock_info=None):
        """判断股票是否符合成长策略条件"""
        return (
            # 强劲的中长期动量
            indicators['momentum_20d'] >= self.min_momentum_20d and
            indicators['momentum_60d'] >= self.min_momentum_60d and
            
            # RSI在强势区间
            self.min_rsi <= indicators['rsi'] <= self.max_rsi and
            
            # 成交量放大
            indicators['volume_ratio'] >= self.min_volume_ratio and
            
            # 价格在相对高位（突破特征）
            indicators['price_position'] >= self.min_price_position and
            
            # 基本趋势条件
            indicators['price'] > indicators['ma20'] and
            indicators['ma20'] > indicators['ma60'] and
            
            # MACD向上
            indicators['macd_hist'] > 0 and
            
            # 波动率在合理范围
            indicators['volatility'] <= self.max_volatility
        )
    
    def calculate_factor_score(self, factor_name, indicators, stock_info=None):
        """计算单个因子评分"""
        if factor_name == 'momentum_20d':
            # 20日动量评分 (0-100)
            momentum = indicators['momentum_20d']
            return min(100, max(0, momentum * 200))  # 50%动量得100分
            
        elif factor_name == 'momentum_60d':
            # 60日动量评分 (0-100)
            momentum = indicators['momentum_60d']
            return min(100, max(0, momentum * 100))  # 100%动量得100分
            
        elif factor_name == 'rsi':
            # RSI评分，50-80之间线性给分
            rsi = indicators['rsi']
            if rsi < 50:
                return 0
            elif rsi > 80:
                return max(0, 100 - (rsi - 80) * 5)  # 超过80开始扣分
            else:
                return (rsi - 50) / 30 * 100  # 50-80线性给分
                
        elif factor_name == 'volume_ratio':
            # 成交量比率评分
            ratio = indicators['volume_ratio']
            return min(100, max(0, (ratio - 1) * 50))  # 2倍成交量得100分
            
        elif factor_name == 'price_position':
            # 价格位置评分
            position = indicators['price_position']
            return position * 100
            
        return 0
    
    def get_strategy_description(self):
        """获取策略描述"""
        return f"""
成长策略 - 捕捉具有强劲成长动量的股票

选股条件:
1. 20日动量 >= {self.min_momentum_20d:.1%}
2. 60日动量 >= {self.min_momentum_60d:.1%}
3. RSI范围: {self.min_rsi} - {self.max_rsi}
4. 成交量比率 >= {self.min_volume_ratio}
5. 价格位置 >= {self.min_price_position}
6. 价格 > 20日均线 > 60日均线
7. MACD柱状线为正
8. 波动率 <= {self.max_volatility:.1%}

因子权重:
- 中期动量(20日): 30%
- 长期动量(60日): 25%
- 相对强弱指标: 20%
- 成交量因子: 15%
- 价格位置: 10%
        """ 