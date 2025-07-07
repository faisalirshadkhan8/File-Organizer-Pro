# Path validation and permission checks

import os
import stat
from pathlib import Path
from typing import List, Optional, Tuple
from .logger import get_logger


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class PathValidator:
    """
    Comprehensive path and permission validation for File Organizer Pro
    
    Features:
    - Path existence and accessibility checks
    - Permission validation (read/write/execute)
    - Safe path resolution
    - Directory creation validation
    - File operation safety checks
    """
    
    def __init__(self):
        self.logger = get_logger()
    
    def validate_source_directory(self, path: str) -> Path:
        """
        Validate source directory for organization
        
        Args:
            path: Source directory path
            
        Returns:
            Validated Path object
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            source_path = Path(path).resolve()
            
            # Check if path exists
            if not source_path.exists():
                raise ValidationError(f"Source directory does not exist: {source_path}")
            
            # Check if it's a directory
            if not source_path.is_dir():
                raise ValidationError(f"Source path is not a directory: {source_path}")
            
            # Check read permissions
            if not self._check_read_permission(source_path):
                raise ValidationError(f"No read permission for directory: {source_path}")
            
            # Check if directory is accessible
            if not self._is_directory_accessible(source_path):
                raise ValidationError(f"Directory is not accessible: {source_path}")
            
            self.logger.debug(f"✅ Source directory validated: {source_path}")
            return source_path
            
        except Exception as e:
            self.logger.error(f"Source directory validation failed: {e}")
            raise ValidationError(f"Invalid source directory: {e}")
    
    def validate_destination_directory(self, path: str, create_if_missing: bool = True) -> Path:
        """
        Validate destination directory for file operations
        
        Args:
            path: Destination directory path
            create_if_missing: Whether to create directory if it doesn't exist
            
        Returns:
            Validated Path object
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            dest_path = Path(path).resolve()
            
            # If directory doesn't exist, try to create it
            if not dest_path.exists():
                if create_if_missing:
                    try:
                        dest_path.mkdir(parents=True, exist_ok=True)
                        self.logger.debug(f"📁 Created destination directory: {dest_path}")
                    except OSError as e:
                        raise ValidationError(f"Cannot create destination directory: {e}")
                else:
                    raise ValidationError(f"Destination directory does not exist: {dest_path}")
            
            # Check if it's a directory
            if not dest_path.is_dir():
                raise ValidationError(f"Destination path is not a directory: {dest_path}")
            
            # Check write permissions
            if not self._check_write_permission(dest_path):
                raise ValidationError(f"No write permission for directory: {dest_path}")
            
            self.logger.debug(f"✅ Destination directory validated: {dest_path}")
            return dest_path
            
        except Exception as e:
            if not isinstance(e, ValidationError):
                self.logger.error(f"Destination directory validation failed: {e}")
                raise ValidationError(f"Invalid destination directory: {e}")
            raise
    
    def validate_file_path(self, file_path: str) -> Path:
        """
        Validate individual file path
        
        Args:
            file_path: File path to validate
            
        Returns:
            Validated Path object
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            path = Path(file_path).resolve()
            
            # Check if file exists
            if not path.exists():
                raise ValidationError(f"File does not exist: {path}")
            
            # Check if it's a file (not directory)
            if not path.is_file():
                raise ValidationError(f"Path is not a file: {path}")
            
            # Check if file is readable
            if not self._check_read_permission(path):
                raise ValidationError(f"No read permission for file: {path}")
            
            # Check if file is not in use (basic check)
            if not self._is_file_accessible(path):
                raise ValidationError(f"File may be in use or locked: {path}")
            
            return path
            
        except Exception as e:
            if not isinstance(e, ValidationError):
                self.logger.error(f"File validation failed: {e}")
                raise ValidationError(f"Invalid file: {e}")
            raise
    
    def validate_move_operation(self, source: str, destination: str) -> Tuple[Path, Path]:
        """
        Validate file move operation
        
        Args:
            source: Source file path
            destination: Destination file path
            
        Returns:
            Tuple of validated (source_path, destination_path)
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate source file
        source_path = self.validate_file_path(source)
        
        # Validate destination directory
        dest_path = Path(destination).resolve()
        dest_dir = dest_path.parent
        
        # Ensure destination directory exists and is writable
        self.validate_destination_directory(str(dest_dir))
        
        # Check if destination file already exists
        if dest_path.exists():
            self.logger.warning(f"⚠️ Destination file already exists: {dest_path}")
        
        # Check if we have permission to delete source file
        source_dir = source_path.parent
        if not self._check_write_permission(source_dir):
            raise ValidationError(f"No permission to move file from: {source_dir}")
        
        return source_path, dest_path
    
    def validate_copy_operation(self, source: str, destination: str) -> Tuple[Path, Path]:
        """
        Validate file copy operation
        
        Args:
            source: Source file path
            destination: Destination file path
            
        Returns:
            Tuple of validated (source_path, destination_path)
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate source file
        source_path = self.validate_file_path(source)
        
        # Validate destination directory
        dest_path = Path(destination).resolve()
        dest_dir = dest_path.parent
        
        # Ensure destination directory exists and is writable
        self.validate_destination_directory(str(dest_dir))
        
        # Check available disk space
        if not self._check_disk_space(source_path, dest_dir):
            raise ValidationError("Insufficient disk space for copy operation")
        
        return source_path, dest_path
    
    def get_safe_filename(self, filename: str, directory: Path) -> str:
        """
        Generate a safe filename that doesn't conflict with existing files
        
        Args:
            filename: Original filename
            directory: Target directory
            
        Returns:
            Safe filename (may be modified with number suffix)
        """
        base_path = directory / filename
        
        if not base_path.exists():
            return filename
        
        # File exists, generate alternative name
        name_stem = base_path.stem
        suffix = base_path.suffix
        counter = 1
        
        while True:
            new_filename = f"{name_stem}_{counter}{suffix}"
            new_path = directory / new_filename
            
            if not new_path.exists():
                self.logger.debug(f"🔄 Generated safe filename: {new_filename}")
                return new_filename
            
            counter += 1
            
            # Prevent infinite loop
            if counter > 9999:
                raise ValidationError("Cannot generate safe filename - too many conflicts")
    
    def scan_directory_safety(self, directory: Path) -> dict:
        """
        Perform safety scan of directory before operations
        
        Args:
            directory: Directory to scan
            
        Returns:
            Dictionary with safety information
        """
        safety_info = {
            "total_files": 0,
            "accessible_files": 0,
            "locked_files": 0,
            "hidden_files": 0,
            "system_files": 0,
            "large_files": [],  # Files > 100MB
            "warnings": []
        }
        
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    safety_info["total_files"] += 1
                    
                    # Check if file is accessible
                    if self._is_file_accessible(file_path):
                        safety_info["accessible_files"] += 1
                    else:
                        safety_info["locked_files"] += 1
                        safety_info["warnings"].append(f"Locked file: {file_path}")
                    
                    # Check if file is hidden
                    if self._is_hidden_file(file_path):
                        safety_info["hidden_files"] += 1
                    
                    # Check if file is system file
                    if self._is_system_file(file_path):
                        safety_info["system_files"] += 1
                        safety_info["warnings"].append(f"System file: {file_path}")
                    
                    # Check file size
                    try:
                        file_size = file_path.stat().st_size
                        if file_size > 100 * 1024 * 1024:  # 100MB
                            safety_info["large_files"].append({
                                "path": str(file_path),
                                "size_mb": round(file_size / (1024 * 1024), 2)
                            })
                    except OSError:
                        pass
                        
        except Exception as e:
            safety_info["warnings"].append(f"Scan error: {e}")
        
        return safety_info
    
    def _check_read_permission(self, path: Path) -> bool:
        """Check if path has read permission"""
        try:
            return os.access(path, os.R_OK)
        except OSError:
            return False
    
    def _check_write_permission(self, path: Path) -> bool:
        """Check if path has write permission"""
        try:
            return os.access(path, os.W_OK)
        except OSError:
            return False
    
    def _is_directory_accessible(self, path: Path) -> bool:
        """Check if directory is accessible (can list contents)"""
        try:
            list(path.iterdir())
            return True
        except (OSError, PermissionError):
            return False
    
    def _is_file_accessible(self, path: Path) -> bool:
        """Check if file is accessible (not locked or in use)"""
        try:
            # Try to open file in read mode
            with open(path, 'rb'):
                pass
            return True
        except (OSError, PermissionError):
            return False
    
    def _is_hidden_file(self, path: Path) -> bool:
        """Check if file is hidden"""
        try:
            if os.name == 'nt':  # Windows
                attrs = os.stat(path).st_file_attributes
                return bool(attrs & stat.FILE_ATTRIBUTE_HIDDEN)
            else:  # Unix/Linux/Mac
                return path.name.startswith('.')
        except (OSError, AttributeError):
            return False
    
    def _is_system_file(self, path: Path) -> bool:
        """Check if file is a system file"""
        try:
            if os.name == 'nt':  # Windows
                attrs = os.stat(path).st_file_attributes
                return bool(attrs & stat.FILE_ATTRIBUTE_SYSTEM)
            else:
                # On Unix systems, consider files in system directories as system files
                system_dirs = ['/bin', '/sbin', '/usr/bin', '/usr/sbin', '/etc']
                return any(str(path).startswith(sys_dir) for sys_dir in system_dirs)
        except (OSError, AttributeError):
            return False
    
    def _check_disk_space(self, source_file: Path, dest_dir: Path) -> bool:
        """Check if there's enough disk space for file operation"""
        try:
            file_size = source_file.stat().st_size
            free_space = os.statvfs(dest_dir).f_bavail * os.statvfs(dest_dir).f_frsize
            
            # Require at least 10% more space than file size
            return free_space > (file_size * 1.1)
        except (OSError, AttributeError):
            # If we can't check, assume it's okay
            return True


