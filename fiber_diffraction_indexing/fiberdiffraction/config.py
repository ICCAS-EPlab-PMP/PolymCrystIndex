"""
输入配置类 / Input Configuration
==============================

该模块提供 InputConfig 类，用于读取和解析纤维衍射索引的输入文件。

注意：输入文件的行号与 Fortran 程序中的定义一致，请勿修改！
WARNING: Line numbers in input file MUST match Fortran program definition!

用法 / Usage:
    from fiberdiffraction import InputConfig
    
    config = InputConfig("input.txt")
    print(config.population_size)
    print(config.get_all_parameters())
"""

from typing import List, Tuple, Dict, Any


class InputConfig:
    """输入参数配置类 / Input Parameter Configuration Class
    
    从输入文件读取所有参数配置，行号与 Fortran 程序保持一致。
    Reads all parameters from input file, line numbers must match Fortran.
    
    属性 / Attributes:
        filename: 输入文件路径 / Input file path
        lines: 文件所有行的内容 / File lines content
    """
    
    def __init__(self, filename: str):
        """初始化输入配置 / Initialize input configuration
        
        Args:
            filename: 输入文件路径 / Input file path
            
        Raises:
            FileNotFoundError: 文件不存在 / File not found
            IOError: 文件读取错误 / File read error
        """
        self.filename = filename
        self.lines = []
        self._read_file()
    
    def _read_file(self) -> None:
        """读取输入文件到内存 / Read input file into memory"""
        try:
            with open(self.filename, 'r') as f:
                self.lines = f.readlines()
        except FileNotFoundError:
            raise FileNotFoundError(f"输入文件未找到: {self.filename}")
        except IOError as e:
            raise IOError(f"读取输入文件错误: {e}")
    
    # =========================================================================
    # 核心遗传算法参数 / Core Genetic Algorithm Parameters
    # =========================================================================
    
    @property
    def population_size(self) -> int:
        """种群大小 / Population Size
        
        每代包含的晶胞个体数量。值越大，搜索越全面，但计算时间越长。
        Number of unit cell individuals per generation. Larger values 
        provide more comprehensive search but require more computation.
        
        对应输入文件第 4 行（索引 3）
        """
        return int(self.lines[3].split()[0])
    
    @property
    def generation_steps(self) -> int:
        """进化代数 / Generation Steps
        
        优化迭代次数。值越大，越可能找到最优解，但耗时越长。
        Number of optimization iterations. Larger values increase 
        chance of finding optimal solution but require more time.
        
        对应输入文件第 5 行（索引 4）
        """
        return int(self.lines[4].split()[0])
    
    @property
    def survival_rate(self) -> float:
        """存活率 / Survival Rate
        
        遗传算法中选择保留到下一代的最佳个体比例。范围 [0-1]。
        Proportion of best individuals selected to survive to next generation.
        Range [0-1]. Too high reduces search diversity.
        
        对应输入文件第 6 行（索引 5）
        """
        return float(self.lines[5].split()[0])
    
    @property
    def crossover_rate(self) -> float:
        """交叉率 / Crossover Rate
        
        通过交叉操作产生新个体的比例。范围 [0-1]。
        Proportion of new individuals created through crossover.
        Range [0-1].
        
        对应输入文件第 7 行（索引 6）
        """
        return float(self.lines[6].split()[0])
    
    @property
    def mutation_rate(self) -> float:
        """变异率 / Mutation Rate
        
        通过变异操作产生新个体的比例。范围 [0-1]。
        值太低可能陷入局部最优，值太高会破坏优秀解。
        Proportion of new individuals created through mutation.
        Range [0-1]. Too low may get stuck in local optimum.
        
        对应输入文件第 8 行（索引 7）
        """
        return float(self.lines[7].split()[0])
    
    # =========================================================================
    # 晶胞结构参数 / Unit Cell Structure Parameters
    # =========================================================================
    
    @property
    def c_axis(self) -> float:
        """C轴参数 / C-axis Parameter
        
        晶胞的 c 轴长度（埃）。设为 0 表示由算法优化此参数，
        其他值表示固定 c 轴长度。
        Unit cell c-axis length (Angstrom). 0 = variable (optimized by algorithm),
        other value = fixed c-axis length.
        
        对应输入文件第 11 行（索引 10）
        """
        return float(self.lines[10].split()[0])
    
    @property
    def layer_mode(self) -> int:
        """层模式 / Layer Mode
        
        是否启用层状结构处理。非零值表示启用。
        Whether to enable layer structure processing.
        Non-zero = enabled.
        
        对应输入文件第 13 行（索引 12）
        """
        return int(self.lines[12].split()[0])
    
    # =========================================================================
    # 参数边界 / Parameter Bounds
    # =========================================================================
    
    @property
    def parameter_min(self) -> List[float]:
        """参数最小值 / Parameter Minimum Values
        
        晶胞参数的搜索下界: [a, b, c, alpha, beta, gamma]
        - a, b, c: 轴长（埃）/ Axis lengths (Angstrom)
        - alpha, beta, gamma: 晶胞角度（度）/ Cell angles (degrees)
        
        对应输入文件第 25 行（索引 24）
        """
        return [float(x) for x in self.lines[24].strip(' \n').split()]
    
    @property
    def parameter_max(self) -> List[float]:
        """参数最大值 / Parameter Maximum Values
        
        晶胞参数的搜索上界: [a, b, c, alpha, beta, gamma]
        - a, b, c: 轴长（埃）/ Axis lengths (Angstrom)
        - alpha, beta, gamma: 晶胞角度（度）/ Cell angles (degrees)
        
        对应输入文件第 26 行（索引 25）
        """
        return [float(x) for x in self.lines[25].strip(' \n').split()]
    
    # =========================================================================
    # 高级选项 / Advanced Options
    # =========================================================================
    
    @property
    def tilt_status(self) -> int:
        """倾斜状态 / Tilt Status
        
        是否优化纤维倾斜角。1 = 启用，0 = 禁用。
        Whether to optimize fiber tilt angle.
        1 = enabled, 0 = disabled.
        
        对应输入文件第 27 行（索引 26）
        """
        return int(self.lines[26])
    
    @property
    def omp_threads(self) -> int:
        """OpenMP线程数 / OpenMP Thread Count
        
        用于 Fortran 并行计算的线程数。0 表示由系统决定。
        Number of threads for Fortran parallel computation.
        0 = system default.
        
        对应输入文件第 28 行（索引 27）
        """
        try:
            return int(self.lines[27].split()[0])
        except (IndexError, ValueError):
            return 0
    
    # =========================================================================
    # 计算属性 / Computed Properties
    # =========================================================================
    
    @property
    def survive_count(self) -> int:
        """计算存活个体数量 / Compute survivor count
        
        根据 population_size * survival_rate 计算。
        """
        return int(self.population_size * self.survival_rate)
    
    @property
    def crossover_count(self) -> int:
        """计算交叉个体数量 / Compute crossover count
        
        根据 population_size * crossover_rate 计算。
        """
        return int(self.population_size * self.crossover_rate)
    
    @property
    def mutation_count(self) -> int:
        """计算变异个体数量 / Compute mutation count
        
        根据 population_size * mutation_rate 计算。
        """
        return int(self.population_size * self.mutation_rate)
    
    @property
    def random_count(self) -> int:
        """计算随机生成个体数量 / Compute random generation count
        
        剩余的个体数量 = population_size - survive - crossover - mutation
        """
        total = self.survive_count + self.crossover_count + self.mutation_count
        return max(0, self.population_size - total)
    
    # =========================================================================
    # 方法 / Methods
    # =========================================================================
    
    def get_all_parameters(self) -> Dict[str, Any]:
        """获取所有参数的字典 / Get all parameters as dictionary
        
        Returns:
            包含所有输入参数的字典 / Dictionary containing all input parameters
        """
        return {
            # 遗传算法参数 / GA Parameters
            'population_size': self.population_size,
            'generation_steps': self.generation_steps,
            'survival_rate': self.survival_rate,
            'crossover_rate': self.crossover_rate,
            'mutation_rate': self.mutation_rate,
            
            # 晶胞结构 / Cell Structure
            'c_axis': self.c_axis,
            'layer_mode': self.layer_mode,
            
            # 参数边界 / Parameter Bounds
            'parameter_min': self.parameter_min,
            'parameter_max': self.parameter_max,
            
            # 高级选项 / Advanced Options
            'tilt_status': self.tilt_status,
            'omp_threads': self.omp_threads,
            
            # 计算数量 / Computed Counts
            'survive_count': self.survive_count,
            'crossover_count': self.crossover_count,
            'mutation_count': self.mutation_count,
            'random_count': self.random_count,
        }
    
    def validate(self) -> Tuple[bool, str]:
        """验证输入参数是否有效 / Validate input parameters
        
        检查各项参数是否在合理范围内。
        Checks if all parameters are within reasonable ranges.
        
        Returns:
            (是否有效, 错误消息) 元组 / (is_valid, error_message) tuple
        """
        # 检查种群大小 / Check population size
        if self.population_size <= 0:
            return False, f"种群大小必须大于 0: {self.population_size}"
        
        # 检查存活率 / Check survival rate
        if not (0 <= self.survival_rate <= 1):
            return False, f"存活率必须在 0-1 之间: {self.survival_rate}"
        
        # 检查交叉率 / Check crossover rate
        if not (0 <= self.crossover_rate <= 1):
            return False, f"交叉率必须在 0-1 之间: {self.crossover_rate}"
        
        # 检查变异率 / Check mutation rate
        if not (0 <= self.mutation_rate <= 1):
            return False, f"变异率必须在 0-1 之间: {self.mutation_rate}"
        
        # 检查参数边界 / Check parameter bounds
        if len(self.parameter_min) != 6:
            return False, f"参数最小值必须有 6 个元素: {len(self.parameter_min)}"
        
        if len(self.parameter_max) != 6:
            return False, f"参数最大值必须有 6 个元素: {len(self.parameter_max)}"
        
        # 检查最小值 <= 最大值 / Check min <= max
        for i in range(6):
            if self.parameter_min[i] > self.parameter_max[i]:
                return False, f"参数 {i} 最小值 > 最大值: {self.parameter_min[i]} > {self.parameter_max[i]}"
        
        # 检查长度参数必须为正 / Check length parameters are positive
        for i in range(3):
            if self.parameter_min[i] <= 0:
                return False, f"长度参数 {i} 必须为正: {self.parameter_min[i]}"
        
        return True, ""
