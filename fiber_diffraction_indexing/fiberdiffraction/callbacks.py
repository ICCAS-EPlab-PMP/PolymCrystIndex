"""
输出接口模块 / Output Callback Interface
=====================================

该模块提供 IndexingCallback 类，用于向 GUI 或其他消费者发送状态更新信号。

回调接口用于解耦主流程和 UI，允许：
1. GUI 实时显示进度
2. 记录日志
3. 其他消费者订阅状态变化

用法 / Usage:
    # 继承方式 / Inheritance method
    from fiberdiffraction import IndexingCallback, FiberDiffractionIndexer
    
    class MyGUI(IndexingCallback):
        def on_progress(self, step, message):
            print(f"进度: {message}")
    
    indexer = FiberDiffractionIndexer("input.txt", "diffraction.txt", callback=MyGUI())
    indexer.run()
    
    # 函数式方式 / Function method
    from fiberdiffraction import CallbackAdapter
    
    adapter = CallbackAdapter(
        on_progress=lambda s, m: print(f"[{s}] {m}")
    )
"""

from typing import Optional, Callable
from abc import ABC, abstractmethod


class IndexingCallback(ABC):
    """索引过程的回调接口 / Indexing Callback Interface
    
    GUI 或其他消费者可以继承此类来接收状态更新。
    GUI or other consumers can inherit this class to receive status updates.
    """
    
    @abstractmethod
    def on_step_start(self, step: int, total: int) -> None:
        """步骤开始时调用 / Called when step starts
        
        Args:
            step: 当前步骤编号（从 0 开始）/ Current step number (starting from 0)
            total: 总步骤数 / Total number of steps
        """
        pass
    
    @abstractmethod
    def on_step_end(self, step: int, total: int, elapsed: float) -> None:
        """步骤结束时调用 / Called when step ends
        
        Args:
            step: 当前步骤编号 / Current step number
            total: 总步骤数 / Total number of steps
            elapsed: 步骤耗时（秒）/ Step elapsed time (seconds)
        """
        pass
    
    @abstractmethod
    def on_progress(self, step: int, message: str) -> None:
        """进度更新时调用 / Called on progress update
        
        Args:
            step: 当前步骤编号 / Current step number
            message: 进度消息 / Progress message
        """
        pass
    
    @abstractmethod
    def on_error(self, step: int, error: Exception) -> None:
        """发生错误时调用 / Called on error
        
        Args:
            step: 当前步骤编号（-1 表示全局错误）/ Current step number (-1 for global errors)
            error: 错误对象 / Error object
        """
        pass
    
    @abstractmethod
    def on_complete(self, total_time: float, results: dict) -> None:
        """全部完成时调用 / Called on completion
        
        Args:
            total_time: 总耗时（秒）/ Total time (seconds)
            results: 结果字典，包含 total_time, hdf5_file 等 / Results dict
        """
        pass


class DefaultCallback(IndexingCallback):
    """默认回调实现 / Default Callback Implementation
    
    输出到控制台 / Outputs to console.
    """
    
    def on_step_start(self, step: int, total: int) -> None:
        print(f"\n=== 步骤 {step + 1}/{total} 开始 ===")
    
    def on_step_end(self, step: int, total: int, elapsed: float) -> None:
        print(f"=== 步骤 {step + 1}/{total} 完成，耗时 {elapsed:.2f}秒 ===")
    
    def on_progress(self, step: int, message: str) -> None:
        print(f"[步骤 {step + 1}] {message}")
    
    def on_error(self, step: int, error: Exception) -> None:
        print(f"[错误] 步骤 {step + 1}: {error}")
    
    def on_complete(self, total_time: float, results: dict) -> None:
        print(f"\n=== 全部完成，总耗时 {total_time:.2f}秒 ===")


class SilentCallback(IndexingCallback):
    """静默回调 / Silent Callback
    
    不输出任何信息 / Outputs nothing.
    """
    
    def on_step_start(self, step: int, total: int) -> None:
        pass
    
    def on_step_end(self, step: int, total: int, elapsed: float) -> None:
        pass
    
    def on_progress(self, step: int, message: str) -> None:
        pass
    
    def on_error(self, step: int, error: Exception) -> None:
        pass
    
    def on_complete(self, total_time: float, results: dict) -> None:
        pass


class CallbackAdapter:
    """回调适配器 / Callback Adapter
    
    支持使用函数作为回调，而不是必须继承类。
    Supports using functions as callbacks instead of inheriting class.
    
    用法 / Usage:
        adapter = CallbackAdapter(
            on_step_start=lambda s, t: print(f"开始 {s + 1}/{t}"),
            on_progress=lambda s, m: print(f"进度: {m}"),
        )
        indexer = FiberDiffractionIndexer("input.txt", "diffraction.txt", callback=adapter)
    """
    
    def __init__(
        self,
        on_step_start: Optional[Callable[[int, int], None]] = None,
        on_step_end: Optional[Callable[[int, int, float], None]] = None,
        on_progress: Optional[Callable[[int, str], None]] = None,
        on_error: Optional[Callable[[int, Exception], None]] = None,
        on_complete: Optional[Callable[[float, dict], None]] = None,
    ):
        """初始化适配器 / Initialize adapter
        
        Args:
            on_step_start: 步骤开始回调 / Step start callback
            on_step_end: 步骤结束回调 / Step end callback
            on_progress: 进度回调 / Progress callback
            on_error: 错误回调 / Error callback
            on_complete: 完成回调 / Complete callback
        """
        self._on_step_start = on_step_start
        self._on_step_end = on_step_end
        self._on_progress = on_progress
        self._on_error = on_error
        self._on_complete = on_complete
    
    def on_step_start(self, step: int, total: int) -> None:
        if self._on_step_start:
            self._on_step_start(step, total)
    
    def on_step_end(self, step: int, total: int, elapsed: float) -> None:
        if self._on_step_end:
            self._on_step_end(step, total, elapsed)
    
    def on_progress(self, step: int, message: str) -> None:
        if self._on_progress:
            self._on_progress(step, message)
    
    def on_error(self, step: int, error: Exception) -> None:
        if self._on_error:
            self._on_error(step, error)
    
    def on_complete(self, total_time: float, results: dict) -> None:
        if self._on_complete:
            self._on_complete(total_time, results)
