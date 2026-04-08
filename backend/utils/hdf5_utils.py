"""Utility functions for HDF5 operations."""
from typing import Dict, List, Any, Optional
import numpy as np


def read_hdf5_cell_parameters(hdf5_path: str) -> Optional[Dict[str, float]]:
    """Read cell parameters from HDF5 file.
    
    Args:
        hdf5_path: Path to HDF5 file
        
    Returns:
        Dictionary with cell parameters or None
    """
    try:
        import h5py
        
        with h5py.File(hdf5_path, 'r') as f:
            if 'cell_parameters' in f:
                cell_data = f['cell_parameters'][:]
                
                if len(cell_data) >= 6:
                    return {
                        'a': float(cell_data[0]),
                        'b': float(cell_data[1]),
                        'c': float(cell_data[2]),
                        'alpha': float(cell_data[3]),
                        'beta': float(cell_data[4]),
                        'gamma': float(cell_data[5])
                    }
        
        return None
        
    except Exception:
        return None


def read_hdf5_convergence(hdf5_path: str) -> List[Dict[str, Any]]:
    """Read convergence data from HDF5 file.
    
    Args:
        hdf5_path: Path to HDF5 file
        
    Returns:
        List of convergence records
    """
    try:
        import h5py
        
        convergence_data = []
        
        with h5py.File(hdf5_path, 'r') as f:
            if 'convergence' in f:
                conv_group = f['convergence']
                
                for step_key in conv_group.keys():
                    step_data = conv_group[step_key]
                    
                    record = {
                        'step': int(step_key),
                        'error': float(step_data.attrs.get('error', 0.0)),
                        'cell': list(step_data[:])
                    }
                    
                    convergence_data.append(record)
        
        return convergence_data
        
    except Exception:
        return []


def read_hdf5_metadata(hdf5_path: str) -> Optional[Dict[str, Any]]:
    """Read metadata from HDF5 file.
    
    Args:
        hdf5_path: Path to HDF5 file
        
    Returns:
        Dictionary with metadata or None
    """
    try:
        import h5py
        
        with h5py.File(hdf5_path, 'r') as f:
            if 'metadata' in f.attrs:
                return dict(f.attrs)
        
        return None
        
    except Exception:
        return None
