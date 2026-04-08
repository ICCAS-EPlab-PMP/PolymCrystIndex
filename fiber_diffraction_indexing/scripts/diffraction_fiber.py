"""
Diffraction Fiber Main Orchestration Module
==========================================

DEPRECATED:
    This legacy script is no longer part of the supported production indexing
    chain. The maintained execution path uses backend/services/indexing_service.py
    together with fiberdiffraction/indexer.py, which isolate each task in its own
    workdir and avoid shared cwd side effects.

    To avoid accidentally reintroducing global cwd / shared-file risks, this
    script is blocked by default unless the environment variable
    POLYCRY_ALLOW_LEGACY_DIFFRACTION_FIBER=1 is explicitly set.

This module serves as the main entry point for the fiber diffraction
indexing process. It orchestrates the execution of various sub-programs
including initialization, indexing, and sorting.

The module implements a multi-step workflow:
    1. Initialize project and create result directory
    2. For each iteration step:
       a. Run indexing program to optimize unit cell parameters
       b. Run sorting program to generate next generation
       c. Archive previous generation files

Version: 1.7
Release Date: 2026.02.28

Usage:
    python diffraction_fiber_v0c.py -i input.txt -d diffraction.txt
    python diffraction_fiber_v0c.py -v  # Show version and citation info

Citation:
    If you use this software, please cite:
    Ma, T., Hu, W., Wang, D. & Liu, G. (2025). A global optimization 
    approach to automated indexing of fiber diffraction patterns. 
    J. Appl. Cryst. 58.
"""

import os
import sys
import argparse
import time
import shutil
from pathlib import Path
from typing import Optional, List


PROGRAM_NAME = "POLYCRYSTINDEX"
VERSION = "1.7"
RELEASE_DATE = "2026.02.28"
LEGACY_ENABLE_ENV = "POLYCRY_ALLOW_LEGACY_DIFFRACTION_FIBER"


def is_windows() -> bool:
    """Check if the current platform is Windows.
    
    Returns:
        bool: True if Windows, False otherwise
    """
    return os.name == 'nt'


def print_version_and_references() -> None:
    """Print version information and citation references."""
    print(f"""
{PROGRAM_NAME}
============================ VERSION {VERSION} ============================
RELEASE in {RELEASE_DATE}

-------------------------REFERENCE-------------------
This software utilizes the MINPACK library for nonlinear optimization.
Software base on following MINPACK references:

Jorge More, Burton Garbow, Kenneth Hillstrom,
User Guide for MINPACK-1,
Technical Report ANL-80-74,
Argonne National Laboratory, 1980.

Jorge More, Danny Sorenson, Burton Garbow, Kenneth Hillstream,
The MINPACK Project,
in Sources and Development of Mathematical Software,
edited by Wayne Cowell,
Prentice-Hall, 1984,
ISBN: 0-13-823501-5,
LC: QA76.95.S68.

Additionally, please CITE the following paper for this work:

Ma, T., Hu, W., Wang, D. & Liu, G. (2025).A global optimization approach 
to automated indexing of fiber diffraction patterns. J. Appl. Cryst. 58.
------------------------------------------------------------------
""")


def run_command(cmd: str, timeout: Optional[float] = None) -> int:
    """Execute a shell command in a cross-platform manner.
    
    Args:
        cmd: Command string to execute
        timeout: Optional timeout in seconds
        
    Returns:
        int: Return code (0 = success)
    """
    if is_windows():
        return os.system(cmd)
    else:
        return os.system(cmd)


def ensure_directory(path: str) -> None:
    """Ensure a directory exists, create if it doesn't.
    
    Args:
        path: Directory path to create
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def move_file(source: str, dest: str) -> bool:
    """Move a file from source to destination.
    
    Args:
        source: Source file path
        dest: Destination directory or file path
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if os.path.exists(source):
            shutil.move(source, dest)
            return True
        return False
    except Exception as e:
        print(f"Warning: Failed to move {source} to {dest}: {e}")
        return False


