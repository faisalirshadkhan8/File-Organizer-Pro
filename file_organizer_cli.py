#!/usr/bin/env python3
"""
File Organizer Pro - Command Line Interface
A powerful CLI tool for organizing files by type or date.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.organizer import main
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

if __name__ == "__main__":
    main()
