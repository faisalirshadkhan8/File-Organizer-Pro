# Date-based file organization and sorting logic

import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from enum import Enum

from .utils.logger import get_logger
from .utils.validator import get_validator, ValidationError


class DateSource(Enum):
    """Sources for file date information"""
    CREATION_TIME = "creation"          # File creation time
    MODIFICATION_TIME = "modification"  # Last modification time
    ACCESS_TIME = "access"             # Last access time
    FILENAME_PATTERN = "filename"      # Extract from filename
    EXIF_DATA = "exif"                 # From image EXIF data
    AUTO_DETECT = "auto"               # Automatically choose best source


class DateFormat(Enum):
    """Date folder organization formats"""
    YYYY = "YYYY"                      # 2024
    YYYY_MM = "YYYY-MM"               # 2024-01
    YYYY_MM_DD = "YYYY-MM-DD"         # 2024-01-15
    YYYY_QQ = "YYYY-QQ"               # 2024-Q1
    YYYY_WW = "YYYY-WW"               # 2024-W03
    MM_YYYY = "MM-YYYY"               # 01-2024
    MMM_YYYY = "MMM-YYYY"             # Jan-2024
    YYYY_MMM = "YYYY-MMM"             # 2024-Jan
    YYYY_MMMM = "YYYY-MMMM"           # 2024-January
    CUSTOM = "custom"                  # User-defined format


class DateRange:
    """Represents a date range for filtering"""
    
    def __init__(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None):
        self.start_date = start_date
        self.end_date = end_date
    
    def contains(self, date: datetime) -> bool:
        """Check if date falls within range"""
        if self.start_date and date < self.start_date:
            return False
        if self.end_date and date > self.end_date:
            return False
        return True
    
    def __str__(self) -> str:
        start = self.start_date.strftime("%Y-%m-%d") if self.start_date else "∞"
        end = self.end_date.strftime("%Y-%m-%d") if self.end_date else "∞"
        return f"[{start} to {end}]"


