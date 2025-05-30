#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股量化回测系统 - 重构版 main.py
功能：模块化的量化选股回测系统
作者：Claude
时间：2025年
"""

from config import config
from data_manager import DataManager
from backtest_engine import BacktestEngine
from result_analyzer import ResultAnalyzer

# 导入策略
from strategies import MomentumStrategy, ValueStrategy, GrowthStrategy


def run_single_strategy_backtest(strategy_class, strategy_name=None, **strategy_params):
    """运行单个策略回测"""
    print(f"\n{'='*60}")
    print(f"🚀 开始回测策略: {strategy_name or strategy_class.__name__}")
    print(f"{'='*60}")
    
    # 1. 数据加载
    print("阶段1: 数据加载")
    print("-" * 30)
    data_manager = DataManager(config)
    
    if not data_manager.load_data():
        print("❌ 数据加载失败，请先运行 setup_data.py")
        return None
    
    # 2. 初始化策略
    print(f"\n阶段2: 初始化策略")
    print("-" * 30)
    strategy = strategy_class(config_obj=config, data_manager=data_manager, **strategy_params)
    print(strategy.get_strategy_description())
    
    # 3. 运行回测
    print(f"\n阶段3: 执行回测")
    print("-" * 30)
    engine = BacktestEngine(strategy, config, data_manager)
    results = engine.run_backtest()
    
    # 4. 分析结果
    print(f"\n阶段4: 结果分析")
    print("-" * 30)
    analyzer = ResultAnalyzer(results, config)
    analyzer.print_summary()
    analyzer.plot_results()
    analyzer.export_detailed_analysis()
    
    return results


def run_multiple_strategies_comparison():
    """运行多策略对比"""
    print(f"\n{'='*60}")
    print("🔥 多策略对比回测")
    print(f"{'='*60}")
    
    # 定义要对比的策略
    strategies_to_test = [
        (MomentumStrategy, "动量策略", {}),
        (ValueStrategy, "价值策略", {}),
        (GrowthStrategy, "成长策略", {}),
        # 你可以添加更多策略或参数变体
        (MomentumStrategy, "保守动量策略", {
            'min_rsi': 30, 'max_rsi': 70, 'min_momentum_5d': 0
        }),
        (ValueStrategy, "激进价值策略", {
            'max_price_position': 0.4, 'max_rsi': 60
        })
    ]
    
    # 数据加载（只需要一次）
    data_manager = DataManager(config)
    if not data_manager.load_data():
        print("❌ 数据加载失败")
        return
    
    all_results = []
    
    # 逐个测试策略
    for strategy_class, strategy_name, params in strategies_to_test:
        print(f"\n🧪 测试策略: {strategy_name}")
        print("-" * 40)
        
        try:
            # 初始化策略
            strategy = strategy_class(config_obj=config, data_manager=data_manager, **params)
            
            # 运行回测
            engine = BacktestEngine(strategy, config, data_manager)
            results = engine.run_backtest()
            results['strategy_name'] = strategy_name
            
            # 简要分析
            analyzer = ResultAnalyzer(results, config)
            metrics = analyzer.calculate_metrics()
            
            print(f"  📊 年化收益率: {metrics['annual_return']:.2%}")
            print(f"  📉 最大回撤: {metrics['max_drawdown']:.2%}")
            print(f"  📐 夏普比率: {metrics['sharpe_ratio']:.2f}")
            
            all_results.append((strategy_name, metrics, results))
            
        except Exception as e:
            print(f"  ❌ 策略测试失败: {e}")
    
    # 对比结果
    print(f"\n{'='*60}")
    print("📊 策略对比结果")
    print(f"{'='*60}")
    
    if all_results:
        # 排序（按年化收益率）
        all_results.sort(key=lambda x: x[1]['annual_return'], reverse=True)
        
        print(f"{'策略名称':<15} {'年化收益':<10} {'最大回撤':<10} {'夏普比率':<10} {'胜率':<8}")
        print("-" * 60)
        
        for strategy_name, metrics, _ in all_results:
            print(f"{strategy_name:<15} {metrics['annual_return']:>8.2%} "
                  f"{metrics['max_drawdown']:>8.2%} {metrics['sharpe_ratio']:>8.2f} "
                  f"{metrics['win_rate']:>6.2%}")
        
        # 显示最佳策略
        best_strategy = all_results[0]
        print(f"\n🏆 最佳策略: {best_strategy[0]}")
        print(f"   年化收益率: {best_strategy[1]['annual_return']:.2%}")
        print(f"   风险收益比: {best_strategy[1]['sharpe_ratio']:.2f}")


def run_custom_strategy_example():
    """演示如何创建自定义策略"""
    print(f"\n{'='*60}")
    print("📝 自定义策略示例")
    print(f"{'='*60}")
    
    from strategy_base import BaseStrategy
    
    class CustomStrategy(BaseStrategy):
        """自定义策略示例"""
        
        def __init__(self, **kwargs):
            super().__init__("自定义策略", **kwargs)
            # 你的策略参数
            self.custom_param = kwargs.get('custom_param', 0.5)
        
        def is_qualified_stock(self, indicators, stock_info=None):
            """自定义选股条件"""
            return (
                indicators['rsi'] > 30 and 
                indicators['rsi'] < 70 and
                indicators['momentum_5d'] > 0 and
                indicators['price'] > indicators['ma20']
            )
        
        def calculate_score(self, indicators, stock_info=None):
            """自定义评分逻辑"""
            score = (
                indicators['momentum_5d'] * 50 +
                (indicators['rsi'] - 50) * 0.5 +
                indicators['volume_ratio'] * 10
            )
            return score
    
    print("✅ 自定义策略创建完成")
    print("💡 你可以继承 BaseStrategy 类来创建自己的策略")
    print("💡 需要实现 is_qualified_stock() 和 calculate_score() 方法")
    
    # 可以取消注释来测试自定义策略
    # run_single_strategy_backtest(CustomStrategy, "我的自定义策略", custom_param=0.8)


def show_system_info():
    """显示系统信息"""
    print("🚀 A股量化回测系统 - 模块化版本")
    print("="*60)
    print(f"💰 初始资金: {config.INITIAL_CAPITAL:,} 元")
    print(f"📅 回测周期: {config.START_DATE} 至 {config.END_DATE}")
    print(f"🔄 调仓频率: {config.REBALANCE_FREQ}")
    print(f"📊 最大持仓: {config.MAX_POSITIONS} 只")
    print(f"💼 交易成本: 佣金{config.COMMISSION_RATE:.2%} + 印花税{config.STAMP_TAX:.2%}")
    print("="*60)
    
    print("\n📁 系统架构:")
    print("  ├── config.py           # 配置管理")
    print("  ├── data_manager.py     # 数据管理")
    print("  ├── technical_analyzer.py # 技术分析")
    print("  ├── strategy_base.py    # 策略基类")
    print("  ├── backtest_engine.py  # 回测引擎")
    print("  ├── result_analyzer.py  # 结果分析")
    print("  ├── strategies/         # 策略目录")
    print("  │   ├── momentum_strategy.py")
    print("  │   ├── value_strategy.py")
    print("  │   └── growth_strategy.py")
    print("  └── main.py            # 主程序")


def main():
    """主程序入口"""
    show_system_info()
    
    print("\n🎯 选择运行模式:")
    print("1. 单策略回测 - 动量策略")
    print("2. 单策略回测 - 价值策略") 
    print("3. 单策略回测 - 成长策略")
    print("4. 多策略对比")
    print("5. 自定义策略示例")
    print("6. 全部运行")
    
    try:
        choice = input("\n请选择模式 (1-6): ").strip()
        
        if choice == '1':
            run_single_strategy_backtest(MomentumStrategy, "动量策略")
        elif choice == '2':
            run_single_strategy_backtest(ValueStrategy, "价值策略")
        elif choice == '3':
            run_single_strategy_backtest(GrowthStrategy, "成长策略")
        elif choice == '4':
            run_multiple_strategies_comparison()
        elif choice == '5':
            run_custom_strategy_example()
        elif choice == '6':
            # 全部运行
            run_single_strategy_backtest(MomentumStrategy, "动量策略")
            run_single_strategy_backtest(ValueStrategy, "价值策略")
            run_single_strategy_backtest(GrowthStrategy, "成长策略")
            run_multiple_strategies_comparison()
        else:
            print("❌ 无效选择，默认运行动量策略")
            run_single_strategy_backtest(MomentumStrategy, "动量策略")
            
    except KeyboardInterrupt:
        print("\n\n👋 程序已退出")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
    
    print(f"\n🎉 量化回测系统运行完成！")
    print("💡 提示:")
    print("  1. 修改 config.py 来调整系统参数")
    print("  2. 在 strategies/ 目录下创建你的策略")
    print("  3. 继承 BaseStrategy 类来实现自定义策略")
    print("  4. 使用 BacktestEngine 来测试你的策略")


if __name__ == "__main__":
    main()