# -*- mode: python ; coding: utf-8 -*-

import importlib.util
import os
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
)

block_cipher = None
spec_root = Path.cwd()
repo_root = spec_root.parent
icon_file = repo_root / 'icon' / 'polymindex.ico'

PACKAGE_MODE = os.environ.get('POLYCRY_PYSIDE_PACKAGE_MODE', 'onefile').strip().lower()
if PACKAGE_MODE not in {'onefile', 'onedir'}:
    PACKAGE_MODE = 'onefile'


def _module_exists(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _collect_submodules(module_name: str) -> list[str]:
    if not _module_exists(module_name):
        return []
    try:
        return collect_submodules(module_name)
    except Exception:
        return []


def _collect_data_files(module_name: str) -> list[tuple[str, str]]:
    if not _module_exists(module_name):
        return []
    try:
        return collect_data_files(module_name)
    except Exception:
        return []


def _collect_dynamic_libs(module_name: str) -> list[tuple[str, str]]:
    if not _module_exists(module_name):
        return []
    try:
        return collect_dynamic_libs(module_name)
    except Exception:
        return []


def _dedupe(entries):
    seen = set()
    result = []
    for entry in entries:
        key = tuple(entry) if isinstance(entry, (list, tuple)) else entry
        if key in seen:
            continue
        seen.add(key)
        result.append(entry)
    return result


datas = []
datas.extend(_collect_data_files('silx.resources'))
if _module_exists('pyFAI.resources'):
    datas.extend(_collect_data_files('pyFAI.resources'))
elif _module_exists('pyFAI'):
    datas.extend(_collect_data_files('pyFAI'))

binaries = []
binaries.extend(_collect_dynamic_libs('hdf5plugin'))
binaries.extend(_collect_dynamic_libs('silx'))

hiddenimports = [
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtSvg',
    'hdf5plugin',
]
hiddenimports.extend(_collect_submodules('fabio'))
hiddenimports.extend(_collect_submodules('pyFAI'))
hiddenimports.extend(_collect_submodules('silx'))
if _module_exists('pyFAI.resources'):
    hiddenimports.append('pyFAI.resources')
if _module_exists('silx.resources'):
    hiddenimports.append('silx.resources')

datas = _dedupe(datas)
binaries = _dedupe(binaries)
hiddenimports = sorted(set(hiddenimports))

a = Analysis(
    ['post/pyside6/post16.py'],
    pathex=[str(spec_root), str(spec_root / 'post' / 'pyside6')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt6', 'tkinter'],
    noarchive=False,
)
pyz = PYZ(a.pure)

if PACKAGE_MODE == 'onefile':
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='PolymCrystIndex-Post',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        icon=str(icon_file) if icon_file.exists() else None,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='PolymCrystIndex-Post',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,
        console=False,
        icon=str(icon_file) if icon_file.exists() else None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        name='PolymCrystIndex-Post',
    )
