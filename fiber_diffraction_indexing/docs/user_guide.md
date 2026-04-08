# 用户指南 / User Guide

## 简介 / Introduction

POLYCRYSTINDEX 是一款通过遗传算法（Genetic Algorithm, GA）优化实现纤维衍射图自动化指标化的软件包。

POLYCRYSTINDEX is a software package for automated indexing of fiber diffraction patterns using genetic algorithm optimization.

本指南将帮助您快速上手。

This guide will help you get started quickly.

## 安装 / Installation

### 系统要求 / System Requirements

- Python 3.8 或更高版本 / Python 3.8 or higher
- NumPy
- SciPy
- h5py (用于 HDF5 支持 / for HDF5 support)
- matplotlib (用于绘图 / for plotting)

### 安装步骤 / Installation Steps

```bash
# 1. 克隆仓库 / Clone repository
git clone <repository-url>
cd fiber-diffraction-indexing

# 2. 安装依赖 / Install dependencies
pip install h5py numpy matplotlib

# 3. 安装包 / Install package
pip install -e .
```

## 基本用法 / Basic Usage

### 命令行接口 / Command Line Interface

```bash
# 基本用法 / Basic usage
python -m fiberdiffraction -i input.txt -d diffraction.txt

# 显示版本 / Show version
python -m fiberdiffraction -v

# 显示配置 / Show configuration
python -m fiberdiffraction -i input.txt -d diffraction.txt -s
```

### Python API

```python
from fiberdiffraction import FiberDiffractionIndexer

# 创建索引器 / Create indexer
indexer = FiberDiffractionIndexer("input.txt", "diffraction.txt")

# 运行 / Run
indexer.run()
```

## 输入文件格式 / Input File Format

输入文件应遵循以下格式（行号与 Fortran 程序严格对应）：

Input file should follow this format (line numbers correspond to Fortran):

```
# 第 1-3 行：波长等信息 / Wavelength and other info
1.5418              # X射线波长 (Angstrom)
0                   # 备用参数
flat                # 备用参数

# 第 4 行：population_size - 种群大小
2000                # 每代包含的晶胞个体数量

# 第 5 行：generation_steps - 进化代数
30                  # 迭代优化次数

# 第 6 行：survival_rate - 存活率
0.1                 # 遗传算法中选择保留的比例 [0-1]

# 第 7 行：crossover_rate - 交叉率
0.2                 # 交叉操作产生的个体比例 [0-1]

# 第 8 行：mutation_rate - 变异率
0.5                 # 变异操作产生的个体比例 [0-1]

# 第 11 行：c_axis - C轴参数
0                   # 0=可变，其他=固定值

# 第 13 行：layer_mode - 层模式
1                   # 非零=启用层状结构处理

# 第 25 行：parameter_min - 参数最小值
5.0 5.0 5.0 30 30 30  # [a, b, c, alpha, beta, gamma] 最小值

# 第 26 行：parameter_max - 参数最大值
15.0 15.0 15.0 150 150 150  # [a, b, c, alpha, beta, gamma] 最大值

# 第 27 行：tilt_status - 倾斜状态
0                   # 1=启用纤维倾斜角优化，0=禁用

# 第 28 行：omp_threads - OpenMP线程数
0                   # 并行计算线程数，0=系统默认
```

### 参数详细说明 / Parameter Details

| 参数 | 说明 |
|------|------|
| **population_size** | 种群大小，遗传算法中每代的个体数量。越大搜索越全面，但计算越慢 |
| **survival_rate** | 存活率，每代中保留到下一代的最佳个体比例。如 0.1 表示保留 10% |
| **crossover_rate** | 交叉率，通过组合两个父代个体产生新个体的比例 |
| **mutation_rate** | 变异率，通过随机改变参数产生新个体的比例 |
| **c_axis** | C轴参数，晶胞的 c 轴长度（埃）。设为 0 表示由算法优化 |
| **layer_mode** | 层模式，1 表示处理层状结构，0 表示普通纤维 |
| **tilt_status** | 倾斜状态，1 表示优化纤维倾斜角，0 表示不考虑倾斜 |
| **omp_threads** | OpenMP 线程数，用于 Fortran 并行计算。0 表示由系统决定 |

