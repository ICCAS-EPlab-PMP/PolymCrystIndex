"""File service for managing uploads and downloads."""
import os
import shutil
from pathlib import Path
from typing import Optional, Tuple

from core.config import settings


class FileService:
    """Service for file operations."""
    
    @staticmethod
    def validate_diffraction_data(content: str) -> Tuple[bool, int, str]:
        """Validate diffraction data format.
        
        Expected format: q psi intensity (one per line)
        
        Args:
            content: File content as string
            
        Returns:
            Tuple of (is_valid, count, message)
        """
        lines = content.strip().split('\n')
        valid_count = 0
        warnings = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split()
            if len(parts) < 3:
                return False, 0, f"Line {i+1}: Expected 3 values (q, psi, intensity), got {len(parts)}"
            
            try:
                q = float(parts[0])
                psi = float(parts[1])
                intensity = float(parts[2])
                
                if q < 0:
                    return False, 0, f"Line {i+1}: q value cannot be negative"
                if psi < 0:
                    warnings.append(f"Line {i+1}: psi is negative (will use absolute value)")
                if psi > 360:
                    warnings.append(f"Line {i+1}: psi > 360 degrees")
                if intensity < 0:
                    warnings.append(f"Line {i+1}: intensity is negative")
                
                valid_count += 1
            except ValueError as e:
                return False, 0, f"Line {i+1}: Invalid number format - {e}"
        
        if valid_count == 0:
            return False, 0, "No valid data lines found"
        
        if warnings:
            warning_msg = f"Valid format (with {len(warnings)} warnings): " + "; ".join(warnings[:5])
            if len(warnings) > 5:
                warning_msg += f" ... and {len(warnings) - 5} more"
            return True, valid_count, warning_msg
        
        return True, valid_count, "Valid format"
    
    @staticmethod
    def save_uploaded_file(file_content: bytes, filename: str, subdir: str = "temp") -> str:
        """Save uploaded file to disk.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            subdir: Subdirectory under UPLOAD_DIR
            
        Returns:
            Path to saved file (normalized with forward slashes)
        """
        save_dir = os.path.join(settings.UPLOAD_DIR, subdir)
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        
        safe_filename = f"{filename}"
        file_path = os.path.join(save_dir, safe_filename)
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        return file_path.replace('\\', '/')
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """Get file size in bytes."""
        return os.path.getsize(file_path)
    
    @staticmethod
    def delete_file(file_path: str) -> bool:
        """Delete a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False
    
    @staticmethod
    def create_result_archive(task_id: str, output_path: str) -> str:
        """Create ZIP archive of results.
        
        Args:
            task_id: Task identifier
            output_path: Output ZIP file path
            
        Returns:
            Path to created archive
        """
        work_dir = os.path.join(settings.WORKING_DIR, task_id)
        result_dir = os.path.join(settings.RESULT_DIR, task_id)
        
        Path(result_dir).mkdir(parents=True, exist_ok=True)
        
        if os.path.exists(work_dir):
            shutil.copytree(work_dir, result_dir, dirs_exist_ok=True)
        
        shutil.make_archive(
            output_path.replace('.zip', ''),
            'zip',
            result_dir
        )
        
        return f"{output_path}.zip"
    
    @staticmethod
    def read_diffraction_file(file_path: str) -> Tuple[list, list, list]:
        """Read diffraction data file.
        
        Args:
            file_path: Path to diffraction file
            
        Returns:
            Tuple of (q_values, psi_values, intensities)
        """
        q_values = []
        psi_values = []
        intensities = []
        
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        q_values.append(float(parts[0]))
                        psi_values.append(float(parts[1]))
                        intensities.append(float(parts[2]))
                    except ValueError:
                        continue
        
        return q_values, psi_values, intensities
