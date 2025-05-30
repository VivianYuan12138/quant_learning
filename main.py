#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股量化回测系统 - main.py
功能：完整的量化选股回测系统
作者：Claude
时间：2025年
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pickle
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 设置中文字体 - 修复乱码问题
import matplotlib
import platform

# 根据不同操作系统设置字体
system = platform.system()
if system == 'Darwin':  # macOS
    plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'STHeiti', 'SimHei']
elif system == 'Windows':  # Windows
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'FangSong']
else:  # Linux
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'WenQuanYi Micro Hei']

plt.rcParams['axes.unicode_minus'] = False

# 如果还是有问题，使用英文标题
USE_ENGLISH_LABELS = True  # 设为True使用英文，False使用中文

# =============================================================================
# 配置参数
# =============================================================================

class Config:
    """主系统配置"""
    # 缓存目录
    CACHE_DIR = './data_cache/'
    STOCK_POOL_FILE = 'stock_pool.pkl'
    PRICE_DATA_FILE = 'price_data.pkl'
    
    # 回测参数
    INITIAL_CAPITAL = 1000000  # 初始资金100万元
    MAX_POSITIONS = 6        # 最大持仓数量
    
    # 回测时间范围
    START_DATE = '2021-01-01'
    END_DATE = '2024-01-01'
    
    # 交易成本
    COMMISSION_RATE = 0.0003  # 佣金费率0.03%
    STAMP_TAX = 0.001        # 印花税0.1%（仅卖出）
    MIN_COMMISSION = 5       # 最低佣金5元
    
    # 选股参数
    MIN_MARKET_CAP = 50      # 最小市值50亿
    MIN_DATA_DAYS = 100      # 最少数据天数

config = Config()

# =============================================================================
# 数据管理器
# =============================================================================

class DataManager:
    """数据管理器"""
    
    def __init__(self, config):
        self.config = config
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

# =============================================================================
# 技术分析模块
# =============================================================================

class TechnicalAnalyzer:
    """技术分析器"""
    
    @staticmethod
    def calculate_indicators(price_data, lookback_days=60):
        """计算技术指标"""
        if len(price_data) < lookback_days:
            return None
        
        close = price_data['close']
        high = price_data['high']
        low = price_data['low']
        volume = price_data['volume']
        
        # 移动平均线
        ma5 = close.rolling(5).mean()
        ma10 = close.rolling(10).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd = ema12 - ema26
        macd_signal = macd.ewm(span=9).mean()
        macd_hist = macd - macd_signal
        
        # 布林带
        bb_middle = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        bb_upper = bb_middle + 2 * bb_std
        bb_lower = bb_middle - 2 * bb_std
        bb_position = (close - bb_lower) / (bb_upper - bb_lower)
        
        # 动量指标
        momentum_5d = close / close.shift(5) - 1
        momentum_10d = close / close.shift(10) - 1
        momentum_20d = close / close.shift(20) - 1
        
        # 波动率
        volatility = close.rolling(20).std() / close.rolling(20).mean()
        
        # 成交量指标
        volume_ma20 = volume.rolling(20).mean()
        volume_ratio = volume / volume_ma20
        
        # 价格相对位置
        price_position = (close - low.rolling(60).min()) / (high.rolling(60).max() - low.rolling(60).min())
        
        # 获取最新值
        latest = {
            'price': close.iloc[-1],
            'ma5': ma5.iloc[-1],
            'ma10': ma10.iloc[-1],
            'ma20': ma20.iloc[-1],
            'ma60': ma60.iloc[-1],
            'rsi': rsi.iloc[-1],
            'macd': macd.iloc[-1],
            'macd_signal': macd_signal.iloc[-1],
            'macd_hist': macd_hist.iloc[-1],
            'bb_position': bb_position.iloc[-1],
            'momentum_5d': momentum_5d.iloc[-1],
            'momentum_10d': momentum_10d.iloc[-1],
            'momentum_20d': momentum_20d.iloc[-1],
            'volatility': volatility.iloc[-1],
            'volume_ratio': volume_ratio.iloc[-1],
            'price_position': price_position.iloc[-1]
        }
        
        return latest

# =============================================================================
# 选股策略
# =============================================================================