## 衍射文件格式 / Diffraction File Format

衍射文件应每行包含一个或多个数值（用空格分隔）：

Diffraction file should contain one or more values per line (space-separated):

```
# 格式：q_value [intensity] [flag]
# q_value: 散射矢量大小 (Å⁻¹)
# intensity: 相对强度（可选）
# flag: 标志位（可选）

1.517936588  0.070902605  1
1.560187996  14.47948188  0.4
1.683363696  0.063412146   1
...
```

## 高级用法 / Advanced Usage

### HDF5 模式 / HDF5 Mode

HDF5 模式将所有数据集成到一个 HDF5 文件中，方便后续分析和可视化。

HDF5 mode integrates all data into a single HDF5 file for easier analysis and visualization.

```python
from fiberdiffraction import FiberDiffractionIndexer

# 启用 HDF5 模式 / Enable HDF5 mode
indexer = FiberDiffractionIndexer(
    "input.txt", "diffraction.txt",
    use_hdf5=True,
    hdf5_file="results.h5"  # 可选，默认 results.h5
)
indexer.run()

# 运行完成后自动删除 TXT 文件
# TXT files are automatically deleted after completion
```

### GUI 回调接口 / GUI Callback Interface

通过继承 `IndexingCallback` 类实现 GUI 进度反馈：

Implement GUI progress feedback by extending `IndexingCallback`:

```python
from fiberdiffraction import IndexingCallback, FiberDiffractionIndexer

class MyGUI(IndexingCallback):
    """自定义 GUI 回调类 / Custom GUI callback class"""
    
    def __init__(self):
        self.progress_bar = None
        self.log_text = None
    
    def on_step_start(self, step: int, total: int) -> None:
        """步骤开始时调用 / Called when step starts"""
        print(f"开始优化步骤 {step + 1}/{total}")
        # self.progress_bar.setRange(0, total)
        # self.progress_bar.setValue(step)
    
    def on_step_end(self, step: int, total: int, elapsed: float) -> None:
        """步骤结束时调用 / Called when step ends"""
        print(f"步骤 {step + 1} 完成，耗时 {elapsed:.2f}秒")
        # self.progress_bar.setValue(step + 1)
    
    def on_progress(self, step: int, message: str) -> None:
        """进度更新时调用 / Called on progress update"""
        # self.log_text.append(f"[步骤 {step + 1}] {message}")
        pass
    
    def on_error(self, step: int, error: Exception) -> None:
        """发生错误时调用 / Called on error"""
        # self.show_error_dialog(str(error))
        pass
    
    def on_complete(self, total_time: float, results: dict) -> None:
        """全部完成时调用 / Called on completion"""
        # self.show_results_dialog(results)
        pass

# 使用回调 / Use callback
gui = MyGUI()
indexer = FiberDiffractionIndexer(
    "input.txt", "diffraction.txt",
    callback=gui
)
indexer.run()
```

### 函数式回调 / Function Callback

也可以使用函数作为回调：

You can also use functions as callbacks:

```python
from fiberdiffraction import CallbackAdapter, FiberDiffractionIndexer

adapter = CallbackAdapter(
    on_step_start=lambda s, t: print(f"开始 {s + 1}/{t}"),
    on_step_end=lambda s, t, e: print(f"完成 {s + 1}/{t}，耗时 {e:.2f}秒"),
    on_progress=lambda s, m: print(f"[{s + 1}] {m}"),
    on_complete=lambda t, r: print(f"全部完成，耗时 {t:.2f}秒")
)

indexer = FiberDiffractionIndexer(
    "input.txt", "diffraction.txt",
    callback=adapter
)
indexer.run()
```

## 绘图功能 / Plotting

### 绘图类使用 / Using Plotter

