"""
HDF5 管理类 / HDF5 Manager
======================

该模块提供 HDF5Manager 类，用于管理 HDF5 文件的读写操作。

HDF5 文件结构：
    results.h5
    ├── config/                  # 配置参数
    │   └── (各种参数)
    ├── populations/             # 各代种群
    │   ├── step_0              # 第 0 代种群
    │   ├── step_1              # 第 1 代种群
    │   └── ...
    ├── convergence/             # 收敛数据
    │   ├── best_errors         # 各步最佳误差
    │   └── best_cells          # 各步最佳晶胞
    ├── timing/                  # 时间记录
    │   ├── step_times          # 各步耗时
    │   └── total_time          # 总耗时
    └── metadata/                # 元数据
        ├── created_at          # 创建时间
        └── version             # 版本号

用法 / Usage:
    from fiberdiffraction import HDF5Manager

    # 写入模式 / Write mode
    hdf5 = HDF5Manager("results.h5", mode='w')
    hdf5.write_population(step=0, cells=[[1,2,3,4,5,6]])
    hdf5.close()

    # 读取模式 / Read mode
    hdf5 = HDF5Manager("results.h5", mode='r')
    cells = hdf5.read_population(0)
    hdf5.close()
"""

import os
import h5py
import numpy as np
from typing import List, Optional, Dict, Any, cast
from datetime import datetime


