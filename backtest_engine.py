#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回测引擎 - backtest_engine.py
"""

import pandas as pd
from config import config
from data_manager import DataManager


class BacktestEngine:
    """完整回测引擎"""
    
    def __init__(self, strategy, config_obj=None, data_manager=None):
        self.strategy = strategy
        self.config = config_obj or config
        self.data_manager = data_manager or DataManager(self.config)
        
        # 设置策略的数据管理器
        if hasattr(self.strategy, 'data_manager'):
            self.strategy.data_manager = self.data_manager
        
        # 交易状态
        self.cash = self.config.INITIAL_CAPITAL
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
        
        # 使用策略选股
        selected_stocks = self.strategy.select_stocks_for_date(date)
        
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
    
    def run_backtest(self, start_date=None, end_date=None, rebalance_freq=None):
        """运行回测"""
        start_date = start_date or self.config.START_DATE
        end_date = end_date or self.config.END_DATE
        rebalance_freq = rebalance_freq or self.config.REBALANCE_FREQ
        
        print("\n" + "="*60)
        print("🚀 开始量化回测")
        print("="*60)
        print(f"策略: {self.strategy.name}")
        print(f"回测周期: {start_date} 至 {end_date}")
        print(f"调仓频率: {rebalance_freq}")
        print("="*60)
        
        # 生成调仓日期
        freq_map = {
            'M': 'MS',    # 月度开始
            'Q': 'QS',    # 季度开始
            'Y': 'YS'     # 年度开始
        }
        
        rebalance_dates = pd.date_range(
            start=start_date,
            end=end_date,
            freq=freq_map.get(rebalance_freq, 'QS')
        )
        
        print(f"调仓次数: {len(rebalance_dates)}次")
        print(f"调仓日期: {[d.strftime('%Y-%m-%d') for d in rebalance_dates[:5]]}{'...' if len(rebalance_dates) > 5 else ''}")
        
        # 执行回测
        for i, date in enumerate(rebalance_dates):
            date_str = date.strftime('%Y-%m-%d')
            print(f"\n[{i+1}/{len(rebalance_dates)}] 🗓️ {date_str}")
            self.rebalance(date_str)
        
        print(f"\n✅ 回测完成！共执行{len(self.trades)}笔交易")
        
        return {
            'portfolio_history': self.portfolio_history,
            'trades': self.trades,
            'final_value': self.get_portfolio_value(end_date),
            'strategy_name': self.strategy.name
        }
    
    def get_portfolio_summary(self):
        """获取组合摘要"""
        if not self.portfolio_history:
            return {}
        
        history_df = pd.DataFrame(self.portfolio_history)
        initial_value = self.config.INITIAL_CAPITAL
        final_value = history_df['value'].iloc[-1]
        
        return {
            'initial_value': initial_value,
            'final_value': final_value,
            'total_return': (final_value - initial_value) / initial_value,
            'total_trades': len(self.trades),
            'final_positions': len(self.positions),
            'final_cash': self.cash
        } 