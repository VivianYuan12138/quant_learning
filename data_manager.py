#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据管理器 - data_manager.py
"""

import pandas as pd
import pickle
import os
from config import config


class DataManager:
    """数据管理器"""
    
    def __init__(self, config_obj=None):
        self.config = config_obj or config
        self.stock_pool = None
        self.price_data = None
    
    def load_data(self):
        """加载缓存数据"""
        print("📁 加载数据...")
        
        # 检查文件是否存在
        stock_pool_file = os.path.join(self.config.CACHE_DIR, self.config.STOCK_POOL_FILE)
        price_data_file = os.path.join(self.config.CACHE_DIR, self.config.PRICE_DATA_FILE)
        
        if not os.path.exists(stock_pool_file) or not os.path.exists(price_data_file):
            print("❌ 缓存数据文件不存在")
            print("💡 请先运行 setup_data.py 获取数据")
            return False
        
        try:
            # 加载股票池
            with open(stock_pool_file, 'rb') as f:
                self.stock_pool = pickle.load(f)
            print(f"✅ 股票池: {len(self.stock_pool)}只")
            
            # 加载价格数据
            with open(price_data_file, 'rb') as f:
                self.price_data = pickle.load(f)
            print(f"✅ 价格数据: {len(self.price_data)}只")
            
            # 数据质量检查
            valid_stocks = []
            for _, stock in self.stock_pool.iterrows():
                code = stock['code']
                if (code in self.price_data and 
                    not self.price_data[code].empty and 
                    len(self.price_data[code]) >= self.config.MIN_DATA_DAYS):
                    valid_stocks.append(stock)
            
            self.stock_pool = pd.DataFrame(valid_stocks)
            print(f"✅ 有效股票: {len(self.stock_pool)}只")
            
            if len(self.stock_pool) < 50:
                print("⚠️ 有效股票数量较少，建议重新获取数据")
            
            return True
            
        except Exception as e:
            print(f"❌ 数据加载失败: {e}")
            return False
    
    def get_stock_pool(self):
        """获取股票池"""
        return self.stock_pool if self.stock_pool is not None else pd.DataFrame()
    
    def get_price_data(self, stock_code):
        """获取价格数据"""
        if self.price_data and stock_code in self.price_data:
            return self.price_data[stock_code]
        return pd.DataFrame()
    
    def get_stock_info(self, stock_code):
        """获取股票基本信息"""
        if self.stock_pool is not None:
            stock_info = self.stock_pool[self.stock_pool['code'] == stock_code]
            if not stock_info.empty:
                return stock_info.iloc[0]
        return None
    
    def get_available_stocks(self, date=None):
        """获取指定日期可用的股票列表"""
        available_stocks = []
        stock_pool = self.get_stock_pool()
        
        for _, stock in stock_pool.iterrows():
            code = stock['code']
            price_data = self.get_price_data(code)
            
            if not price_data.empty:
                if date is None:
                    available_stocks.append(stock)
                else:
                    # 检查指定日期是否有数据
                    price_data_filtered = price_data[price_data.index <= date]
                    if len(price_data_filtered) >= self.config.MIN_DATA_DAYS:
                        available_stocks.append(stock)
        
        return pd.DataFrame(available_stocks)
    
    def validate_data_quality(self):
        """验证数据质量"""
        if self.stock_pool is None or self.price_data is None:
            return False
        
        issues = []
        
        for _, stock in self.stock_pool.iterrows():
            code = stock['code']
            
            if code not in self.price_data:
                issues.append(f"股票 {code} 缺少价格数据")
                continue
            
            price_data = self.price_data[code]
            
            if price_data.empty:
                issues.append(f"股票 {code} 价格数据为空")
                continue
            
            # 检查数据完整性
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in price_data.columns]
            if missing_columns:
                issues.append(f"股票 {code} 缺少列: {missing_columns}")
            
            # 检查数据质量
            if price_data['close'].isna().sum() > len(price_data) * 0.1:
                issues.append(f"股票 {code} 收盘价数据缺失过多")
        
        if issues:
            print("❌ 数据质量问题:")
            for issue in issues[:10]:  # 只显示前10个问题
                print(f"  {issue}")
            if len(issues) > 10:
                print(f"  ... 还有 {len(issues) - 10} 个问题")
            return False
        
        print("✅ 数据质量检查通过")
        return True 