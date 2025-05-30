#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股数据获取系统 - setup_data.py
功能：获取沪深主板A股历史数据，支持断点续传和容错恢复
作者：Claude
时间：2025年
"""

import pandas as pd
import numpy as np
import akshare as ak
import pickle
import os
import json
import time
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# 配置参数
# =============================================================================

class DataConfig:
    """数据获取配置"""
    # 缓存目录
    CACHE_DIR = './data_cache/'
    STOCK_POOL_FILE = 'stock_pool.pkl'
    PRICE_DATA_FILE = 'price_data.pkl'
    PROGRESS_FILE = 'progress.json'
    FAILED_STOCKS_FILE = 'failed_stocks.json'
    
    # 数据时间范围
    START_DATE = '2020-01-01'  # 从2020年开始
    END_DATE = datetime.now().strftime('%Y-%m-%d')  # 到今天
    
    # 容错参数
    MAX_RETRIES = 3          # 每只股票最大重试次数
    SAVE_INTERVAL = 10       # 每10只股票保存一次进度
    REQUEST_DELAY = 0.3      # 请求间隔(秒)
    RETRY_DELAY = 1.0        # 重试间隔(秒)
    
    # 股票筛选条件
    MAIN_BOARD_PREFIXES = ['000', '002', '600', '601', '603']  # 只要主板
    EXCLUDE_KEYWORDS = ['ST', '退', 'N ', 'C ']  # 排除关键词

config = DataConfig()

# 创建缓存目录
if not os.path.exists(config.CACHE_DIR):
    os.makedirs(config.CACHE_DIR)

# =============================================================================
# 进度管理器
# =============================================================================

class ProgressManager:
    """进度管理器 - 支持断点续传"""
    
    def __init__(self, config):
        self.config = config
        self.progress_file = os.path.join(config.CACHE_DIR, config.PROGRESS_FILE)
        self.failed_file = os.path.join(config.CACHE_DIR, config.FAILED_STOCKS_FILE)
        self.progress_data = self.load_progress()
        self.failed_stocks = self.load_failed_stocks()
    
    def load_progress(self):
        """加载进度数据"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'completed_stocks': [],
            'total_stocks': 0,
            'last_update': None,
            'start_time': None
        }
    
    def load_failed_stocks(self):
        """加载失败股票记录"""
        if os.path.exists(self.failed_file):
            try:
                with open(self.failed_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_progress(self):
        """保存进度"""
        self.progress_data['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(self.progress_data, f, ensure_ascii=False, indent=2)
    
    def save_failed_stocks(self):
        """保存失败股票记录"""
        with open(self.failed_file, 'w', encoding='utf-8') as f:
            json.dump(self.failed_stocks, f, ensure_ascii=False, indent=2)
    
    def mark_completed(self, stock_code):
        """标记股票为已完成"""
        if stock_code not in self.progress_data['completed_stocks']:
            self.progress_data['completed_stocks'].append(stock_code)
    
    def mark_failed(self, stock_code, error_msg):
        """标记股票为失败"""
        self.failed_stocks[stock_code] = {
            'error': str(error_msg),
            'retry_count': self.failed_stocks.get(stock_code, {}).get('retry_count', 0) + 1,
            'last_attempt': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def is_completed(self, stock_code):
        """检查股票是否已完成"""
        return stock_code in self.progress_data['completed_stocks']
    
    def should_retry(self, stock_code):
        """检查是否应该重试"""
        if stock_code not in self.failed_stocks:
            return True
        return self.failed_stocks[stock_code].get('retry_count', 0) < self.config.MAX_RETRIES
    
    def get_retry_count(self, stock_code):
        """获取重试次数"""
        return self.failed_stocks.get(stock_code, {}).get('retry_count', 0)
    
    def print_status(self):
        """打印当前状态"""
        completed = len(self.progress_data['completed_stocks'])
        total = self.progress_data['total_stocks']
        failed = len(self.failed_stocks)
        
        if total > 0:
            progress_pct = completed / total * 100
            print(f"📊 进度: {completed}/{total} ({progress_pct:.1f}%) | 失败: {failed}只")
            
            if completed > 0 and self.progress_data.get('start_time'):
                start_time = datetime.strptime(self.progress_data['start_time'], '%Y-%m-%d %H:%M:%S')
                elapsed = (datetime.now() - start_time).total_seconds()
                avg_time = elapsed / completed
                remaining = (total - completed) * avg_time
                
                if remaining > 0:
                    eta = datetime.now() + timedelta(seconds=remaining)
                    print(f"⏱️  预计完成时间: {eta.strftime('%H:%M:%S')}")

# =============================================================================
# 数据获取器
# =============================================================================

class RobustDataFetcher:
    """强化数据获取器"""
    
    def __init__(self, config):
        self.config = config
        self.progress_manager = ProgressManager(config)
    
    def get_main_board_stocks(self):
        """获取沪深主板股票列表"""
        print("="*60)
        print("步骤1: 获取沪深主板A股列表")
        print("="*60)
        
        cache_file = os.path.join(self.config.CACHE_DIR, self.config.STOCK_POOL_FILE)
        
        # 检查缓存
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'rb') as f:
                    cached_stocks = pickle.load(f)
                print(f"✅ 发现股票池缓存，共{len(cached_stocks)}只股票")
                
                # 显示缓存信息
                if not cached_stocks.empty:
                    code_stats = cached_stocks['code'].str[:3].value_counts()
                    print("📊 缓存股票分布:")
                    for prefix, count in code_stats.items():
                        board_name = {
                            '000': '深圳主板', '002': '深圳中小板', 
                            '600': '上海主板', '601': '上海主板', '603': '上海主板'
                        }.get(prefix, '其他')
                        print(f"  {prefix}xxx ({board_name}): {count}只")
                
                # 询问是否使用缓存
                choice = input("是否使用缓存的股票池？(y/n): ").lower().strip()
                if choice == 'y':
                    return cached_stocks
                else:
                    print("重新获取股票池...")
            except Exception as e:
                print(f"⚠️ 缓存文件损坏: {e}")
        
        # 获取全部A股列表
        try:
            print("正在获取A股列表...")
            all_stocks = ak.stock_info_a_code_name()
            print(f"✅ 获取到{len(all_stocks)}只A股")
            
            # 筛选沪深主板
            main_board_stocks = all_stocks[
                # 只要主板代码
                (all_stocks['code'].str[:3].isin(self.config.MAIN_BOARD_PREFIXES)) &
                # 排除ST等股票
                (~all_stocks['name'].str.contains('|'.join(self.config.EXCLUDE_KEYWORDS), na=False))
            ].copy()
            
            print(f"✅ 筛选出沪深主板A股: {len(main_board_stocks)}只")
            
            # 显示统计信息
            code_stats = main_board_stocks['code'].str[:3].value_counts()
            print("📊 股票分布:")
            for prefix, count in code_stats.items():
                board_name = {
                    '000': '深圳主板', '002': '深圳中小板', 
                    '600': '上海主板', '601': '上海主板', '603': '上海主板'
                }.get(prefix, '其他')
                print(f"  {prefix}xxx ({board_name}): {count}只")
            
            # 显示前10只股票样本
            print("\n📋 股票样本 (前10只):")
            for _, stock in main_board_stocks.head(10).iterrows():
                print(f"  {stock['code']} {stock['name']}")
            
            # 保存到缓存
            with open(cache_file, 'wb') as f:
                pickle.dump(main_board_stocks, f)
            print(f"✅ 股票池已保存到缓存")
            
            return main_board_stocks
            
        except Exception as e:
            print(f"❌ 获取股票列表失败: {e}")
            return pd.DataFrame()
    
    def get_stock_price_with_retry(self, stock_code, stock_name):
        """带重试的价格数据获取"""
        retry_count = self.progress_manager.get_retry_count(stock_code)
        
        for attempt in range(retry_count, self.config.MAX_RETRIES):
            try:
                # 格式化日期
                start_str = self.config.START_DATE.replace('-', '')
                end_str = self.config.END_DATE.replace('-', '')
                
                # 获取历史数据
                df = ak.stock_zh_a_hist(symbol=stock_code, 
                                       start_date=start_str,
                                       end_date=end_str)
                
                if df.empty:
                    raise ValueError("返回数据为空")
                
                # 数据预处理
                df['日期'] = pd.to_datetime(df['日期'])
                df.set_index('日期', inplace=True)
                df.sort_index(inplace=True)
                
                # 标准化列名
                df = df.rename(columns={
                    '开盘': 'open', '最高': 'high', '最低': 'low',
                    '收盘': 'close', '成交量': 'volume', '成交额': 'amount'
                })
                
                # 数据质量检查
                if len(df) < 100:  # 至少要有100个交易日的数据
                    raise ValueError(f"数据量不足，只有{len(df)}条记录")
                
                if df['close'].isna().sum() > len(df) * 0.1:  # 缺失数据不能超过10%
                    raise ValueError("数据缺失过多")
                
                return df[['open', 'high', 'low', 'close', 'volume']]
                
            except Exception as e:
                error_msg = str(e)
                print(f"    ❌ 尝试{attempt+1}/{self.config.MAX_RETRIES}: {error_msg}")
                
                # 记录失败
                self.progress_manager.mark_failed(stock_code, error_msg)
                
                if attempt < self.config.MAX_RETRIES - 1:
                    print(f"    ⏳ {self.config.RETRY_DELAY}秒后重试...")
                    time.sleep(self.config.RETRY_DELAY)
                else:
                    print(f"    💀 {stock_code} {stock_name} 最终失败")
                    self.progress_manager.save_failed_stocks()
                    return pd.DataFrame()
        
        return pd.DataFrame()
    
    def fetch_price_data(self, stock_list):
        """批量获取价格数据"""
        print("\n" + "="*60)
        print("步骤2: 获取历史价格数据")
        print("="*60)
        print(f"📅 数据时间范围: {self.config.START_DATE} 至 {self.config.END_DATE}")
        print(f"🔄 容错设置: 每只股票最多重试{self.config.MAX_RETRIES}次")
        print(f"💾 保存频率: 每{self.config.SAVE_INTERVAL}只股票保存一次")
        
        # 加载已有的价格数据
        price_cache_file = os.path.join(self.config.CACHE_DIR, self.config.PRICE_DATA_FILE)
        price_data = {}
        
        if os.path.exists(price_cache_file):
            try:
                with open(price_cache_file, 'rb') as f:
                    price_data = pickle.load(f)
                print(f"✅ 加载现有缓存，包含{len(price_data)}只股票数据")
            except Exception as e:
                print(f"⚠️ 价格缓存文件损坏: {e}")
                price_data = {}
        
        # 初始化进度
        total_stocks = len(stock_list)
        self.progress_manager.progress_data['total_stocks'] = total_stocks
        
        if not self.progress_manager.progress_data.get('start_time'):
            self.progress_manager.progress_data['start_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 确定需要处理的股票
        stocks_to_process = []
        for _, stock in stock_list.iterrows():
            stock_code = stock['code']
            
            # 检查是否已完成且数据存在
            if (self.progress_manager.is_completed(stock_code) and 
                stock_code in price_data and 
                not price_data[stock_code].empty):
                continue
            
            # 检查是否应该重试
            if self.progress_manager.should_retry(stock_code):
                stocks_to_process.append(stock)
        
        if not stocks_to_process:
            print("✅ 所有股票数据已获取完成！")
            return price_data
        
        print(f"📋 待处理股票: {len(stocks_to_process)}只")
        print(f"✅ 已完成股票: {len(self.progress_manager.progress_data['completed_stocks'])}只")
        print(f"❌ 失败股票: {len(self.progress_manager.failed_stocks)}只")
        
        # 显示当前进度
        self.progress_manager.print_status()
        
        # 询问是否继续
        if len(stocks_to_process) > 50:
            estimated_minutes = len(stocks_to_process) * 0.5
            choice = input(f"\n即将获取{len(stocks_to_process)}只股票数据，预计需要{estimated_minutes:.0f}分钟，是否继续？(y/n): ")
            if choice.lower().strip() != 'y':
                print("用户取消操作")
                return price_data
        
        print("\n🚀 开始获取数据...")
        
        # 批量获取数据
        success_count = 0
        start_time = time.time()
        
        for i, stock in enumerate(stocks_to_process):
            stock_code = stock['code']
            stock_name = stock['name']
            
            print(f"\n[{i+1}/{len(stocks_to_process)}] {stock_code} {stock_name}")
            
            # 获取数据
            df = self.get_stock_price_with_retry(stock_code, stock_name)
            
            if not df.empty:
                price_data[stock_code] = df
                self.progress_manager.mark_completed(stock_code)
                success_count += 1
                print(f"    ✅ 成功获取{len(df)}条记录 ({df.index[0].strftime('%Y-%m-%d')} 至 {df.index[-1].strftime('%Y-%m-%d')})")
            else:
                print(f"    ❌ 获取失败")
            
            # 定期保存进度
            if (i + 1) % self.config.SAVE_INTERVAL == 0:
                with open(price_cache_file, 'wb') as f:
                    pickle.dump(price_data, f)
                self.progress_manager.save_progress()
                
                # 计算平均速度和剩余时间
                elapsed = time.time() - start_time
                avg_time = elapsed / (i + 1)
                remaining_time = (len(stocks_to_process) - i - 1) * avg_time
                
                print(f"    💾 已保存进度 ({len(price_data)}只股票)")
                print(f"    ⏱️  预计剩余时间: {remaining_time/60:.1f}分钟")
                self.progress_manager.print_status()
            
            # 请求延时
            time.sleep(self.config.REQUEST_DELAY)
        
        # 最终保存
        with open(price_cache_file, 'wb') as f:
            pickle.dump(price_data, f)
        self.progress_manager.save_progress()
        
        print(f"\n{'='*60}")
        print("📊 数据获取完成统计")
        print(f"{'='*60}")
        print(f"✅ 成功获取: {success_count}只股票")
        print(f"❌ 失败股票: {len(self.progress_manager.failed_stocks)}只")
        print(f"💾 总缓存数据: {len(price_data)}只股票")
        print(f"⏱️  总耗时: {(time.time() - start_time)/60:.1f}分钟")
        
        # 显示失败股票
        if self.progress_manager.failed_stocks:
            print(f"\n⚠️ 失败股票列表:")
            for code, info in list(self.progress_manager.failed_stocks.items())[:10]:
                print(f"  {code}: {info['error'][:50]}... (重试{info['retry_count']}次)")
            
            if len(self.progress_manager.failed_stocks) > 10:
                print(f"  ... 还有{len(self.progress_manager.failed_stocks)-10}只股票失败")
        
        return price_data

# =============================================================================
# 主要功能函数
# =============================================================================

def setup_data():
    """数据准备主函数 - 支持断点续传"""
    print("🚀 A股数据获取系统启动")
    print("="*60)
    print(f"📅 时间范围: {config.START_DATE} 至 {config.END_DATE}")
    print(f"🎯 目标范围: 沪深主板A股 (000/002/600/601/603)")
    print(f"🛡️ 容错机制: 每股最多重试{config.MAX_RETRIES}次，每{config.SAVE_INTERVAL}只保存一次")
    print(f"📁 缓存位置: {config.CACHE_DIR}")
    print("="*60)
    
    try:
        # 创建数据获取器
        fetcher = RobustDataFetcher(config)
        
        # 步骤1: 获取股票池
        stock_list = fetcher.get_main_board_stocks()
        
        if stock_list.empty:
            print("❌ 股票池获取失败，程序终止")
            return False
        
        # 步骤2: 获取价格数据
        price_data = fetcher.fetch_price_data(stock_list)
        
        if len(price_data) == 0:
            print("❌ 价格数据获取失败，程序终止")
            return False
        
        print(f"\n🎉 数据准备完成!")
        print(f"📊 股票池: {len(stock_list)}只")
        print(f"💾 价格数据: {len(price_data)}只")
        print(f"📁 缓存位置: {config.CACHE_DIR}")
        print("\n✅ 现在可以使用这些数据进行量化回测了！")
        
        return True
        
    except KeyboardInterrupt:
        print(f"\n⚠️ 用户中断操作")
        print(f"💾 进度已保存，下次运行将从中断处继续")
        return False
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        return False

def check_data_status():
    """检查数据状态"""
    print("📊 数据状态检查")
    print("="*40)
    
    # 检查股票池
    stock_pool_file = os.path.join(config.CACHE_DIR, config.STOCK_POOL_FILE)
    if os.path.exists(stock_pool_file):
        try:
            with open(stock_pool_file, 'rb') as f:
                stock_pool = pickle.load(f)
            print(f"✅ 股票池: {len(stock_pool)}只股票")
        except:
            print("❌ 股票池文件损坏")
    else:
        print("❌ 股票池文件不存在")
    
    # 检查价格数据
    price_data_file = os.path.join(config.CACHE_DIR, config.PRICE_DATA_FILE)
    if os.path.exists(price_data_file):
        try:
            with open(price_data_file, 'rb') as f:
                price_data = pickle.load(f)
            print(f"✅ 价格数据: {len(price_data)}只股票")
            
            # 检查数据质量
            valid_count = sum(1 for df in price_data.values() if not df.empty and len(df) > 100)
            print(f"✅ 有效数据: {valid_count}只股票")
            
        except:
            print("❌ 价格数据文件损坏")
    else:
        print("❌ 价格数据文件不存在")
    
    # 检查进度
    progress_manager = ProgressManager(config)
    progress_manager.print_status()

if __name__ == "__main__":
    print("🎯 A股数据获取系统")
    print("="*30)
    print("运行方式:")
    print("1. 直接运行: python setup_data.py")
    print("2. 导入使用: from setup_data import setup_data")
    print("="*30)
    
    # 如果直接运行文件，则执行数据获取
    setup_data()