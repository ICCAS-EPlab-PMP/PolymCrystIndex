"""
文件操作类 / File Operations
=========================

该模块提供 FileManager 类，用于管理文件操作。

用法 / Usage:
    from fiberdiffraction import FileManager
    
    fm = FileManager()
    fm.ensure_directory(os.path.join(workdir, "result"))
    fm.move_file(os.path.join(workdir, "cell_0.txt"), os.path.join(workdir, "result"))
"""

import os
import shutil
from pathlib import Path
from typing import Optional


class FileManager:
    """文件操作管理器 / File Operations Manager
    
    负责文件的移动、复制、清理等操作。
    Responsible for file operations: move, copy, cleanup, etc.
    """
    
    @staticmethod
    def ensure_directory(path: str) -> None:
        """确保目录存在，不存在则创建 / Ensure directory exists, create if not
        
        Args:
            path: 要创建的目录路径 / Directory path to create
        """
        Path(path).mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def move_file(source: str, dest_dir: str) -> bool:
        """将文件移动到目标目录 / Move file to destination directory
        
        Args:
            source: 源文件路径 / Source file path
            dest_dir: 目标目录路径 / Destination directory path
            
        Returns:
            成功返回 True，否则返回 False / Returns True on success, False otherwise
        """
        try:
            if os.path.exists(source):
                shutil.move(source, dest_dir)
                return True
            return False
        except Exception as e:
            print(f"Warning: Failed to move {source} to {dest_dir}: {e}")
            return False
    
    @staticmethod
    def copy_file(source: str, dest_dir: str) -> bool:
        """将文件复制到目标目录 / Copy file to destination directory
        
        Args:
            source: 源文件路径 / Source file path
            dest_dir: 目标目录路径 / Destination directory path
            
        Returns:
            成功返回 True，否则返回 False / Returns True on success, False otherwise
        """
        try:
            if os.path.exists(source):
                shutil.copy(source, dest_dir)
                return True
            return False
        except Exception as e:
            print(f"Warning: Failed to copy {source} to {dest_dir}: {e}")
            return False
    
    @staticmethod
    def file_exists(path: str) -> bool:
        """检查文件是否存在 / Check if file exists
        
        Args:
            path: 要检查的文件路径 / File path to check
            
        Returns:
            文件存在返回 True / Returns True if file exists
        """
        return os.path.exists(path)
    
    @staticmethod
    def cleanup_old_files(step: int, layer_mode: int, workdir: str, result_dir: str) -> None:
        """归档上一步生成的文件 / Archive files from previous step
        
        将上一代的 cell 文件和 annealing 文件移动到 result/ 目录。
        Moves previous generation cell and annealing files to result/ directory.
        
        Args:
            step: 当前步骤编号 / Current step number
            layer_mode: 层模式标志（非零 = 启用）/ Layer mode flag (non-zero = enabled)
            workdir: 工作目录路径 / Work directory path
            result_dir: 结果目录路径 / Result directory path
        """
        if step > 0:
            prev_cell = os.path.join(workdir, f"cell_{step - 1}.txt")
            if os.path.exists(prev_cell):
                FileManager.move_file(prev_cell, result_dir)
            
            if layer_mode != 0:
                prev_annealing = os.path.join(workdir, f"cell_{step - 1}_annealing.txt")
                if os.path.exists(prev_annealing):
                    FileManager.move_file(prev_annealing, result_dir)
    
    @staticmethod
    def cleanup_final_files(step: int, layer_mode: int, workdir: str, result_dir: str) -> None:
        """在处理结束时归档文件 / Archive files at end of processing
        
        将最后一代的文件和下一代的文件移动/复制到 result/ 目录。
        Moves/copies final generation files to result/ directory.
        
        Args:
            step: 最终步骤编号 / Final step number
            layer_mode: 层模式标志（非零 = 启用）/ Layer mode flag (non-zero = enabled)
            workdir: 工作目录路径 / Work directory path
            result_dir: 结果目录路径 / Result directory path
        """
        final_cell = os.path.join(workdir, f"cell_{step}.txt")
        if os.path.exists(final_cell):
            FileManager.move_file(final_cell, result_dir)
        
        if layer_mode != 0:
            final_annealing = os.path.join(workdir, f"cell_{step}_annealing.txt")
            if os.path.exists(final_annealing):
                FileManager.move_file(final_annealing, result_dir)
        
        next_cell = os.path.join(workdir, f"cell_{step + 1}.txt")
        if os.path.exists(next_cell):
            FileManager.copy_file(next_cell, result_dir)
