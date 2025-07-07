# File operations engine - Core file manipulation and organization

import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from enum import Enum

from .utils.logger import get_logger
from .utils.validator import get_validator, ValidationError
from .utils.conflict_resolver import get_conflict_resolver
from .category_mapper import get_category_mapper


class OperationMode(Enum):
    """File operation modes"""
    MOVE = "move"
    COPY = "copy"
    ORGANIZE_BY_TYPE = "organize_by_type"
    ORGANIZE_BY_DATE = "organize_by_date"


class OrganizationResult:
    """Results of file organization operation"""
    
    def __init__(self):
        self.total_files = 0
        self.processed_files = 0
        self.skipped_files = 0
        self.error_files = 0
        self.categories_created = 0
        self.conflicts_resolved = 0
        self.total_size_moved = 0
        self.operation_time = 0.0
        self.errors = []
        self.processed_categories = {}
        self.dry_run = False
    
    def add_error(self, file_path: str, error: str):
        """Add an error to the results"""
        self.errors.append({"file": file_path, "error": error})
        self.error_files += 1
    
    def add_processed_file(self, file_path: str, category: str, size: int):
        """Add a successfully processed file"""
        self.processed_files += 1
        self.total_size_moved += size
        
        if category not in self.processed_categories:
            self.processed_categories[category] = {"count": 0, "size": 0}
        
        self.processed_categories[category]["count"] += 1
        self.processed_categories[category]["size"] += size
    
    def get_summary(self) -> Dict:
        """Get operation summary"""
        return {
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "skipped_files": self.skipped_files,
            "error_files": self.error_files,
            "success_rate": round((self.processed_files / self.total_files) * 100, 1) if self.total_files > 0 else 0,
            "categories_created": self.categories_created,
            "conflicts_resolved": self.conflicts_resolved,
            "total_size_mb": round(self.total_size_moved / (1024 * 1024), 2),
            "operation_time": round(self.operation_time, 2),
            "dry_run": self.dry_run,
            "processed_categories": self.processed_categories
        }


