"""
Fiber Diffraction Indexing 包
=============================

用于纤维衍射图案自动索引的全局优化方法。

架构：
    - InputConfig: 输入配置类
    - PopulationManager: 种群管理类
    - GeneticEngine: 遗传算法类
    - FortranCaller: Fortran调用类
    - FileManager: 文件操作类
    - FiberDiffractionIndexer: 主协调器类
    - HDF5Manager: HDF5 文件管理类
    - Plotter: 绘图类
    - IndexingCallback: 回调接口类

用法示例：
    # 命令行
    python -m fiberdiffraction -i input.txt -d diffraction.txt
    
    # Python API - 基本流程
    from fiberdiffraction import FiberDiffractionIndexer
    
    indexer = FiberDiffractionIndexer("input.txt", "diffraction.txt")
    indexer.run()
    
    # Python API - HDF5 模式
    indexer = FiberDiffractionIndexer("input.txt", "diffraction.txt",
                                      use_hdf5=True, hdf5_file="results.h5")
    indexer.run()
    
    # Python API - GUI 回调
    from fiberdiffraction import IndexingCallback, FiberDiffractionIndexer
    
    class MyGUI(IndexingCallback):
        def on_progress(self, step, message):
            # 更新 GUI 进度条
            pass
    
    indexer = FiberDiffractionIndexer("input.txt", "diffraction.txt", callback=MyGUI())
    indexer.run()
    
    # Python API - 单独使用配置
    from fiberdiffraction import InputConfig
    
    config = InputConfig("input.txt")
    print(config.population_size)
    print(config.parameter_min)
    
    # Python API - 绘图
    from fiberdiffraction import HDF5Manager, Plotter
    
    hdf5 = HDF5Manager("results.h5", mode='r')
    plotter = Plotter(hdf5)
    plotter.plot_timing()
    plotter.plot_convergence()
    hdf5.close()
"""

__version__ = "1.7.0"
__author__ = "POLYCRYSTINDEX Team"
__email__ = "polycrystindex@example.com"
__license__ = "MIT"

# 导入核心类
from .config import InputConfig
from .population import PopulationManager
from .genetic import GeneticEngine
from .fortran import FortranCaller
from .fileio import FileManager
from .indexer import FiberDiffractionIndexer
from .callbacks import IndexingCallback, DefaultCallback, SilentCallback, CallbackAdapter
from .hdf5 import HDF5Manager
from .plotter import Plotter
from .cli import main

__all__ = [
    # 核心类
    "InputConfig",
    "PopulationManager",
    "GeneticEngine",
    "FortranCaller",
    "FileManager",
    "FiberDiffractionIndexer",
    
    # 回调接口
    "IndexingCallback",
    "DefaultCallback",
    "SilentCallback",
    "CallbackAdapter",
    
    # HDF5
    "HDF5Manager",
    
    # 绘图
    "Plotter",
    
    # CLI
    "main",
]
