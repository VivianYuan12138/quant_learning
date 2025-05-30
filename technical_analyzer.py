#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术分析器 - technical_analyzer.py
"""

import pandas as pd
import numpy as np
from config import config


class TechnicalAnalyzer:
    """技术分析器"""
    
    def __init__(self, config_obj=None):
        self.config = config_obj or config
    
    def calculate_indicators(self, price_data, lookback_days=None):
        """计算技术指标"""
        if lookback_days is None:
            lookback_days = self.config.LOOKBACK_DAYS
        
        if len(price_data) < lookback_days:
            return None
        
        close = price_data['close']
        high = price_data['high']
        low = price_data['low']
        volume = price_data['volume']
        
        indicators = {}
        
        # 基础价格数据
        indicators.update(self._calculate_basic_prices(close, high, low))
        
        # 移动平均线
        indicators.update(self._calculate_moving_averages(close))
        
        # 动量指标
        indicators.update(self._calculate_momentum_indicators(close))
        
        # 趋势指标
        indicators.update(self._calculate_trend_indicators(close))
        
        # 波动率指标
        indicators.update(self._calculate_volatility_indicators(close, high, low))
        
        # 成交量指标
        indicators.update(self._calculate_volume_indicators(volume, close))
        
        return indicators
    
    def _calculate_basic_prices(self, close, high, low):
        """计算基础价格数据"""
        return {
            'price': close.iloc[-1],
            'high_52w': high.rolling(252).max().iloc[-1],
            'low_52w': low.rolling(252).min().iloc[-1],
        }
    
    def _calculate_moving_averages(self, close):
        """计算移动平均线"""
        mas = {}
        for period in self.config.MA_PERIODS:
            ma = close.rolling(period).mean()
            mas[f'ma{period}'] = ma.iloc[-1]
        
        # 均线排列
        mas['ma_trend'] = self._get_ma_trend()
        
        return mas
    
    def _calculate_momentum_indicators(self, close):
        """计算动量指标"""
        # RSI
        rsi = self._calculate_rsi(close, self.config.RSI_PERIOD)
        
        # 动量
        momentum_5d = close / close.shift(5) - 1
        momentum_10d = close / close.shift(10) - 1
        momentum_20d = close / close.shift(20) - 1
        momentum_60d = close / close.shift(60) - 1
        
        # ROC (Rate of Change)
        roc_10 = (close - close.shift(10)) / close.shift(10) * 100
        
        return {
            'rsi': rsi.iloc[-1],
            'momentum_5d': momentum_5d.iloc[-1],
            'momentum_10d': momentum_10d.iloc[-1],
            'momentum_20d': momentum_20d.iloc[-1],
            'momentum_60d': momentum_60d.iloc[-1],
            'roc_10': roc_10.iloc[-1],
        }
    
    def _calculate_trend_indicators(self, close):
        """计算趋势指标"""
        # MACD
        macd, macd_signal, macd_hist = self._calculate_macd(close)
        
        # 布林带
        bb_upper, bb_middle, bb_lower, bb_position = self._calculate_bollinger_bands(close)
        
        # ADX (平均趋向指数)
        # 这里简化实现，可以后续扩展
        
        return {
            'macd': macd.iloc[-1],
            'macd_signal': macd_signal.iloc[-1],
            'macd_hist': macd_hist.iloc[-1],
            'bb_upper': bb_upper.iloc[-1],
            'bb_middle': bb_middle.iloc[-1],
            'bb_lower': bb_lower.iloc[-1],
            'bb_position': bb_position.iloc[-1],
        }
    
    def _calculate_volatility_indicators(self, close, high, low):
        """计算波动率指标"""
        # 历史波动率
        returns = close.pct_change()
        volatility_20 = returns.rolling(20).std() * np.sqrt(252)  # 年化波动率
        
        # ATR (平均真实范围)
        atr = self._calculate_atr(high, low, close)
        
        # 价格相对位置
        price_position = (close - low.rolling(60).min()) / (high.rolling(60).max() - low.rolling(60).min())
        
        return {
            'volatility': volatility_20.iloc[-1],
            'atr': atr.iloc[-1],
            'price_position': price_position.iloc[-1],
        }
    
    def _calculate_volume_indicators(self, volume, close):
        """计算成交量指标"""
        # 成交量移动平均
        volume_ma20 = volume.rolling(20).mean()
        volume_ratio = volume / volume_ma20
        
        # OBV (能量潮)
        obv = self._calculate_obv(volume, close)
        
        # 成交量价格趋势 (VPT)
        vpt = self._calculate_vpt(volume, close)
        
        return {
            'volume_ratio': volume_ratio.iloc[-1],
            'volume_ma20': volume_ma20.iloc[-1],
            'obv': obv.iloc[-1],
            'vpt': vpt.iloc[-1],
        }
    
    def _calculate_rsi(self, close, period):
        """计算RSI"""
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_macd(self, close):
        """计算MACD"""
        ema12 = close.ewm(span=self.config.MACD_FAST).mean()
        ema26 = close.ewm(span=self.config.MACD_SLOW).mean()
        macd = ema12 - ema26
        macd_signal = macd.ewm(span=self.config.MACD_SIGNAL).mean()
        macd_hist = macd - macd_signal
        return macd, macd_signal, macd_hist
    
    def _calculate_bollinger_bands(self, close):
        """计算布林带"""
        bb_middle = close.rolling(self.config.BB_PERIOD).mean()
        bb_std = close.rolling(self.config.BB_PERIOD).std()
        bb_upper = bb_middle + self.config.BB_STD * bb_std
        bb_lower = bb_middle - self.config.BB_STD * bb_std
        bb_position = (close - bb_lower) / (bb_upper - bb_lower)
        return bb_upper, bb_middle, bb_lower, bb_position
    
    def _calculate_atr(self, high, low, close, period=14):
        """计算ATR"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(period).mean()
        return atr
    
    def _calculate_obv(self, volume, close):
        """计算OBV"""
        price_change = close.diff()
        obv = (volume * np.sign(price_change)).cumsum()
        return obv
    
    def _calculate_vpt(self, volume, close):
        """计算VPT"""
        price_change_pct = close.pct_change()
        vpt = (volume * price_change_pct).cumsum()
        return vpt
    
    def _get_ma_trend(self):
        """判断均线趋势"""
        # 这个方法需要在有均线数据的情况下调用
        # 简化实现，可以后续扩展
        return 1  # 1: 上升, 0: 横盘, -1: 下降
    
    def get_signal_strength(self, indicators):
        """计算信号强度 (0-100)"""
        if not indicators:
            return 0
        
        strength = 0
        max_strength = 0
        
        # RSI信号 (20分)
        rsi = indicators.get('rsi', 50)
        if 30 <= rsi <= 70:
            strength += 20 * (1 - abs(rsi - 50) / 20)
        max_strength += 20
        
        # 动量信号 (30分)
        momentum_5d = indicators.get('momentum_5d', 0)
        momentum_20d = indicators.get('momentum_20d', 0)
        if momentum_5d > 0 and momentum_20d > 0:
            strength += 30
        elif momentum_5d > 0 or momentum_20d > 0:
            strength += 15
        max_strength += 30
        
        # MACD信号 (25分)
        macd_hist = indicators.get('macd_hist', 0)
        if macd_hist > 0:
            strength += 25
        max_strength += 25
        
        # 布林带信号 (15分)
        bb_position = indicators.get('bb_position', 0.5)
        if 0.2 <= bb_position <= 0.8:
            strength += 15
        max_strength += 15
        
        # 成交量信号 (10分)
        volume_ratio = indicators.get('volume_ratio', 1)
        if volume_ratio > 1:
            strength += 10
        max_strength += 10
        
        return min(100, (strength / max_strength) * 100) if max_strength > 0 else 0 