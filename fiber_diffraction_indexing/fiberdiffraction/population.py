"""
种群管理类 / Population Manager
==========================

该模块提供 PopulationManager 类，用于管理晶胞参数种群。

晶胞参数格式：[a, b, c, alpha, beta, gamma, tilt_angle]
Cell parameter format: [a, b, c, alpha, beta, gamma, tilt_angle]
- a, b, c: 轴长（埃）/ Axis lengths (Angstrom)
- alpha, beta, gamma: 晶胞角度（度）/ Cell angles (degrees)
- tilt_angle: 纤维倾斜角（度）/ Fiber tilt angle (degrees)

用法 / Usage:
    from fiberdiffraction import PopulationManager, InputConfig
    
    config = InputConfig("input.txt")
    pop = PopulationManager(config)
    pop.initialize_random()
    pop.save_to_file("cell_0.txt")
"""

import random
from typing import List, Tuple, Optional
from .config import InputConfig


class PopulationManager:
    """晶胞参数种群管理器 / Unit Cell Population Manager
    
    负责种群的初始化、加载、保存和排序。
    Responsible for population initialization, loading, saving, and sorting.
    
    属性 / Attributes:
        config: 输入配置 / Input configuration
        cells: 晶胞参数列表 / Cell parameter list
        tilt_angles: 倾斜角度列表 / Tilt angle list
    """
    
    def __init__(self, config: InputConfig):
        """初始化种群管理器 / Initialize population manager
        
        Args:
            config: 输入配置对象 / Input configuration object
        """
        self.config = config
        self.cells: List[List[float]] = []
        self.tilt_angles: List[float] = []
    
    def initialize_random(self) -> None:
        """用随机晶胞初始化种群 / Initialize population with random cells
        
        根据输入配置中的参数边界，随机生成初始种群。
        Generates initial population randomly based on parameter bounds in config.
        """
        self.cells = []
        self.tilt_angles = []
        
        for _ in range(self.config.population_size):
            cell, tilt = self._generate_random_cell()
            self.cells.append(cell)
            self.tilt_angles.append(tilt)
    
    def _generate_random_cell(self) -> Tuple[List[float], float]:
        """生成一个随机晶胞 / Generate a random cell
        
        在配置指定的参数边界内随机生成晶胞参数。
        Generates random cell parameters within config-specified bounds.
        
        注意：a >= b（晶体学惯例）
        Note: a >= b (crystallographic convention)
        
        Returns:
            (晶胞参数列表, 倾斜角度) 元组 / (cell parameter list, tilt angle) tuple
        """
        min_vals = self.config.parameter_min
        max_vals = self.config.parameter_max
        
        # 随机生成 a, b（确保 a >= b）
        a = random.uniform(min_vals[0], max_vals[0])
        b = random.uniform(min_vals[1], max_vals[1])
        if a < b:
            a, b = b, a
        
        # 随机生成 c（如果 c_axis = 0，否则使用固定值）
        if self.config.c_axis == 0:
            c = random.uniform(min_vals[2], max_vals[2])
        else:
            c = self.config.c_axis
        
        # 随机生成角度
        alpha = random.uniform(min_vals[3], max_vals[3])
        beta = random.uniform(min_vals[4], max_vals[4])
        gamma = random.uniform(min_vals[5], max_vals[5])
        
        # 随机生成倾斜角度（如果启用）
        if self.config.tilt_status == 1:
            tilt_angle = random.uniform(-10, 10)
        else:
            tilt_angle = 0.0
        
        return [a, b, c, alpha, beta, gamma], tilt_angle
    
    def load_from_file(self, filename: str) -> None:
        """从文件加载种群 / Load population from file
        
        Args:
            filename: 晶胞参数文件路径 / Cell parameter file path
            
        Raises:
            FileNotFoundError: 文件不存在 / File not found
        """
        self.cells = []
        self.tilt_angles = []
        
        with open(filename, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 6:
                    continue
                
                cell = [float(parts[i]) for i in range(6)]
                self.cells.append(cell)
                
                if len(parts) >= 7 and self.config.tilt_status == 1:
                    self.tilt_angles.append(float(parts[6]))
                else:
                    self.tilt_angles.append(0.0)
    
    def save_to_file(self, filename: str) -> None:
        """保存种群到文件 / Save population to file
        
        Args:
            filename: 输出文件路径 / Output file path
        """
        with open(filename, 'w') as f:
            for i, cell in enumerate(self.cells):
                if self.config.tilt_status == 1:
                    line = (
                        f"{cell[0]:.4f} {cell[1]:.4f} {cell[2]:.4f} "
                        f"{cell[3]:.4f} {cell[4]:.4f} {cell[5]:.4f} "
                        f"{self.tilt_angles[i]:.4f}\n"
                    )
                else:
                    line = (
                        f"{cell[0]:.4f} {cell[1]:.4f} {cell[2]:.4f} "
                        f"{cell[3]:.4f} {cell[4]:.4f} {cell[5]:.4f}\n"
                    )
                f.write(line)
    
    def sort_by_diffraction(self, diffraction_file: str) -> None:
        """根据衍射数据排序种群 / Sort population by diffraction data
        
        读取衍射数据文件，按 q 值排序，然后重新排列种群。
        Reads diffraction data file, sorts by q-value, reorders population.
        
        Args:
            diffraction_file: 衍射数据文件路径 / Diffraction data file path
        """
        # 读取衍射数据 / Read diffraction data
        diffraction = []
        with open(diffraction_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                parts = line.strip().split()
                if len(parts) >= 1:
                    try:
                        q_value = float(parts[0])
                        diffraction.append([q_value, line_num - 1])
                    except ValueError:
                        continue
        
        # 按 q 值排序 / Sort by q-value
        diffraction.sort(key=lambda x: x[0])
        
        # 找出重复的晶胞 / Find duplicate cells
        duplicate_indices = set()
        for i in range(len(self.cells)):
            for j in range(i + 1, len(self.cells)):
                if self._is_duplicate(self.cells[i], self.cells[j]):
                    duplicate_indices.add(j)
        
        # 重新排列种群 / Reorder population
        new_cells = []
        new_tilt_angles = []
        
        for q_val, idx in diffraction:
            if idx < len(self.cells) and idx not in duplicate_indices:
                new_cells.append(self.cells[idx])
                new_tilt_angles.append(self.tilt_angles[idx])
        
        self.cells = new_cells
        self.tilt_angles = new_tilt_angles
    
    def _is_duplicate(self, cell1: List[float], cell2: List[float],
                     length_threshold: float = 0.1,
                     angle_threshold: float = 0.5) -> bool:
        """检查两个晶胞是否重复 / Check if two cells are duplicates
        
        使用长度差异阈值（0.1埃）和角度差异阈值（0.5度）判断。
        Uses length difference threshold (0.1 Angstrom) and angle 
        difference threshold (0.5 degree) for判断.
        
        Args:
            cell1: 第一个晶胞参数 / First cell parameters
            cell2: 第二个晶胞参数 / Second cell parameters
            length_threshold: 长度差异阈值 / Length difference threshold
            angle_threshold: 角度差异阈值 / Angle difference threshold
            
        Returns:
            如果重复返回 True / Returns True if duplicates
        """
        # 检查长度参数 / Check length parameters
        length_similar = (
            abs(cell1[0] - cell2[0]) < length_threshold and
            abs(cell1[1] - cell2[1]) < length_threshold and
            abs(cell1[2] - cell2[2]) < length_threshold
        )
        
        # 检查角度参数（考虑对称性）/ Check angles (considering symmetry)
        angle1_ok = (abs(cell1[3] - cell2[3]) < angle_threshold or 
                    abs(180 - cell1[3] - cell2[3]) < angle_threshold)
        angle2_ok = (abs(cell1[4] - cell2[4]) < angle_threshold or 
                    abs(180 - cell1[4] - cell2[4]) < angle_threshold)
        angle3_ok = (abs(cell1[5] - cell2[5]) < angle_threshold or 
                    abs(180 - cell1[5] - cell2[5]) < angle_threshold)
        
        return length_similar and angle1_ok and angle2_ok and angle3_ok
    
    def size(self) -> int:
        """获取当前种群大小 / Get current population size"""
        return len(self.cells)
    
    def is_empty(self) -> bool:
        """检查种群是否为空 / Check if population is empty"""
        return len(self.cells) == 0
    
    def get_best_cell(self) -> Optional[List[float]]:
        """获取最佳晶胞参数 / Get best cell parameters
        
        Returns:
            最佳晶胞参数，如果种群为空返回 None / Best cell parameters or None
        """
        if self.is_empty():
            return None
        return self.cells[0].copy()
    
    def get_all_cells(self) -> List[List[float]]:
        """获取所有晶胞参数的副本 / Get copy of all cell parameters
        
        Returns:
            晶胞参数列表的副本 / Copy of cell parameter list
        """
        return [cell.copy() for cell in self.cells]
