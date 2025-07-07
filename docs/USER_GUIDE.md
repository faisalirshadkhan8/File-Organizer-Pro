# File Organizer Pro User Guide

## Overview

File Organizer Pro is a powerful command-line tool that automatically sorts and organizes files in any directory based on file type or date.

## Features

- **Type-based Organization**: Groups files into categories (Documents, Images, Videos, etc.)
- **Date-based Organization**: Sorts files into YYYY-MM-DD folder structure
- **Dry-run Mode**: Preview changes before applying them
- **Conflict Resolution**: Automatically handles duplicate files
- **Customizable Categories**: Define your own file type mappings
- **Detailed Logging**: Track all operations with comprehensive logs

## Getting Started

1. Install dependencies: `pip install -r requirements.txt`
2. Run the organizer: `python -m src.organizer [directory]`
3. Use `--dry-run` to preview changes first

## Configuration

Customize file categories by editing `config/custom_categories.json`

## Safety Features

- Backup creation before major operations
- Conflict resolution with auto-renaming
- Validation of paths and permissions
- Comprehensive error handling
