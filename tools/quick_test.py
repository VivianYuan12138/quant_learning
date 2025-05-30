#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股量化系统快速测试 - quick_test.py
功能：使用少量数据快速验证系统功能
作者：Claude
时间：2025年
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
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

class QuickTestConfig:
    """快速测试配置"""
    # 缓存目录
    CACHE_DIR = './data_cache/'
    STOCK_POOL_FILE = 'stock_pool.pkl'
    PRICE_DATA_FILE = 'price_data.pkl'
    
    # 测试参数
    INITIAL_CAPITAL = 10000
    MAX_POSITIONS = 6
    TEST_STOCK_COUNT = 20  # 只测试20只股票
    
    # 测试时间范围（缩短）
    START_DATE = '2023-01-01'
    END_DATE = '2023-12-31'
    
    # 交易成本
    COMMISSION_RATE = 0.0003
    STAMP_TAX = 0.001
    MIN_COMMISSION = 5

config = QuickTestConfig()

# =============================================================================
# 数据加载器
# =============================================================================

class QuickDataLoader:
    """快速数据加载器"""
    
    def __init__(self, config):
        self.config = config
    
    def load_test_data(self):
        """加载测试数据"""
        print("🔍 加载测试数据...")
        
        # 检查缓存文件是否存在
        stock_pool_file = os.path.join(self.config.CACHE_DIR, self.config.STOCK_POOL_FILE)
        price_data_file = os.path.join(self.config.CACHE_DIR, self.config.PRICE_DATA_FILE)
        
        if not os.path.exists(stock_pool_file) or not os.path.exists(price_data_file):
            print("❌ 未找到缓存数据文件")
            print("💡 请先运行 setup_data.py 获取数据")
            return None, None
        
        try:
            # 加载股票池
            with open(stock_pool_file, 'rb') as f:
                stock_pool = pickle.load(f)
            print(f"✅ 加载股票池: {len(stock_pool)}只股票")
            
            # 加载价格数据
            with open(price_data_file, 'rb') as f:
                price_data = pickle.load(f)
            print(f"✅ 加载价格数据: {len(price_data)}只股票")
            
            # 选择测试用的股票（随机选择）
            available_stocks = []
            for _, stock in stock_pool.iterrows():
                if stock['code'] in price_data and not price_data[stock['code']].empty:
                    available_stocks.append(stock)
                    if len(available_stocks) >= self.config.TEST_STOCK_COUNT:
                        break
            
            if len(available_stocks) < 5:
                print("❌ 可用测试数据不足")
                return None, None
            
            test_stock_pool = pd.DataFrame(available_stocks)
            test_price_data = {stock['code']: price_data[stock['code']] 
                             for stock in available_stocks}
            
            print(f"✅ 测试数据准备完成: {len(test_stock_pool)}只股票")
            
            return test_stock_pool, test_price_data
            
        except Exception as e:
            print(f"❌ 加载数据失败: {e}")
            return None, None

# =============================================================================
# 简化技术分析
# =============================================================================

class SimpleTechnicalAnalyzer:
    """简化技术分析器"""
    
    @staticmethod
    def calculate_indicators(price_data):
        """计算技术指标"""
        if len(price_data) < 30:
            return None
        
        close = price_data['close']
        
        # 移动平均线
        ma5 = close.rolling(5).mean()
        ma20 = close.rolling(20).mean()
        
        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # 动量
        momentum = close / close.shift(10) - 1
        
        return {
            'current_price': close.iloc[-1],
            'ma5': ma5.iloc[-1],
            'ma20': ma20.iloc[-1],
            'rsi': rsi.iloc[-1],
            'momentum': momentum.iloc[-1]
        }

# =============================================================================
# 简化选股策略
# =============================================================================

class QuickStockSelector:
    """快速选股策略"""
    
    def __init__(self, config):
        self.config = config
        self.analyzer = SimpleTechnicalAnalyzer()
    
    def select_stocks(self, stock_pool, price_data, date):
        """选股"""
        print(f"📊 执行选股 - {date}")
        
        candidates = []
        
        for _, stock in stock_pool.iterrows():
            stock_code = stock['code']
            
            if stock_code not in price_data:
                continue
            
            # 获取到指定日期的数据
            stock_price_data = price_data[stock_code]
            date_filtered = stock_price_data[stock_price_data.index <= date]
            
            if len(date_filtered) < 30:
                continue
            
            # 计算技术指标
            indicators = self.analyzer.calculate_indicators(date_filtered)
            if indicators is None:
                continue
            
            # 简化选股条件
            if (indicators['current_price'] > indicators['ma20'] and
                indicators['ma5'] > indicators['ma20'] and
                20 <= indicators['rsi'] <= 80 and
                indicators['momentum'] > -0.2):
                
                score = (
                    indicators['momentum'] * 50 +
                    (indicators['current_price'] / indicators['ma20'] - 1) * 30 +
                    (70 - abs(indicators['rsi'] - 50)) * 0.5
                )
                
                candidates.append({
                    'code': stock_code,
                    'name': stock['name'],
                    'score': score,
                    'price': indicators['current_price'],
                    'rsi': indicators['rsi'],  
                    'momentum': indicators['momentum']
                })
        
        if candidates:
            candidates_df = pd.DataFrame(candidates)
            selected = candidates_df.nlargest(self.config.MAX_POSITIONS, 'score')
            
            print(f"✅ 选出 {len(selected)} 只股票:")
            for _, stock in selected.iterrows():
                print(f"  {stock['code']} {stock['name']:<8} 评分:{stock['score']:.1f}")
            
            return selected
        else:
            print("⚠️ 未找到符合条件的股票")
            return pd.DataFrame()

