"""
主协调器类 / Main Orchestrator
===========================

该模块提供 FiberDiffractionIndexer 类，用于协调整个索引流程。

工作流程：
    1. 初始化 (Initialization)
       - 读取输入配置 (Read input configuration)
       - 设置 OpenMP 线程 (Setup OpenMP threads)
       - 创建结果目录 (Create result directory)
    
    2. 循环优化 (Optimization Loop)
       对于每个 step (0 到 generation_steps-1):
       - 2.1: 初始化种群 (step=0时)
       - 2.2: 调用 Fortran 优化 (single_polymcrystindex)
       - 2.3: 调用排序程序 (FiberDiffractionSort)
       - 2.4: 归档文件到 result/
       - 2.5: 写入 HDF5 (如果启用)
    
    3. 完成 (Completion)
       - 写入总时间
       - 生成图表 (如果使用 HDF5)
       - 清理 TXT 文件 (如果使用 HDF5)

用法 / Usage:
    from fiberdiffraction import FiberDiffractionIndexer
    
    # 基本用法 / Basic usage
    indexer = FiberDiffractionIndexer("input.txt", "diffraction.txt")
    indexer.run()
    
    # HDF5 模式 / HDF5 mode
    indexer = FiberDiffractionIndexer("input.txt", "diffraction.txt", 
                                      use_hdf5=True, hdf5_file="results.h5")
    indexer.run()
    
    # GUI 回调 / GUI callback
    class MyGUI(IndexingCallback):
        def on_progress(self, step, message):
            print(f"进度: {message}")
    
    indexer = FiberDiffractionIndexer("input.txt", "diffraction.txt", callback=MyGUI())
    indexer.run()
"""

import os
import time
from typing import Optional, Dict, Any
from .config import InputConfig
from .population import PopulationManager
from .genetic import GeneticEngine
from .fortran import FortranCaller
from .fileio import FileManager
from .callbacks import IndexingCallback, DefaultCallback
from .hdf5 import HDF5Manager
from .plotter import Plotter


