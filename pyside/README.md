# PySide Tools

该目录包含两类本地桌面调试工具：

- `previous/`：前处理 / WAXS 衍射数据分析工具（PySide6）
- `post/`：后处理查看器（当前保留 `pyside6/` 版本）

## Structure

```text
pyside/
├── previous/
│   ├── main.py
│   └── waxs_viewer/
└── post/
    └── pyside6/
```

## Recommended Entry Points

### Previous

```bash
cd pyside/previous
python main.py
```

### Post

当前入口：`post/pyside6/post16.py`

```bash
cd pyside/post/pyside6
python post16.py
```

## One-Click Launch

Windows:

- `launch_previous.bat`
- `launch_post.bat`

PowerShell:

- `scripts/run-previous.ps1`
- `scripts/run-post.ps1`

这些脚本会自动创建独立虚拟环境并安装依赖，再启动对应工具。

## Packaging

预留的 Windows 打包脚本：

- `build_exe.ps1`
- `build_exe.bat`
- `package_previous.spec`
- `package_post.spec`

执行：

```powershell
cd pyside
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

默认会生成打包输出目录，包括：

- `dist/`：最终 onefile / onedir 产物
- `build/`：PyInstaller 中间构建目录
- `spec/`：输出 spec 相关中间文件
- `win-exe/`：整理后的 Windows 发布目录
- `package-summary.txt`：最终打包摘要

脚本行为：

- `build_exe.ps1` 会先为每个目标尝试 `onefile`。
- 若 `onefile` 构建失败，会自动清理残留并回退到 `onedir`。
- 最终采用模式、是否触发回退以及产物位置会写入 `package-summary.txt`。
- `package_previous.spec` 与 `package_post.spec` 已显式补充 PySide6 / fabio / pyFAI / silx / hdf5plugin 的 hiddenimports、datas、binaries 收集逻辑。

说明：

- 打包产物以 `build_exe.ps1` 当前配置的输出目录为准；`_release_bundle/` 仅可作为 **[DEPRECATED]** 历史说明存在。
- `backup/` 是仓库外 `../backup/` 归档区，构建/部署脚本不得引用它。

## Current Notes

- 当前目录主要用于调试与准备发布，不是完整 installer 级别的正式安装包结构。
- 已提供 PyInstaller spec 与统一打包脚本。
- `previous/` 中已补占位 logo，并增加资源回退路径。
