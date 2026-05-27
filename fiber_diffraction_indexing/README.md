[中文版](README.zh.md)

# Fiber Diffraction Indexing

## Overview

POLYCRYSTINDEX is a software package for automated indexing of fiber diffraction patterns using genetic algorithm optimization.

### Main Features

- **GA Optimization**: Global optimization algorithm to find optimal unit cell parameters
- **Cross-Platform**: Supports Windows, Linux, and macOS
- **HDF5 Storage**: Optional integration of all data into HDF5 files
- **GUI Callback**: Supports GUI integration with real-time progress feedback
- **Modular Architecture**: Clear separation of concerns, easy to extend

## Installation

```bash
# Install dependencies
pip install h5py numpy matplotlib

# Install package
pip install -e .
```

## Quick Start

```python
# Command Line
python -m fiberdiffraction -i input.txt -d diffraction.txt

# Show version
python -m fiberdiffraction -v
```

## Project Structure

```
fiber_diffraction_indexing/
├── fiberdiffraction/          # Main package
│   ├── __init__.py           # Package exports
│   ├── __main__.py           # Module entry point
│   ├── cli.py                # CLI entry point
│   ├── indexer.py            # Main orchestrator
│   ├── config.py             # Input configuration
│   ├── population.py         # Population management
│   ├── genetic.py            # Genetic algorithm
│   ├── fortran.py            # External program caller
│   ├── fileio.py             # File operations
│   ├── callbacks.py          # Callback interface
│   ├── hdf5.py               # HDF5 management
│   ├── plotter.py            # Plotting
│   └── version.py            # Version info
│
├── scripts/                  # Original scripts
│   ├── initial.py           # Initialization script
│   ├── sort.py              # Sorting script
│   └── diffraction_fiber.py # Diffraction calculation
│
├── docs/                     # Documentation
│   ├── user_guide.md        # User guide
│   └── api_reference.md     # API reference
│
└── config/                   # Configuration templates
    └── input_template.txt    # Input template
```

## Core Parameters

| Parameter | Line | Description |
|-----------|------|-------------|
| `population_size` | 5 | Population size, number of unit cell individuals per generation |
| `survival_rate` | 6 | Survival rate, proportion retained in genetic algorithm [0-1] |
| `crossover_rate` | 7 | Crossover rate, proportion produced by crossover operation [0-1] |
| `mutation_rate` | 8 | Mutation rate, proportion produced by mutation operation [0-1] |
| `c_axis` | 11 | C-axis parameter, 0=variable, other=fixed value |
| `layer_mode` | 13 | Layer mode, whether to enable layered structure processing |
| `parameter_min` | 25 | Parameter minimum [a, b, c, α, β, γ] |
| `parameter_max` | 26 | Parameter maximum |
| `tilt_status` | 27 | Tilt status, whether to optimize fiber tilt angle |
| `omp_threads` | 28 | OpenMP thread count, number of parallel threads |

## Usage

### CLI

```bash
# Basic usage
python -m fiberdiffraction -i input.txt -d diffraction.txt

# Show configuration
python -m fiberdiffraction -i input.txt -d diffraction.txt -s

# HDF5 mode
python -m fiberdiffraction -i input.txt -d diffraction.txt --hdf5
```

### Python API

```python
from fiberdiffraction import FiberDiffractionIndexer

# Basic workflow
indexer = FiberDiffractionIndexer("input.txt", "diffraction.txt")
indexer.run()

# HDF5 mode
indexer = FiberDiffractionIndexer(
    "input.txt", "diffraction.txt",
    use_hdf5=True,
    hdf5_file="results.h5"
)
indexer.run()
```

### GUI Callback

```python
from fiberdiffraction import IndexingCallback, FiberDiffractionIndexer

class MyGUI(IndexingCallback):
    """Custom GUI callback class"""
    
    def on_step_start(self, step, total):
        print(f"Starting step {step + 1}/{total}")
        self.update_progress_bar(step / total)
    
    def on_step_end(self, step, total, elapsed):
        print(f"Step {step + 1} completed, took {elapsed:.2f}s")
    
    def on_progress(self, step, message):
        self.append_log(f"[Step {step + 1}] {message}")
    
    def on_error(self, step, error):
        self.show_error(str(error))
    
    def on_complete(self, total_time, results):
        self.show_results(results)

# Use callback
indexer = FiberDiffractionIndexer(
    "input.txt", "diffraction.txt",
    callback=MyGUI()
)
indexer.run()
```

## HDF5 Data Structure

```
results.h5
├── config/                  # Configuration
├── populations/             # Population per step
│   └── step_N               # Population at step N
├── convergence/              # Convergence data
│   ├── best_errors          # Best error per step
│   └── best_cells           # Best cell per step
├── timing/                  # Timing records
│   ├── step_times           # Time per step
│   └── total_time           # Total time
└── metadata/                # Metadata
```

## Plotting

```python
from fiberdiffraction import HDF5Manager, Plotter

hdf5 = HDF5Manager("results.h5", mode='r')
plotter = Plotter(hdf5)

# Timing curve
plotter.plot_timing(save_path="figures/timing.png")

# Convergence curve
plotter.plot_convergence(save_path="figures/convergence.png")

# Parameter evolution
plotter.plot_parameters(save_path="figures/parameters.png")

hdf5.close()
```

## Input File Format

```
# Lines 1-3: Wavelength and comments
1.5418
0
flat

# Line 4: population_size - Population size (individuals per generation)
2000

# Line 5: generation_steps - Evolution generations (iterations)
30

# Line 6: survival_rate - Survival rate [0-1]
0.1

# Line 7: crossover_rate - Crossover rate [0-1]
0.2

# Line 8: mutation_rate - Mutation rate [0-1]
0.5

# Line 11: c_axis - C-axis parameter (0=variable)
0

# Line 13: layer_mode - Layer mode (non-zero=enabled)
1

# Line 25: parameter_min - Parameter minimum [a, b, c, α, β, γ]
3.0 3.0 15.0 90.0 90.0 90.0

# Line 26: parameter_max - Parameter maximum
10.0 10.0 20.0 90.0 90.0 90.0

# Line 27: tilt_status - Tilt status (1=enabled)
0

# Line 28: omp_threads - OpenMP thread count (0=system default)
0
```

## Citation

If you use this software, please cite:

```
Ma, T., Hu, W., Wang, D. & Liu, G. (2025). A global optimization approach 
to automated indexing of fiber diffraction patterns. J. Appl. Cryst. 58.
```

## License

MIT License

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting pull requests.