class HDF5Manager:
    """HDF5 文件管理器 / HDF5 File Manager

    负责将所有数据写入 HDF5 文件，支持追加和覆盖模式。
    Responsible for writing all data to HDF5 file, supports append and overwrite modes.

    属性 / Attributes:
        filename: HDF5 文件路径 / HDF5 file path
        mode: 文件打开模式 / File open mode
        h5file: HDF5 文件对象 / HDF5 file object
    """

    def __init__(self, filename: str, mode: str = "a"):
        """初始化 HDF5 管理器 / Initialize HDF5 manager

        Args:
            filename: HDF5 文件路径 / HDF5 file path
            mode: 文件模式 / File mode ('r'=read, 'w'=write, 'a'=append)
        """
        self.filename = filename
        self.mode = mode
        self.h5file: Optional[h5py.File] = None
        self._open()

    def _open(self) -> None:
        """打开 HDF5 文件 / Open HDF5 file"""
        self.h5file = h5py.File(self.filename, self.mode)

    def close(self) -> None:
        """关闭 HDF5 文件 / Close HDF5 file"""
        if self.h5file:
            self.h5file.close()
            self.h5file = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _ensure_group(self, path: str) -> h5py.Group:
        """确保组存在，不存在则创建 / Ensure group exists, create if not

        Args:
            path: 组路径 / Group path

        Returns:
            HDF5 组对象 / HDF5 group object
        """
        assert self.h5file is not None
        if path in self.h5file:
            return cast(h5py.Group, self.h5file[path])
        return self.h5file.create_group(path)

    def _normalize_plot_image_name(self, name: str) -> str:
        """规范化 PNG 名称 / Normalize PNG image name"""
        normalized = name.strip().lower()
        if normalized.endswith(".png"):
            normalized = normalized[:-4]
        if normalized == "timming":
            return "timing"
        return normalized

    def write_config(self, config_dict: Dict[str, Any]) -> None:
        """写入配置参数 / Write configuration parameters

        Args:
            config_dict: 配置参数字典 / Configuration dictionary
        """
        grp = self._ensure_group("config")

        for key, value in config_dict.items():
            if key in grp:
                del grp[key]

            if isinstance(value, list):
                grp.create_dataset(key, data=np.array(value))
            elif isinstance(value, (int, float)):
                grp.attrs[key] = value
            else:
                grp.attrs[key] = str(value)

    def write_population(
        self,
        step: int,
        cells: List[List[float]],
        tilt_angles: Optional[List[float]] = None,
    ) -> None:
        """写入种群数据 / Write population data

        Args:
            step: 步骤编号 / Step number
            cells: 晶胞参数列表 / Cell parameter list
            tilt_angles: 倾斜角度列表（可选）/ Tilt angle list (optional)
        """
        grp = self._ensure_group("populations")
        dataset_name = f"step_{step}"

        if dataset_name in grp:
            del grp[dataset_name]

        data = np.array(cells)
        grp.create_dataset(dataset_name, data=data)

        if tilt_angles:
            grp[f"{dataset_name}"].attrs["tilt_angles"] = np.array(tilt_angles)

    def append_population(
        self, step: int, cell: List[float], tilt_angle: Optional[float] = None
    ) -> None:
        """追加单个晶胞到种群数据 / Append single cell to population

        Args:
            step: 步骤编号 / Step number
            cell: 晶胞参数 / Cell parameters
            tilt_angle: 倾斜角度（可选）/ Tilt angle (optional)
        """
        grp = self._ensure_group("populations")
        dataset_name = f"step_{step}"

        if dataset_name not in grp:
            data = np.array([cell])
            grp.create_dataset(dataset_name, data=data, maxshape=(None, len(cell)))
        else:
            ds = cast(h5py.Dataset, grp[dataset_name])
            ds.resize(ds.shape[0] + 1, axis=0)
            ds[-1] = cell

        if tilt_angle is not None:
            grp[f"{dataset_name}"].attrs["tilt_angles"] = np.append(
                grp[f"{dataset_name}"].attrs.get("tilt_angles", []), tilt_angle
            )

    def write_diffraction(self, data: List[List[float]]) -> None:
        """写入衍射数据 / Write diffraction data

        Args:
            data: 衍射数据列表 / Diffraction data list
        """
        grp = self._ensure_group("diffraction")

        if "data" in grp:
            del grp["data"]

        grp.create_dataset("data", data=np.array(data))

    def write_timing(self, step: int, elapsed: float) -> None:
        """写入时间记录 / Write timing record

        Args:
            step: 步骤编号 / Step number
            elapsed: 步骤耗时（秒）/ Step elapsed time (seconds)
        """
        grp = self._ensure_group("timing")

        if "step_times" not in grp:
            grp.create_dataset("step_times", data=[elapsed], maxshape=(None,))
        else:
            ds = cast(h5py.Dataset, grp["step_times"])
            ds.resize(ds.shape[0] + 1, axis=0)
            ds[-1] = elapsed

    def write_total_time(self, total_time: float) -> None:
        """写入总耗时 / Write total time

        Args:
            total_time: 总耗时（秒）/ Total time (seconds)
        """
        grp = self._ensure_group("timing")
        grp.attrs["total_time"] = total_time

    def write_convergence(
        self, step: int, best_error: float, best_cell: List[float]
    ) -> None:
        """写入收敛数据 / Write convergence data

        Args:
            step: 步骤编号 / Step number
            best_error: 最佳误差 / Best error
            best_cell: 最佳晶胞参数 / Best cell parameters
        """
        grp = self._ensure_group("convergence")

        # 写入最佳误差 / Write best error
        if "best_errors" not in grp:
            grp.create_dataset("best_errors", data=[best_error], maxshape=(None,))
        else:
            ds = cast(h5py.Dataset, grp["best_errors"])
            ds.resize(ds.shape[0] + 1, axis=0)
            ds[-1] = best_error

        # 写入最佳晶胞 / Write best cell
        if "best_cells" not in grp:
            grp.create_dataset(
                "best_cells", data=[best_cell], maxshape=(None, len(best_cell))
            )
        else:
            ds = cast(h5py.Dataset, grp["best_cells"])
            ds.resize(ds.shape[0] + 1, axis=0)
            ds[-1] = best_cell

    def write_metadata(self, version: str = "1.8.0") -> None:
        """写入元数据 / Write metadata

        Args:
            version: 版本号 / Version
        """
        grp = self._ensure_group("metadata")
        grp.attrs["created_at"] = datetime.now().isoformat()
        grp.attrs["version"] = version

    def write_plot_image(
        self,
        name: str,
        image_bytes: bytes,
        filename: Optional[str] = None,
        content_type: str = "image/png",
        aliases: Optional[List[str]] = None,
    ) -> None:
        """写入 PNG 图片 / Write PNG image"""
        grp = self._ensure_group("images")
        dataset_name = self._normalize_plot_image_name(name)

        if dataset_name in grp:
            del grp[dataset_name]

        dataset = grp.create_dataset(
            dataset_name, data=np.frombuffer(image_bytes, dtype=np.uint8)
        )
        dataset.attrs["filename"] = filename or f"{dataset_name}.png"
        dataset.attrs["content_type"] = content_type
        if aliases:
            dataset.attrs["aliases"] = np.array(aliases, dtype="S")

    def read_plot_image(self, name: str) -> Optional[bytes]:
        """读取 PNG 图片字节 / Read PNG image bytes"""
        grp = self._ensure_group("images")
        dataset_name = self._normalize_plot_image_name(name)
        if dataset_name not in grp:
            return None
        dataset = cast(h5py.Dataset, grp[dataset_name])
        return bytes(dataset[:])

    def list_plot_images(self) -> Dict[str, Dict[str, Any]]:
        """列出已收录 PNG / List stored PNG artifacts"""
        grp = self._ensure_group("images")
        images: Dict[str, Dict[str, Any]] = {}

        for name in grp.keys():
            dataset = cast(h5py.Dataset, grp[name])
            aliases = dataset.attrs.get("aliases", [])
            images[name] = {
                "filename": dataset.attrs.get("filename", f"{name}.png"),
                "content_type": dataset.attrs.get("content_type", "image/png"),
                "size": int(dataset.shape[0]),
                "aliases": [
                    alias.decode("utf-8") if isinstance(alias, bytes) else str(alias)
                    for alias in aliases
                ],
            }

        return images

    def read_population(self, step: int) -> Optional[np.ndarray]:
        """读取种群数据 / Read population data

        Args:
            step: 步骤编号 / Step number

        Returns:
            晶胞参数数组，不存在返回 None / Cell parameter array or None
        """
        grp = self._ensure_group("populations")
        dataset_name = f"step_{step}"

        if dataset_name in grp:
            dataset = cast(h5py.Dataset, grp[dataset_name])
            return dataset[:]
        return None

    def read_config(self) -> Dict[str, Any]:
        """读取配置参数 / Read configuration

        Returns:
            配置参数字典 / Configuration dictionary
        """
        grp = self._ensure_group("config")
        config = {}

        for key in grp.attrs:
            config[key] = grp.attrs[key]

        for key in grp.keys():
            dataset = grp[key]
            if isinstance(dataset, h5py.Dataset):
                config[key] = dataset[:]

        return config

    def read_convergence(self) -> Dict[str, np.ndarray]:
        """读取收敛数据 / Read convergence data

        Returns:
            包含 best_errors 和 best_cells 的字典 / Dict with best_errors and best_cells
        """
        grp = self._ensure_group("convergence")
        result = {}

        if "best_errors" in grp:
            result["best_errors"] = cast(h5py.Dataset, grp["best_errors"])[:]

        if "best_cells" in grp:
            result["best_cells"] = cast(h5py.Dataset, grp["best_cells"])[:]

        return result

    def read_timing(self) -> Dict[str, Any]:
        """读取时间记录 / Read timing records

        Returns:
            包含 step_times 和 total_time 的字典 / Dict with step_times and total_time
        """
        grp = self._ensure_group("timing")
        result = {}

        if "step_times" in grp:
            result["step_times"] = cast(h5py.Dataset, grp["step_times"])[:]

        if "total_time" in grp.attrs:
            result["total_time"] = grp.attrs["total_time"]

        return result

    def list_steps(self) -> List[int]:
        """列出所有步骤编号 / List all step numbers

        Returns:
            步骤编号列表 / Step number list
        """
        grp = self._ensure_group("populations")
        steps = []

        for key in grp.keys():
            key_name = str(key)
            if key_name.startswith("step_"):
                try:
                    step = int(key_name.split("_")[1])
                    steps.append(step)
                except ValueError:
                    pass

        return sorted(steps)

    def exists(self) -> bool:
        """检查文件是否存在 / Check if file exists"""
        return os.path.exists(self.filename)