# =============================================================================
# 简化回测引擎
# =============================================================================

class QuickBacktestEngine:
    """快速回测引擎"""
    
    def __init__(self, config):
        self.config = config
        self.selector = QuickStockSelector(config)
        
        # 交易状态
        self.cash = config.INITIAL_CAPITAL
        self.positions = {}
        self.portfolio_history = []
        self.trades = []
    
    def calculate_cost(self, amount, is_sell=False):
        """计算交易成本"""
        commission = max(amount * self.config.COMMISSION_RATE, self.config.MIN_COMMISSION)
        stamp_tax = amount * self.config.STAMP_TAX if is_sell else 0
        return commission + stamp_tax
    
    def execute_trade(self, action, code, price, shares, date):
        """执行交易"""
        amount = shares * price
        cost = self.calculate_cost(amount, action == 'sell')
        
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
    
    def get_portfolio_value(self, date, price_data):
        """计算组合价值"""
        total_value = self.cash
        
        for code, shares in self.positions.items():
            if code in price_data:
                stock_data = price_data[code]
                date_data = stock_data[stock_data.index <= date]
                if not date_data.empty:
                    current_price = date_data['close'].iloc[-1]
                    total_value += shares * current_price
        
        return total_value
    
    def rebalance(self, date, stock_pool, price_data):
        """执行调仓"""
        print(f"\n📅 执行调仓 - {date}")
        
        # 选股
        selected_stocks = self.selector.select_stocks(stock_pool, price_data, date)
        
        if selected_stocks.empty:
            print("❌ 无选股结果，跳过调仓")
            return
        
        # 清仓不在新选股中的股票
        current_codes = set(self.positions.keys())
        selected_codes = set(selected_stocks['code'])
        to_sell = current_codes - selected_codes
        
        for code in to_sell:
            shares = self.positions[code]
            stock_data = price_data[code]
            date_data = stock_data[stock_data.index <= date]
            if not date_data.empty:
                sell_price = date_data['close'].iloc[-1]
                if self.execute_trade('sell', code, sell_price, shares, date):
                    print(f"  📤 卖出 {code} {shares}股 @{sell_price:.2f}")
        
        # 计算目标仓位并买入
        portfolio_value = self.get_portfolio_value(date, price_data)
        target_value_per_stock = portfolio_value * 0.9 / len(selected_stocks)
        
        for _, stock in selected_stocks.iterrows():
            code = stock['code']
            target_price = stock['price']
            
            target_shares = int(target_value_per_stock // (target_price * 100)) * 100
            current_shares = self.positions.get(code, 0)
            
            if target_shares > current_shares:
                shares_to_buy = target_shares - current_shares
                if self.execute_trade('buy', code, target_price, shares_to_buy, date):
                    print(f"  📥 买入 {code} {stock['name']} {shares_to_buy}股 @{target_price:.2f}")
        
        # 记录组合状态
        final_value = self.get_portfolio_value(date, price_data)
        self.portfolio_history.append({
            'date': pd.to_datetime(date),
            'value': final_value,
            'cash': self.cash,
            'positions': len(self.positions)
        })
        
        print(f"  💰 组合价值: {final_value:.0f}元, 现金: {self.cash:.0f}元")
    
    def run_backtest(self, stock_pool, price_data):
        """运行快速回测"""
        print("🚀 开始快速回测")
        print("="*40)
        
        # 生成季度调仓日期
        rebalance_dates = pd.date_range(
            start=self.config.START_DATE,
            end=self.config.END_DATE,
            freq='QS'
        )
        
        print(f"回测周期: {len(rebalance_dates)}个季度")
        
        for i, date in enumerate(rebalance_dates):
            date_str = date.strftime('%Y-%m-%d')
            print(f"\n[{i+1}/{len(rebalance_dates)}] {date_str}")
            self.rebalance(date_str, stock_pool, price_data)
        
        print(f"\n✅ 快速回测完成！共执行{len(self.trades)}笔交易")

# =============================================================================
# 结果分析
# =============================================================================

class QuickResultAnalyzer:
    """快速结果分析"""
    
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
        
        # 年化收益率
        days = (self.history_df['date'].iloc[-1] - self.history_df['date'].iloc[0]).days
        annual_return = (1 + total_return) ** (365 / days) - 1
        
        # 最大回撤
        peak = self.history_df['value'].expanding().max()
        drawdown = (self.history_df['value'] - peak) / peak
        max_drawdown = drawdown.min()
        
        return {
            'initial_value': initial,
            'final_value': final,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'trade_count': len(self.engine.trades)
        }
    
    def plot_results(self):
        """绘制结果图表"""
        if self.history_df.empty:
            print("无数据可绘制")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        
        # 根据设置选择标题语言
        if USE_ENGLISH_LABELS:
            titles = ['Portfolio Value', 'Cumulative Return', 'Cash Ratio', 'Position Count']
            ylabels = ['Value (CNY)', 'Return (%)', 'Ratio (%)', 'Stock Count']
        else:
            titles = ['资产净值曲线', '累计收益率', '现金占比', '持仓数量']
            ylabels = ['价值(元)', '收益率(%)', '占比(%)', '股票数量']
        
        # 净值曲线
        axes[0,0].plot(self.history_df['date'], self.history_df['value'], 'b-', linewidth=2)
        axes[0,0].axhline(self.engine.config.INITIAL_CAPITAL, color='r', linestyle='--', alpha=0.7)
        axes[0,0].set_title(titles[0])
        axes[0,0].set_ylabel(ylabels[0])
        axes[0,0].grid(True, alpha=0.3)
        
        # 收益率
        returns = (self.history_df['value'] / self.engine.config.INITIAL_CAPITAL - 1) * 100
        axes[0,1].plot(self.history_df['date'], returns, 'g-', linewidth=2)
        axes[0,1].axhline(0, color='r', linestyle='--', alpha=0.7)
        axes[0,1].set_title(titles[1])
        axes[0,1].set_ylabel(ylabels[1])
        axes[0,1].grid(True, alpha=0.3)
        
        # 现金占比
        cash_pct = self.history_df['cash'] / self.history_df['value'] * 100
        axes[1,0].plot(self.history_df['date'], cash_pct, 'orange', linewidth=2)
        axes[1,0].set_title(titles[2])
        axes[1,0].set_ylabel(ylabels[2])
        axes[1,0].grid(True, alpha=0.3)
        
        # 持仓数量
        axes[1,1].plot(self.history_df['date'], self.history_df['positions'], 
                      'purple', marker='o', linewidth=2)
        axes[1,1].set_title(titles[3])
        axes[1,1].set_ylabel(ylabels[3])
        axes[1,1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def print_summary(self):
        """打印结果总结"""
        metrics = self.calculate_metrics()
        
        print("\n" + "="*50)
        print("📊 快速测试结果总结")
        print("="*50)
        
        if metrics:
            print(f"💰 初始资金: {metrics['initial_value']:,.0f} 元")
            print(f"💎 最终价值: {metrics['final_value']:,.0f} 元")
            print(f"📈 总收益率: {metrics['total_return']:.2%}")
            print(f"📊 年化收益率: {metrics['annual_return']:.2%}")
            print(f"📉 最大回撤: {metrics['max_drawdown']:.2%}")
            print(f"🔄 交易次数: {metrics['trade_count']} 笔")
            
            # 简单评级
            if metrics['annual_return'] > 0.10:
                rating = "良好 👍"
            elif metrics['annual_return'] > 0.05:
                rating = "一般 👌"
            else:
                rating = "需要优化 🤔"
            
            print(f"📋 测试评级: {rating}")
        else:
            print("❌ 无法计算指标")
        
        print("="*50)

# =============================================================================
# 主函数
# =============================================================================

def quick_test():
    """快速测试主函数"""
    print("🧪 A股量化系统 - 快速测试")
    print("="*40)
    print(f"💰 测试资金: {config.INITIAL_CAPITAL:,} 元") 
    print(f"📅 测试周期: {config.START_DATE} 至 {config.END_DATE}")
    print(f"📊 测试股票: 最多 {config.TEST_STOCK_COUNT} 只")
    print(f"🔄 调仓频率: 季度")
    print("="*40)
    
    # 加载测试数据
    data_loader = QuickDataLoader(config)
    stock_pool, price_data = data_loader.load_test_data()
    
    if stock_pool is None or price_data is None:
        return False
    
    # 运行回测
    engine = QuickBacktestEngine(config)
    engine.run_backtest(stock_pool, price_data)
    
    # 分析结果
    analyzer = QuickResultAnalyzer(engine)
    analyzer.print_summary()
    analyzer.plot_results()
    
    # 显示交易记录
    if engine.trades:
        print(f"\n📋 交易记录:")
        trades_df = pd.DataFrame(engine.trades)
        for _, trade in trades_df.iterrows():
            action = "买入" if trade['action'] == 'buy' else "卖出"
            print(f"  {trade['date']} {action} {trade['code']} "
                  f"{trade['shares']}股 @{trade['price']:.2f}元")
    
    print(f"\n✅ 快速测试完成！")
    print("💡 如果结果满意，可以运行完整版本的 main.py")
    return True

if __name__ == "__main__":
    quick_test()