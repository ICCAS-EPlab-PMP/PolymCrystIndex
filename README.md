# PolymCrystIndex

[![Release](https://img.shields.io/badge/release-windowsV17-blue)](https://github.com/ICCAS-EPlab-PMP/PolymCrystalIndex/releases/tag/windowsV17)
[![Homepage](https://img.shields.io/badge/homepage-polymcrystal.com-0a7cff)](https://www.polymcrystal.com)
[![Preview](https://img.shields.io/badge/preview-index.polymcrystal.com-6f42c1)](https://index.polymcrystal.com)
[![Paper](https://img.shields.io/badge/paper-IUCr%20oc5041-blue)](https://journals.iucr.org/paper?oc5041)

> 纤维衍射图谱指标化平台  
> A fiber diffraction pattern indexing platform for scientific analysis, verification, and deployment.

PolymCrystIndex 面向纤维衍射与聚合物结构分析场景，提供从图像预处理、峰提取、二维积分到晶胞参数优化与 Miller 指数标注的完整工作流。项目同时维护 Linux 服务器版、Windows 本地桌面版、独立 Python 能力封装与配套工具链，适合研究团队、同步辐射实验用户和需要可复核分析流程的工程化场景。

PolymCrystIndex provides an end-to-end workflow for fiber diffraction analysis, including preprocessing, peak extraction, 2D integration, cell parameter optimization, and Miller indexing. The repository serves Linux server deployment, Windows desktop delivery, reusable Python components, and supporting tools for research teams and synchrotron users who need reproducible analysis workflows.

---

## 项目目标 / Project Goals

- 为纤维衍射数据提供可复核、可导出、可持续维护的指标化工作流。
- 将算法核心、服务接口、桌面交付和服务器部署统一维护在同一仓库中。
- 支持实验室本地分析与多用户共享部署两类典型使用方式。

- Deliver a reproducible and reviewable indexing workflow for fiber diffraction data.
- Maintain algorithm core, service layer, desktop delivery, and server deployment in one repository.
- Support both local laboratory usage and shared multi-user deployment.

## 面向用户 / Who This Project Is For

- 纤维衍射、聚合物晶体与材料结构分析研究人员

- Researchers in fiber diffraction, polymer crystallography, and materials analysis

## 核心能力 / Key Capabilities

- 原始图像与二维积分图像的峰提取
- 基于 Fortran 核心的晶胞参数搜索、优化与指标化
- Miller 指数自动标注、结果导出与复核
- Linux 多用户服务端与 Windows 本地桌面版双交付
- Python/FastAPI/Vue/Fortran 统一维护，便于长期演进

- Peak extraction from raw diffraction images and integrated 2D maps
- Fortran-backed cell search, optimization, and indexing
- Automatic Miller assignment, export, and result review
- Dual delivery for Linux multi-user deployment and Windows desktop use
- Unified maintenance across Python, FastAPI, Vue, and Fortran layers

## 交付形态 / Delivery Modes

| 形态 / Mode | 适用对象 / Best For | 说明 / Notes |
|---|---|---|
| Windows Desktop | 单机研究与离线处理 | 适合实验室本地快速使用 |
| Linux Server | 多用户共享与集中部署 | 适合课题组、实验平台与服务器环境 |
| Python Components | 脚本化调用与二次集成 | 适合自动化流程和算法复用 |
| PySide Tools | 辅助前后处理 | 适合特定调试和处理场景 |

## 界面与流程展示占位 / Media Placeholders

> [中英共用图片占位 / Shared image placeholder] 在这里放置主界面截图，供中文与英文说明共用。  
> Insert one shared overview screenshot here for both Chinese and English readers.

> [中英共用 GIF 占位 / Shared GIF placeholder] 在这里放置完整工作流 GIF（upload → extract peaks → index → export），供中英文共用。  
> Insert one shared workflow GIF here for both Chinese and English readers.

## 安装 / Installation

### Windows

**国内下载 / China mirror**  
http://www.polymcrystal.com/download/PolymCrystindexsetup.zip

**国际下载 / International release**  
https://github.com/ICCAS-EPlab-PMP/PolymCrystalIndex/releases/download/windowsV17/PolymCrystIndex.Setup.1.7.0.exe

下载后运行安装程序即可。建议使用发布包而不是自行拼装运行环境。

Download the installer and run it directly. For most users, the packaged installer is the recommended path.

### Linux

Linux 暂时不单独发布安装包。请先克隆仓库，然后直接运行 `Workspace/deploy/server/` 下的部署脚本。

We do not currently ship a separate Linux release package. Please clone the repository and run the deployment scripts under `Workspace/deploy/server/`.

```bash
git clone https://github.com/ICCAS-EPlab-PMP/PolymCrystalIndex.git
cd PolymCrystalIndex/Workspace/deploy/server

# 以当前用户方式安装 / user-mode install
APP_PROFILE=cloud bash ./install_user_linux.sh

# 或 root/systemd 方式 / root + systemd install
sudo APP_PROFILE=cloud bash ./deploy_linux.sh
```

环境要求可参考 `deploy/README.md`：Python 3.9+、Node.js 16+、可用的 gfortran，以及常见 Linux 发行版环境。

For environment requirements, see `deploy/README.md`: Python 3.9+, Node.js 16+, an available gfortran toolchain, and a standard Linux distribution.

### macOS（未测试） / macOS (untested)

我们目前没有 macOS 设备，也**没有发布经过验证的 macOS 安装包**。以下方式仅作为与 Linux 相近的参考流程，**未经过官方测试**。

We do not currently maintain or test macOS devices, and we **do not provide a validated macOS release package** at this time. The following is a Linux-like reference workflow only and is **not officially validated**.

```bash
# example only; adjust to your own source package layout
tar -xzf your-source-package.tar.gz
cd PolymCrystIndex/Workspace/deploy/server
bash ./install_user_linux.sh
```

如果在 macOS 上使用，请预期需要自行调整 Python、Node.js、Fortran 和系统路径配置。

If you use macOS, expect manual adjustments for Python, Node.js, Fortran, and path configuration.

## 示例流程 / Example Workflow

### SSRF 16B HDPE 纤维样品完整示例 / End-to-End SSRF 16B HDPE Example

仓库中的 `Workspace/EXAMPLE/` 提供了一个可复核示例，包含上海光源 SSRF 16B 线站的 HDPE 纤维样品数据、Y2O3 标样校准文件，以及指标化结果文件。

The `Workspace/EXAMPLE/` directory contains a reproducible example based on an HDPE fiber sample measured at SSRF 16B, with Y2O3 calibration data and indexing outputs.

欢迎用户直接基于 `Workspace/EXAMPLE/` 进行尝试，快速熟悉从示例数据到结果文件的整体流程。后续我们也会补充配套视频说明。

Users are encouraged to start directly with `Workspace/EXAMPLE/` to get familiar with the overall flow from sample data to result files. Video walkthroughs will be added in the future.

## 文档导航 / Documentation

- [`Reference.md`](Reference.md)：仓库结构、模块职责、接口速查与技术参考  
  Repository structure, module mapping, API quick reference, and technical details
- [`deploy/README.md`](deploy/README.md)：Linux 部署与运维说明  
  Linux deployment and operations guide
- [`docs/API_DOCUMENTATION.md`](docs/API_DOCUMENTATION.md)：接口文档  
  API documentation
- [`docs/FRONTEND_BACKEND_MANUAL.md`](docs/FRONTEND_BACKEND_MANUAL.md)：前后端说明  
  Frontend/backend manual
- [`docs/FORTRAN_MANUAL.md`](docs/FORTRAN_MANUAL.md)：Fortran 核心说明  
  Fortran core manual
- [`pyside/README.md`](pyside/README.md)：PySide 工具说明  
  PySide tool guide

## 贡献 / Contributing

欢迎通过 GitHub Issues 提交问题、使用反馈与功能建议；如需贡献代码或文档，请在提交前先说明修改目标和适用场景，以便我们保持桌面端、服务端与算法核心的一致性。

Bug reports, workflow feedback, and feature requests are welcome through GitHub Issues. If you plan to contribute code or documentation, please describe the intended use case first so we can keep the desktop, server, and algorithm layers aligned.

- Issues: https://github.com/ICCAS-EPlab-PMP/PolymCrystalIndex/issues
- Project site: http://www.polymcrystal.com/

## 引用 / Citation

如果本项目对你的研究有帮助，请引用：

If this project contributes to your research, please cite:

论文链接 / Paper link: https://journals.iucr.org/paper?oc5041

```text
Ma, T., Hu, W., Wang, D. & Liu, G. (2025).
PolymCrystIndex: A fiber diffraction pattern indexing platform.
J. Appl. Cryst. 58, 759-767.
```

## 产权、维护与机构信息 / Ownership, Maintenance, and Institutional Links

PolymCrystIndex 由中国科学院化学研究所相关研究团队长期维护。项目主页与相关机构链接如下：

PolymCrystIndex is maintained for long-term research use by teams affiliated with the Institute of Chemistry, Chinese Academy of Sciences. Relevant links are listed below.

- PolymCrystIndex: http://www.polymcrystal.com/
- PMP group: http://pmp.iccas.ac.cn/
- ICCAS: https://www.iccas.ac.cn/
- EP lab: http://eplab.iccas.ac.cn/

## 致谢 / Acknowledgements

- 中国科学院化学研究所 / Institute of Chemistry, Chinese Academy of Sciences
- 工程塑料实验室 / Engineering Plastics Laboratory
- 高分子形态与加工 / Polymer Morphology and Processing
- pyFAI: https://github.com/silx-kit/pyFAI
- FabIO: https://github.com/silx-kit/fabio