class FileDate:
    """Container for file date information"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.creation_date = None
        self.modification_date = None
        self.access_date = None
        self.filename_date = None
        self.exif_date = None
        self.best_date = None
        self.date_source = None
        
        self._extract_all_dates()
        self._determine_best_date()
    
    def _extract_all_dates(self):
        """Extract all available date information"""
        if not self.file_path.exists():
            return
        
        try:
            # Get filesystem dates
            stat_info = self.file_path.stat()
            self.creation_date = datetime.fromtimestamp(stat_info.st_ctime)
            self.modification_date = datetime.fromtimestamp(stat_info.st_mtime)
            self.access_date = datetime.fromtimestamp(stat_info.st_atime)
            
            # Extract date from filename
            self.filename_date = self._extract_date_from_filename()
            
            # Extract EXIF date for images
            if self._is_image_file():
                self.exif_date = self._extract_exif_date()
                
        except (OSError, ValueError) as e:
            logger = get_logger()
            logger.warning(f"⚠️ Could not extract dates from {self.file_path}: {e}")
    
    def _determine_best_date(self):
        """Determine the most reliable date to use"""
        # Priority order: EXIF > Filename > Creation > Modification
        if self.exif_date:
            self.best_date = self.exif_date
            self.date_source = DateSource.EXIF_DATA
        elif self.filename_date:
            self.best_date = self.filename_date
            self.date_source = DateSource.FILENAME_PATTERN
        elif self.creation_date:
            self.best_date = self.creation_date
            self.date_source = DateSource.CREATION_TIME
        elif self.modification_date:
            self.best_date = self.modification_date
            self.date_source = DateSource.MODIFICATION_TIME
        else:
            self.best_date = datetime.now()
            self.date_source = None
    
    def _extract_date_from_filename(self) -> Optional[datetime]:
        """Extract date from filename using common patterns"""
        filename = self.file_path.name
        
        # Common date patterns in filenames
        patterns = [
            r'(\d{4})-(\d{2})-(\d{2})',          # YYYY-MM-DD
            r'(\d{4})(\d{2})(\d{2})',            # YYYYMMDD
            r'(\d{2})-(\d{2})-(\d{4})',          # MM-DD-YYYY
            r'(\d{2})(\d{2})(\d{4})',            # MMDDYYYY
            r'(\d{4})-(\d{2})',                  # YYYY-MM
            r'(\d{4})(\d{2})',                   # YYYYMM
            r'IMG_(\d{4})(\d{2})(\d{2})',        # IMG_YYYYMMDD
            r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})',  # YYYY-MM-DD_HH-MM-SS
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        # Determine if it's YYYY-MM-DD or MM-DD-YYYY
                        if len(groups[0]) == 4:  # YYYY-MM-DD
                            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        else:  # MM-DD-YYYY
                            month, day, year = int(groups[0]), int(groups[1]), int(groups[2])
                        
                        return datetime(year, month, day)
                    elif len(groups) == 2:  # YYYY-MM
                        year, month = int(groups[0]), int(groups[1])
                        return datetime(year, month, 1)
                    elif len(groups) == 6:  # YYYY-MM-DD_HH-MM-SS
                        year, month, day, hour, minute, second = map(int, groups)
                        return datetime(year, month, day, hour, minute, second)
                        
                except ValueError:
                    continue
        
        return None
    
    def _is_image_file(self) -> bool:
        """Check if file is an image that might contain EXIF data"""
        image_extensions = {'.jpg', '.jpeg', '.tiff', '.tif', '.raw', '.cr2', '.nef', '.arw'}
        return self.file_path.suffix.lower() in image_extensions
    
    def _extract_exif_date(self) -> Optional[datetime]:
        """Extract date from EXIF data (requires PIL/Pillow)"""
        try:
            from PIL import Image
            from PIL.ExifTags import TAGS
            
            with Image.open(self.file_path) as img:
                exif_data = img.getexif()
                
                # Look for date tags
                date_tags = ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']
                
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    
                    if tag_name in date_tags and isinstance(value, str):
                        # Parse EXIF date format: "YYYY:MM:DD HH:MM:SS"
                        try:
                            return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                        except ValueError:
                            continue
                            
        except (ImportError, OSError, ValueError):
            # PIL not available or file cannot be read
            pass
        
        return None
    
    def get_date(self, source: DateSource = DateSource.AUTO_DETECT) -> Optional[datetime]:
        """Get date from specified source"""
        if source == DateSource.AUTO_DETECT:
            return self.best_date
        elif source == DateSource.CREATION_TIME:
            return self.creation_date
        elif source == DateSource.MODIFICATION_TIME:
            return self.modification_date
        elif source == DateSource.ACCESS_TIME:
            return self.access_date
        elif source == DateSource.FILENAME_PATTERN:
            return self.filename_date
        elif source == DateSource.EXIF_DATA:
            return self.exif_date
        else:
            return self.best_date


class DateOrganizer:
    """
    Advanced date-based file organization system
    
    Features:
    - Multiple date sources (filesystem, filename, EXIF)
    - Flexible date formats for folder organization
    - Date range filtering
    - Smart date detection and validation
    - Duplicate date handling
    - Time zone support
    - Custom date parsing patterns
    """
    
    def __init__(self):
        self.logger = get_logger()
        self.validator = get_validator()
        
        # Configuration
        self.default_date_source = DateSource.AUTO_DETECT
        self.default_format = DateFormat.YYYY_MM_DD
        self.handle_unknown_dates = True
        self.unknown_date_folder = "Unknown-Date"
        
        # Statistics
        self.processed_files = 0
        self.date_extraction_stats = {}
    
    def organize_files_by_date(self,
                              file_paths: List[str],
                              date_source: DateSource = DateSource.AUTO_DETECT,
                              date_format: DateFormat = DateFormat.YYYY_MM_DD,
                              date_range: Optional[DateRange] = None,
                              custom_format: Optional[str] = None) -> Dict[str, List[str]]:
        """
        Organize files into date-based groups
        
        Args:
            file_paths: List of file paths to organize
            date_source: Source for date information
            date_format: Format for date folder names
            date_range: Optional date range filter
            custom_format: Custom strftime format string
            
        Returns:
            Dictionary mapping date folder names to file lists
        """
        date_groups = {}
        self.processed_files = 0
        self.date_extraction_stats = {}
        
        self.logger.info(f"🗓️ Organizing {len(file_paths)} files by date")
        self.logger.info(f"📅 Date source: {date_source.value}, Format: {date_format.value}")
        
        for file_path in file_paths:
            try:
                # Extract file date information
                file_date = FileDate(file_path)
                selected_date = file_date.get_date(date_source)
                
                # Track date extraction statistics
                source_used = file_date.date_source.value if file_date.date_source else "unknown"
                self.date_extraction_stats[source_used] = self.date_extraction_stats.get(source_used, 0) + 1
                
                # Apply date range filter if specified
                if date_range and selected_date and not date_range.contains(selected_date):
                    self.logger.debug(f"📅 File {Path(file_path).name} outside date range {date_range}")
                    continue
                
                # Generate folder name
                if selected_date:
                    folder_name = self._format_date_folder(selected_date, date_format, custom_format)
                else:
                    if self.handle_unknown_dates:
                        folder_name = self.unknown_date_folder
                    else:
                        continue
                
                # Add to appropriate group
                if folder_name not in date_groups:
                    date_groups[folder_name] = []
                
                date_groups[folder_name].append(file_path)
                self.processed_files += 1
                
                self.logger.debug(f"📁 {Path(file_path).name} → {folder_name} "
                                f"({selected_date.strftime('%Y-%m-%d %H:%M') if selected_date else 'no date'})")
                
            except Exception as e:
                self.logger.error(f"❌ Error processing {file_path}: {e}")
                
                # Add to unknown date folder if handling unknowns
                if self.handle_unknown_dates:
                    if self.unknown_date_folder not in date_groups:
                        date_groups[self.unknown_date_folder] = []
                    date_groups[self.unknown_date_folder].append(file_path)
        
        # Log statistics
        self._log_organization_stats(date_groups)
        
        return date_groups
    
    def _format_date_folder(self, 
                           date: datetime, 
                           date_format: DateFormat,
                           custom_format: Optional[str] = None) -> str:
        """Format date into folder name"""
        if date_format == DateFormat.CUSTOM and custom_format:
            return date.strftime(custom_format)
        elif date_format == DateFormat.YYYY:
            return date.strftime("%Y")
        elif date_format == DateFormat.YYYY_MM:
            return date.strftime("%Y-%m")
        elif date_format == DateFormat.YYYY_MM_DD:
            return date.strftime("%Y-%m-%d")
        elif date_format == DateFormat.YYYY_QQ:
            quarter = (date.month - 1) // 3 + 1
            return f"{date.year}-Q{quarter}"
        elif date_format == DateFormat.YYYY_WW:
            week = date.isocalendar()[1]
            return f"{date.year}-W{week:02d}"
        elif date_format == DateFormat.MM_YYYY:
            return date.strftime("%m-%Y")
        elif date_format == DateFormat.MMM_YYYY:
            return date.strftime("%b-%Y")
        elif date_format == DateFormat.YYYY_MMM:
            return date.strftime("%Y-%b")
        elif date_format == DateFormat.YYYY_MMMM:
            return date.strftime("%Y-%B")
        else:
            return date.strftime("%Y-%m-%d")  # Default fallback
    
    def analyze_date_distribution(self, file_paths: List[str]) -> Dict:
        """
        Analyze date distribution of files
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            Dictionary with date distribution statistics
        """
        analysis = {
            "total_files": len(file_paths),
            "files_with_dates": 0,
            "files_without_dates": 0,
            "date_range": {"earliest": None, "latest": None},
            "date_sources": {},
            "yearly_distribution": {},
            "monthly_distribution": {},
            "problematic_files": []
        }
        
        dates = []
        
        for file_path in file_paths:
            try:
                file_date = FileDate(file_path)
                
                if file_date.best_date:
                    analysis["files_with_dates"] += 1
                    dates.append(file_date.best_date)
                    
                    # Track date sources
                    source = file_date.date_source.value if file_date.date_source else "unknown"
                    analysis["date_sources"][source] = analysis["date_sources"].get(source, 0) + 1
                    
                    # Yearly distribution
                    year = file_date.best_date.year
                    analysis["yearly_distribution"][year] = analysis["yearly_distribution"].get(year, 0) + 1
                    
                    # Monthly distribution
                    month_key = f"{file_date.best_date.year}-{file_date.best_date.month:02d}"
                    analysis["monthly_distribution"][month_key] = analysis["monthly_distribution"].get(month_key, 0) + 1
                    
                else:
                    analysis["files_without_dates"] += 1
                    analysis["problematic_files"].append(file_path)
                    
            except Exception as e:
                analysis["problematic_files"].append(f"{file_path}: {str(e)}")
        
        # Calculate date range
        if dates:
            analysis["date_range"]["earliest"] = min(dates)
            analysis["date_range"]["latest"] = max(dates)
        
        return analysis
    
    def get_files_in_date_range(self,
                               file_paths: List[str],
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None,
                               date_source: DateSource = DateSource.AUTO_DETECT) -> List[str]:
        """
        Filter files by date range
        
        Args:
            file_paths: List of file paths to filter
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)
            date_source: Source for date information
            
        Returns:
            List of file paths within the date range
        """
        date_range = DateRange(start_date, end_date)
        filtered_files = []
        
        self.logger.info(f"🔍 Filtering {len(file_paths)} files by date range: {date_range}")
        
        for file_path in file_paths:
            try:
                file_date = FileDate(file_path)
                selected_date = file_date.get_date(date_source)
                
                if selected_date and date_range.contains(selected_date):
                    filtered_files.append(file_path)
                    
            except Exception as e:
                self.logger.warning(f"⚠️ Error filtering {file_path}: {e}")
        
        self.logger.info(f"📊 Found {len(filtered_files)} files in date range")
        return filtered_files
    
    def suggest_date_format(self, file_paths: List[str]) -> DateFormat:
        """
        Suggest optimal date format based on file date distribution
        
        Args:
            file_paths: List of file paths to analyze
            
        Returns:
            Suggested DateFormat
        """
        analysis = self.analyze_date_distribution(file_paths)
        
        if not analysis["files_with_dates"]:
            return DateFormat.YYYY_MM_DD  # Default
        
        # Calculate date span
        earliest = analysis["date_range"]["earliest"]
        latest = analysis["date_range"]["latest"]
        
        if not (earliest and latest):
            return DateFormat.YYYY_MM_DD
        
        date_span = latest - earliest
        
        # Suggest format based on span
        if date_span.days <= 31:  # Within a month
            return DateFormat.YYYY_MM_DD
        elif date_span.days <= 365:  # Within a year
            return DateFormat.YYYY_MM
        elif date_span.days <= 365 * 3:  # Within 3 years
            return DateFormat.YYYY_MM
        else:  # Multiple years
            return DateFormat.YYYY
    
    def _log_organization_stats(self, date_groups: Dict[str, List[str]]):
        """Log organization statistics"""
        total_folders = len(date_groups)
        total_files = sum(len(files) for files in date_groups.values())
        
        self.logger.info(f"📊 Date organization complete:")
        self.logger.info(f"   📁 Created {total_folders} date folders")
        self.logger.info(f"   📄 Organized {total_files} files")
        
        # Log date source statistics
        self.logger.info("📅 Date sources used:")
        for source, count in self.date_extraction_stats.items():
            percentage = (count / self.processed_files) * 100 if self.processed_files > 0 else 0
            self.logger.info(f"   {source}: {count} files ({percentage:.1f}%)")
        
        # Log largest folders
        sorted_folders = sorted(date_groups.items(), key=lambda x: len(x[1]), reverse=True)
        self.logger.info("📈 Largest date folders:")
        for folder, files in sorted_folders[:5]:
            self.logger.info(f"   {folder}: {len(files)} files")


# Global date organizer instance
_global_organizer: Optional[DateOrganizer] = None


def get_date_organizer() -> DateOrganizer:
    """
    Get or create the global date organizer instance
    
    Returns:
        DateOrganizer instance
    """
    global _global_organizer
    if _global_organizer is None:
        _global_organizer = DateOrganizer()
    return _global_organizer


# Convenience functions
def organize_by_date(file_paths: List[str],
                    date_format: str = "YYYY-MM-DD",
                    date_source: str = "auto") -> Dict[str, List[str]]:
    """Quick date-based organization"""
    organizer = get_date_organizer()
    format_enum = DateFormat(date_format)
    source_enum = DateSource(date_source)
    return organizer.organize_files_by_date(file_paths, source_enum, format_enum)


def analyze_file_dates(file_paths: List[str]) -> Dict:
    """Quick date analysis"""
    organizer = get_date_organizer()
    return organizer.analyze_date_distribution(file_paths)


def filter_by_date_range(file_paths: List[str],
                        start_date: str,
                        end_date: str) -> List[str]:
    """
    Quick date range filtering
    
    Args:
        file_paths: List of file paths
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        Filtered file list
    """
    organizer = get_date_organizer()
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    return organizer.get_files_in_date_range(file_paths, start, end)
