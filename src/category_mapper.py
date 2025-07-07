# File-type classification system

import json
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from .utils.logger import get_logger
from .utils.validator import get_validator, ValidationError


class CategoryMapper:
    """
    Advanced file categorization system for File Organizer Pro
    
    Features:
    - Extension-based classification
    - MIME type detection
    - Custom category definitions
    - Configurable category mappings
    - Magic number file type detection
    - Category priority system
    """
    
    # Default file categories with extensions
    DEFAULT_CATEGORIES = {
        "Documents": [
            ".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".pages",
            ".xls", ".xlsx", ".csv", ".ods", ".numbers",
            ".ppt", ".pptx", ".odp", ".key",
            ".epub", ".mobi", ".azw", ".azw3"
        ],
        "Images": [
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
            ".svg", ".webp", ".ico", ".raw", ".cr2", ".nef", ".arw",
            ".heic", ".heif", ".avif"
        ],
        "Videos": [
            ".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm",
            ".m4v", ".3gp", ".mpg", ".mpeg", ".m2v", ".asf"
        ],
        "Audio": [
            ".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a",
            ".opus", ".aiff", ".au", ".ra", ".ape"
        ],
        "Archives": [
            ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz",
            ".tar.gz", ".tar.bz2", ".tar.xz", ".dmg", ".iso"
        ],
        "Code": [
            ".py", ".js", ".html", ".css", ".cpp", ".c", ".h", ".hpp",
            ".java", ".php", ".rb", ".go", ".rs", ".swift", ".kt",
            ".ts", ".jsx", ".tsx", ".vue", ".sql", ".json", ".xml",
            ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf"
        ],
        "Executables": [
            ".exe", ".msi", ".app", ".deb", ".rpm", ".dmg", ".pkg",
            ".apk", ".ipa", ".appx", ".snap"
        ],
        "Fonts": [
            ".ttf", ".otf", ".woff", ".woff2", ".eot", ".pfb", ".pfm"
        ],
        "3D_Models": [
            ".obj", ".fbx", ".dae", ".3ds", ".blend", ".max", ".ma", ".mb",
            ".c4d", ".lwo", ".lws", ".ply", ".stl"
        ],
        "CAD": [
            ".dwg", ".dxf", ".step", ".stp", ".iges", ".igs", ".sat",
            ".parasolid", ".x_t", ".x_b"
        ],
        "eBooks": [
            ".epub", ".mobi", ".azw", ".azw3", ".fb2", ".lit", ".pdb"
        ],
        "Spreadsheets": [
            ".xls", ".xlsx", ".csv", ".ods", ".numbers", ".tsv"
        ]
    }
    
    # MIME type mappings for additional detection
    MIME_CATEGORIES = {
        "Documents": [
            "application/pdf", "application/msword", "text/plain",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.oasis.opendocument.text"
        ],
        "Images": [
            "image/jpeg", "image/png", "image/gif", "image/bmp",
            "image/tiff", "image/svg+xml", "image/webp"
        ],
        "Videos": [
            "video/mp4", "video/avi", "video/quicktime", "video/x-msvideo",
            "video/webm", "video/x-flv"
        ],
        "Audio": [
            "audio/mpeg", "audio/wav", "audio/flac", "audio/aac",
            "audio/ogg", "audio/x-ms-wma"
        ]
    }
    
    # Magic numbers for file type detection (first few bytes)
    MAGIC_NUMBERS = {
        b'\x89PNG\r\n\x1a\n': "Images",          # PNG
        b'\xff\xd8\xff': "Images",               # JPEG
        b'GIF87a': "Images",                     # GIF87a
        b'GIF89a': "Images",                     # GIF89a
        b'%PDF': "Documents",                    # PDF
        b'PK\x03\x04': "Archives",              # ZIP
        b'Rar!\x1a\x07\x00': "Archives",        # RAR
        b'7z\xbc\xaf\x27\x1c': "Archives",      # 7Z
        b'\x00\x00\x01\x00': "Images",          # ICO
        b'ftyp': "Videos",                       # MP4 (at offset 4)
    }
    
    def __init__(self, config_dir: str = "config"):
        self.logger = get_logger()
        self.validator = get_validator()
        self.config_dir = Path(config_dir)
        
        # Initialize categories
        self.categories = self.DEFAULT_CATEGORIES.copy()
        self.custom_categories = {}
        
        # Load configurations
        self._load_default_config()
        self._load_custom_config()
        
        # Build reverse lookup for fast extension mapping
        self._build_extension_map()
        
        # Initialize MIME types
        mimetypes.init()
    
    def _load_default_config(self):
        """Load default category configuration"""
        default_config_file = self.config_dir / "default_categories.json"
        
        if default_config_file.exists():
            try:
                with open(default_config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    
                if "categories" in config_data:
                    # Merge with defaults, allowing overrides
                    for category, extensions in config_data["categories"].items():
                        if category in self.categories:
                            # Extend existing category
                            self.categories[category].extend(extensions)
                        else:
                            # Add new category
                            self.categories[category] = extensions
                    
                    self.logger.debug(f"✅ Loaded default configuration: {default_config_file}")
                    
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"⚠️ Could not load default config: {e}")
    
    def _load_custom_config(self):
        """Load custom user configuration"""
        custom_config_file = self.config_dir / "custom_categories.json"
        
        if custom_config_file.exists():
            try:
                with open(custom_config_file, 'r', encoding='utf-8') as f:
                    self.custom_categories = json.load(f)
                    
                if "categories" in self.custom_categories:
                    # Custom categories override defaults
                    for category, extensions in self.custom_categories["categories"].items():
                        self.categories[category] = extensions
                    
                    self.logger.debug(f"✅ Loaded custom configuration: {custom_config_file}")
                    
            except (json.JSONDecodeError, IOError) as e:
                self.logger.warning(f"⚠️ Could not load custom config: {e}")
    
    def _build_extension_map(self):
        """Build reverse lookup map: extension -> category"""
        self.extension_map = {}
        
        for category, extensions in self.categories.items():
            for ext in extensions:
                # Normalize extension (lowercase, ensure starts with dot)
                normalized_ext = ext.lower()
                if not normalized_ext.startswith('.'):
                    normalized_ext = '.' + normalized_ext
                
                # Handle conflicts - last category wins
                if normalized_ext in self.extension_map:
                    self.logger.debug(f"🔄 Extension conflict: {normalized_ext} "
                                    f"mapped to {category} (was {self.extension_map[normalized_ext]})")
                
                self.extension_map[normalized_ext] = category
    
    def get_file_category(self, file_path: str) -> Tuple[str, str]:
        """
        Determine the category of a file using multiple detection methods
        
        Args:
            file_path: Path to the file
            
        Returns:
            Tuple of (category_name, detection_method)
            detection_method can be: 'extension', 'mime', 'magic', 'unknown'
        """
        try:
            # Validate file first
            path = self.validator.validate_file_path(file_path)
            
            # Method 1: Extension-based detection (fastest)
            category = self._get_category_by_extension(path)
            if category:
                return category, "extension"
            
            # Method 2: MIME type detection
            category = self._get_category_by_mime(path)
            if category:
                return category, "mime"
            
            # Method 3: Magic number detection (most reliable)
            category = self._get_category_by_magic(path)
            if category:
                return category, "magic"
            
            # No category found
            return "Uncategorized", "unknown"
            
        except ValidationError as e:
            self.logger.error(f"Cannot categorize file {file_path}: {e}")
            return "Uncategorized", "error"
    
    def _get_category_by_extension(self, path: Path) -> Optional[str]:
        """Get category based on file extension"""
        # Handle compound extensions (e.g., .tar.gz)
        suffixes = path.suffixes
        
        # Try compound extension first
        if len(suffixes) >= 2:
            compound_ext = ''.join(suffixes[-2:]).lower()
            if compound_ext in self.extension_map:
                return self.extension_map[compound_ext]
        
        # Try single extension
        if suffixes:
            single_ext = suffixes[-1].lower()
            if single_ext in self.extension_map:
                return self.extension_map[single_ext]
        
        return None
    
    def _get_category_by_mime(self, path: Path) -> Optional[str]:
        """Get category based on MIME type"""
        try:
            mime_type, _ = mimetypes.guess_type(str(path))
            
            if mime_type:
                for category, mime_list in self.MIME_CATEGORIES.items():
                    if mime_type in mime_list:
                        return category
        except Exception:
            pass
        
        return None
    
    def _get_category_by_magic(self, path: Path) -> Optional[str]:
        """Get category based on magic numbers (file signatures)"""
        try:
            with open(path, 'rb') as f:
                # Read first 16 bytes
                header = f.read(16)
                
                # Check magic numbers
                for magic_bytes, category in self.MAGIC_NUMBERS.items():
                    if header.startswith(magic_bytes):
                        return category
                
                # Special case for MP4 - ftyp at offset 4
                if len(header) >= 8 and header[4:8] == b'ftyp':
                    return "Videos"
                    
        except (IOError, OSError):
            pass
        
        return None
    
    def categorize_files(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """
        Categorize a list of files
        
        Args:
            file_paths: List of file paths to categorize
            
        Returns:
            Dictionary mapping category names to lists of file paths
        """
        categorized = {}
        stats = {"total": 0, "categorized": 0, "uncategorized": 0, "errors": 0}
        
        for file_path in file_paths:
            stats["total"] += 1
            
            try:
                category, method = self.get_file_category(file_path)
                
                if category not in categorized:
                    categorized[category] = []
                
                categorized[category].append(file_path)
                
                if category == "Uncategorized":
                    stats["uncategorized"] += 1
                else:
                    stats["categorized"] += 1
                
                self.logger.debug(f"📁 {Path(file_path).name} → {category} ({method})")
                
            except Exception as e:
                stats["errors"] += 1
                self.logger.error(f"Error categorizing {file_path}: {e}")
                
                # Add to uncategorized
                if "Uncategorized" not in categorized:
                    categorized["Uncategorized"] = []
                categorized["Uncategorized"].append(file_path)
        
        # Log statistics
        self.logger.info(f"📊 Categorization complete: {stats['categorized']} categorized, "
                        f"{stats['uncategorized']} uncategorized, {stats['errors']} errors")
        
        return categorized
    
    def get_category_stats(self, categorized_files: Dict[str, List[str]]) -> Dict[str, Dict]:
        """
        Generate statistics for categorized files
        
        Args:
            categorized_files: Dictionary from categorize_files()
            
        Returns:
            Dictionary with detailed statistics per category
        """
        stats = {}
        total_files = sum(len(files) for files in categorized_files.values())
        
        for category, files in categorized_files.items():
            file_count = len(files)
            
            # Calculate sizes
            total_size = 0
            accessible_files = 0
            
            for file_path in files:
                try:
                    path = Path(file_path)
                    if path.exists():
                        total_size += path.stat().st_size
                        accessible_files += 1
                except (OSError, ValueError):
                    pass
            
            stats[category] = {
                "file_count": file_count,
                "percentage": round((file_count / total_files) * 100, 1) if total_files > 0 else 0,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "accessible_files": accessible_files,
                "inaccessible_files": file_count - accessible_files
            }
        
        return stats
    
    def add_custom_category(self, category_name: str, extensions: List[str]) -> bool:
        """
        Add a custom category with extensions
        
        Args:
            category_name: Name of the new category
            extensions: List of file extensions
            
        Returns:
            True if successfully added, False otherwise
        """
        try:
            # Validate extensions
            normalized_extensions = []
            for ext in extensions:
                if not ext.startswith('.'):
                    ext = '.' + ext
                normalized_extensions.append(ext.lower())
            
            # Add to categories
            self.categories[category_name] = normalized_extensions
            
            # Rebuild extension map
            self._build_extension_map()
            
            # Save to custom config
            self._save_custom_config()
            
            self.logger.info(f"✅ Added custom category '{category_name}' with {len(extensions)} extensions")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add custom category: {e}")
            return False
    
    def remove_category(self, category_name: str) -> bool:
        """
        Remove a category
        
        Args:
            category_name: Name of category to remove
            
        Returns:
            True if successfully removed, False otherwise
        """
        try:
            if category_name in self.categories:
                del self.categories[category_name]
                self._build_extension_map()
                self._save_custom_config()
                
                self.logger.info(f"✅ Removed category '{category_name}'")
                return True
            else:
                self.logger.warning(f"⚠️ Category '{category_name}' not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to remove category: {e}")
            return False
    
    def _save_custom_config(self):
        """Save current categories to custom config file"""
        try:
            custom_config_file = self.config_dir / "custom_categories.json"
            
            # Only save non-default categories
            custom_only = {}
            for category, extensions in self.categories.items():
                if category not in self.DEFAULT_CATEGORIES or extensions != self.DEFAULT_CATEGORIES[category]:
                    custom_only[category] = extensions
            
            config_data = {"categories": custom_only}
            
            # Ensure config directory exists
            self.config_dir.mkdir(exist_ok=True)
            
            with open(custom_config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"💾 Saved custom configuration: {custom_config_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save custom config: {e}")
    
    def get_all_categories(self) -> Dict[str, List[str]]:
        """
        Get all available categories and their extensions
        
        Returns:
            Dictionary of category names to extension lists
        """
        return self.categories.copy()
    
    def get_supported_extensions(self) -> Set[str]:
        """
        Get all supported file extensions
        
        Returns:
            Set of all supported extensions
        """
        extensions = set()
        for ext_list in self.categories.values():
            extensions.update(ext_list)
        return extensions
    
    def suggest_category(self, extension: str) -> Optional[str]:
        """
        Suggest a category for an unknown extension
        
        Args:
            extension: File extension
            
        Returns:
            Suggested category name or None
        """
        # Normalize extension
        ext = extension.lower()
        if not ext.startswith('.'):
            ext = '.' + ext
        
        # Simple heuristics based on common patterns
        if ext in ['.txt', '.md', '.rst']:
            return "Documents"
        elif ext in ['.log', '.cfg', '.ini']:
            return "System"
        elif ext.endswith('rc') or ext in ['.sh', '.bat', '.ps1']:
            return "Scripts"
        elif ext in ['.tmp', '.temp', '.bak', '.old']:
            return "Temporary"
        
        return None


# Global category mapper instance
_global_mapper: Optional[CategoryMapper] = None


def get_category_mapper() -> CategoryMapper:
    """
    Get or create the global category mapper instance
    
    Returns:
        CategoryMapper instance
    """
    global _global_mapper
    if _global_mapper is None:
        _global_mapper = CategoryMapper()
    return _global_mapper


# Convenience functions
def categorize_file(file_path: str) -> Tuple[str, str]:
    """Quick file categorization"""
    return get_category_mapper().get_file_category(file_path)


def categorize_directory(directory_path: str) -> Dict[str, List[str]]:
    """
    Categorize all files in a directory
    
    Args:
        directory_path: Directory to scan
        
    Returns:
        Dictionary mapping categories to file lists
    """
    try:
        mapper = get_category_mapper()
        validator = get_validator()
        
        # Validate directory
        dir_path = validator.validate_source_directory(directory_path)
        
        # Get all files
        files = []
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                files.append(str(file_path))
        
        # Categorize files
        return mapper.categorize_files(files)
        
    except ValidationError as e:
        logger = get_logger()
        logger.error(f"Cannot categorize directory {directory_path}: {e}")
        return {}


def get_category_info() -> Dict[str, List[str]]:
    """Get information about all available categories"""
    return get_category_mapper().get_all_categories()