```python
from fiberdiffraction import HDF5Manager, Plotter

# 打开 HDF5 文件 / Open HDF5 file
hdf5 = HDF5Manager("results.h5", mode='r')

# 创建绘图器 / Create plotter
plotter = Plotter(hdf5)

# 时间曲线 - 显示每步耗时 / Timing curve
fig = plotter.plot_timing(
    save_path="figures/timing.png",  # 保存路径（可选）
    show=True                         # 显示图表
)

# 收敛曲线 - 显示 GA 收敛过程 / Convergence curve
fig = plotter.plot_convergence(
    save_path="figures/convergence.png",
    show=True
)

# 参数演化 - 显示最佳参数变化 / Parameter evolution
fig = plotter.plot_parameters(
    save_path="figures/parameters.png",
    show=True
)

# 关闭 HDF5 / Close HDF5
hdf5.close()

# 保存所有图表 / Save all plots
hdf5 = HDF5Manager("results.h5", mode='r')
plotter = Plotter(hdf5)
plotter.save_all("figures/")  # 保存到目录
hdf5.close()
```

### HDF5 数据读取 / Reading HDF5 Data

```python
from fiberdiffraction import HDF5Manager

hdf5 = HDF5Manager("results.h5", mode='r')

# 读取配置 / Read configuration
config = hdf5.read_config()
print(config)

# 读取收敛数据 / Read convergence data
convergence = hdf5.read_convergence()
print(convergence['best_errors'])  # 各步最佳误差
print(convergence['best_cells'])    # 各步最佳晶胞

# 读取种群 / Read population
pop_step_0 = hdf5.read_population(0)

# 读取时间 / Read timing
timing = hdf5.read_timing()
print(timing['step_times'])   # 各步耗时
print(timing['total_time'])    # 总耗时

hdf5.close()
```

## 输出文件 / Output Files

### TXT 模式（默认）

```
result/                    # 结果目录
├── cell_0.txt           # 初始种群
├── cell_1.txt           # 第 1 代种群
├── cell_1_annealing.txt # 第 1 代退火结果
├── cell_2.txt           # 第 2 代种群
└── ...
```

### HDF5 模式

```
results.h5               # 单一 HDF5 文件包含所有数据
```

## 配置选项详解 / Configuration Options

### 种群参数 / Population Parameters

| 参数 | 建议值 | 说明 |
|------|--------|------|
| population_size | 500-5000 | 根据计算资源调整，越大越耗时 |
| generation_steps | 20-100 | 迭代次数，越多越可能找到最优解 |
| survival_rate | 0.1-0.3 | 存活比例，太高会降低搜索多样性 |
| crossover_rate | 0.2-0.4 | 交叉比例 |
| mutation_rate | 0.3-0.5 | 变异比例，太低会陷入局部最优 |

### 参数边界 / Parameter Bounds

| 参数 | 说明 | 典型范围 |
|------|------|----------|
| a, b, c | 晶胞轴长 (Å) | 3-30 |
| alpha, beta, gamma | 晶胞角度 (°) | 60-120 |

## 故障排除 / Troubleshooting

### 常见问题 / Common Issues

1. **File Not Found Error**
   - 确保输入和衍射文件存在 / Ensure input and diffraction files exist
   - 检查文件路径是否正确 / Check file paths are correct

2. **Invalid Input Format**
   - 验证输入文件具有正确的行数 / Verify input file has correct number of lines
   - 检查参数值是否在边界内 / Check parameter values are within bounds

3. **Memory Issues**
   - 减小 population_size / Reduce population_size
   - 减少 generation_steps / Reduce generation_steps

### 获取帮助 / Getting Help

- 查看 README.md 文件
- 查看 config/ 目录中的示例输入文件
- 在 GitHub 上提交问题

## 引用 / Citation

如果使用本软件，请引用：

If you use this software, please cite:

```
Ma, T., Hu, W., Wang, D. & Liu, G. (2025). A global optimization approach 
to automated indexing of fiber diffraction patterns. J. Appl. Cryst. 58.
```