class FiberDiffractionIndexer:
    """纤维衍射索引主协调器 / Fiber Diffraction Index Main Orchestrator
    
    协调整个索引流程，包括初始化、优化和排序。
    Orchestrates the entire indexing workflow.
    
    支持 / Supports:
        - 回调接口（GUI 信号）/ Callback interface (GUI signals)
        - HDF5 存储模式 / HDF5 storage mode
        - 绘图输出 / Plot output
    
    属性 / Attributes:
        input_file: 输入文件路径 / Input file path
        diffraction_file: 衍射数据文件路径 / Diffraction data file path
        config: 输入配置 / Input configuration
        population: 种群管理器 / Population manager
        genetic_engine: 遗传算法引擎 / Genetic algorithm engine
        fortran_caller: Fortran 调用器 / Fortran caller
        file_manager: 文件管理器 / File manager
        callback: 回调接口 / Callback interface
        hdf5: HDF5 管理器（可选）/ HDF5 manager (optional)
    """
    
    def __init__(self, input_file: str, diffraction_file: str,
                 callback: Optional[IndexingCallback] = None,
                 use_hdf5: bool = False,
                 hdf5_file: Optional[str] = None):
        """初始化索引器 / Initialize indexer
        
        Args:
            input_file: 输入文件路径 / Input file path
            diffraction_file: 衍射数据文件路径 / Diffraction data file path
            callback: 回调接口（默认为 DefaultCallback）/ Callback (default: DefaultCallback)
            use_hdf5: 是否使用 HDF5 模式 / Enable HDF5 mode
            hdf5_file: HDF5 文件路径（默认为 results.h5）/ HDF5 file path (default: results.h5)
        """
        self.input_file = input_file
        self.diffraction_file = diffraction_file
        
        self.workdir = os.path.dirname(os.path.abspath(input_file))
        self.result_dir = os.path.join(self.workdir, "result")
        self.figures_dir = os.path.join(self.workdir, "figures")
        
        # =====================================================================
        # 初始化组件 / Initialize components
        # =====================================================================
        self.config = InputConfig(input_file)           # 输入配置 / Input configuration
        self.population = PopulationManager(self.config)  # 种群管理 / Population management
        self.genetic_engine = GeneticEngine(self.config)  # 遗传算法 / Genetic algorithm
        self.fortran_caller = FortranCaller(self.config, workdir=self.workdir)  # Fortran 调用 / Fortran wrapper
        self.file_manager = FileManager()               # 文件操作 / File operations
        
        # =====================================================================
        # 回调接口 / Callback interface
        # =====================================================================
        self.callback = callback or DefaultCallback()
        
        # =====================================================================
        # HDF5 支持 / HDF5 support
        # =====================================================================
        self.use_hdf5 = use_hdf5
        self.hdf5: Optional[HDF5Manager] = None
        if use_hdf5:
            hdf5_path = hdf5_file or os.path.join(self.workdir, "results.h5")
            self.hdf5 = HDF5Manager(hdf5_path, mode='w')
            self._write_hdf5_config()
            self._write_hdf5_metadata()
    
    def _write_hdf5_config(self) -> None:
        """写入 HDF5 配置 / Write HDF5 configuration"""
        if self.hdf5:
            config_dict = self.config.get_all_parameters()
            self.hdf5.write_config(config_dict)
    
    def _write_hdf5_metadata(self) -> None:
        """写入 HDF5 元数据 / Write HDF5 metadata"""
        if self.hdf5:
            self.hdf5.write_metadata()
    
    def validate(self) -> None:
        """验证输入配置 / Validate input configuration
        
        Raises:
            ValueError: 配置验证失败 / Configuration validation failed
        """
        is_valid, error_msg = self.config.validate()
        if not is_valid:
            raise ValueError(f"配置验证失败: {error_msg}")
    
    def run(self) -> None:
        """运行完整的索引流程 / Run complete indexing workflow
        
        主流程：
        1. 验证配置
        2. 设置 OpenMP 线程
        3. 创建结果目录
        4. 循环执行优化步骤
        5. 写入总时间
        6. 生成图表（如使用 HDF5）
        7. 清理 TXT 文件（如使用 HDF5）
        """
        try:
            # =================================================================
            # 步骤 1: 验证配置 / Step 1: Validate configuration
            # =================================================================
            self.validate()
            
            # =================================================================
            # 步骤 2: 设置 OpenMP 线程 / Step 2: Setup OpenMP threads
            # =================================================================
            self.fortran_caller.setup_omp_threads()
            
            # =================================================================
            # 步骤 3: 创建结果目录 / Step 3: Create result directory
            # =================================================================
            self.file_manager.ensure_directory(self.result_dir)
            
            # =================================================================
            # 步骤 4: 记录开始时间并运行优化循环
            # Step 4: Record start time and run optimization loop
            # =================================================================
            start_time = time.time()
            
            for step in range(self.config.generation_steps):
                self._run_single_step(step, start_time)
            
            end_time = time.time()
            total_time = end_time - start_time
            
            # =================================================================
            # 步骤 5: 写入总时间 / Step 5: Write total time
            # =================================================================
            if self.hdf5:
                self.hdf5.write_total_time(total_time)
            
            # =================================================================
            # 步骤 6: 生成图表 / Step 6: Generate plots
            # =================================================================
            if self.use_hdf5:
                self._generate_plots()
            
            # =================================================================
            # 步骤 7: 清理 TXT 文件 / Step 7: Cleanup TXT files
            # =================================================================
            if self.use_hdf5:
                self._cleanup_txt_files()
            
            # =================================================================
            # 步骤 8: 完成回调 / Step 8: Completion callback
            # =================================================================
            results = {
                "total_time": total_time,
                "hdf5_file": self.hdf5.filename if self.hdf5 else None,
            }
            self.callback.on_complete(total_time, results)
            
        except FileNotFoundError as e:
            self.callback.on_error(-1, e)
            print(f"Error: 文件未找到: {e}")
            raise
        except ValueError as e:
            self.callback.on_error(-1, e)
            print(f"Error: 配置错误: {e}")
            raise
        except Exception as e:
            self.callback.on_error(-1, e)
            print(f"Error: 意外错误: {e}")
            raise
        finally:
            # 关闭 HDF5 / Close HDF5
            if self.hdf5:
                self.hdf5.close()
    
    def _run_single_step(self, step: int, start_time: float) -> None:
        """运行单个优化步骤 / Run single optimization step
        
        单步流程：
        1. 步骤开始回调
        2. 初始化种群 (step=0 时)
        3. 调用 Fortran 优化程序
        4. 调用排序程序生成下一代
        5. 归档文件
        6. 写入 HDF5 数据
        7. 步骤结束回调
        
        Args:
            step: 步骤编号 (从 0 开始) / Step number (starting from 0)
            start_time: 总开始时间 / Total start time
        """
        total = self.config.generation_steps
        step_start = time.time()
        
        # =====================================================================
        # 步骤 2.1: 步骤开始回调 / Step 2.1: Step start callback
        # =====================================================================
        self.callback.on_step_start(step, total)
        
        # =====================================================================
        # 步骤 2.2: 初始化种群 (仅 step=0 时)
        # Step 2.2: Initialize population (only when step=0)
        # =====================================================================
        if step == 0:
            self.callback.on_progress(step, "初始化种群...")
            self.initialize_population()
            if self.hdf5:
                self._write_population_to_hdf5(step)
        
        # =====================================================================
        # 步骤 2.3: 调用 Fortran 优化程序
        # Step 2.3: Call Fortran optimization program
        # 调用 single_polymcrystindex 对当前种群进行优化
        # =====================================================================
        self.callback.on_progress(step, "运行 Fortran 优化...")
        self.run_optimization_step(step)
        
        time.sleep(0.5)
        
        # =====================================================================
        # 步骤 2.4: 写入收敛数据 / Step 2.4: Write convergence data
        # =====================================================================
        best_error = 0.0
        if self.hdf5:
            best_error = self._write_convergence_to_hdf5(step)
        
        # =====================================================================
        # 步骤 2.5: 调用排序程序生成下一代
        # Step 2.5: Call sorting program to generate next generation
        # =====================================================================
        self.callback.on_progress(step, f"运行 Fortran 优化... 最佳误差: {best_error:.6f}")
        self.run_sorting_step(step)
        
        # =====================================================================
        # 写入种群到 HDF5 / Write population to HDF5
        # =====================================================================
        if self.hdf5 and step < total - 1:
            self._write_population_to_hdf5(step + 1)
        
        # =====================================================================
        # 步骤 2.6: 归档文件 / Step 2.6: Archive files
        # 将上一代的 cell 文件移动到 result/ 目录
        # =====================================================================
        self.callback.on_progress(step, "归档文件...")
        self.archive_files(step)
        
        step_end = time.time()
        step_elapsed = step_end - step_start
        
        # =====================================================================
        # 写入时间记录 / Write timing record
        # =====================================================================
        if self.hdf5:
            self.hdf5.write_timing(step, step_elapsed)
        
        # =====================================================================
        # 步骤 2.7: 步骤结束回调 / Step 2.7: Step end callback
        # =====================================================================
        self.callback.on_step_end(step, total, step_elapsed)
        
        time.sleep(1)
    
    def _write_population_to_hdf5(self, step: int) -> None:
        """写入种群到 HDF5 / Write population to HDF5
        
        Args:
            step: 步骤编号 / Step number
        """
        cell_file = os.path.join(self.workdir, f"cell_{step}.txt")
        if os.path.exists(cell_file):
            cells = []
            with open(cell_file, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 6:
                        cells.append([float(x) for x in parts[:6]])
            
            if cells:
                self.hdf5.write_population(step, cells)
    
    def _write_convergence_to_hdf5(self, step: int) -> float:
        """写入收敛数据到 HDF5 / Write convergence data to HDF5
        
        从 error_N.txt 读取最佳误差，从 annealing 文件读取最佳晶胞，写入 HDF5。
        
        Args:
            step: 步骤编号 / Step number
            
        Returns:
            best_error: 最佳误差值 / Best error value
        """
        annealing_file = os.path.join(self.workdir, f"cell_{step}_annealing.txt")
        error_file = os.path.join(self.workdir, f"error_{step}.txt")
        
        best_error = 0.0
        best_cell = []
        
        if os.path.exists(error_file):
            try:
                with open(error_file, 'r') as f:
                    errors = []
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                errors.append(float(line))
                            except ValueError:
                                pass
                    if errors:
                        best_error = min(errors)
            except Exception as e:
                print(f"[Warning] Error reading diffraction file: {e}")
        
        if os.path.exists(annealing_file):
            try:
                with open(annealing_file, 'r') as f:
                    first_line = f.readline().strip().split()
                    if len(first_line) >= 6:
                        best_cell = [float(x) for x in first_line[:6]]
            except Exception as e:
                print(f"[Warning] Error reading annealing file: {e}")
        
        if best_cell:
            self.hdf5.write_convergence(step, best_error, best_cell)
        
        return best_error
    
    def _generate_plots(self) -> None:
        """生成图表 / Generate plots
        
        使用 Plotter 生成所有图表，保存到 figures/ 目录。
        Uses Plotter to generate all plots, saves to figures/ directory.
        """
        if self.hdf5:
            self.callback.on_progress(-1, "生成图表...")
            plotter = Plotter(self.hdf5)
            plotter.save_all(self.figures_dir)
    
    def _cleanup_txt_files(self) -> None:
        """清理 TXT 文件 / Cleanup TXT files
        
        HDF5 模式完成后删除临时 TXT 文件以节省空间。
        Deletes temporary TXT files after HDF5 mode completion to save space.
        """
        self.callback.on_progress(-1, "清理 TXT 文件...")
        
        txt_patterns = [
            "cell_*.txt",
            "error_*.txt",
            "diffraction.txt",
        ]
        
        import glob
        for pattern in txt_patterns:
            full_pattern = os.path.join(self.workdir, pattern)
            for file in glob.glob(full_pattern):
                try:
                    os.remove(file)
                    print(f"  删除: {file}")
                except Exception as e:
                    print(f"  删除失败: {file} - {e}")
    
    def initialize_population(self) -> None:
        """初始化种群 / Initialize population
        
        生成初始随机种群，写入 cell_0.txt。
        Generates initial random population, writes to cell_0.txt.
        
        目前调用 Fortran 程序实现 / Currently calls Fortran program.
        """
        # 方法1：使用 Python 类 / Method 1: Use Python class
        # self.population.initialize_random()
        # self.population.save_to_file("cell_0.txt")
        
        # 方法2：调用 Fortran 程序 / Method 2: Call Fortran program
        self.fortran_caller.run_initialization(self.input_file)
    
    def run_optimization_step(self, step: int) -> None:
        """运行优化步骤 / Run optimization step
        
        调用 Fortran 程序 single_polymcrystindex 对晶胞参数进行优化。
        Calls Fortran program single_polymcrystindex to optimize cell parameters.
        
        Args:
            step: 步骤编号 / Step number
        """
        self.fortran_caller.run_optimization(
            self.input_file, self.diffraction_file, step
        )
    
    def run_sorting_step(self, step: int) -> None:
        """运行排序步骤 / Run sorting step
        
        调用 Fortran 程序 FiberDiffractionSort 对晶胞进行排序，
        根据衍射数据匹配程度选择最优个体，生成下一代。
        Calls Fortran program FiberDiffractionSort to sort cells and 
        generate next generation based on diffraction matching.
        
        Args:
            step: 步骤编号 / Step number
        """
        annealing_file = f"cell_{step}_annealing.txt"
        annealing_path = os.path.join(os.path.dirname(os.path.abspath(self.input_file)), annealing_file)
        
        if self.file_manager.file_exists(annealing_path):
            self.fortran_caller.run_sorting(
                self.input_file, annealing_path, step + 1, self.diffraction_file
            )
    
    def archive_files(self, step: int) -> None:
        """归档文件 / Archive files
        
        将完成的 cell 文件移动到 result/ 目录。
        Moves completed cell files to result/ directory.
        
        Args:
            step: 步骤编号 / Step number
        """
        self.file_manager.cleanup_old_files(step, self.config.layer_mode, self.workdir, self.result_dir)
        
        if step == self.config.generation_steps - 1:
            self.file_manager.cleanup_final_files(step, self.config.layer_mode, self.workdir, self.result_dir)
    
    def get_config_summary(self) -> str:
        """获取配置摘要 / Get configuration summary
        
        Returns:
            格式化的配置摘要字符串 / Formatted configuration summary string
        """
        params = self.config.get_all_parameters()
        
        summary = "=== Fiber Diffraction Indexing Configuration ===\n"
        summary += f"Population Size:    {params['population_size']}\n"
        summary += f"Generation Steps:   {params['generation_steps']}\n"
        summary += f"Survival Rate:      {params['survival_rate']}\n"
        summary += f"Crossover Rate:     {params['crossover_rate']}\n"
        summary += f"Mutation Rate:      {params['mutation_rate']}\n"
        summary += f"C-axis:             {params['c_axis']}\n"
        summary += f"Layer Mode:         {params['layer_mode']}\n"
        summary += f"Tilt Status:        {params['tilt_status']}\n"
        summary += f"OMP Threads:        {params['omp_threads']}\n"
        summary += f"Parameter Min:      {params['parameter_min']}\n"
        summary += f"Parameter Max:      {params['parameter_max']}\n"
        summary += f"HDF5 Mode:          {self.use_hdf5}\n"
        
        return summary