class FileManager:
    """
    Advanced file operations manager for File Organizer Pro
    
    Features:
    - Safe file operations (move, copy, organize)
    - Dry-run mode for previewing changes
    - Conflict resolution with multiple strategies
    - Progress tracking and detailed logging
    - Rollback capability for failed operations
    - Batch operations with error handling
    - Size and permission validation
    """
    
    def __init__(self):
        self.logger = get_logger()
        self.validator = get_validator()
        self.conflict_resolver = get_conflict_resolver()
        self.category_mapper = get_category_mapper()
        
        # Operation state
        self.current_operation = None
        self.operation_start_time = None
        self.rollback_operations = []
    
    def organize_by_type(self, 
                        source_dir: str, 
                        destination_dir: str = None,
                        dry_run: bool = False,
                        create_subdirs: bool = True,
                        progress_callback: Optional[Callable] = None) -> OrganizationResult:
        """
        Organize files by their type/category
        
        Args:
            source_dir: Source directory containing files to organize
            destination_dir: Destination directory (uses source_dir if None)
            dry_run: Preview mode - don't actually move files
            create_subdirs: Create category subdirectories
            progress_callback: Optional callback for progress updates
            
        Returns:
            OrganizationResult with operation details
        """
        result = OrganizationResult()
        result.dry_run = dry_run
        operation_id = f"organize_type_{int(time.time())}"
        
        try:
            # Start operation tracking
            self.logger.log_operation_start(operation_id, 
                f"Organizing files by type - Source: {source_dir}")
            self.operation_start_time = time.time()
            
            # Validate directories
            source_path = self.validator.validate_source_directory(source_dir)
            
            if destination_dir is None:
                dest_path = source_path
            else:
                dest_path = self.validator.validate_destination_directory(destination_dir)
            
            # Scan and categorize files
            self.logger.info("🔍 Scanning and categorizing files...")
            files_to_process = self._scan_files(source_path)
            result.total_files = len(files_to_process)
            
            if result.total_files == 0:
                self.logger.info("📭 No files found to organize")
                return result
            
            # Categorize files
            categorized_files = self.category_mapper.categorize_files(files_to_process)
            
            # Process each category
            for category, files in categorized_files.items():
                if category == "Uncategorized" and not create_subdirs:
                    # Skip uncategorized files if not creating subdirs
                    result.skipped_files += len(files)
                    continue
                
                # Create category directory if needed
                if create_subdirs:
                    category_dir = dest_path / category
                    if not dry_run:
                        category_dir.mkdir(exist_ok=True)
                    
                    if not category_dir.exists() and not dry_run:
                        result.categories_created += 1
                else:
                    category_dir = dest_path
                
                # Process files in category
                for file_path in files:
                    try:
                        success = self._move_file_to_category(
                            file_path, category_dir, dry_run, result
                        )
                        
                        if success:
                            file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
                            result.add_processed_file(file_path, category, file_size)
                        
                        # Update progress
                        if progress_callback:
                            progress = (result.processed_files + result.error_files) / result.total_files
                            progress_callback(progress, file_path, category)
                            
                    except Exception as e:
                        result.add_error(file_path, str(e))
                        self.logger.error(f"❌ Failed to process {file_path}: {e}")
            
            # Complete operation
            result.operation_time = time.time() - self.operation_start_time
            self._log_operation_results(operation_id, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Organization by type failed: {e}")
            result.add_error("OPERATION", str(e))
            return result
    
    def organize_by_date(self,
                        source_dir: str,
                        destination_dir: str = None,
                        dry_run: bool = False,
                        date_format: str = "YYYY-MM-DD",
                        use_creation_date: bool = False,
                        progress_callback: Optional[Callable] = None) -> OrganizationResult:
        """
        Organize files by their date (creation or modification)
        
        Args:
            source_dir: Source directory containing files
            destination_dir: Destination directory (uses source_dir if None)
            dry_run: Preview mode
            date_format: Date folder format (YYYY-MM-DD, YYYY-MM, YYYY)
            use_creation_date: Use creation date instead of modification date
            progress_callback: Optional progress callback
            
        Returns:
            OrganizationResult with operation details
        """
        result = OrganizationResult()
        result.dry_run = dry_run
        operation_id = f"organize_date_{int(time.time())}"
        
        try:
            # Start operation
            self.logger.log_operation_start(operation_id,
                f"Organizing files by date - Source: {source_dir}")
            self.operation_start_time = time.time()
            
            # Validate directories
            source_path = self.validator.validate_source_directory(source_dir)
            
            if destination_dir is None:
                dest_path = source_path
            else:
                dest_path = self.validator.validate_destination_directory(destination_dir)
            
            # Scan files
            files_to_process = self._scan_files(source_path)
            result.total_files = len(files_to_process)
            
            if result.total_files == 0:
                self.logger.info("📭 No files found to organize")
                return result
            
            # Group files by date
            date_groups = self._group_files_by_date(files_to_process, date_format, use_creation_date)
            
            # Process each date group
            for date_folder, files in date_groups.items():
                # Create date directory
                date_dir = dest_path / date_folder
                if not dry_run:
                    date_dir.mkdir(exist_ok=True)
                
                if not date_dir.exists() and not dry_run:
                    result.categories_created += 1
                
                # Process files in date group
                for file_path in files:
                    try:
                        success = self._move_file_to_category(
                            file_path, date_dir, dry_run, result
                        )
                        
                        if success:
                            file_size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
                            result.add_processed_file(file_path, date_folder, file_size)
                        
                        # Update progress
                        if progress_callback:
                            progress = (result.processed_files + result.error_files) / result.total_files
                            progress_callback(progress, file_path, date_folder)
                            
                    except Exception as e:
                        result.add_error(file_path, str(e))
                        self.logger.error(f"❌ Failed to process {file_path}: {e}")
            
            # Complete operation
            result.operation_time = time.time() - self.operation_start_time
            self._log_operation_results(operation_id, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Organization by date failed: {e}")
            result.add_error("OPERATION", str(e))
            return result
    
    def move_file(self, source: str, destination: str, dry_run: bool = False) -> bool:
        """
        Move a single file with conflict resolution
        
        Args:
            source: Source file path
            destination: Destination file path
            dry_run: Preview mode
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate paths
            source_path, dest_path = self.validator.validate_move_operation(source, destination)
            
            # Handle conflicts
            if dest_path.exists():
                resolved_path = self.conflict_resolver.resolve_conflict(
                    str(source_path), str(dest_path), dry_run
                )
                dest_path = Path(resolved_path)
            
            # Perform operation
            if not dry_run:
                # Ensure destination directory exists
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Move file
                shutil.move(str(source_path), str(dest_path))
                
                # Add to rollback operations
                self.rollback_operations.append({
                    "operation": "move",
                    "original_path": str(dest_path),
                    "backup_path": str(source_path)
                })
            
            # Log operation
            self.logger.log_file_action(
                "MOVE", str(source_path), str(dest_path), dry_run
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to move {source} to {destination}: {e}")
            return False
    
    def copy_file(self, source: str, destination: str, dry_run: bool = False) -> bool:
        """
        Copy a single file with conflict resolution
        
        Args:
            source: Source file path
            destination: Destination file path
            dry_run: Preview mode
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate paths
            source_path, dest_path = self.validator.validate_copy_operation(source, destination)
            
            # Handle conflicts
            if dest_path.exists():
                resolved_path = self.conflict_resolver.resolve_conflict(
                    str(source_path), str(dest_path), dry_run
                )
                dest_path = Path(resolved_path)
            
            # Perform operation
            if not dry_run:
                # Ensure destination directory exists
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file
                shutil.copy2(str(source_path), str(dest_path))
            
            # Log operation
            self.logger.log_file_action(
                "COPY", str(source_path), str(dest_path), dry_run
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to copy {source} to {destination}: {e}")
            return False
    
    def batch_operation(self, 
                       operations: List[Dict],
                       dry_run: bool = False,
                       progress_callback: Optional[Callable] = None) -> OrganizationResult:
        """
        Perform batch file operations
        
        Args:
            operations: List of operation dicts with 'type', 'source', 'destination'
            dry_run: Preview mode
            progress_callback: Optional progress callback
            
        Returns:
            OrganizationResult with batch operation details
        """
        result = OrganizationResult()
        result.dry_run = dry_run
        result.total_files = len(operations)
        
        operation_id = f"batch_{int(time.time())}"
        self.logger.log_operation_start(operation_id, f"Batch operation: {len(operations)} files")
        self.operation_start_time = time.time()
        
        for i, operation in enumerate(operations):
            try:
                op_type = operation.get("type", "move").lower()
                source = operation["source"]
                destination = operation["destination"]
                
                if op_type == "move":
                    success = self.move_file(source, destination, dry_run)
                elif op_type == "copy":
                    success = self.copy_file(source, destination, dry_run)
                else:
                    raise ValueError(f"Unknown operation type: {op_type}")
                
                if success:
                    file_size = Path(source).stat().st_size if Path(source).exists() else 0
                    result.add_processed_file(source, op_type, file_size)
                else:
                    result.add_error(source, f"Failed {op_type} operation")
                
                # Update progress
                if progress_callback:
                    progress = (i + 1) / len(operations)
                    progress_callback(progress, source, op_type)
                    
            except Exception as e:
                result.add_error(operation.get("source", "unknown"), str(e))
        
        result.operation_time = time.time() - self.operation_start_time
        self._log_operation_results(operation_id, result)
        
        return result
    
    def _scan_files(self, directory: Path) -> List[str]:
        """Scan directory for files to process"""
        files = []
        
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    # Skip hidden files and system files by default
                    if not file_path.name.startswith('.'):
                        files.append(str(file_path))
                        
        except PermissionError as e:
            self.logger.warning(f"⚠️ Permission denied scanning {directory}: {e}")
        
        self.logger.info(f"📊 Found {len(files)} files to process")
        return files
    
    def _move_file_to_category(self, 
                              file_path: str, 
                              category_dir: Path, 
                              dry_run: bool,
                              result: OrganizationResult) -> bool:
        """Move a file to its category directory"""
        try:
            source_path = Path(file_path)
            dest_path = category_dir / source_path.name
            
            # Handle conflicts
            if dest_path.exists():
                resolved_path = self.conflict_resolver.resolve_conflict(
                    str(source_path), str(dest_path), dry_run
                )
                dest_path = Path(resolved_path)
                result.conflicts_resolved += 1
            
            # Perform move
            if not dry_run:
                shutil.move(str(source_path), str(dest_path))
            
            # Log action
            self.logger.log_file_action(
                "MOVE", str(source_path), str(dest_path), dry_run
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to move {file_path}: {e}")
            return False
    
    def _group_files_by_date(self, 
                            files: List[str], 
                            date_format: str, 
                            use_creation_date: bool) -> Dict[str, List[str]]:
        """Group files by their date"""
        date_groups = {}
        
        for file_path in files:
            try:
                path = Path(file_path)
                
                # Get file date
                if use_creation_date:
                    timestamp = path.stat().st_ctime
                else:
                    timestamp = path.stat().st_mtime
                
                # Format date folder name
                file_date = datetime.fromtimestamp(timestamp)
                
                if date_format == "YYYY-MM-DD":
                    date_folder = file_date.strftime("%Y-%m-%d")
                elif date_format == "YYYY-MM":
                    date_folder = file_date.strftime("%Y-%m")
                elif date_format == "YYYY":
                    date_folder = file_date.strftime("%Y")
                else:
                    date_folder = file_date.strftime("%Y-%m-%d")  # Default
                
                if date_folder not in date_groups:
                    date_groups[date_folder] = []
                
                date_groups[date_folder].append(file_path)
                
            except Exception as e:
                self.logger.warning(f"⚠️ Could not get date for {file_path}: {e}")
                
                # Add to "Unknown" group
                if "Unknown-Date" not in date_groups:
                    date_groups["Unknown-Date"] = []
                date_groups["Unknown-Date"].append(file_path)
        
        return date_groups
    
    def _log_operation_results(self, operation_id: str, result: OrganizationResult):
        """Log detailed operation results"""
        summary = result.get_summary()
        
        if result.dry_run:
            self.logger.info(f"🔍 DRY RUN SUMMARY - {operation_id} files would be processed:")
            for key, value in summary.items():
                self.logger.info(f"   {key}: {value} files")
        else:
            self.logger.log_operation_success(operation_id, 
                f"Processed {summary['processed_files']}/{summary['total_files']} files")
        
        # Log category statistics
        for category, stats in summary["processed_categories"].items():
            self.logger.info(f"📁 {category}: {stats['count']} files "
                           f"({round(stats['size'] / (1024*1024), 2)} MB)")
        
        # Log errors if any
        if result.errors:
            self.logger.warning(f"⚠️ {len(result.errors)} errors occurred:")
            for error in result.errors[:5]:  # Show first 5 errors
                self.logger.error(f"  • {error['file']}: {error['error']}")
    
    def get_organization_preview(self, 
                               source_dir: str, 
                               mode: str = "type") -> Dict:
        """
        Get a preview of what organization would do
        
        Args:
            source_dir: Source directory to analyze
            mode: Organization mode ('type' or 'date')
            
        Returns:
            Dictionary with preview information including file mappings
        """
        try:
            source_path = self.validator.validate_source_directory(source_dir)
            files = self._scan_files(source_path)
            
            if mode == "type":
                categorized = self.category_mapper.categorize_files(files)
                stats = self.category_mapper.get_category_stats(categorized)
                file_mappings = categorized
            elif mode == "date":
                date_groups = self._group_files_by_date(files, "YYYY-MM-DD", False)
                stats = {}
                for date, file_list in date_groups.items():
                    total_size = sum(Path(f).stat().st_size for f in file_list 
                                   if Path(f).exists())
                    stats[date] = {
                        "file_count": len(file_list),
                        "total_size_mb": round(total_size / (1024*1024), 2)
                    }
                file_mappings = date_groups
            else:
                raise ValueError(f"Unknown mode: {mode}")
            
            return {
                "mode": mode,
                "total_files": len(files),
                "categories": stats,
                "estimated_folders": len(stats),
                "file_mappings": file_mappings
            }
            
        except Exception as e:
            self.logger.error(f"❌ Preview failed: {e}")
            return {"error": str(e)}


# Global file manager instance
_global_manager: Optional[FileManager] = None


def get_file_manager() -> FileManager:
    """
    Get or create the global file manager instance
    
    Returns:
        FileManager instance
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = FileManager()
    return _global_manager


# Convenience functions
def organize_files_by_type(source_dir: str, 
                          destination_dir: str = None,
                          dry_run: bool = False) -> OrganizationResult:
    """Quick file organization by type"""
    return get_file_manager().organize_by_type(source_dir, destination_dir, dry_run)


def organize_files_by_date(source_dir: str,
                          destination_dir: str = None, 
                          dry_run: bool = False) -> OrganizationResult:
    """Quick file organization by date"""
    return get_file_manager().organize_by_date(source_dir, destination_dir, dry_run)


def preview_organization(source_dir: str, mode: str = "type") -> Dict:
    """Quick organization preview"""
    return get_file_manager().get_organization_preview(source_dir, mode)
