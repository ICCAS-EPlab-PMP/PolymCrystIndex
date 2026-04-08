"""
绘图模块 / Plotting Module
======================

该模块提供 Plotter 类，用于绘制各种分析图表。

生成的图表：
    1. 时间曲线 (timing.png) - 显示每步耗时
    2. 收敛曲线 (convergence.png) - 显示 GA 收敛过程
    3. 参数演化 (parameters.png) - 显示最佳参数变化
    4. 种群演化 (population_evolution.png) - 显示种群分布

用法 / Usage:
    from fiberdiffraction import HDF5Manager, Plotter
    
    hdf5 = HDF5Manager("results.h5", mode='r')
    plotter = Plotter(hdf5)
    
    # 绘制单个图表 / Plot single chart
    plotter.plot_timing(save_path="figures/timing.png")
    
    # 保存所有图表 / Save all plots
    plotter.save_all("figures/")
    
    hdf5.close()
"""

import os
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional, List, Dict, Any
from .hdf5 import HDF5Manager


class Plotter:
    """结果绘图器 / Results Plotter
    
    从 HDF5 文件读取数据并绘制分析图表。
    Reads data from HDF5 file and plots analysis charts.
    
    属性 / Attributes:
        hdf5: HDF5 管理器 / HDF5 manager
    """
    
    def __init__(self, hdf5: HDF5Manager):
        """初始化绘图器 / Initialize plotter
        
        Args:
            hdf5: HDF5 管理器对象 / HDF5 manager object
        """
        self.hdf5 = hdf5
    
    def plot_timing(self, save_path: Optional[str] = None,
                   show: bool = True) -> Optional[plt.Figure]:
        """绘制时间曲线 / Plot timing curve
        
        显示每一步的耗时分布（柱状图）。
        Displays time consumption for each step (bar chart).
        
        Args:
            save_path: 保存路径（可选）/ Save path (optional)
            show: 是否显示图表 / Whether to show chart
            
        Returns:
            matplotlib Figure 对象，失败返回 None / matplotlib Figure or None
        """
        timing = self.hdf5.read_timing()
        
        if not timing or "step_times" not in timing:
            print("Warning: No timing data available")
            return None
        
        step_times = timing["step_times"]
        steps = np.arange(len(step_times))
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 绘制柱状图 / Draw bar chart
        bars = ax.bar(steps, step_times, color='steelblue', alpha=0.8)
        
        # 添加数值标签 / Add value labels
        for bar, time_val in zip(bars, step_times):
            ax.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                   f'{time_val:.1f}s',
                   ha='center', va='bottom', fontsize=9)
        
        # 设置图表属性 / Set chart properties
        ax.set_xlabel('Step', fontsize=12)
        ax.set_ylabel('Time (seconds)', fontsize=12)
        ax.set_title('Execution Time per Step', fontsize=14, fontweight='bold')
        ax.set_xticks(steps)
        ax.set_xticklabels([f'Step {i}' for i in steps])
        ax.grid(axis='y', alpha=0.3)
        
        # 添加总时间信息 / Add total time info
        if "total_time" in timing:
            total = timing["total_time"]
            ax.text(0.98, 0.95, f'Total: {total:.2f}s',
                   transform=ax.transAxes, ha='right', va='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Timing plot saved to: {save_path}")
        
        if show:
            plt.show()
        
        return fig
    
    def plot_convergence(self, save_path: Optional[str] = None,
                       show: bool = True) -> Optional[plt.Figure]:
        """绘制 GA 收敛曲线 / Plot GA convergence curve
        
        显示误差随代数的变化。
        Displays error changes over generations.
        
        Args:
            save_path: 保存路径（可选）/ Save path (optional)
            show: 是否显示图表 / Whether to show chart
            
        Returns:
            matplotlib Figure 对象，失败返回 None / matplotlib Figure or None
        """
        convergence = self.hdf5.read_convergence()
        
        if not convergence or "best_errors" not in convergence:
            print("Warning: No convergence data available")
            return None
        
        best_errors = convergence["best_errors"]
        steps = np.arange(len(best_errors))
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 绘制收敛曲线 / Draw convergence curve
        ax.plot(steps, best_errors, 'o-', color='darkgreen',
               linewidth=2, markersize=8, label='Best Error')
        
        # 填充区域 / Fill area
        ax.fill_between(steps, best_errors, alpha=0.2, color='green')
        
        # 设置图表属性 / Set chart properties
        ax.set_xlabel('Step', fontsize=12)
        ax.set_ylabel('Error', fontsize=12)
        ax.set_title('GA Convergence Curve', fontsize=14, fontweight='bold')
        ax.set_xticks(steps)
        ax.set_xticklabels([f'Step {i}' for i in steps])
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        # 添加最佳值标注 / Add best value annotation
        best_idx = np.argmin(best_errors)
        best_val = best_errors[best_idx]
        ax.annotate(f'Best: {best_val:.4f}\n(Step {best_idx})',
                   xy=(best_idx, best_val),
                   xytext=(best_idx + 0.5, best_val + (max(best_errors) - best_val) * 0.3),
                   arrowprops=dict(arrowstyle='->', color='red'),
                   fontsize=10, color='red')
        
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Convergence plot saved to: {save_path}")
        
        if show:
            plt.show()
        
        return fig
    
    def plot_parameters(self, save_path: Optional[str] = None,
                      show: bool = True) -> Optional[plt.Figure]:
        """绘制参数演化图 / Plot parameter evolution
        
        显示最佳晶胞参数随步骤的变化。
        Displays best cell parameter changes over steps.
        
        Args:
            save_path: 保存路径（可选）/ Save path (optional)
            show: 是否显示图表 / Whether to show chart
            
        Returns:
            matplotlib Figure 对象，失败返回 None / matplotlib Figure or None
        """
        convergence = self.hdf5.read_convergence()
        
        if not convergence or "best_cells" not in convergence:
            print("Warning: No parameter data available")
            return None
        
        best_cells = convergence["best_cells"]
        steps = np.arange(len(best_cells))
        
        # 参数名称和颜色 / Parameter names and colors
        param_names = ['a', 'b', 'c', 'α', 'β', 'γ']
        colors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#a65628']
        
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()
        
        for i in range(6):
            ax = axes[i]
            param_values = best_cells[:, i]
            
            ax.plot(steps, param_values, 'o-', color=colors[i],
                   linewidth=2, markersize=8)
            ax.fill_between(steps, param_values, alpha=0.2, color=colors[i])
            
            ax.set_xlabel('Step', fontsize=10)
            ax.set_ylabel(param_names[i], fontsize=10)
            ax.set_title(f'Parameter {param_names[i]}', fontsize=11, fontweight='bold')
            ax.grid(True, alpha=0.3)
        
        plt.suptitle('Best Cell Parameters Evolution', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Parameters plot saved to: {save_path}")
        
        if show:
            plt.show()
        
        return fig
    
    def plot_population_evolution(self, save_path: Optional[str] = None,
                                 show: bool = True) -> Optional[plt.Figure]:
        """绘制种群演化图 / Plot population evolution
        
        显示各代种群的参数分布。
        Displays parameter distribution of each generation.
        
        Args:
            save_path: 保存路径（可选）/ Save path (optional)
            show: 是否显示图表 / Whether to show chart
            
        Returns:
            matplotlib Figure 对象，失败返回 None / matplotlib Figure or None
        """
        steps = self.hdf5.list_steps()
        
        if not steps:
            print("Warning: No population data available")
            return None
        
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()
        param_names = ['a', 'b', 'c', 'α', 'β', 'γ']
        
        for step in steps:
            population = self.hdf5.read_population(step)
            if population is None:
                continue
            
            for i in range(6):
                ax = axes[i]
                ax.scatter([step] * len(population), population[:, i],
                          alpha=0.3, s=10, color='steelblue')
        
        for i, ax in enumerate(axes):
            ax.set_xlabel('Step', fontsize=10)
            ax.set_ylabel(param_names[i], fontsize=10)
            ax.set_title(f'Parameter {param_names[i]} Distribution', fontsize=11)
            ax.grid(True, alpha=0.3)
        
        plt.suptitle('Population Evolution', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Population evolution plot saved to: {save_path}")
        
        if show:
            plt.show()
        
        return fig
    
    def save_all(self, output_dir: str = "figures") -> None:
        """保存所有图表 / Save all plots
        
        保存所有图表到指定目录。
        Saves all plots to specified directory.
        
        Args:
            output_dir: 输出目录 / Output directory
        """
        os.makedirs(output_dir, exist_ok=True)
        
        self.plot_timing(
            save_path=os.path.join(output_dir, "timing.png"),
            show=False
        )
        
        self.plot_convergence(
            save_path=os.path.join(output_dir, "convergence.png"),
            show=False
        )
        
        self.plot_parameters(
            save_path=os.path.join(output_dir, "parameters.png"),
            show=False
        )
        
        self.plot_population_evolution(
            save_path=os.path.join(output_dir, "population_evolution.png"),
            show=False
        )
        
        print(f"All plots saved to: {output_dir}/")