# Global validator instance
_global_validator: Optional[PathValidator] = None


def get_validator() -> PathValidator:
    """
    Get or create the global validator instance
    
    Returns:
        PathValidator instance
    """
    global _global_validator
    if _global_validator is None:
        _global_validator = PathValidator()
    return _global_validator


# Convenience functions for quick validation
def validate_source_dir(path: str) -> Path:
    """Quick source directory validation"""
    return get_validator().validate_source_directory(path)


def validate_dest_dir(path: str) -> Path:
    """Quick destination directory validation"""
    return get_validator().validate_destination_directory(path)


def validate_file(path: str) -> Path:
    """Quick file validation"""
    return get_validator().validate_file_path(path)


def is_safe_to_organize(directory: str) -> bool:
    """
    Quick safety check for directory organization
    
    Args:
        directory: Directory path to check
        
    Returns:
        True if safe to organize, False otherwise
    """
    try:
        validator = get_validator()
        dir_path = validator.validate_source_directory(directory)
        safety_info = validator.scan_directory_safety(dir_path)
        
        # Consider unsafe if too many locked/system files
        total_files = safety_info["total_files"]
        problem_files = safety_info["locked_files"] + safety_info["system_files"]
        
        if total_files > 0:
            problem_ratio = problem_files / total_files
            return problem_ratio < 0.1  # Less than 10% problematic files
        
        return True
        
    except ValidationError:
        return False
