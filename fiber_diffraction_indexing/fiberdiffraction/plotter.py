"""
绘图模块 / Plotting Module
======================

该模块提供 Plotter 类，用于绘制默认结果图表。

生成的图表：
    1. 时间曲线 (timing.png) - 显示每步耗时
    2. 收敛曲线 (convergence.png) - 显示 GA 收敛过程

用法 / Usage:
    from fiberdiffraction import HDF5Manager, Plotter

    hdf5 = HDF5Manager("results.h5", mode='r')
    plotter = Plotter(hdf5)

    # 绘制单个图表 / Plot single chart
    plotter.plot_timing(save_path="result/timing.png")

    # 保存默认结果图表 / Save default result plots
    plotter.save_all("result/")

    hdf5.close()
"""

import io
import os
from typing import Dict, Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from .hdf5 import HDF5Manager


class Plotter:
    """结果绘图器 / Results Plotter"""

    def __init__(self, hdf5: HDF5Manager):
        """初始化绘图器 / Initialize plotter"""
        self.hdf5 = hdf5

    def _figure_to_png_bytes(self, fig: Figure) -> bytes:
        """将图表编码为 PNG 字节 / Encode figure as PNG bytes"""
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
        return buffer.getvalue()

    def plot_timing(
        self, save_path: Optional[str] = None, show: bool = True
    ) -> Optional[Figure]:
        """绘制时间曲线 / Plot timing curve"""
        timing = self.hdf5.read_timing()

        if not timing or "step_times" not in timing:
            print("Warning: No timing data available")
            return None

        step_times = timing["step_times"]
        steps = np.arange(len(step_times))

        fig, ax = plt.subplots(figsize=(10, 6))
        bars = ax.bar(steps, step_times, color="steelblue", alpha=0.8)

        for bar, time_val in zip(bars, step_times):
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                bar.get_height(),
                f"{time_val:.1f}s",
                ha="center",
                va="bottom",
                fontsize=9,
            )

        ax.set_xlabel("Step", fontsize=12)
        ax.set_ylabel("Time (seconds)", fontsize=12)
        ax.set_title("Execution Time per Step", fontsize=14, fontweight="bold")
        ax.set_xticks(steps)
        ax.set_xticklabels([f"Step {i}" for i in steps])
        ax.grid(axis="y", alpha=0.3)

        if "total_time" in timing:
            total = timing["total_time"]
            ax.text(
                0.98,
                0.95,
                f"Total: {total:.2f}s",
                transform=ax.transAxes,
                ha="right",
                va="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
            )

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Timing plot saved to: {save_path}")

        if show:
            plt.show()

        return fig

    def plot_convergence(
        self, save_path: Optional[str] = None, show: bool = True
    ) -> Optional[Figure]:
        """绘制 GA 收敛曲线 / Plot GA convergence curve"""
        convergence = self.hdf5.read_convergence()

        if not convergence or "best_errors" not in convergence:
            print("Warning: No convergence data available")
            return None

        best_errors = convergence["best_errors"]
        steps = np.arange(len(best_errors))

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(
            steps,
            best_errors,
            "o-",
            color="darkgreen",
            linewidth=2,
            markersize=8,
            label="Best Error",
        )
        ax.fill_between(steps, best_errors, alpha=0.2, color="green")

        ax.set_xlabel("Step", fontsize=12)
        ax.set_ylabel("Error", fontsize=12)
        ax.set_title("GA Convergence Curve", fontsize=14, fontweight="bold")
        ax.set_xticks(steps)
        ax.set_xticklabels([f"Step {i}" for i in steps])
        ax.grid(True, alpha=0.3)
        ax.legend()

        best_idx = np.argmin(best_errors)
        best_val = best_errors[best_idx]
        ax.annotate(
            f"Best: {best_val:.4f}\n(Step {best_idx})",
            xy=(best_idx, best_val),
            xytext=(
                best_idx + 0.5,
                best_val + (max(best_errors) - best_val) * 0.3,
            ),
            arrowprops=dict(arrowstyle="->", color="red"),
            fontsize=10,
            color="red",
        )

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches="tight")
            print(f"Convergence plot saved to: {save_path}")

        if show:
            plt.show()

        return fig

    def save_all(self, output_dir: Optional[str] = None) -> Dict[str, str]:
        """保存默认结果 PNG 并收录进 HDF5 / Save default PNGs and store them in HDF5"""
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        saved_paths: Dict[str, str] = {}
        plot_specs = [
            ("timing", "timing.png", ["timming", "timming.png"], self.plot_timing),
            ("convergence", "convergence.png", [], self.plot_convergence),
        ]

        for name, filename, aliases, renderer in plot_specs:
            save_path = os.path.join(output_dir, filename) if output_dir else None
            fig = renderer(save_path=save_path, show=False)
            if fig is None:
                continue

            self.hdf5.write_plot_image(
                name,
                self._figure_to_png_bytes(fig),
                filename=filename,
                aliases=aliases,
            )
            plt.close(fig)
            saved_paths[name] = save_path or f"hdf5:/images/{name}"

        if output_dir:
            print(f"Default plots saved to: {output_dir}/")
        else:
            print("Default plots saved to HDF5")

        return saved_paths
