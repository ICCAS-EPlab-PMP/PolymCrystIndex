# PySide Tools

该目录包含两类本地桌面调试工具：

- `previous/`：前处理 / WAXS 衍射数据分析工具（PySide6）
- `post/`：后处理查看器（含多个 Qt 绑定变体）

## Structure

```text
pyside/
├── previous/
│   ├── main.py
│   └── waxs_viewer/
└── post/
    ├── pyside6/
    ├── QT/
    └── silxversion/
```

## Recommended Entry Points

### Previous

```bash
cd pyside/previous
python main.py
```

### Post

推荐优先使用 `post/silxversion/post16.py`：

```bash
cd pyside/post/silxversion
python post16.py
```

备选：

- `post/pyside6/post16.py`
- `post/QT/post16.py`（PyQt6 版本，不作为首选）

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

默认会生成：

- 优先尝试 onefile：
  - `../execute/pyside/dist/PolymCrystIndex-Previous.exe`
  - `../execute/pyside/dist/PolymCrystIndex-Post.exe`
- 若 onefile 失败则自动回退 onedir：
  - `../execute/pyside/dist/PolymCrystIndex-Previous/`
  - `../execute/pyside/dist/PolymCrystIndex-Post/`

并同步到：

- `../execute/pyside/win-exe/pyside-previous/`
- `../execute/pyside/win-exe/pyside-post/`

脚本行为：

- `build_exe.ps1` 会先为每个目标尝试 `onefile`。
- 若 `onefile` 构建失败，会自动清理残留并回退到 `onedir`。
- 最终采用模式、是否触发回退、dist 产物路径与整理后的 `win-exe/` 路径会写入 `../execute/pyside/package-summary.txt`。
- `package_previous.spec` 与 `package_post.spec` 已显式补充 PySide6 / fabio / pyFAI / silx / hdf5plugin 的 hiddenimports、datas、binaries 收集逻辑。

说明：

- `execute/` 是唯一活动构建输出目录；`_release_bundle/` 仅可作为 **[DEPRECATED]** 历史说明存在。
- `backup/` 是仓库外 `../backup/` 归档区，构建/部署脚本不得引用它。

## Current Notes

- 当前目录主要用于调试与准备发布，不是完整 installer 级别的正式安装包结构。
- 已提供 PyInstaller spec 与统一打包脚本。
- `previous/` 中已补占位 logo，并增加资源回退路径。
