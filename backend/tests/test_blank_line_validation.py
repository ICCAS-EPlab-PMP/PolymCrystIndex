"""Blank line validation tests for validate_diffraction_data."""

from __future__ import annotations

import importlib.util
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _load_module(module_name: str, relative_path: str):
    """Load a module from a relative path."""
    helper_path = os.path.join(os.path.dirname(__file__), "..", relative_path)
    spec = importlib.util.spec_from_file_location(module_name, helper_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


file_service_module = _load_module(
    "test_file_service_module", os.path.join("services", "file_service.py")
)

FileService = file_service_module.FileService


def test_blank_line_warning():
    """Data with blank lines mixed in → success=True, count>0, message contains blank line and line number."""
    content = """1.0 10.0 100.0

2.0 20.0 200.0
# comment line

3.0 30.0 300.0

4.0 40.0 400.0"""
    is_valid, count, msg = FileService.validate_diffraction_data(content)
    assert is_valid is True
    assert count == 4
    assert "blank line" in msg
    # Line 2 and line 6 are blank (1-indexed)
    assert "Line 2" in msg or "Line 6" in msg


def test_blank_line_empty_only():
    """Only blank lines and comments → success=False, count=0, message='No valid data lines found'."""
    content = """

# only comments here

   """
    is_valid, count, msg = FileService.validate_diffraction_data(content)
    assert is_valid is False
    assert count == 0
    assert msg == "No valid data lines found"


def test_normal_data_no_warning():
    """Clean data with no blank lines → success=True, message does not contain 'blank line'."""
    content = """1.0 10.0 100.0
2.0 20.0 200.0
3.0 30.0 300.0"""
    is_valid, count, msg = FileService.validate_diffraction_data(content)
    assert is_valid is True
    assert count == 3
    assert "blank line" not in msg


def test_format_error_still_hard_failure():
    """Format error line still returns hard failure (no change)."""
    # Line 3 has only 2 values (missing intensity)
    content = """1.0 10.0 100.0
2.0 20.0 200.0
3.0 40.0"""
    is_valid, count, msg = FileService.validate_diffraction_data(content)
    assert is_valid is False
    assert count == 0
    assert "Expected 3 values" in msg
    assert "Line 3" in msg