#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结果分析器 - result_analyzer.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

from config import config

# 设置中文字体
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


class ResultAnalyzer:
    """结果分析器"""
    
    def __init__(self, backtest_results, config_obj=None):
        self.results = backtest_results
        self.config = config_obj or config
        
        # 从回测结果中提取数据
        self.portfolio_history = backtest_results.get('portfolio_history', [])
        self.trades = backtest_results.get('trades', [])
        self.strategy_name = backtest_results.get('strategy_name', '未知策略')
        
        # 转换为DataFrame
        self.history_df = pd.DataFrame(self.portfolio_history)
        self.trades_df = pd.DataFrame(self.trades) if self.trades else pd.DataFrame()
    
    def calculate_metrics(self):
        """计算绩效指标"""
        if self.history_df.empty:
            return {}
        
        initial = self.config.INITIAL_CAPITAL
        final = self.history_df['value'].iloc[-1]
        
        total_return = (final - initial) / initial
        
        # 计算年化收益率
        start_date = self.history_df['date'].iloc[0]
        end_date = self.history_df['date'].iloc[-1]
        days = (end_date - start_date).days
        annual_return = (1 + total_return) ** (365 / days) - 1 if days > 0 else 0
        
        # 计算最大回撤
        peak = self.history_df['value'].expanding().max()
        drawdown = (self.history_df['value'] - peak) / peak
        max_drawdown = drawdown.min()
        
        # 计算胜率（期间收益率）
        returns = self.history_df['value'].pct_change().dropna()
        win_rate = (returns > 0).mean() if len(returns) > 0 else 0
        
        # 计算夏普比率
        if len(returns) > 1:
            risk_free_rate = 0.03  # 假设无风险利率3%
            period_risk_free = risk_free_rate / len(returns)  # 调整到期间频率
            excess_returns = returns - period_risk_free
            sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(len(returns)) if excess_returns.std() > 0 else 0
        else:
            sharpe_ratio = 0
        
        # 计算波动率
        volatility = returns.std() * np.sqrt(len(returns)) if len(returns) > 1 else 0
        
        # 计算信息比率
        if len(returns) > 1:
            information_ratio = returns.mean() / returns.std() * np.sqrt(len(returns))
        else:
            information_ratio = 0
        
        # 计算最大连续亏损天数
        losing_streaks = []
        current_streak = 0
        for ret in returns:
            if ret < 0:
                current_streak += 1
            else:
                if current_streak > 0:
                    losing_streaks.append(current_streak)
                current_streak = 0
        if current_streak > 0:
            losing_streaks.append(current_streak)
        max_losing_streak = max(losing_streaks) if losing_streaks else 0
        
        return {
            'strategy_name': self.strategy_name,
            'initial_value': initial,
            'final_value': final,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'sharpe_ratio': sharpe_ratio,
            'information_ratio': information_ratio,
            'volatility': volatility,
            'max_losing_streak': max_losing_streak,
            'trade_count': len(self.trades),
            'days': days
        }
    
    def plot_results(self, save_path=None):
        """绘制结果图表"""
        if self.history_df.empty:
            print("无数据可绘制")
            return
        
        # 根据设置选择标题语言
        if self.config.USE_ENGLISH_LABELS:
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
        axes[0,0].axhline(self.config.INITIAL_CAPITAL, 
                         color='r', linestyle='--', alpha=0.7, label='Initial Capital')
        axes[0,0].set_title(f"{titles[0]} - {self.strategy_name}", fontsize=12, fontweight='bold')
        axes[0,0].set_ylabel(ylabels[0])
        axes[0,0].legend()
        axes[0,0].grid(True, alpha=0.3)
        
        # 2. 累计收益率
        returns = (self.history_df['value'] / self.config.INITIAL_CAPITAL - 1) * 100
        axes[0,1].plot(self.history_df['date'], returns, 'g-', linewidth=2)
        axes[0,1].axhline(0, color='r', linestyle='--', alpha=0.7)
        axes[0,1].set_title(titles[1], fontsize=12, fontweight='bold')
        axes[0,1].set_ylabel(ylabels[1])
        axes[0,1].grid(True, alpha=0.3)
        
        # 3. 现金占比
        if 'cash' in self.history_df.columns:
            cash_ratio = self.history_df['cash'] / self.history_df['value'] * 100
            axes[0,2].plot(self.history_df['date'], cash_ratio, 'orange', linewidth=2)
        axes[0,2].set_title(titles[2], fontsize=12, fontweight='bold')
        axes[0,2].set_ylabel(ylabels[2])
        axes[0,2].grid(True, alpha=0.3)
        
        # 4. 持仓数量
        if 'positions' in self.history_df.columns:
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
        if len(period_returns) > 0:
            axes[1,2].hist(period_returns, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
            axes[1,2].axvline(period_returns.mean(), color='r', linestyle='--', 
                             label=f'Mean: {period_returns.mean():.2f}%')
            axes[1,2].legend()
        axes[1,2].set_title(titles[5], fontsize=12, fontweight='bold')
        axes[1,2].set_ylabel(ylabels[5])
        axes[1,2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"图表已保存到: {save_path}")
        
        plt.show()
    
    def print_summary(self):
        """打印回测总结"""
        metrics = self.calculate_metrics()
        
        print("\n" + "="*60)
        print(f"📊 {self.strategy_name} 回测结果总结")
        print("="*60)
        
        if metrics:
            print(f"💰 初始资金: {metrics['initial_value']:,.0f} 元")
            print(f"💎 最终价值: {metrics['final_value']:,.0f} 元")
            print(f"📈 总收益率: {metrics['total_return']:.2%}")
            print(f"📊 年化收益率: {metrics['annual_return']:.2%}")
            print(f"📉 最大回撤: {metrics['max_drawdown']:.2%}")
            print(f"🎯 胜率: {metrics['win_rate']:.2%}")
            print(f"📐 夏普比率: {metrics['sharpe_ratio']:.2f}")
            print(f"📊 信息比率: {metrics['information_ratio']:.2f}")
            print(f"📊 年化波动率: {metrics['volatility']:.2%}")
            print(f"📅 最大连续亏损期: {metrics['max_losing_streak']} 期")
            print(f"🔄 交易次数: {metrics['trade_count']} 笔")
            print(f"⏱️ 回测天数: {metrics['days']} 天")
            
            # 策略评级
            score = self._calculate_strategy_score(metrics)
            rating = self._get_strategy_rating(score)
            print(f"📋 策略评级: {rating} (评分: {score:.1f}/100)")
        else:
            print("❌ 无法计算绩效指标")
        
        print("="*60)
    
    def _calculate_strategy_score(self, metrics):
        """计算策略评分"""
        score = 0
        
        # 收益率评分 (30分)
        annual_return = metrics['annual_return']
        if annual_return > 0.20:
            score += 30
        elif annual_return > 0.15:
            score += 25
        elif annual_return > 0.10:
            score += 20
        elif annual_return > 0.05:
            score += 15
        elif annual_return > 0:
            score += 10
        
        # 风险控制评分 (25分)
        max_drawdown = abs(metrics['max_drawdown'])
        if max_drawdown < 0.05:
            score += 25
        elif max_drawdown < 0.10:
            score += 20
        elif max_drawdown < 0.15:
            score += 15
        elif max_drawdown < 0.20:
            score += 10
        elif max_drawdown < 0.30:
            score += 5
        
        # 夏普比率评分 (20分)
        sharpe = metrics['sharpe_ratio']
        if sharpe > 2:
            score += 20
        elif sharpe > 1.5:
            score += 15
        elif sharpe > 1:
            score += 10
        elif sharpe > 0.5:
            score += 5
        
        # 胜率评分 (15分)
        win_rate = metrics['win_rate']
        if win_rate > 0.6:
            score += 15
        elif win_rate > 0.55:
            score += 12
        elif win_rate > 0.5:
            score += 10
        elif win_rate > 0.45:
            score += 7
        elif win_rate > 0.4:
            score += 5
        
        # 稳定性评分 (10分)
        if metrics['max_losing_streak'] <= 2:
            score += 10
        elif metrics['max_losing_streak'] <= 3:
            score += 8
        elif metrics['max_losing_streak'] <= 5:
            score += 5
        elif metrics['max_losing_streak'] <= 7:
            score += 3
        
        return score
    
    def _get_strategy_rating(self, score):
        """根据评分获取评级"""
        if score >= 85:
            return "优秀 🌟🌟🌟🌟🌟"
        elif score >= 70:
            return "良好 🌟🌟🌟🌟"
        elif score >= 55:
            return "中等 🌟🌟🌟"
        elif score >= 40:
            return "一般 🌟🌟"
        elif score >= 25:
            return "较差 🌟"
        else:
            return "需要优化 😞"
    
    def export_detailed_analysis(self, export_path=None):
        """导出详细分析"""
        print(f"\n📋 详细分析:")
        print("-" * 80)
        
        if not self.trades_df.empty:
            # 交易统计
            buy_trades = self.trades_df[self.trades_df['action'] == 'buy']
            sell_trades = self.trades_df[self.trades_df['action'] == 'sell']
            
            print(f"买入交易: {len(buy_trades)}笔")
            print(f"卖出交易: {len(sell_trades)}笔")
            print(f"总手续费: {self.trades_df['cost'].sum():,.2f}元")
            
            if len(buy_trades) > 0:
                avg_buy_amount = (buy_trades['shares'] * buy_trades['price']).mean()
                print(f"平均买入金额: {avg_buy_amount:,.0f}元")
            
            if len(sell_trades) > 0:
                avg_sell_amount = (sell_trades['shares'] * sell_trades['price']).mean()
                print(f"平均卖出金额: {avg_sell_amount:,.0f}元")
            
            # 最近交易记录
            print(f"\n最近10笔交易:")
            for _, trade in self.trades_df.tail(10).iterrows():
                action_cn = "买入" if trade['action'] == 'buy' else "卖出"
                print(f"  {trade['date']} {action_cn} {trade['code']} "
                      f"{trade['shares']:>6}股 @{trade['price']:>7.2f}元 "
                      f"手续费:{trade['cost']:>6.2f}元")
        else:
            print("无交易记录")
        
        # 导出到文件
        if export_path:
            try:
                metrics = self.calculate_metrics()
                export_data = {
                    'metrics': metrics,
                    'portfolio_history': self.portfolio_history,
                    'trades': self.trades
                }
                
                import pickle
                with open(export_path, 'wb') as f:
                    pickle.dump(export_data, f)
                print(f"\n✅ 详细分析已导出到: {export_path}")
            except Exception as e:
                print(f"❌ 导出失败: {e}")
    
    def compare_with_benchmark(self, benchmark_return=0.08):
        """与基准收益率比较"""
        metrics = self.calculate_metrics()
        if not metrics:
            return
        
        print(f"\n📊 与基准收益率({benchmark_return:.1%})比较:")
        print("-" * 40)
        
        annual_return = metrics['annual_return']
        excess_return = annual_return - benchmark_return
        
        print(f"策略年化收益率: {annual_return:.2%}")
        print(f"基准年化收益率: {benchmark_return:.2%}")
        print(f"超额收益率: {excess_return:+.2%}")
        
        if excess_return > 0:
            print("✅ 策略跑赢基准")
        else:
            print("❌ 策略跑输基准") 