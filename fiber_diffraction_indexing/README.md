# 纤维衍射指标化软件 / Fiber Diffraction Indexing

## 概述 / Overview

POLYCRYSTINDEX 是一款通过遗传算法（Genetic Algorithm, GA）优化实现纤维衍射图自动化指标化的软件包。

POLYCRYSTINDEX is a software package for automated indexing of fiber diffraction patterns using genetic algorithm optimization.

### 主要功能 / Main Features

- **遗传算法优化 (GA Optimization)**：通过全局优化算法寻找最优晶胞参数
- **跨平台支持 (Cross-Platform)**：支持 Windows、Linux 和 macOS
- **HDF5 数据存储 (HDF5 Storage)**：可选将所有数据集成到 HDF5 文件
- **GUI 回调接口 (GUI Callback)**：支持 GUI 集成，实时反馈进度
- **模块化架构 (Modular Architecture)**：清晰的关注点分离，易于扩展

## 安装 / Installation

```bash
# 安装依赖 / Install dependencies
pip install h5py numpy matplotlib

# 安装包 / Install package
pip install -e .
```

## 快速开始 / Quick Start

```python
# 命令行 / Command Line
python -m fiberdiffraction -i input.txt -d diffraction.txt

# 显示版本 / Show version
python -m fiberdiffraction -v
```

## 项目结构 / Project Structure

```
fiber_diffraction_indexing/
├── fiberdiffraction/          # 主包 / Main package
│   ├── __init__.py           # 包导出 / Package exports
│   ├── __main__.py           # 模块入口 / Module entry point
│   ├── cli.py                # 命令行入口 / CLI entry point
│   ├── indexer.py            # 主协调器 / Main orchestrator
│   ├── config.py             # 输入配置 / Input configuration
│   ├── population.py         # 种群管理 / Population management
│   ├── genetic.py            # 遗传算法 / Genetic algorithm
│   ├── fortran.py            # 外部程序调用 / External program caller
│   ├── fileio.py             # 文件操作 / File operations
│   ├── callbacks.py          # 回调接口 / Callback interface
│   ├── hdf5.py               # HDF5 管理 / HDF5 management
│   ├── plotter.py            # 绘图模块 / Plotting
│   └── version.py            # 版本信息 / Version info
│
├── scripts/                  # 原始脚本 / Original scripts
│   ├── initial.py           # 初始化脚本 / Initialization script
│   ├── sort.py              # 排序脚本 / Sorting script
│   └── diffraction_fiber.py # 衍射计算 / Diffraction calculation
│
├── tests/                    # 测试 / Tests
├── docs/                     # 文档 / Documentation
│   ├── user_guide.md        # 用户指南 / User guide
│   └── api_reference.md     # API 参考 / API reference
│
└── config/                   # 配置模板 / Configuration templates
    └── input_template.txt    # 输入模板 / Input template
```

## 核心参数说明 / Core Parameters

| 参数 / Parameter | 行号 / Line | 说明 / Description |
|-----------------|-------------|-------------------|
| `population_size` | 5 | 种群大小，每代包含的晶胞个体数量 |
| `survival_rate` | 6 | 存活率，遗传算法中选择保留的比例 [0-1] |
| `crossover_rate` | 7 | 交叉率，交叉操作产生的个体比例 [0-1] |
| `mutation_rate` | 8 | 变异率，变异操作产生的个体比例 [0-1] |
| `c_axis` | 11 | C轴参数，0=可变，其他=固定值 |
| `layer_mode` | 13 | 层模式，是否启用层状结构处理 |
| `parameter_min` | 25 | 参数最小值 [a, b, c, α, β, γ] |
| `parameter_max` | 26 | 参数最大值 |
| `tilt_status` | 27 | 倾斜状态，是否优化纤维倾斜角 |
| `omp_threads` | 28 | OpenMP线程数，并行计算线程数 |

## 使用方法 / Usage

### 命令行接口 / CLI

```bash
# 基本用法 / Basic usage
python -m fiberdiffraction -i input.txt -d diffraction.txt

# 显示配置 / Show configuration
python -m fiberdiffraction -i input.txt -d diffraction.txt -s

# HDF5 模式 / HDF5 mode
python -m fiberdiffraction -i input.txt -d diffraction.txt --hdf5
```

