#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件 - config.py
"""

class Config:
    """主系统配置"""
    
    # =============================================================================
    # 数据配置
    # =============================================================================
    CACHE_DIR = './data_cache/'
    STOCK_POOL_FILE = 'stock_pool.pkl'
    PRICE_DATA_FILE = 'price_data.pkl'
    
    # =============================================================================
    # 回测配置
    # =============================================================================
    INITIAL_CAPITAL = 1000000    # 初始资金100万元
    MAX_POSITIONS = 6           # 最大持仓数量
    
    # 回测时间范围
    START_DATE = '2021-01-01'
    END_DATE = '2024-01-01'
    
    # 调仓频率 ('M': 月度, 'Q': 季度, 'Y': 年度)
    REBALANCE_FREQ = 'Q'  # 季度调仓
    
    # =============================================================================
    # 交易成本配置
    # =============================================================================
    COMMISSION_RATE = 0.0003    # 佣金费率0.03%
    STAMP_TAX = 0.001          # 印花税0.1%（仅卖出）
    MIN_COMMISSION = 5         # 最低佣金5元
    
    # =============================================================================
    # 选股配置
    # =============================================================================
    MIN_MARKET_CAP = 50        # 最小市值50亿
    MIN_DATA_DAYS = 100        # 最少数据天数
    
    # =============================================================================
    # 技术分析配置
    # =============================================================================
    LOOKBACK_DAYS = 60         # 技术指标计算回看天数
    
    # 移动平均线周期
    MA_PERIODS = [5, 10, 20, 60]
    
    # RSI参数
    RSI_PERIOD = 14
    
    # MACD参数
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    
    # 布林带参数
    BB_PERIOD = 20
    BB_STD = 2
    
    # =============================================================================
    # 显示配置
    # =============================================================================
    USE_ENGLISH_LABELS = True  # 设为True使用英文，False使用中文

# 创建默认配置实例
config = Config() 