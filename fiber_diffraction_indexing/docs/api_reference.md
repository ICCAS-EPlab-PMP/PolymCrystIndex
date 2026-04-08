# API 参考文档 / API Reference

完整运行指南和 Python API 教程。

## 目录

1. [快速开始 / Quick Start](#1-快速开始)
2. [命令行接口 / CLI](#2-命令行接口)
3. [Python API 教程](#3-python-api-教程)
4. [完整示例 / Complete Examples](#4-完整示例)
5. [故障排除 / Troubleshooting](#5-故障排除)

---

## 1. 快速开始 / Quick Start

### 1.1 环境准备

**系统要求 / System Requirements:**
- Python 3.8+
- 操作系统：Windows / Linux / macOS
- Fortran 可执行文件（已编译）

**依赖包 / Dependencies:**
```
numpy>=1.21.0
scipy>=1.7.0
h5py>=3.7.0      # HDF5 支持
matplotlib>=3.5.0 # 绘图
```

### 1.2 安装步骤

```bash
# 步骤 1: 进入项目目录
cd fiber_diffraction_indexing

# 步骤 2: 安装依赖
pip install -e .

# 步骤 3: 验证安装
python -c "from fiberdiffraction import FiberDiffractionIndexer; print('安装成功！')"
```

### 1.3 准备文件

**输入文件 (input.txt):**
```
1.5418              # X射线波长 (Angstrom) / X-ray wavelength
0                   # 备用参数 / Reserved
flat                # 备用参数 / Reserved
2000                # 种群大小 / Population size (每代个体数量)
30                  # 进化代数 / Generation steps
0.1                 # 存活率 / Survival rate [0-1]
0.2                 # 交叉率 / Crossover rate [0-1]
0.5                 # 变异率 / Mutation rate [0-1]
0                   # 备用参数 / Reserved
2                   # 备用参数 / Reserved
0                   # C轴参数 / C-axis (0=可变, 其他=固定值)
22                  # 备用参数 / Reserved
1                   # 层模式 / Layer mode (非零=启用)
1                   # 备用参数 / Reserved
1.0                 # 备用参数 / Reserved
100.0               # 备用参数 / Reserved
1000.0              # 备用参数 / Reserved
0                   # 备用参数 / Reserved
0                   # 备用参数 / Reserved
0                   # 备用参数 / Reserved
0                   # 备用参数 / Reserved
0                   # 备用参数 / Reserved
1                   # 备用参数 / Reserved
0.95                # 备用参数 / Reserved
3.0 3.0 15.0 90.0 90.0 90.0  # 参数最小值 / Parameter min [a,b,c,α,β,γ]
10.0 10.0 20.0 90.0 90.0 90.0 # 参数最大值 / Parameter max
0                   # 倾斜状态 / Tilt status (1=启用)
0                   # OpenMP线程数 / OMP threads (0=系统默认)
```

**衍射文件 (diffraction.txt):**
```
# 格式：q_value  intensity  flag
# q_value: 散射矢量大小 (Å⁻¹) / Scattering vector magnitude
# intensity: 相对强度 / Relative intensity
# flag: 标志位 / Flag

1.5179  0.071  1
1.5602  14.48  0.4
1.6834  0.063  1
...
```

### 1.4 最小运行示例

```bash
# 命令行方式 / Command line
python -m fiberdiffraction -i input.txt -d diffraction.txt

# Python 方式 / Python API
from fiberdiffraction import FiberDiffractionIndexer

indexer = FiberDiffractionIndexer("input.txt", "diffraction.txt")
indexer.run()
```

---

## 2. 命令行接口 / CLI

### 2.1 基本用法

```bash
python -m fiberdiffraction [选项]
```

### 2.2 参数说明

| 参数 | 简写 | 说明 | 必需 |
|------|------|------|------|
| `--input` | `-i` | 输入文件路径 / Input file path | 是 |
| `--diffraction` | `-d` | 衍射数据文件路径 / Diffraction file path | 是 |
| `--version` | `-v` | 显示版本信息 / Show version | 否 |
| `--show-config` | `-s` | 显示配置摘要 / Show config summary | 否 |

### 2.3 示例

```bash
# 基本运行 / Basic run
python -m fiberdiffraction -i input.txt -d diffraction.txt

# 显示版本 / Show version
python -m fiberdiffraction -v

# 显示配置后运行 / Show config then run
python -m fiberdiffraction -i input.txt -d diffraction.txt -s
```

---

## 3. Python API 教程

### 3.1 InputConfig - 输入配置类

读取和解析输入文件参数。

#### 属性 / Properties

| 属性 | 类型 | 说明 |
|------|------|------|
| `population_size` | int | **种群大小** - 每代包含的晶胞个体数量 |
| `generation_steps` | int | **进化代数** - 优化迭代次数 |
| `survival_rate` | float | **存活率** - 遗传算法中选择保留的比例 [0-1] |
| `crossover_rate` | float | **交叉率** - 交叉操作产生的个体比例 [0-1] |
| `mutation_rate` | float | **变异率** - 变异操作产生的个体比例 [0-1] |
| `c_axis` | float | **C轴参数** - 晶胞c轴长度(Å)，0表示可变 |
| `layer_mode` | int | **层模式** - 是否启用层状结构处理 |
| `parameter_min` | List[float] | **参数最小值** - [a, b, c, α, β, γ] |
| `parameter_max` | List[float] | **参数最大值** - [a, b, c, α, β, γ] |
| `tilt_status` | int | **倾斜状态** - 是否优化纤维倾斜角 (1=启用) |
| `omp_threads` | int | **OpenMP线程数** - 并行计算线程数 |

#### 计算属性 / Computed Properties

| 属性 | 说明 |
|------|------|
| `survive_count` | 存活个体数量 = population_size × survival_rate |
| `crossover_count` | 交叉个体数量 = population_size × crossover_rate |
| `mutation_count` | 变异个体数量 = population_size × mutation_rate |
| `random_count` | 随机生成个体数量 |

#### 方法 / Methods

```python
get_all_parameters() -> Dict[str, Any]
    """返回所有参数的字典 / Returns all parameters as dict"""

validate() -> Tuple[bool, str]
    """验证参数有效性 / Validates parameters
    返回: (是否有效, 错误消息) / Returns: (is_valid, error_message)
    """
```

#### 使用示例 / Examples

```python
from fiberdiffraction import InputConfig

# 创建配置实例
config = InputConfig("input.txt")

# 访问属性
print(f"种群大小: {config.population_size}")
print(f"存活率: {config.survival_rate}")
print(f"参数边界: {config.parameter_min} 到 {config.parameter_max}")

# 获取所有参数
params = config.get_all_parameters()
for key, value in params.items():
    print(f"{key}: {value}")

# 验证配置
is_valid, error = config.validate()
if not is_valid:
    print(f"配置错误: {error}")
```

---

### 3.2 FiberDiffractionIndexer - 主协调器

协调整个索引流程的主类。

#### 初始化参数 / Constructor

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `input_file` | str | 必需 | 输入文件路径 / Input file path |
| `diffraction_file` | str | 必需 | 衍射数据文件路径 / Diffraction file path |
| `callback` | IndexingCallback | DefaultCallback() | 回调接口 / Callback interface |
| `use_hdf5` | bool | False | 是否使用 HDF5 模式 / Enable HDF5 mode |
| `hdf5_file` | str | "results.h5" | HDF5 文件路径 / HDF5 file path |

#### 方法 / Methods

```python
run() -> None
    """运行完整的索引流程 / Run complete indexing workflow"""

validate() -> None
    """验证输入配置（失败抛出 ValueError）/ Validate config"""

initialize_population() -> None
    """初始化种群（调用 Fortran 程序）/ Initialize population"""

run_optimization_step(step: int) -> None
    """运行单步优化 / Run single optimization step"""

run_sorting_step(step: int) -> None
    """运行排序生成下一代 / Run sorting for next generation"""

archive_files(step: int) -> None
    """归档文件到 result/ 目录 / Archive files"""

get_config_summary() -> str
    """返回配置摘要字符串 / Returns config summary"""
```

#### 使用示例 / Examples

```python
from fiberdiffraction import FiberDiffractionIndexer

# 基本用法 / Basic usage
indexer = FiberDiffractionIndexer("input.txt", "diffraction.txt")
indexer.run()

# HDF5 模式 / HDF5 mode
indexer = FiberDiffractionIndexer(
    "input.txt", 
    "diffraction.txt",
    use_hdf5=True,
    hdf5_file="my_results.h5"
)
indexer.run()

# 显示配置 / Show config
print(indexer.get_config_summary())
```

---

### 3.3 PopulationManager - 种群管理

管理晶胞参数种群。

#### 方法 / Methods

```python
initialize_random() -> None
    """随机初始化种群 / Initialize with random cells"""

load_from_file(filename: str) -> None
    """从文件加载种群 / Load population from file"""

save_to_file(filename: str) -> None
    """保存种群到文件 / Save population to file"""

sort_by_diffraction(diffraction_file: str) -> None
    """根据衍射数据排序种群 / Sort by diffraction data"""

size() -> int
    """返回种群大小 / Returns population size"""

is_empty() -> bool
    """检查种群是否为空 / Check if empty"""

get_best_cell() -> Optional[List[float]]
    """返回最佳晶胞参数 / Returns best cell"""

get_all_cells() -> List[List[float]]
    """返回所有晶胞参数副本 / Returns all cells copy"""
```

#### 使用示例 / Examples

```python
from fiberdiffraction import PopulationManager, InputConfig

config = InputConfig("input.txt")
pop = PopulationManager(config)

# 随机初始化
pop.initialize_random()
print(f"种群大小: {pop.size()}")

# 保存到文件
pop.save_to_file("cell_0.txt")

# 从文件加载
pop.load_from_file("cell_0.txt")

# 获取最佳晶胞
best = pop.get_best_cell()
print(f"最佳晶胞: {best}")
```

---

### 3.4 GeneticEngine - 遗传算法引擎

执行遗传算法操作。

#### 方法 / Methods

```python
generate_new_generation(cells: List[List[float]]) -> List[List[float]]
    """生成新一代种群
    
    流程:
    1. 选择 - 从当前代选择存活个体
    2. 交叉 - 组合两个父代产生新个体
    3. 变异 - 随机改变某些个体参数
    4. 随机 - 生成新随机个体增加多样性
    
    Args:
        cells: 当前种群（按适应度排序）
    
    Returns:
        新一代晶胞参数
    """
```

#### 使用示例 / Examples

```python
from fiberdiffraction import GeneticEngine, InputConfig, PopulationManager

config = InputConfig("input.txt")
engine = GeneticEngine(config)
pop = PopulationManager(config)

# 初始化
pop.initialize_random()
cells = pop.get_all_cells()

# 生成新一代
new_cells = engine.generate_new_generation(cells)
print(f"新一代大小: {len(new_cells)}")
```

---

### 3.5 FortranCaller - Fortran 调用器

调用 Fortran 可执行文件。

**注意：实际的晶胞优化计算由 Fortran 程序完成！**

#### 方法 / Methods

```python
setup_omp_threads() -> None
    """设置 OpenMP 线程数 / Setup OMP threads"""

run_initialization(input_file: str) -> None
    """运行初始化程序生成 cell_0.txt"""

run_optimization(input_file: str, diffraction_file: str, step: int) -> None
    """运行优化程序 single_polymcrystindex"""

run_sorting(input_file: str, cell_file: str, generation: int) -> None
    """运行排序程序 FiberDiffractionSort"""
```

#### 注意事项 / Notes

- Windows 使用 `.exe` 扩展名
- Linux 使用 `./` 前缀
- 可执行文件必须在当前工作目录

#### 使用示例 / Examples

```python
from fiberdiffraction import FortranCaller, InputConfig

config = InputConfig("input.txt")
caller = FortranCaller(config)

# 设置 OpenMP
caller.setup_omp_threads()

# 运行初始化
caller.run_initialization("input.txt")

# 运行优化
caller.run_optimization("input.txt", "diffraction.txt", step=0)
```

---

### 3.6 FileManager - 文件操作

静态方法进行文件操作。

#### 方法 / Methods

```python
FileManager.ensure_directory(path: str) -> None
    """创建目录（如不存在）"""

FileManager.move_file(source: str, dest_dir: str) -> bool
    """移动文件，返回是否成功"""

FileManager.copy_file(source: str, dest_dir: str) -> bool
    """复制文件，返回是否成功"""

FileManager.file_exists(path: str) -> bool
    """检查文件是否存在"""

FileManager.cleanup_old_files(step: int, layer_mode: int) -> None
    """归档上一代文件"""

FileManager.cleanup_final_files(step: int, layer_mode: int) -> None
    """最终归档"""
```

#### 使用示例 / Examples

```python
from fiberdiffraction import FileManager

# 创建目录
FileManager.ensure_directory("result")

# 移动文件
FileManager.move_file("cell_0.txt", "result")

# 检查文件
if FileManager.file_exists("cell_1.txt"):
    print("文件存在")
```

---

### 3.7 HDF5Manager - HDF5 管理

读写 HDF5 文件。

#### 初始化 / Constructor

```python
HDF5Manager(filename: str, mode: str = 'a')
# mode: 'r'=读, 'w'=写, 'a'=追加
```

#### 写入方法 / Write Methods

```python
write_config(config_dict: Dict[str, Any]) -> None
    """写入配置参数"""

write_population(step: int, cells: List[List[float]], 
                tilt_angles: Optional[List[float]] = None) -> None
    """写入种群数据"""

write_timing(step: int, elapsed: float) -> None
    """写入时间记录"""

write_total_time(total_time: float) -> None
    """写入总耗时"""

write_convergence(step: int, best_error: float, best_cell: List[float]) -> None
    """写入收敛数据"""

write_metadata(version: str = "1.7.0") -> None
    """写入元数据"""
```

#### 读取方法 / Read Methods

```python
read_population(step: int) -> Optional[np.ndarray]
    """读取种群数据"""

read_config() -> Dict[str, Any]
    """读取配置参数"""

read_convergence() -> Dict[str, np.ndarray]
    """读取收敛数据"""

read_timing() -> Dict[str, Any]
    """读取时间记录"""

list_steps() -> List[int]
    """列出所有步骤编号"""
```

#### HDF5 文件结构 / File Structure

```
results.h5
├── config/              # 配置参数
├── populations/         # 各代种群 (step_0, step_1, ...)
├── convergence/         # 收敛数据 (best_errors, best_cells)
├── timing/              # 时间记录 (step_times, total_time)
└── metadata/            # 元数据 (created_at, version)
```

#### 使用示例 / Examples

```python
from fiberdiffraction import HDF5Manager

# 写入模式
with HDF5Manager("results.h5", mode='w') as hdf5:
    hdf5.write_config({"population_size": 2000})
    hdf5.write_population(0, [[5.0, 5.0, 15.0, 90, 90, 90]])
    hdf5.write_total_time(120.5)

# 读取模式
with HDF5Manager("results.h5", mode='r') as hdf5:
    config = hdf5.read_config()
    pop = hdf5.read_population(0)
    timing = hdf5.read_timing()
    
    print(f"种群大小: {config['population_size']}")
    print(f"总耗时: {timing['total_time']}秒")
```

---

### 3.8 Plotter - 绘图

生成分析图表。

#### 方法 / Methods

```python
plot_timing(save_path: Optional[str] = None, show: bool = True) -> Figure
    """
    时间曲线 - 显示每步耗时柱状图
    
    Args:
        save_path: 保存路径（可选）
        show: 是否显示图表
    """

plot_convergence(save_path: Optional[str] = None, show: bool = True) -> Figure
    """收敛曲线 - 显示 GA 收敛过程"""

plot_parameters(save_path: Optional[str] = None, show: bool = True) -> Figure
    """参数演化 - 显示最佳参数变化"""

plot_population_evolution(save_path: Optional[str] = None, show: bool = True) -> Figure
    """种群演化 - 显示种群分布"""

save_all(output_dir: str = "figures") -> None
    """保存所有图表到目录"""
```

#### 使用示例 / Examples

```python
from fiberdiffraction import HDF5Manager, Plotter

# 读取并绘图
hdf5 = HDF5Manager("results.h5", mode='r')
plotter = Plotter(hdf5)

# 单独绘图
plotter.plot_timing("figures/timing.png", show=False)
plotter.plot_convergence("figures/convergence.png", show=False)
plotter.plot_parameters("figures/parameters.png", show=True)

# 保存所有图表
plotter.save_all("figures/")

hdf5.close()
```

---

### 3.9 IndexingCallback - 回调接口

用于 GUI 集成的回调接口。

#### 抽象方法 / Abstract Methods

```python
class IndexingCallback(ABC):
    def on_step_start(self, step: int, total: int) -> None:
        """步骤开始时调用"""
        
    def on_step_end(self, step: int, total: int, elapsed: float) -> None:
        """步骤结束时调用"""
        
    def on_progress(self, step: int, message: str) -> None:
        """进度更新时调用"""
        
    def on_error(self, step: int, error: Exception) -> None:
        """发生错误时调用"""
        
    def on_complete(self, total_time: float, results: dict) -> None:
        """全部完成时调用"""
```

#### 预定义实现 / Predefined Implementations

**DefaultCallback** - 输出到控制台
```python
from fiberdiffraction import DefaultCallback

callback = DefaultCallback()
# 自动打印进度信息
```

**SilentCallback** - 静默模式
```python
from fiberdiffraction import SilentCallback

callback = SilentCallback()
# 不输出任何信息
```

**CallbackAdapter** - 函数式回调
```python
from fiberdiffraction import CallbackAdapter

callback = CallbackAdapter(
    on_step_start=lambda s, t: print(f"开始 {s+1}/{t}"),
    on_progress=lambda s, m: print(f"[{s+1}] {m}"),
    on_complete=lambda t, r: print(f"完成！耗时 {t:.1f}秒")
)
```

#### GUI 集成示例 / GUI Integration Example

```python
from fiberdiffraction import IndexingCallback, FiberDiffractionIndexer

class MyGUI(IndexingCallback):
    """自定义 GUI 回调类"""
    
    def __init__(self, progress_bar, log_text):
        self.progress_bar = progress_bar
        self.log_text = log_text
    
    def on_step_start(self, step, total):
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(step)
        self.log_text.append(f"开始步骤 {step + 1}/{total}")
    
    def on_step_end(self, step, total, elapsed):
        self.progress_bar.setValue(step + 1)
        self.log_text.append(f"步骤 {step + 1} 完成，耗时 {elapsed:.1f}秒")
    
    def on_progress(self, step, message):
        self.log_text.append(f"[步骤 {step + 1}] {message}")
    
    def on_error(self, step, error):
        self.log_text.append(f"错误: {error}")
    
    def on_complete(self, total_time, results):
        self.log_text.append(f"全部完成！总耗时 {total_time:.1f}秒")

# 使用
gui = MyGUI(progress_bar, log_text)
indexer = FiberDiffractionIndexer(
    "input.txt", "diffraction.txt",
    callback=gui
)
indexer.run()
```

---

## 4. 完整示例 / Complete Examples

### 4.1 基本优化流程

```python
from fiberdiffraction import FiberDiffractionIndexer

# 创建索引器
indexer = FiberDiffractionIndexer(
    input_file="input.txt",
    diffraction_file="diffraction.txt"
)

# 显示配置
print(indexer.get_config_summary())

# 运行
indexer.run()

print("优化完成！")
```

### 4.2 HDF5 模式完整流程

```python
from fiberdiffraction import FiberDiffractionIndexer, HDF5Manager, Plotter

# 运行优化（HDF5 模式）
indexer = FiberDiffractionIndexer(
    input_file="input.txt",
    diffraction_file="diffraction.txt",
    use_hdf5=True,
    hdf5_file="results.h5"
)
indexer.run()

# 分析结果
with HDF5Manager("results.h5", mode='r') as hdf5:
    # 读取收敛数据
    conv = hdf5.read_convergence()
    print(f"最佳误差: {min(conv['best_errors']):.4f}")
    
    # 读取最佳晶胞
    best_idx = conv['best_errors'].argmin()
    best_cell = conv['best_cells'][best_idx]
    print(f"最佳晶胞: a={best_cell[0]:.2f}, b={best_cell[1]:.2f}, c={best_cell[2]:.2f}")
    
    # 绘图
    plotter = Plotter(hdf5)
    plotter.save_all("figures/")
```

### 4.3 自定义工作流

```python
from fiberdiffraction import (
    InputConfig, PopulationManager, 
    GeneticEngine, FortranCaller
)

# 读取配置
config = InputConfig("input.txt")
print(f"种群大小: {config.population_size}")
print(f"进化代数: {config.generation_steps}")

# 创建组件
population = PopulationManager(config)
engine = GeneticEngine(config)
fortran = FortranCaller(config)

# 设置 OpenMP
fortran.setup_omp_threads()

# 手动控制流程
for step in range(config.generation_steps):
    if step == 0:
        # 初始化种群
        population.initialize_random()
        population.save_to_file(f"cell_{step}.txt")
    
    # 调用 Fortran 优化
    fortran.run_optimization("input.txt", "diffraction.txt", step)
    
    # 加载排序后的种群
    population.load_from_file(f"cell_{step}.txt")
    
    # 获取最佳晶胞
    best = population.get_best_cell()
    print(f"步骤 {step}: 最佳晶胞 = {best}")
```

### 4.4 进度监控

```python
import time
from fiberdiffraction import CallbackAdapter, FiberDiffractionIndexer

# 创建带时间记录的回调
start_time = time.time()

def log_message(step, message):
    elapsed = time.time() - start_time
    print(f"[{elapsed:.1f}s] 步骤 {step+1}: {message}")

callback = CallbackAdapter(
    on_step_start=lambda s, t: print(f"\n=== 步骤 {s+1}/{t} ==="),
    on_progress=log_message,
    on_complete=lambda t, r: print(f"\n总耗时: {t:.1f}秒")
)

# 运行
indexer = FiberDiffractionIndexer(
    "input.txt", "diffraction.txt",
    callback=callback
)
indexer.run()
```

---

## 5. 故障排除 / Troubleshooting

### 5.1 常见错误

#### 错误 1：找不到 Fortran 可执行文件

```
'single_polymcrystindex.exe' 不是内部或外部命令
```

**解决方案：**
1. 确认 `single_polymcrystindex.exe` 在当前工作目录
2. 或修改 `fortran.py` 中的路径

#### 错误 2：找不到输入文件

```
FileNotFoundError: 输入文件未找到: input.txt
```

**解决方案：**
1. 使用绝对路径
2. 确认文件名正确

#### 错误 3：输入文件格式错误

```
ValueError: 配置验证失败: 种群大小必须大于 0
```

**解决方案：**
1. 检查输入文件行号是否正确
2. 使用示例输入文件作为模板

### 5.2 性能优化

```python
# 减少 OpenMP 线程数
# 在输入文件第 28 行设置

# 系统默认（推荐）
0

# 或指定线程数
4
```

### 5.3 获取帮助

1. 查看配置摘要：
```python
config = InputConfig("input.txt")
print(config.get_all_parameters())
```

2. 验证配置：
```python
is_valid, error = config.validate()
if not is_valid:
    print(f"错误: {error}")
```

3. 使用详细回调：
```python
callback = DefaultCallback()  # 打印详细信息
indexer = FiberDiffractionIndexer(..., callback=callback)
```