class StockSelector:
    """股票选择器"""
    
    def __init__(self, config, data_manager):
        self.config = config
        self.data_manager = data_manager
        self.analyzer = TechnicalAnalyzer()
    
    def select_stocks_for_date(self, target_date, max_selections=None):
        """为指定日期选股"""
        if max_selections is None:
            max_selections = self.config.MAX_POSITIONS
        
        print(f"📊 执行选股 - {target_date}")
        
        stock_pool = self.data_manager.get_stock_pool()
        if stock_pool.empty:
            print("❌ 股票池为空")
            return pd.DataFrame()
        
        candidates = []
        processed = 0
        qualified = 0
        
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
            
            # 选股条件（更严格的筛选）
            if self._is_qualified_stock(indicators):
                score = self._calculate_score(indicators)
                
                candidates.append({
                    'code': stock_code,
                    'name': stock_name,
                    'score': score,
                    'price': indicators['price'],
                    'rsi': indicators['rsi'],
                    'momentum_5d': indicators['momentum_5d'],
                    'momentum_20d': indicators['momentum_20d'],
                    'volatility': indicators['volatility']
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
                print(f"  {stock['code']} {stock['name']:<8} 评分:{stock['score']:.1f} "
                      f"动量:{stock['momentum_5d']:+.1%}")
            
            return selected
        else:
            print("⚠️ 未找到符合条件的股票")
            return pd.DataFrame()
    
    def _is_qualified_stock(self, indicators):
        """判断股票是否符合选股条件"""
        return (
            # 趋势条件
            indicators['price'] > indicators['ma20'] and          # 价格 > 20日均线
            indicators['ma5'] > indicators['ma10'] and            # 5日 > 10日均线
            indicators['ma10'] > indicators['ma20'] and           # 10日 > 20日均线
            indicators['ma20'] > indicators['ma60'] and           # 20日 > 60日均线
            
            # RSI条件
            20 <= indicators['rsi'] <= 75 and                     # RSI在合理区间
            
            # 动量条件
            indicators['momentum_5d'] > -0.05 and                 # 短期动量不太差
            indicators['momentum_20d'] > -0.15 and                # 中期动量不太差
            
            # MACD条件
            indicators['macd'] > indicators['macd_signal'] and     # MACD金叉
            indicators['macd_hist'] > 0 and                       # MACD柱状线为正
            
            # 布林带条件
            0.2 <= indicators['bb_position'] <= 0.8 and          # 价格在布林带合理位置
            
            # 波动率和成交量条件
            indicators['volatility'] < 0.5 and                   # 波动率不太高
            indicators['volume_ratio'] > 0.5 and                 # 成交量不太低
            
            # 价格位置
            indicators['price_position'] > 0.3                   # 价格相对位置不太低
        )
    
    def _calculate_score(self, indicators):
        """计算股票评分"""
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

# =============================================================================
# 回测引擎
# =============================================================================

class BacktestEngine:
    """完整回测引擎"""
    
    def __init__(self, config, data_manager):
        self.config = config
        self.data_manager = data_manager
        self.selector = StockSelector(config, data_manager)
        
        # 交易状态
        self.cash = config.INITIAL_CAPITAL
        self.positions = {}  # {code: shares}
        self.portfolio_history = []
        self.trades = []
    
    def calculate_trading_cost(self, amount, is_sell=False):
        """计算交易成本"""
        commission = max(amount * self.config.COMMISSION_RATE, self.config.MIN_COMMISSION)
        stamp_tax = amount * self.config.STAMP_TAX if is_sell else 0
        return commission + stamp_tax
    
    def execute_trade(self, action, code, price, shares, date):
        """执行交易"""
        amount = shares * price
        cost = self.calculate_trading_cost(amount, action == 'sell')
        
        if action == 'buy':
            total_cost = amount + cost
            if total_cost <= self.cash:
                self.cash -= total_cost
                self.positions[code] = self.positions.get(code, 0) + shares
                self.trades.append({
                    'date': date, 'action': 'buy', 'code': code,
                    'shares': shares, 'price': price, 'cost': cost
                })
                return True
        else:  # sell
            if code in self.positions and self.positions[code] >= shares:
                net_amount = amount - cost
                self.cash += net_amount
                self.positions[code] -= shares
                if self.positions[code] == 0:
                    del self.positions[code]
                self.trades.append({
                    'date': date, 'action': 'sell', 'code': code,
                    'shares': shares, 'price': price, 'cost': cost
                })
                return True
        return False
    
    def get_portfolio_value(self, date):
        """计算组合价值"""
        total_value = self.cash
        
        for code, shares in self.positions.items():
            price_data = self.data_manager.get_price_data(code)
            if not price_data.empty:
                # 获取指定日期或最近日期的价格
                price_on_date = price_data[price_data.index <= date]
                if not price_on_date.empty:
                    current_price = price_on_date['close'].iloc[-1]
                    total_value += shares * current_price
        
        return total_value
    
    def rebalance(self, date):
        """执行调仓"""
        print(f"\n📅 执行调仓 - {date}")
        
        # 选股
        selected_stocks = self.selector.select_stocks_for_date(date)
        
        if selected_stocks.empty:
            print("❌ 无选股结果，跳过调仓")
            return
        
        # 计算当前组合价值
        portfolio_value = self.get_portfolio_value(date)
        
        # 清仓不在新选股中的股票
        current_codes = set(self.positions.keys())
        selected_codes = set(selected_stocks['code'])
        to_sell = current_codes - selected_codes
        
        for code in to_sell:
            shares = self.positions[code]
            price_data = self.data_manager.get_price_data(code)
            if not price_data.empty:
                price_on_date = price_data[price_data.index <= date]
                if not price_on_date.empty:
                    sell_price = price_on_date['close'].iloc[-1]
                    if self.execute_trade('sell', code, sell_price, shares, date):
                        print(f"  📤 卖出 {code} {shares}股 @{sell_price:.2f}")
        
        # 计算目标仓位
        target_value_per_stock = portfolio_value * 0.9 / len(selected_stocks)  # 预留10%现金
        
        # 买入或调整仓位
        for _, stock in selected_stocks.iterrows():
            code = stock['code'] 
            target_price = stock['price']
            
            # 计算目标股数
            target_shares = int(target_value_per_stock // (target_price * 100)) * 100
            current_shares = self.positions.get(code, 0)
            
            if target_shares > current_shares:
                shares_to_buy = target_shares - current_shares
                if self.execute_trade('buy', code, target_price, shares_to_buy, date):
                    print(f"  📥 买入 {code} {stock['name']} {shares_to_buy}股 @{target_price:.2f}")
        
        # 记录组合状态
        final_value = self.get_portfolio_value(date)
        self.portfolio_history.append({
            'date': pd.to_datetime(date),
            'value': final_value,
            'cash': self.cash,
            'positions': len(self.positions)
        })
        
        print(f"  💰 组合价值: {final_value:.0f}元, 现金: {self.cash:.0f}元, 持仓: {len(self.positions)}只")
    
    def run_backtest(self):
        """运行回测"""
        print("\n" + "="*60)
        print("🚀 开始完整回测")
        print("="*60)
        
        # 生成调仓日期（季度）
        rebalance_dates = pd.date_range(
            start=self.config.START_DATE,
            end=self.config.END_DATE,
            freq='QS'  # 季度开始
        )
        
        print(f"回测周期: {len(rebalance_dates)}个季度")
        print(f"调仓日期: {[d.strftime('%Y-%m-%d') for d in rebalance_dates]}")
        
        # 执行回测
        for i, date in enumerate(rebalance_dates):
            date_str = date.strftime('%Y-%m-%d')
            print(f"\n[{i+1}/{len(rebalance_dates)}] 🗓️ {date_str}")
            self.rebalance(date_str)
        
        print(f"\n✅ 回测完成！共执行{len(self.trades)}笔交易")

# =============================================================================
# 结果分析
# =============================================================================

class ResultAnalyzer:
    """结果分析器"""
    
    def __init__(self, backtest_engine):
        self.engine = backtest_engine
        self.history_df = pd.DataFrame(backtest_engine.portfolio_history)
    
    def calculate_metrics(self):
        """计算绩效指标"""
        if self.history_df.empty:
            return {}
        
        initial = self.engine.config.INITIAL_CAPITAL
        final = self.history_df['value'].iloc[-1]
        
        total_return = (final - initial) / initial
        
        # 计算年化收益率
        start_date = self.history_df['date'].iloc[0]
        end_date = self.history_df['date'].iloc[-1]
        days = (end_date - start_date).days
        annual_return = (1 + total_return) ** (365 / days) - 1
        
        # 计算最大回撤
        peak = self.history_df['value'].expanding().max()
        drawdown = (self.history_df['value'] - peak) / peak
        max_drawdown = drawdown.min()
        
        # 计算胜率
        returns = self.history_df['value'].pct_change().dropna()
        win_rate = (returns > 0).mean()
        
        # 计算夏普比率
        excess_returns = returns - 0.03/4  # 假设无风险利率3%
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(4) if excess_returns.std() > 0 else 0
        
        # 计算波动率
        volatility = returns.std() * np.sqrt(4)
        
        return {
            'initial_value': initial,
            'final_value': final,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'sharpe_ratio': sharpe_ratio,
            'volatility': volatility,
            'trade_count': len(self.engine.trades)
        }
    
    def plot_results(self):
        """绘制结果图表 - 修复中文乱码"""
        if self.history_df.empty:
            print("无数据可绘制")
            return
        
        # 根据设置选择标题语言
        if USE_ENGLISH_LABELS:
            titles = ['Portfolio Value Trend', 'Cumulative Return', 'Cash Ratio', 'Holdings Count', 
                     'Drawdown Analysis', 'Return Distribution']
            ylabels = ['Value (CNY)', 'Return (%)', 'Ratio (%)', 'Stock Count', 'Drawdown (%)', 'Frequency']
        else:
            titles = ['投资组合净值走势', '累计收益率', '现金占比', '持仓数量', 
                     '回撤分析', '收益率分布']
            ylabels = ['净值 (元)', '收益率 (%)', '占比 (%)', '股票数量', '回撤 (%)', '频率']
        
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        
        # 1. 净值曲线
        axes[0,0].plot(self.history_df['date'], self.history_df['value'], 
                      'b-', linewidth=2, label='Portfolio')
        axes[0,0].axhline(self.engine.config.INITIAL_CAPITAL, 
                         color='r', linestyle='--', alpha=0.7, label='Initial Capital')
        axes[0,0].set_title(titles[0], fontsize=12, fontweight='bold')
        axes[0,0].set_ylabel(ylabels[0])
        axes[0,0].legend()
        axes[0,0].grid(True, alpha=0.3)
        
        # 2. 累计收益率
        returns = (self.history_df['value'] / self.engine.config.INITIAL_CAPITAL - 1) * 100
        axes[0,1].plot(self.history_df['date'], returns, 'g-', linewidth=2)
        axes[0,1].axhline(0, color='r', linestyle='--', alpha=0.7)
        axes[0,1].set_title(titles[1], fontsize=12, fontweight='bold')
        axes[0,1].set_ylabel(ylabels[1])
        axes[0,1].grid(True, alpha=0.3)
        
        # 3. 现金占比
        cash_ratio = self.history_df['cash'] / self.history_df['value'] * 100
        axes[0,2].plot(self.history_df['date'], cash_ratio, 'orange', linewidth=2)
        axes[0,2].set_title(titles[2], fontsize=12, fontweight='bold')
        axes[0,2].set_ylabel(ylabels[2])
        axes[0,2].grid(True, alpha=0.3)
        
        # 4. 持仓数量
        axes[1,0].plot(self.history_df['date'], self.history_df['positions'], 
                      'purple', marker='o', linewidth=2, markersize=6)
        axes[1,0].set_title(titles[3], fontsize=12, fontweight='bold')
        axes[1,0].set_ylabel(ylabels[3])
        axes[1,0].grid(True, alpha=0.3)
        
        # 5. 回撤分析
        peak = self.history_df['value'].expanding().max()
        drawdown = (self.history_df['value'] - peak) / peak * 100
        axes[1,1].fill_between(self.history_df['date'], drawdown, 0, 
                              alpha=0.3, color='red', label='Drawdown')
        axes[1,1].plot(self.history_df['date'], drawdown, 'r-', linewidth=1)
        axes[1,1].set_title(titles[4], fontsize=12, fontweight='bold')
        axes[1,1].set_ylabel(ylabels[4])
        axes[1,1].grid(True, alpha=0.3)
        
        # 6. 收益率分布
        period_returns = self.history_df['value'].pct_change().dropna() * 100
        axes[1,2].hist(period_returns, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
        axes[1,2].axvline(period_returns.mean(), color='r', linestyle='--', 
                         label=f'Mean: {period_returns.mean():.2f}%')
        axes[1,2].set_title(titles[5], fontsize=12, fontweight='bold')
        axes[1,2].set_ylabel(ylabels[5])
        axes[1,2].legend()
        axes[1,2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def print_summary(self):
        """打印回测总结"""
        metrics = self.calculate_metrics()
        
        print("\n" + "="*60)
        print("📊 完整回测结果总结")
        print("="*60)
        
        if metrics:
            print(f"💰 初始资金: {metrics['initial_value']:,.0f} 元")
            print(f"💎 最终价值: {metrics['final_value']:,.0f} 元")
            print(f"📈 总收益率: {metrics['total_return']:.2%}")
            print(f"📊 年化收益率: {metrics['annual_return']:.2%}")
            print(f"📉 最大回撤: {metrics['max_drawdown']:.2%}")
            print(f"🎯 胜率: {metrics['win_rate']:.2%}")
            print(f"📐 夏普比率: {metrics['sharpe_ratio']:.2f}")
            print(f"📊 年化波动率: {metrics['volatility']:.2%}")
            print(f"🔄 交易次数: {metrics['trade_count']} 笔")
            
            # 策略评级
            if metrics['annual_return'] > 0.15 and metrics['max_drawdown'] > -0.15:
                rating = "优秀 🌟🌟🌟"
            elif metrics['annual_return'] > 0.10 and metrics['max_drawdown'] > -0.20:
                rating = "良好 🌟🌟"
            elif metrics['annual_return'] > 0.05:
                rating = "中等 🌟"
            else:
                rating = "需要优化 🤔"
            
            print(f"📋 策略评级: {rating}")
        else:
            print("❌ 无法计算绩效指标")
        
        print("="*60)
    
    def export_detailed_analysis(self):
        """导出详细分析"""
        if not self.engine.trades:
            print("无交易记录")
            return
        
        trades_df = pd.DataFrame(self.engine.trades)
        
        print(f"\n📋 详细交易分析:")
        print("-" * 80)
        
        # 交易统计
        buy_trades = trades_df[trades_df['action'] == 'buy']
        sell_trades = trades_df[trades_df['action'] == 'sell']
        
        print(f"买入交易: {len(buy_trades)}笔, 总金额: {buy_trades['shares'].sum() * buy_trades['price'].mean():,.0f}元")
        print(f"卖出交易: {len(sell_trades)}笔, 总金额: {sell_trades['shares'].sum() * sell_trades['price'].mean():,.0f}元")
        print(f"总手续费: {trades_df['cost'].sum():,.2f}元")
        
        # 最近交易记录
        print(f"\n最近10笔交易:")
        for _, trade in trades_df.tail(10).iterrows():
            action_cn = "买入" if trade['action'] == 'buy' else "卖出"
            print(f"  {trade['date']} {action_cn} {trade['code']} "
                  f"{trade['shares']:>6}股 @{trade['price']:>7.2f}元 "
                  f"手续费:{trade['cost']:>6.2f}元")

# =============================================================================
# 主程序
# =============================================================================

def main():
    """主程序入口"""
    print("🚀 A股量化选股回测系统 - 完整版")
    print("="*60)
    print(f"💰 初始资金: {config.INITIAL_CAPITAL:,} 元")
    print(f"📅 回测周期: {config.START_DATE} 至 {config.END_DATE}")
    print(f"🔄 调仓频率: 季度")
    print(f"📊 最大持仓: {config.MAX_POSITIONS} 只")
    print(f"💼 交易成本: 佣金{config.COMMISSION_RATE:.2%} + 印花税{config.STAMP_TAX:.2%}")
    print("="*60)
    
    # 数据加载
    print("阶段1: 数据加载")
    print("-" * 30)
    data_manager = DataManager(config)
    
    if not data_manager.load_data():
        print("❌ 数据加载失败，请先运行 setup_data.py")
        return False
    
    # 回测执行
    print(f"\n阶段2: 回测执行")
    print("-" * 30)
    engine = BacktestEngine(config, data_manager)
    engine.run_backtest()
    
    # 结果分析
    print(f"\n阶段3: 结果分析")
    print("-" * 30)
    analyzer = ResultAnalyzer(engine)
    analyzer.print_summary()
    analyzer.plot_results()
    analyzer.export_detailed_analysis()
    
    print(f"\n🎉 A股量化选股回测系统运行完成！")
    print("💡 建议:")
    print("  1. 查看图表分析策略各项表现")
    print("  2. 根据结果调整选股参数")
    print("  3. 尝试不同的时间周期回测")
    print("  4. 考虑加入更多风险控制措施")
    
    return True

if __name__ == "__main__":
    main()