def copy_file(source: str, dest: str) -> bool:
    """Copy a file from source to destination.
    
    Args:
        source: Source file path
        dest: Destination directory or file path
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if os.path.exists(source):
            shutil.copy(source, dest)
            return True
        return False
    except Exception as e:
        print(f"Warning: Failed to copy {source} to {dest}: {e}")
        return False


def cleanup_old_files(step: int, layer: int) -> None:
    """Archive files from the previous step.
    
    Args:
        step: Current step number
        layer: Layer mode flag (non-zero = enabled)
    """
    if step > 0:
        prev_cell = f"cell_{step - 1}.txt"
        if os.path.exists(prev_cell):
            move_file(prev_cell, "result")
        
        if layer != 0:
            prev_annealing = f"cell_{step - 1}_annealing.txt"
            if os.path.exists(prev_annealing):
                move_file(prev_annealing, "result")


def cleanup_final_files(step: int, layer: int) -> None:
    """Archive files at the end of processing.
    
    Args:
        step: Final step number
        layer: Layer mode flag (non-zero = enabled)
    """
    final_cell = f"cell_{step}.txt"
    if os.path.exists(final_cell):
        move_file(final_cell, "result")
    
    if layer != 0:
        final_annealing = f"cell_{step}_annealing.txt"
        if os.path.exists(final_annealing):
            move_file(final_annealing, "result")
    
    next_cell = f"cell_{step + 1}.txt"
    if os.path.exists(next_cell):
        copy_file(next_cell, "result")
        copy_file(next_cell, "result")


def get_executable_name(base_name: str) -> str:
    """Get the platform-specific executable name.
    
    Args:
        base_name: Base name of the executable
        
    Returns:
        str: Platform-specific executable name
    """
    if is_windows():
        return f"{base_name}.exe"
    else:
        return base_name


def run_indexing_step(input_name: str, diffraction_name: str, 
                      step: int, layer: int) -> None:
    """Execute a single indexing step.
    
    Args:
        input_name: Input parameter file name
        diffraction_name: Diffraction data file name
        step: Current step number
        layer: Layer mode flag
    """
    init_exe = get_executable_name("FiberDiffractioninitial")
    index_exe = get_executable_name("POLYCRYSTALINDEX")
    sort_exe = get_executable_name("FiberDiffractionSort")
    
    os.system(f"{init_exe} -i {input_name}")
    
    os.system(
        f"{index_exe} -i {input_name} -d {diffraction_name} "
        f"-c cell_{step}.txt"
    )
    
    time.sleep(0.5)
    
    os.system(
        f"{sort_exe} -i {input_name} -c cell_{step}_annealing.txt "
        f"-n {step + 1}"
    )
    
    time.sleep(1)


def main() -> None:
    """Main entry point for diffraction fiber indexing."""
    if os.environ.get(LEGACY_ENABLE_ENV) != "1":
        print(
            "Error: diffraction_fiber.py is a deprecated legacy script and is disabled by default. "
            f"If you really need to run it for migration/debugging, set {LEGACY_ENABLE_ENV}=1 explicitly."
        )
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description='Fiber diffraction indexing orchestration program',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python diffraction_fiber_v0c.py -i input.txt -d diffraction.txt
    python diffraction_fiber_v0c.py -v  # Show version and citation
        """
    )
    parser.add_argument(
        '-i', '--input',
        help='Input file name',
        required=False
    )
    parser.add_argument(
        '-d', '--diffraction',
        help='Diffraction file name',
        required=False
    )
    parser.add_argument(
        '-v', '--version',
        help='Print version and citation information',
        action='store_true',
        required=False
    )
    
    args = parser.parse_args()
    
    if args.version:
        print_version_and_references()
        return
    
    if not args.input or not args.diffraction:
        print(f"Error: The following arguments are required: -i/--input, -d/--diffraction")
        sys.exit(1)
    
    input_name = args.input
    diffraction_name = args.diffraction
    
    try:
        with open(input_name, 'r') as f:
            lines = f.readlines()
            step = int(lines[4].strip('\n').split()[0])
            layer = int(lines[12].strip('\n').split()[0])
            
            try:
                omp_threads = int(lines[27].strip('\n').split()[0])
            except (IndexError, ValueError):
                omp_threads = 0
        
        if omp_threads > 0:
            os.environ["OMP_NUM_THREADS"] = str(omp_threads)
            print(f"[OpenMP] Setting thread count: {omp_threads}")
        else:
            os.environ.pop("OMP_NUM_THREADS", None)
            print("[OpenMP] Thread count not limited, system will determine")
        
        starttime = time.time()
        
        for i in range(step):
            if i == 0:
                ensure_directory("result")
            
            mid_time1 = time.time()
            
            run_indexing_step(input_name, diffraction_name, i, layer)
            
            cleanup_old_files(i, layer)
            
            try:
                if i == step - 1:
                    cleanup_final_files(i, layer)
            except Exception as e:
                print(f"Warning: Failed to move diffraction file: {e}")
            
            mid_time2 = time.time()
            sys.stdout.flush()
        
        endtime = time.time()
        print(f"Total execution time: {endtime - starttime:.2f} seconds")
        
    except FileNotFoundError as e:
        print(f"Error: Input file not found: {e}")
        sys.exit(1)
    except IndexError as e:
        print(f"Error: Invalid input file format: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
