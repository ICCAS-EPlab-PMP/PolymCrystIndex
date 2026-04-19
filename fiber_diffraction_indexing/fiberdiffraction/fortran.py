"""
外部程序调用类 / External Program Caller
====================================

该模块提供 FortranCaller 类，用于调用外部程序。

实际工作流程：
    1. 初始化：python initial.py -i input.txt → 生成 cell_0.txt
    2. 优化：single_polymcrystindex.exe -i input.txt -d diffraction.txt -c cell_N.txt
    3. 排序：python sort.py -i input.txt -c cell_N_annealing.txt -n N+1

注意：实际的晶胞优化计算由 Fortran 程序完成！
WARNING: Actual cell optimization is performed by Fortran programs!

用法 / Usage:
    from fiberdiffraction import FortranCaller, InputConfig
    
    config = InputConfig("input.txt")
    caller = FortranCaller(config)
    caller.run_optimization("input.txt", "diffraction.txt", step=0)
"""

import os
import shutil
import sys
import subprocess
import time
import threading
from typing import Optional
from pathlib import Path
from .config import InputConfig


class TaskCancelledException(Exception):
    """Custom exception for task cancellation."""
    pass


class FortranCaller:
    """外部程序调用器 / External Program Caller
    
    负责调用外部程序进行晶胞优化计算。
    Responsible for calling external programs for cell optimization.
    
    工作流程：
        - 初始化：调用 Python 脚本 initial.py
        - 优化：调用 Fortran 可执行文件 single_polymcrystindex
        - 排序：调用 Python 脚本 sort.py
    
    属性 / Attributes:
        config: 输入配置 / Input configuration
        scripts_dir: 脚本目录 / Scripts directory
    """
    
    def __init__(self, config: InputConfig, scripts_dir: Optional[str] = None,
                 workdir: Optional[str] = None):
        """初始化调用器 / Initialize caller
        
        Args:
            config: 输入配置对象 / Input configuration object
            scripts_dir: 脚本目录路径（默认自动检测）/ Scripts directory (auto-detected)
            workdir: 工作目录路径（默认当前目录）/ Working directory path (default: current directory)
        """
        self.config = config
        self.scripts_dir = scripts_dir or self._find_scripts_dir()
        self.exe_dir = self._find_exe_dir()
        self.workdir = workdir or os.getcwd()
        self._current_process: Optional[subprocess.Popen] = None

    def kill_current_process(self) -> None:
        """Kill the currently running subprocess if any."""
        if self._current_process is not None and self._current_process.poll() is None:
            self._current_process.kill()
            self._current_process.wait()
            self._current_process = None
    
    @staticmethod
    def is_windows() -> bool:
        """检查当前平台是否为 Windows / Check if running on Windows"""
        return os.name == 'nt'
    
    def _find_scripts_dir(self) -> str:
        """查找脚本目录 / Find scripts directory
        
        查找包含 initial.py 和 sort.py 的目录。
        Searches for directory containing initial.py and sort.py.
        
        Returns:
            脚本目录路径 / Scripts directory path
        """
        possible_dirs = [
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"),
            os.path.join(os.getcwd(), "scripts"),
            os.getcwd(),
        ]
        
        for d in possible_dirs:
            if os.path.exists(os.path.join(d, "initial.py")) and os.path.exists(os.path.join(d, "sort.py")):
                return d
        
        cwd = os.getcwd()
        if os.path.exists(os.path.join(cwd, "initial.py")):
            return cwd
        
        parent_dir = os.path.dirname(cwd)
        if os.path.exists(os.path.join(parent_dir, "initial.py")):
            return parent_dir
        
        return os.path.dirname(os.path.dirname(__file__))
        
        return cwd
    
    def _find_exe_dir(self) -> str:
        """查找可执行文件目录 / Find executable directory
        
        查找包含 lm_opt2.exe 的目录。
        Searches for directory containing lm_opt2.exe.
        
        Returns:
            可执行文件目录路径 / Executable directory path
        """
        configured_exe = os.getenv("FORTRAN_EXECUTABLE")
        if configured_exe:
            configured_path = Path(configured_exe)
            if configured_path.exists():
                return str(configured_path.parent)

        cwd = os.getcwd()

        exe_name = "lm_opt2.exe" if self.is_windows() else "lm_opt2"
        
        if os.path.exists(os.path.join(cwd, exe_name)):
            return cwd
        
        parent_dir = os.path.dirname(cwd)
        if os.path.exists(os.path.join(parent_dir, exe_name)):
            return parent_dir
        
        fortran_dir = os.path.join(parent_dir, "fortrancode")
        if os.path.exists(os.path.join(fortran_dir, exe_name)):
            return fortran_dir
        
        fortran_dir2 = os.path.join(cwd, "fortrancode")
        if os.path.exists(os.path.join(fortran_dir2, exe_name)):
            return fortran_dir2
        
        return cwd
    
    def _get_exe_path(self) -> str:
        """获取可执行文件路径 / Get executable path"""
        configured_exe = os.getenv("FORTRAN_EXECUTABLE")
        if configured_exe:
            return configured_exe

        if self.is_windows():
            exe_name = "lm_opt2.exe"
        else:
            exe_name = "lm_opt2"
        
        return os.path.join(self.exe_dir, exe_name)
    
    def setup_omp_threads(self) -> None:
        """设置 OpenMP 线程数 / Setup OpenMP thread count
        
        从配置读取 omp_threads 并设置环境变量 OMP_NUM_THREADS。
        Reads omp_threads from config and sets OMP_NUM_THREADS environment variable.
        """
        omp_threads = self.config.omp_threads
        
        if omp_threads > 0:
            os.environ["OMP_NUM_THREADS"] = str(omp_threads)
            print(f"[OpenMP] Setting thread count: {omp_threads}")
        else:
            os.environ.pop("OMP_NUM_THREADS", None)
            print("[OpenMP] Thread count not limited, system will determine")
    
    def run_optimization(self, input_file: str, diffraction_file: str,
                         step: int, stop_event: Optional[threading.Event] = None) -> None:
        """运行单步优化 / Run single optimization step
        
        调用 single_polymcrystindex 程序进行晶胞参数优化。
        这是核心的优化步骤，由 Fortran 程序实际执行计算。
        Calls single_polymcrystindex program to optimize cell parameters.
        This is the core optimization step, computation done by Fortran.
        
        Args:
            input_file: 输入文件路径 / Input file path
            diffraction_file: 衍射数据文件路径 / Diffraction data file path
            step: 当前步骤编号 / Current step number
        """
        exe_path = self._get_exe_path()
        input_file_name = os.path.basename(input_file)
        diffraction_file_name = os.path.basename(diffraction_file)
        cell_file_name = f"cell_{step}.txt"
        cell_file = os.path.join(self.workdir, cell_file_name)
        error_file = os.path.join(self.workdir, f"error_{step}.txt")
        fortran_error_file = os.path.join(self.workdir, "diffraction.txt")

        for required_path in (input_file, diffraction_file, cell_file):
            if not os.path.exists(required_path):
                raise FileNotFoundError(required_path)

        if not os.path.exists(exe_path):
            raise FileNotFoundError(f"Fortran executable not found: {exe_path}")
        
        cmd = [
            exe_path,
            "-i", input_file_name,
            "-d", diffraction_file_name,
            "-c", cell_file_name
        ]
        
        print(f"[Fortran] Running optimization step {step}...")
        
        process = subprocess.Popen(cmd, cwd=self.workdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self._current_process = process
        try:
            while process.poll() is None:
                if stop_event and stop_event.is_set():
                    process.kill()
                    process.wait()
                    raise TaskCancelledException("Task cancelled during subprocess execution")
                time.sleep(0.1)
            stdout, stderr = process.communicate()
        finally:
            self._current_process = None
        returncode = process.returncode
        
        if returncode != 0:
            stderr_msg = stderr.strip() if stderr else ""
            raise RuntimeError(
                f"Fortran optimization step {step} failed with code {returncode}: {stderr_msg}"
            )

        if not os.path.exists(fortran_error_file):
            raise FileNotFoundError(fortran_error_file)

        shutil.copyfile(fortran_error_file, error_file)

        annealing_file = os.path.join(self.workdir, f"cell_{step}_annealing.txt")
        if not os.path.exists(annealing_file):
            raise FileNotFoundError(annealing_file)
    
    def run_initialization(self, input_file: str, stop_event: Optional[threading.Event] = None) -> None:
        """运行初始化程序 / Run initialization program
        
        调用 Python 脚本 initial.py 生成初始随机种群 cell_0.txt。
        Calls Python script initial.py to generate initial random population cell_0.txt.
        
        Args:
            input_file: 输入文件路径 / Input file path
        """
        script_path = os.path.join(self.scripts_dir, "initial.py")
        
        input_file_abs = os.path.abspath(input_file)
        
        cmd = [sys.executable, script_path, "-i", input_file_abs]
        
        print(f"[Init] Running initialization...")
        
        process = subprocess.Popen(cmd, cwd=self.workdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self._current_process = process
        try:
            while process.poll() is None:
                if stop_event and stop_event.is_set():
                    process.kill()
                    process.wait()
                    raise TaskCancelledException("Task cancelled during subprocess execution")
                time.sleep(0.1)
            stdout, stderr = process.communicate()
        finally:
            self._current_process = None
        returncode = process.returncode
        
        if returncode != 0:
            stderr_msg = stderr.strip() if stderr else ""
            raise RuntimeError(
                f"Initialization failed with code {returncode}: {stderr_msg}"
            )

        init_cell = os.path.join(self.workdir, "cell_0.txt")
        if not os.path.exists(init_cell):
            raise FileNotFoundError(init_cell)
    
    def run_sorting(self, input_file: str, cell_file: str,
                   generation: int, diffraction_file: str, stop_event: Optional[threading.Event] = None) -> None:
        """运行排序程序 / Run sorting program
        
        调用 Python 脚本 sort.py 根据衍射数据对晶胞进行排序，
        并使用遗传算法生成下一代种群。
        Calls Python script sort.py to sort cells based on diffraction data
        and generate next generation using genetic algorithm.
        
        Args:
            input_file: 输入文件路径 / Input file path
            cell_file: 晶胞参数文件路径 / Cell parameter file path
            generation: 代数编号 / Generation number
            diffraction_file: 衍射数据文件路径 (not used anymore, kept for compatibility)
        """
        script_path = os.path.join(self.scripts_dir, "sort.py")
        
        input_file_abs = os.path.abspath(input_file)
        cell_file_abs = os.path.abspath(cell_file)
        diffraction_file_abs = os.path.abspath(diffraction_file)
        
        cmd = [
            sys.executable,
            script_path,
            "-i", input_file_abs,
            "-c", cell_file_abs,
            "-d", diffraction_file_abs,
            "-n", str(generation)
        ]
        
        print(f"[Sort] Running sorting for generation {generation}...")
        
        process = subprocess.Popen(cmd, cwd=self.workdir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self._current_process = process
        try:
            while process.poll() is None:
                if stop_event and stop_event.is_set():
                    process.kill()
                    process.wait()
                    raise TaskCancelledException("Task cancelled during subprocess execution")
                time.sleep(0.1)
            stdout, stderr = process.communicate()
        finally:
            self._current_process = None
        returncode = process.returncode
        
        if returncode != 0:
            stderr_msg = stderr.strip() if stderr else ""
            raise RuntimeError(
                f"Sorting for generation {generation} failed with code {returncode}: {stderr_msg}"
            )

        next_cell = os.path.join(self.workdir, f"cell_{generation}.txt")
        if not os.path.exists(next_cell):
            raise FileNotFoundError(next_cell)
