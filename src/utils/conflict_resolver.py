# Duplicate file handling and conflict resolution

import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from enum import Enum

from .logger import get_logger


class ConflictStrategy(Enum):
    """Strategies for handling file conflicts"""
    SKIP = "skip"                    # Skip conflicting files
    RENAME = "rename"                # Rename with number suffix
    OVERWRITE = "overwrite"          # Replace existing file
    BACKUP = "backup"                # Backup existing, then overwrite
    SIZE_COMPARE = "size_compare"    # Keep larger file
    DATE_COMPARE = "date_compare"    # Keep newer file
    HASH_COMPARE = "hash_compare"    # Compare file contents


class ConflictInfo:
    """Information about a file conflict"""
    
    def __init__(self, source_path: str, destination_path: str):
        self.source_path = Path(source_path)
        self.destination_path = Path(destination_path)
        self.source_exists = self.source_path.exists()
        self.dest_exists = self.destination_path.exists()
        
        # File metadata
        self.source_size = 0
        self.dest_size = 0
        self.source_mtime = None
        self.dest_mtime = None
        self.source_hash = None
        self.dest_hash = None
        
        if self.source_exists:
            try:
                stat = self.source_path.stat()
                self.source_size = stat.st_size
                self.source_mtime = datetime.fromtimestamp(stat.st_mtime)
            except OSError:
                pass
        
        if self.dest_exists:
            try:
                stat = self.destination_path.stat()
                self.dest_size = stat.st_size
                self.dest_mtime = datetime.fromtimestamp(stat.st_mtime)
            except OSError:
                pass
    
    def are_files_identical(self) -> bool:
        """Check if source and destination files are identical"""
        if not (self.source_exists and self.dest_exists):
            return False
        
        # Quick size check
        if self.source_size != self.dest_size:
            return False
        
        # Compare file hashes
        return self.get_source_hash() == self.get_dest_hash()
    
    def get_source_hash(self) -> Optional[str]:
        """Get MD5 hash of source file"""
        if self.source_hash is None and self.source_exists:
            self.source_hash = self._calculate_file_hash(self.source_path)
        return self.source_hash
    
    def get_dest_hash(self) -> Optional[str]:
        """Get MD5 hash of destination file"""
        if self.dest_hash is None and self.dest_exists:
            self.dest_hash = self._calculate_file_hash(self.destination_path)
        return self.dest_hash
    
    def _calculate_file_hash(self, file_path: Path) -> Optional[str]:
        """Calculate MD5 hash of a file"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (OSError, IOError):
            return None
    
    def get_comparison_info(self) -> Dict:
        """Get comparison information for decision making"""
        return {
            "source_size": self.source_size,
            "dest_size": self.dest_size,
            "source_newer": self.source_mtime > self.dest_mtime if (self.source_mtime and self.dest_mtime) else None,
            "source_larger": self.source_size > self.dest_size,
            "files_identical": self.are_files_identical(),
            "size_difference": abs(self.source_size - self.dest_size),
            "time_difference": abs((self.source_mtime - self.dest_mtime).total_seconds()) if (self.source_mtime and self.dest_mtime) else None
        }


class ConflictResolver:
    """
    Advanced conflict resolution system for File Organizer Pro
    
    Features:
    - Multiple conflict resolution strategies
    - File content comparison (hashing)
    - Intelligent file naming with conflict detection
    - Backup creation for overwrite operations
    - Customizable resolution rules
    - Detailed conflict logging
    """
    
    def __init__(self, default_strategy: ConflictStrategy = ConflictStrategy.RENAME):
        self.logger = get_logger()
        self.default_strategy = default_strategy
        self.backup_dir = Path("backup") / datetime.now().strftime("%Y%m%d_%H%M%S")
        self.conflict_count = 0
        self.resolution_stats = {}
    
    def resolve_conflict(self, 
                        source_path: str, 
                        destination_path: str,
                        strategy: Optional[ConflictStrategy] = None,
                        dry_run: bool = False) -> str:
        """
        Resolve a file conflict using specified strategy
        
        Args:
            source_path: Source file path
            destination_path: Destination file path
            strategy: Conflict resolution strategy (uses default if None)
            dry_run: Preview mode - don't actually resolve
            
        Returns:
            Final destination path after conflict resolution
            
        Raises:
            FileExistsError: If conflict cannot be resolved
        """
        if strategy is None:
            strategy = self.default_strategy
        
        # Create conflict info
        conflict = ConflictInfo(source_path, destination_path)
        
        if not conflict.dest_exists:
            # No conflict - return original destination
            return destination_path
        
        self.conflict_count += 1
        self.logger.warning(f"⚠️ File conflict detected: {destination_path}")
        
        # Track resolution strategy usage
        strategy_name = strategy.value
        if strategy_name not in self.resolution_stats:
            self.resolution_stats[strategy_name] = 0
        self.resolution_stats[strategy_name] += 1
        
        # Apply resolution strategy
        try:
            if strategy == ConflictStrategy.SKIP:
                return self._resolve_skip(conflict, dry_run)
            elif strategy == ConflictStrategy.RENAME:
                return self._resolve_rename(conflict, dry_run)
            elif strategy == ConflictStrategy.OVERWRITE:
                return self._resolve_overwrite(conflict, dry_run)
            elif strategy == ConflictStrategy.BACKUP:
                return self._resolve_backup(conflict, dry_run)
            elif strategy == ConflictStrategy.SIZE_COMPARE:
                return self._resolve_size_compare(conflict, dry_run)
            elif strategy == ConflictStrategy.DATE_COMPARE:
                return self._resolve_date_compare(conflict, dry_run)
            elif strategy == ConflictStrategy.HASH_COMPARE:
                return self._resolve_hash_compare(conflict, dry_run)
            else:
                raise ValueError(f"Unknown conflict strategy: {strategy}")
                
        except Exception as e:
            self.logger.error(f"❌ Conflict resolution failed: {e}")
            raise FileExistsError(f"Cannot resolve conflict: {e}")
    
    def _resolve_skip(self, conflict: ConflictInfo, dry_run: bool) -> str:
        """Skip conflicting file (don't move/copy)"""
        self.logger.info(f"⏭️ Skipping conflicting file: {conflict.source_path.name}")
        raise FileExistsError("File skipped due to conflict")
    
    def _resolve_rename(self, conflict: ConflictInfo, dry_run: bool) -> str:
        """Rename source file with number suffix"""
        dest_path = conflict.destination_path
        counter = 1
        
        while True:
            # Generate new filename with counter
            stem = dest_path.stem
            suffix = dest_path.suffix
            parent = dest_path.parent
            
            new_filename = f"{stem}_{counter}{suffix}"
            new_path = parent / new_filename
            
            if not new_path.exists():
                self.logger.info(f"🔄 Renamed to avoid conflict: {new_filename}")
                return str(new_path)
            
            counter += 1
            
            # Prevent infinite loop
            if counter > 9999:
                raise FileExistsError("Cannot generate unique filename - too many conflicts")
    
    def _resolve_overwrite(self, conflict: ConflictInfo, dry_run: bool) -> str:
        """Overwrite existing file"""
        if not dry_run:
            # Remove existing file
            try:
                conflict.destination_path.unlink()
                self.logger.info(f"🗑️ Overwriting existing file: {conflict.destination_path.name}")
            except OSError as e:
                raise FileExistsError(f"Cannot overwrite file: {e}")
        else:
            self.logger.info(f"🔄 Would overwrite: {conflict.destination_path.name}")
        
        return str(conflict.destination_path)
    
    def _resolve_backup(self, conflict: ConflictInfo, dry_run: bool) -> str:
        """Create backup of existing file, then overwrite"""
        if not dry_run:
            # Create backup directory
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{conflict.destination_path.stem}_{timestamp}{conflict.destination_path.suffix}"
            backup_path = self.backup_dir / backup_filename
            
            # Create backup
            try:
                shutil.copy2(conflict.destination_path, backup_path)
                self.logger.info(f"💾 Created backup: {backup_path}")
                
                # Remove original
                conflict.destination_path.unlink()
                
            except OSError as e:
                raise FileExistsError(f"Cannot create backup: {e}")
        else:
            self.logger.info(f"🔄 Would backup and overwrite: {conflict.destination_path.name}")
        
        return str(conflict.destination_path)
    
    def _resolve_size_compare(self, conflict: ConflictInfo, dry_run: bool) -> str:
        """Keep the larger file"""
        comparison = conflict.get_comparison_info()
        
        if conflict.source_size > conflict.dest_size:
            # Source is larger - overwrite destination
            self.logger.info(f"📏 Keeping larger file (source): {conflict.source_size} > {conflict.dest_size} bytes")
            return self._resolve_overwrite(conflict, dry_run)
        elif conflict.source_size < conflict.dest_size:
            # Destination is larger - skip source
            self.logger.info(f"📏 Keeping larger file (destination): {conflict.dest_size} > {conflict.source_size} bytes")
            raise FileExistsError("Destination file is larger - keeping existing")
        else:
            # Same size - fall back to hash comparison
            self.logger.info("📏 Files are same size - comparing content")
            return self._resolve_hash_compare(conflict, dry_run)
    
    def _resolve_date_compare(self, conflict: ConflictInfo, dry_run: bool) -> str:
        """Keep the newer file"""
        if not (conflict.source_mtime and conflict.dest_mtime):
            # Cannot compare dates - fall back to rename
            self.logger.warning("⚠️ Cannot compare file dates - falling back to rename")
            return self._resolve_rename(conflict, dry_run)
        
        if conflict.source_mtime > conflict.dest_mtime:
            # Source is newer - overwrite destination
            self.logger.info(f"📅 Keeping newer file (source): {conflict.source_mtime} > {conflict.dest_mtime}")
            return self._resolve_overwrite(conflict, dry_run)
        elif conflict.source_mtime < conflict.dest_mtime:
            # Destination is newer - skip source
            self.logger.info(f"📅 Keeping newer file (destination): {conflict.dest_mtime} > {conflict.source_mtime}")
            raise FileExistsError("Destination file is newer - keeping existing")
        else:
            # Same date - fall back to hash comparison
            self.logger.info("📅 Files have same date - comparing content")
            return self._resolve_hash_compare(conflict, dry_run)
    
    def _resolve_hash_compare(self, conflict: ConflictInfo, dry_run: bool) -> str:
        """Compare file contents and keep if different, skip if identical"""
        if conflict.are_files_identical():
            # Files are identical - skip
            self.logger.info(f"🔍 Files are identical - skipping duplicate")
            raise FileExistsError("Files are identical - skipping duplicate")
        else:
            # Files are different - rename to keep both
            self.logger.info(f"🔍 Files are different - keeping both with rename")
            return self._resolve_rename(conflict, dry_run)
    
    def generate_safe_filename(self, 
                              filename: str, 
                              directory: Path,
                              max_attempts: int = 9999) -> str:
        """
        Generate a safe filename that doesn't conflict with existing files
        
        Args:
            filename: Original filename
            directory: Target directory
            max_attempts: Maximum number of attempts to find unique name
            
        Returns:
            Safe filename (may be modified with suffix)
        """
        file_path = directory / filename
        
        if not file_path.exists():
            return filename
        
        # Generate alternative names
        path_obj = Path(filename)
        stem = path_obj.stem
        suffix = path_obj.suffix
        
        for counter in range(1, max_attempts + 1):
            new_filename = f"{stem}_{counter}{suffix}"
            new_path = directory / new_filename
            
            if not new_path.exists():
                self.logger.debug(f"🔄 Generated safe filename: {new_filename}")
                return new_filename
        
        # If we get here, we couldn't find a unique name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # microseconds truncated
        fallback_filename = f"{stem}_{timestamp}{suffix}"
        self.logger.warning(f"⚠️ Using timestamp fallback: {fallback_filename}")
        return fallback_filename
    
    def analyze_conflicts(self, 
                         source_files: List[str], 
                         destination_dir: str) -> Dict:
        """
        Analyze potential conflicts before operation
        
        Args:
            source_files: List of source file paths
            destination_dir: Destination directory
            
        Returns:
            Dictionary with conflict analysis
        """
        dest_path = Path(destination_dir)
        analysis = {
            "total_files": len(source_files),
            "conflicts": 0,
            "identical_files": 0,
            "size_conflicts": 0,
            "date_conflicts": 0,
            "potential_overwrites": 0,
            "conflict_details": []
        }
        
        for source_file in source_files:
            source_path = Path(source_file)
            dest_file_path = dest_path / source_path.name
            
            if dest_file_path.exists():
                conflict = ConflictInfo(source_file, str(dest_file_path))
                comparison = conflict.get_comparison_info()
                
                analysis["conflicts"] += 1
                
                conflict_detail = {
                    "source": source_file,
                    "destination": str(dest_file_path),
                    "source_size": conflict.source_size,
                    "dest_size": conflict.dest_size,
                    "identical": comparison["files_identical"]
                }
                
                if comparison["files_identical"]:
                    analysis["identical_files"] += 1
                    conflict_detail["recommendation"] = "skip_identical"
                elif comparison["source_larger"]:
                    analysis["size_conflicts"] += 1
                    conflict_detail["recommendation"] = "overwrite_larger"
                elif comparison.get("source_newer"):
                    analysis["date_conflicts"] += 1
                    conflict_detail["recommendation"] = "overwrite_newer"
                else:
                    analysis["potential_overwrites"] += 1
                    conflict_detail["recommendation"] = "rename_safe"
                
                analysis["conflict_details"].append(conflict_detail)
        
        return analysis
    
    def get_conflict_stats(self) -> Dict:
        """Get statistics about conflict resolution"""
        return {
            "total_conflicts": self.conflict_count,
            "resolution_strategies": self.resolution_stats.copy(),
            "backup_directory": str(self.backup_dir) if self.backup_dir.exists() else None
        }
    
    def set_backup_directory(self, backup_dir: str):
        """Set custom backup directory"""
        self.backup_dir = Path(backup_dir)
        self.logger.info(f"💾 Backup directory set to: {self.backup_dir}")


# Global conflict resolver instance
_global_resolver: Optional[ConflictResolver] = None


def get_conflict_resolver() -> ConflictResolver:
    """
    Get or create the global conflict resolver instance
    
    Returns:
        ConflictResolver instance
    """
    global _global_resolver
    if _global_resolver is None:
        _global_resolver = ConflictResolver()
    return _global_resolver


# Convenience functions
def resolve_file_conflict(source: str, 
                         destination: str,
                         strategy: str = "rename",
                         dry_run: bool = False) -> str:
    """
    Quick conflict resolution
    
    Args:
        source: Source file path
        destination: Destination file path
        strategy: Resolution strategy name
        dry_run: Preview mode
        
    Returns:
        Resolved destination path
    """
    resolver = get_conflict_resolver()
    strategy_enum = ConflictStrategy(strategy)
    return resolver.resolve_conflict(source, destination, strategy_enum, dry_run)


def generate_unique_filename(filename: str, directory: str) -> str:
    """Quick unique filename generation"""
    resolver = get_conflict_resolver()
    return resolver.generate_safe_filename(filename, Path(directory))


def analyze_potential_conflicts(source_files: List[str], destination_dir: str) -> Dict:
    """Quick conflict analysis"""
    resolver = get_conflict_resolver()
    return resolver.analyze_conflicts(source_files, destination_dir)
