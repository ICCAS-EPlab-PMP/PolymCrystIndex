"""
遗传算法类 / Genetic Algorithm Engine
=================================

该模块提供 GeneticEngine 类，用于执行遗传算法操作。

遗传算法流程：
    1. 选择（Selection）- 从当前代选择存活个体
    2. 交叉（Crossover）- 组合两个父代个体产生新个体
    3. 变异（Mutation）- 随机改变某些个体的参数
    4. 随机生成（Random）- 生成新的随机个体增加多样性

用法 / Usage:
    from fiberdiffraction import GeneticEngine, InputConfig
    
    config = InputConfig("input.txt")
    engine = GeneticEngine(config)
    new_cells = engine.generate_new_generation(cells)
"""

import random
from typing import List, Tuple, Optional
from .config import InputConfig


class GeneticEngine:
    """遗传算法引擎 / Genetic Algorithm Engine
    
    负责执行交叉、变异和随机生成等遗传操作。
    Responsible for genetic operations: crossover, mutation, and random generation.
    
    属性 / Attributes:
        config: 输入配置 / Input configuration
    """
    
    def __init__(self, config: InputConfig):
        """初始化遗传算法引擎 / Initialize genetic engine
        
        Args:
            config: 输入配置对象 / Input configuration object
        """
        self.config = config
    
    def generate_new_generation(self, cells: List[List[float]]) -> List[List[float]]:
        """生成新一代种群 / Generate new generation
        
        通过以下操作生成新一代：
        1. 选择（存活者）
        2. 交叉
        3. 变异
        4. 随机生成
        
        Args:
            cells: 当前种群（已按适应度排序）/ Current population (sorted by fitness)
            
        Returns:
            新一代晶胞参数 / New generation cell parameters
        """
        new_generation = []
        
        # 1. 选择存活者 / Select survivors
        survivors = self._select_survivors(cells)
        new_generation.extend(survivors)
        
        # 2. 交叉 / Crossover
        crossovers = self._generate_crossovers(cells)
        new_generation.extend(crossovers)
        
        # 3. 变异 / Mutation
        mutations = self._generate_mutations(cells)
        new_generation.extend(mutations)
        
        # 4. 随机生成 / Random generation
        random_cells = self._generate_random_cells()
        new_generation.extend(random_cells)
        
        # 确保种群大小 / Ensure population size
        if len(new_generation) > self.config.population_size:
            new_generation = new_generation[:self.config.population_size]
        
        # 验证并修正参数 / Validate and fix parameters
        new_generation = self._validate_and_fix(new_generation)
        
        return new_generation
    
    def _select_survivors(self, cells: List[List[float]]) -> List[List[float]]:
        """选择存活者 / Select survivors
        
        选择当前代中适应度最好的个体作为存活者。
        Selects best-fitted individuals from current generation as survivors.
        
        Args:
            cells: 当前种群 / Current population
            
        Returns:
            存活的晶胞参数 / Survivor cell parameters
        """
        survivors = []
        survive_count = self.config.survive_count
        
        for i in range(min(survive_count, len(cells))):
            cell = [float(x) for x in cells[i][:6]]
            survivors.append(cell)
        
        return survivors
    
    def _generate_crossovers(self, cells: List[List[float]]) -> List[List[float]]:
        """生成交叉个体 / Generate crossover individuals
        
        通过随机选择两个父代，交换部分参数产生新个体。
        Creates new individuals by randomly swapping parameters between two parents.
        
        Args:
            cells: 当前种群 / Current population
            
        Returns:
            交叉产生的晶胞参数 / Crossover cell parameters
        """
        crossovers = []
        cross_count = self.config.crossover_count
        survive_count = self.config.survive_count
        
        # 选择父代池 / Select parent pool
        parent_pool_size = min(int(survive_count * 1.2), len(cells))
        parent_pool = cells[:parent_pool_size]
        
        for _ in range(cross_count):
            if len(parent_pool) < 2:
                break
            
            # 选择两个随机父代 / Select two random parents
            parent1_idx = random.randint(0, len(parent_pool) - 1)
            parent2_idx = random.randint(0, len(parent_pool) - 1)
            while parent2_idx == parent1_idx:
                parent2_idx = random.randint(0, len(parent_pool) - 1)
            
            parent1 = [float(x) for x in parent_pool[parent1_idx][:6]]
            parent2 = [float(x) for x in parent_pool[parent2_idx][:6]]
            
            # 确定要交叉的参数 / Determine parameters to crossover
            if self.config.c_axis == 0:
                param_indices = [0, 1, 2, 3, 4, 5]
            else:
                param_indices = [0, 1, 3, 4, 5]
            
            # 选择随机参数进行交叉 / Select random parameters for crossover
            change_num = min(3, len(param_indices))
            change_list = random.sample(param_indices, change_num)
            
            # 执行交叉 / Perform crossover
            child = parent1.copy()
            for param in change_list:
                if param in [0, 1]:
                    child[param] = parent2[random.choice([0, 1])]
                elif param in [3, 4, 5]:
                    child[param] = parent2[random.choice([3, 4, 5])]
                else:
                    child[param] = parent2[param]
            
            # 添加小随机突变 / Add small random mutation
            for c in range(6):
                if c in [0, 1] or (c == 2 and self.config.c_axis == 0):
                    child[c] += random.uniform(-1, 1) / 4
                elif c in [3, 4, 5]:
                    child[c] += random.uniform(-4, 4)
            
            crossovers.append(child)
        
        return crossovers
    
    def _generate_mutations(self, cells: List[List[float]]) -> List[List[float]]:
        """生成变异个体 / Generate mutation individuals
        
        随机选择个体并改变其部分参数。
        Randomly selects individuals and modifies some of their parameters.
        
        Args:
            cells: 当前种群 / Current population
            
        Returns:
            变异产生的晶胞参数 / Mutated cell parameters
        """
        mutations = []
        mutation_count = self.config.mutation_count
        survive_count = self.config.survive_count
        
        # 选择父代池 / Select parent pool
        parent_pool = cells[:survive_count]
        
        for _ in range(mutation_count):
            if not parent_pool:
                break
            
            # 选择随机父代 / Select random parent
            parent_idx = random.randint(0, len(parent_pool) - 1)
            child = [float(x) for x in parent_pool[parent_idx][:6]]
            
            # 确定要变异的参数 / Determine parameters to mutate
            if self.config.c_axis == 0:
                param_indices = [0, 1, 2, 3, 4, 5]
            else:
                param_indices = [0, 1, 3, 4, 5]
            
            # 选择随机参数进行变异 / Select random parameters for mutation
            change_num = min(3, len(param_indices))
            change_list = random.sample(param_indices, change_num)
            
            # 执行变异 / Perform mutation
            for param in change_list:
                add_num = random.uniform(-3, 3)
                if param in [0, 1] or (param == 2 and self.config.c_axis == 0):
                    child[param] += add_num / 1.5
                elif param in [3, 4, 5]:
                    child[param] += add_num * 2
                else:
                    child[param] += add_num / 2
            
            mutations.append(child)
        
        return mutations
    
    def _generate_random_cells(self) -> List[List[float]]:
        """生成随机晶胞 / Generate random cells
        
        随机生成新个体以增加种群多样性。
        Generates new random individuals to increase population diversity.
        
        Returns:
            随机生成的晶胞参数 / Randomly generated cell parameters
        """
        random_cells = []
        random_count = self.config.random_count
        min_vals = self.config.parameter_min
        max_vals = self.config.parameter_max
        
        for _ in range(random_count):
            a = random.uniform(min_vals[0], max_vals[0])
            b = random.uniform(min_vals[1], max_vals[1])
            
            # 确保 a >= b / Ensure a >= b
            if a < b:
                a, b = b, a
            
            if self.config.c_axis == 0:
                c = random.uniform(min_vals[2], max_vals[2])
            else:
                c = self.config.c_axis
            
            alpha = random.uniform(min_vals[3], max_vals[3])
            beta = random.uniform(min_vals[4], max_vals[4])
            gamma = random.uniform(min_vals[5], max_vals[5])
            
            random_cells.append([a, b, c, alpha, beta, gamma])
        
        return random_cells
    
    def _validate_and_fix(self, cells: List[List[float]]) -> List[List[float]]:
        """验证并修正晶胞参数 / Validate and fix cell parameters
        
        确保所有参数在配置指定的边界内，且 a >= b。
        Ensures all parameters are within config-specified bounds and a >= b.
        
        Args:
            cells: 晶胞参数列表 / Cell parameter list
            
        Returns:
            修正后的晶胞参数 / Fixed cell parameters
        """
        validated = []
        min_vals = self.config.parameter_min
        max_vals = self.config.parameter_max
        
        for cell in cells:
            # 确保 a >= b / Ensure a >= b
            if cell[0] < cell[1]:
                cell[0], cell[1] = cell[1], cell[0]
                cell[3], cell[4] = cell[4], cell[3]
            
            # 限制参数在范围内 / Clamp parameters to bounds
            for i in range(6):
                if i == 2 and self.config.c_axis != 0:
                    continue  # 跳过固定 c 轴 / Skip fixed c-axis
                
                if cell[i] < min_vals[i] or cell[i] > max_vals[i]:
                    cell[i] = random.uniform(min_vals[i], max_vals[i])
            
            validated.append(cell)
        
        return validated
