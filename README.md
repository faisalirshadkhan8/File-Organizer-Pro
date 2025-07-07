# File Organizer Pro

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Status](https://img.shields.io/badge/status-stable-green.svg)

A powerful and user-friendly file organization tool with both graphical and command-line interfaces. Automatically sorts and organizes files by type or date with advanced features like conflict resolution and dry-run mode.

## 🚀 Features

- **🖥️ Graphical Interface**: Modern, intuitive GUI for easy file organization
- **💻 Command Line Interface**: Full CLI for automation and scripting
- **📁 Type-based Organization**: Automatically groups files into categories (Documents, Images, Videos, etc.)
- **📅 Date-based Organization**: Sorts files into date-based folder structures
- **👀 Preview Mode**: See exactly what will happen before making changes
- **🔧 Conflict Resolution**: Smart handling of duplicate files with multiple strategies
- **⚙️ Customizable Categories**: Define your own file type mappings
- **📊 Detailed Logging**: Track all operations with comprehensive logs
- **✅ Safety First**: Built-in validation and error handling

## 📦 Installation

### Quick Setup
```bash
git clone https://github.com/yourusername/file-organizer-pro.git
cd file-organizer-pro
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Linux/Mac
pip install -r requirements.txt
pip install -r requirements-gui.txt
```

## 🎯 Usage

### Graphical Interface (Recommended)
```bash
# Windows
launch_gui.bat

# Or manually
venv\Scripts\activate
python file_organizer_gui.py
```

### Command Line Interface
```bash
# Activate virtual environment first
venv\Scripts\activate

# Organize by file type (with preview)
python file_organizer_cli.py --mode type --dry-run ./downloads

# Organize by date
python file_organizer_cli.py --mode date ./documents

# Organize files to specific destination
python file_organizer_cli.py --mode type ./source --dest ./organized
```

### Advanced Usage
```bash
# Use custom configuration
python -m src.organizer --config ./my_config.json ./files

# Enable verbose logging
python -m src.organizer --mode type --verbose ./downloads
```

## 📋 Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--mode` | Organization mode (`type` or `date`) | `--mode type` |
| `--dry-run` | Preview changes without executing | `--dry-run` |
| `--verbose` | Enable detailed logging | `--verbose` |
| `--config` | Path to custom configuration file | `--config ./custom.json` |

## ⚙️ Configuration

Customize file categories by editing `config/custom_categories.json`:

```json
{
  "categories": {
    "MyDocuments": [".pdf", ".doc", ".txt"],
    "MyImages": [".jpg", ".png", ".gif"],
    "MyCode": [".py", ".js", ".html"]
  }
}
```

## 🏗️ Project Structure

```
file-organizer-pro/
├── src/                    # Core source code
│   ├── organizer.py        # Main CLI entry point
│   ├── file_manager.py     # File operations engine
│   ├── category_mapper.py  # File-type classification
│   ├── date_organizer.py   # Date-based sorting logic
│   └── utils/              # Utilities
├── tests/                  # Comprehensive tests
├── config/                 # Configuration files
├── docs/                   # Documentation
└── scripts/                # Helper scripts
```

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src/

# Generate test files for demo
python scripts/make_demo_files.py
```

## 🛡️ Safety Features

- **Backup Creation**: Automatic backups before major operations
- **Conflict Resolution**: Smart handling of duplicate files
- **Path Validation**: Comprehensive checks for paths and permissions
- **Error Handling**: Robust error recovery and reporting
- **Dry-run Mode**: Always test before making changes

## 📚 Documentation

- [CLI Reference Guide](docs/CLI_REFERENCE.md)
- [User Guide](docs/USER_GUIDE.md)

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with Python and love ❤️
- Inspired by the need for better file organization
- Thanks to all contributors and users

---

**Made with ❤️ by Muhammad Faisal Irhsad**
