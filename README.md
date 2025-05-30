# A股量化回测系统 📈

一个专业的A股量化投资回测框架，采用模块化设计，支持多种选股策略的开发、回测和分析。

## 🎯 项目简介

本项目是一个完整的量化投资回测系统，主要功能包括：

- **模块化架构**：清晰的代码结构，便于维护和扩展
- **多策略支持**：内置动量、价值、成长等经典策略
- **专业回测引擎**：考虑交易成本、滑点等真实交易因素
- **全面分析工具**：丰富的绩效指标和可视化图表
- **策略开发框架**：简单易用的策略开发接口

## 🛠️ 环境安装

### 方法一：一键安装（推荐）

```bash
# 克隆项目
git clone <项目地址>
cd quant_learning

# 使用environment.yml一键创建环境
conda env create -f environment.yml

# 激活环境
conda activate quant
```

### 方法二：手动安装

#### 1. 安装Anaconda/Miniconda

##### Windows系统：
1. 下载[Anaconda](https://www.anaconda.com/products/distribution)或[Miniconda](https://docs.conda.io/en/latest/miniconda.html)
2. 运行安装程序，按提示完成安装
3. 打开"Anaconda Prompt"

##### macOS系统：
```bash
# 使用Homebrew安装
brew install --cask anaconda

# 或者下载pkg文件安装
# https://www.anaconda.com/products/distribution
```

##### Linux系统：
```bash
# 下载安装脚本
wget https://repo.anaconda.com/archive/Anaconda3-2023.09-Linux-x86_64.sh

# 运行安装
bash Anaconda3-2023.09-Linux-x86_64.sh

# 重新加载bashrc
source ~/.bashrc
```

#### 2. 创建虚拟环境

```bash
# 创建Python环境
conda create -n quant python=3.9

# 激活环境
conda activate quant
```

#### 3. 安装依赖包

```bash
# 方法1：使用conda安装主要包
conda install pandas numpy matplotlib seaborn scikit-learn

# 方法2：使用pip安装requirements.txt
pip install -r requirements.txt
```

## 📁 项目结构

```
quant_learning/
├── README.md              # 项目说明文档
├── requirements.txt       # Python依赖清单
├── environment.yml        # Conda环境配置
├── config.py              # 系统配置文件
├── data_manager.py        # 数据管理模块
├── technical_analyzer.py  # 技术分析模块
├── strategy_base.py       # 策略基类
├── backtest_engine.py     # 回测引擎
├── result_analyzer.py     # 结果分析模块
├── main.py               # 主程序入口
├── setup_data.py         # 数据获取脚本
├── strategies/           # 策略目录
│   ├── __init__.py
│   ├── momentum_strategy.py  # 动量策略
│   ├── value_strategy.py     # 价值策略
│   └── growth_strategy.py    # 成长策略
└── data_cache/           # 数据缓存目录
    ├── stock_pool.pkl
    └── price_data.pkl
```

## 🚀 快速开始

### 1. 获取数据

```bash
# 首次运行需要获取股票数据
python setup_data.py
```

### 2. 运行回测

```bash
# 启动主程序
python main.py
```

系统会提供以下选项：
1. 单策略回测 - 动量策略
2. 单策略回测 - 价值策略
3. 单策略回测 - 成长策略
4. 多策略对比
5. 自定义策略示例
6. 全部运行

## 📊 内置策略详解

### 1. 动量策略 (MomentumStrategy) 🚀

**投资理念**：追踪市场趋势，选择具有强劲上升动量的股票

**核心逻辑**：
- 均线多头排列（5日>10日>20日>60日）
- 价格突破20日均线
- MACD金叉且柱状线为正
- RSI在20-75区间（避免超买超卖）
- 成交量放大配合

**适用市场**：牛市、震荡向上行情

### 2. 价值策略 (ValueStrategy) 💎

**投资理念**：寻找被市场低估的优质股票

**核心逻辑**：
- 价格处于相对低位（10%-60%分位）
- RSI不超过70（避免追高）
- 布林带位置较低（10%-50%）
- 波动率相对较低（稳健性）
- 价格仍高于60日均线（基本趋势）

**适用市场**：熊市末期、价值回归阶段

### 3. 成长策略 (GrowthStrategy) 🌱

**投资理念**：捕捉具有强劲成长动量的股票

**核心逻辑**：
- 中期动量≥5%，长期动量≥10%
- RSI在45-80强势区间
- 成交量显著放大（≥1.2倍）
- 价格处于相对高位（突破特征）
- 多因子加权评分

**适用市场**：成长股行情、科技股牛市

## ⚙️ 系统配置

编辑 `config.py` 来调整系统参数：

```python
# 回测配置
INITIAL_CAPITAL = 1000000    # 初始资金
MAX_POSITIONS = 6           # 最大持仓数
START_DATE = '2021-01-01'   # 回测开始日期
END_DATE = '2024-01-01'     # 回测结束日期
REBALANCE_FREQ = 'Q'        # 调仓频率（M/Q/Y）

# 交易成本
COMMISSION_RATE = 0.0003    # 佣金费率
STAMP_TAX = 0.001          # 印花税
MIN_COMMISSION = 5         # 最低佣金

# 选股条件
MIN_MARKET_CAP = 50        # 最小市值（亿元）
MIN_DATA_DAYS = 100        # 最少数据天数
```

## 🔧 自定义策略开发

继承 `BaseStrategy` 类创建自己的策略：

```python
from strategy_base import BaseStrategy

class MyStrategy(BaseStrategy):
    def __init__(self, **kwargs):
        super().__init__("我的策略", **kwargs)
    
    def is_qualified_stock(self, indicators, stock_info=None):
        """定义选股条件"""
        return (
            indicators['rsi'] > 30 and 
            indicators['rsi'] < 70 and
            indicators['momentum_5d'] > 0
        )
    
    def calculate_score(self, indicators, stock_info=None):
        """定义评分逻辑"""
        return (
            indicators['momentum_5d'] * 50 +
            indicators['rsi'] * 0.5 +
            indicators['volume_ratio'] * 10
        )
```

## 📈 分析功能

系统提供丰富的分析功能：

### 绩效指标
- 总收益率 & 年化收益率
- 最大回撤 & 夏普比率
- 胜率 & 波动率
- 信息比率 & 最大连续亏损期

### 可视化图表
- 投资组合净值走势
- 累计收益率曲线
- 回撤分析图
- 收益率分布直方图
- 持仓数量变化
- 现金占比趋势

### 策略评级
基于收益率、风险控制、夏普比率、胜率等维度的综合评分（0-100分）

## 📋 使用示例

```python
# 1. 单策略回测
from strategies import MomentumStrategy
from backtest_engine import BacktestEngine
from result_analyzer import ResultAnalyzer

# 创建策略
strategy = MomentumStrategy()

# 运行回测
engine = BacktestEngine(strategy)
results = engine.run_backtest()

# 分析结果
analyzer = ResultAnalyzer(results)
analyzer.print_summary()
analyzer.plot_results()

# 2. 多策略对比
strategies = [MomentumStrategy(), ValueStrategy(), GrowthStrategy()]
# ... 对比逻辑
```

## 🔍 注意事项

1. **数据依赖**：首次使用需运行 `setup_data.py` 获取股票数据
2. **计算性能**：大量股票回测可能耗时较长，建议先用小样本测试
3. **参数调优**：不同市场环境下策略参数需要适当调整
4. **风险控制**：回测结果不代表未来表现，投资需谨慎

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进项目：

1. Fork本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 📞 联系方式

如有问题或建议，欢迎通过以下方式联系：

- 提交Issue：[GitHub Issues](项目地址/issues)
- 邮箱：your.email@example.com

---

⭐ 如果这个项目对你有帮助，请给个Star支持一下！