### Python API

```python
from fiberdiffraction import FiberDiffractionIndexer

# 基本流程 / Basic workflow
indexer = FiberDiffractionIndexer("input.txt", "diffraction.txt")
indexer.run()

# HDF5 模式 / HDF5 mode
indexer = FiberDiffractionIndexer(
    "input.txt", "diffraction.txt",
    use_hdf5=True,
    hdf5_file="results.h5"
)
indexer.run()
```

### GUI 回调 / GUI Callback

```python
from fiberdiffraction import IndexingCallback, FiberDiffractionIndexer

class MyGUI(IndexingCallback):
    """自定义 GUI 回调类 / Custom GUI callback class"""
    
    def on_step_start(self, step, total):
        print(f"开始步骤 {step + 1}/{total}")
        self.update_progress_bar(step / total)
    
    def on_step_end(self, step, total, elapsed):
        print(f"步骤 {step + 1} 完成，耗时 {elapsed:.2f}秒")
    
    def on_progress(self, step, message):
        self.append_log(f"[步骤 {step + 1}] {message}")
    
    def on_error(self, step, error):
        self.show_error(str(error))
    
    def on_complete(self, total_time, results):
        self.show_results(results)

# 使用回调 / Use callback
indexer = FiberDiffractionIndexer(
    "input.txt", "diffraction.txt",
    callback=MyGUI()
)
indexer.run()
```

## HDF5 数据结构 / HDF5 Data Structure

```
results.h5
├── config/                  # 配置参数 / Configuration
├── populations/             # 各代种群 / Population per step
│   └── step_N               # 第 N 代种群
├── convergence/              # 收敛数据 / Convergence data
│   ├── best_errors          # 最佳误差 / Best error per step
│   └── best_cells           # 最佳晶胞 / Best cell per step
├── timing/                  # 时间记录 / Timing records
│   ├── step_times           # 各步耗时 / Time per step
│   └── total_time           # 总耗时 / Total time
└── metadata/                # 元数据 / Metadata
```

## 绘图 / Plotting

```python
from fiberdiffraction import HDF5Manager, Plotter

hdf5 = HDF5Manager("results.h5", mode='r')
plotter = Plotter(hdf5)

# 时间曲线 / Timing curve
plotter.plot_timing(save_path="figures/timing.png")

# 收敛曲线 / Convergence curve
plotter.plot_convergence(save_path="figures/convergence.png")

# 参数演化 / Parameter evolution
plotter.plot_parameters(save_path="figures/parameters.png")

hdf5.close()
```

## 输入文件格式 / Input File Format

```
# 第 1-3 行：波长等注释信息 / Wavelength and comments
1.5418
0
flat

# 第 4 行：population_size - 种群大小（每代个体数量）
2000

# 第 5 行：generation_steps - 进化代数（迭代次数）
30

# 第 6 行：survival_rate - 存活率 [0-1]
0.1

# 第 7 行：crossover_rate - 交叉率 [0-1]
0.2

# 第 8 行：mutation_rate - 变异率 [0-1]
0.5

# 第 11 行：c_axis - C轴参数（0=可变）
0

# 第 13 行：layer_mode - 层模式（非零=启用）
1

# 第 25 行：parameter_min - 参数最小值 [a, b, c, α, β, γ]
3.0 3.0 15.0 90.0 90.0 90.0

# 第 26 行：parameter_max - 参数最大值
10.0 10.0 20.0 90.0 90.0 90.0

# 第 27 行：tilt_status - 倾斜状态（1=启用）
0

# 第 28 行：omp_threads - OpenMP线程数（0=系统默认）
0
```

## 引用 / Citation

如果使用本软件，请引用 / If you use this software, please cite:

```
Ma, T., Hu, W., Wang, D. & Liu, G. (2025). A global optimization approach 
to automated indexing of fiber diffraction patterns. J. Appl. Cryst. 58.
```

## 许可证 / License

MIT License

## 贡献 / Contributing

欢迎贡献！请在提交拉取请求前阅读贡献指南。

Contributions are welcome! Please read the contributing guidelines before submitting pull requests.
