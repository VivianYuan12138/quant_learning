#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略基类 - strategy_base.py
用户可以继承这个基类来实现自己的选股策略
"""

import pandas as pd
from abc import ABC, abstractmethod
from technical_analyzer import TechnicalAnalyzer
from config import config


class BaseStrategy(ABC):
    """策略基类"""
    
    def __init__(self, name, config_obj=None, data_manager=None, **kwargs):
        self.name = name
        self.config = config_obj or config
        self.data_manager = data_manager
        self.analyzer = TechnicalAnalyzer(config_obj)
        
        # 策略参数，子类可以重写
        self.max_selections = self.config.MAX_POSITIONS
        self.min_score = 0  # 最低评分要求
        
    @abstractmethod
    def is_qualified_stock(self, indicators, stock_info=None):
        """
        判断股票是否符合选股条件
        
        Args:
            indicators (dict): 技术指标字典
            stock_info (pd.Series): 股票基本信息
            
        Returns:
            bool: 是否符合条件
        """
        pass
    
    @abstractmethod
    def calculate_score(self, indicators, stock_info=None):
        """
        计算股票评分
        
        Args:
            indicators (dict): 技术指标字典
            stock_info (pd.Series): 股票基本信息
            
        Returns:
            float: 股票评分
        """
        pass
    
    def select_stocks_for_date(self, target_date, max_selections=None):
        """为指定日期选股"""
        if max_selections is None:
            max_selections = self.max_selections
        
        print(f"📊 执行选股策略: {self.name} - {target_date}")
        
        if not self.data_manager:
            print("❌ 数据管理器未设置")
            return pd.DataFrame()
        
        stock_pool = self.data_manager.get_stock_pool()
        if stock_pool.empty:
            print("❌ 股票池为空")
            return pd.DataFrame()
        
        candidates = []
        processed = 0
        
        for _, stock in stock_pool.iterrows():
            stock_code = stock['code']
            stock_name = stock['name']
            
            # 获取价格数据
            price_data = self.data_manager.get_price_data(stock_code)
            if price_data.empty:
                continue
            
            # 筛选到目标日期之前的数据
            price_data_filtered = price_data[price_data.index <= target_date]
            if len(price_data_filtered) < self.config.MIN_DATA_DAYS:
                continue
            
            # 计算技术指标
            indicators = self.analyzer.calculate_indicators(price_data_filtered)
            if indicators is None:
                continue
            
            # 检查是否符合选股条件
            if self.is_qualified_stock(indicators, stock):
                score = self.calculate_score(indicators, stock)
                
                if score >= self.min_score:
                    candidates.append({
                        'code': stock_code,
                        'name': stock_name,
                        'score': score,
                        'price': indicators['price'],
                        'indicators': indicators  # 保存所有指标供后续分析
                    })
            
            processed += 1
            if processed % 100 == 0:
                print(f"  已处理 {processed} 只股票，找到 {len(candidates)} 只候选")
        
        # 按评分排序选择
        if candidates:
            candidates_df = pd.DataFrame(candidates)
            selected = candidates_df.nlargest(max_selections, 'score')
            
            print(f"✅ 选出 {len(selected)} 只股票:")
            for _, stock in selected.iterrows():
                self._print_stock_info(stock)
            
            return selected
        else:
            print("⚠️ 未找到符合条件的股票")
            return pd.DataFrame()
    
    def _print_stock_info(self, stock):
        """打印股票信息"""
        indicators = stock['indicators']
        print(f"  {stock['code']} {stock['name']:<8} "
              f"评分:{stock['score']:.1f} "
              f"价格:{stock['price']:.2f} "
              f"RSI:{indicators.get('rsi', 0):.1f}")
    
    def get_strategy_description(self):
        """获取策略描述"""
        return f"策略名称: {self.name}"
    
    def set_parameters(self, **kwargs):
        """设置策略参数"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                print(f"设置参数 {key} = {value}")
            else:
                print(f"警告: 未知参数 {key}")


class MultiFactorStrategy(BaseStrategy):
    """多因子策略基类"""
    
    def __init__(self, name, factors=None, weights=None, **kwargs):
        super().__init__(name, **kwargs)
        
        # 因子配置
        self.factors = factors or []
        self.weights = weights or {}
        
        # 默认权重
        if not self.weights and self.factors:
            weight = 1.0 / len(self.factors)
            self.weights = {factor: weight for factor in self.factors}
    
    def add_factor(self, factor_name, weight=1.0, condition=None):
        """添加因子"""
        self.factors.append(factor_name)
        self.weights[factor_name] = weight
        if condition:
            setattr(self, f'{factor_name}_condition', condition)
    
    def calculate_factor_score(self, factor_name, indicators, stock_info=None):
        """计算单个因子评分 - 子类需要实现"""
        return 0
    
    def calculate_score(self, indicators, stock_info=None):
        """计算综合评分"""
        total_score = 0
        total_weight = 0
        
        for factor in self.factors:
            if factor in self.weights:
                factor_score = self.calculate_factor_score(factor, indicators, stock_info)
                weight = self.weights[factor]
                total_score += factor_score * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0


class RankBasedStrategy(BaseStrategy):
    """基于排名的策略基类"""
    
    def __init__(self, name, ranking_factors=None, **kwargs):
        super().__init__(name, **kwargs)
        self.ranking_factors = ranking_factors or []
    
    def get_stock_rankings(self, target_date):
        """获取股票排名"""
        stock_pool = self.data_manager.get_stock_pool()
        stock_data = []
        
        for _, stock in stock_pool.iterrows():
            stock_code = stock['code']
            price_data = self.data_manager.get_price_data(stock_code)
            
            if not price_data.empty:
                price_data_filtered = price_data[price_data.index <= target_date]
                if len(price_data_filtered) >= self.config.MIN_DATA_DAYS:
                    indicators = self.analyzer.calculate_indicators(price_data_filtered)
                    if indicators:
                        stock_data.append({
                            'code': stock_code,
                            'name': stock['name'],
                            'indicators': indicators
                        })
        
        # 计算排名
        df = pd.DataFrame(stock_data)
        for factor in self.ranking_factors:
            df[f'{factor}_rank'] = df['indicators'].apply(
                lambda x: x.get(factor, 0)
            ).rank(ascending=False)
        
        return df 