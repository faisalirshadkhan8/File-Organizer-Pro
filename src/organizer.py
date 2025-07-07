# Main CLI entry point for File Organizer Pro

import sys
import click
import time
from pathlib import Path
from typing import Optional

from .utils.logger import setup_logging, get_logger
from .utils.validator import get_validator, ValidationError, is_safe_to_organize
from .file_manager import get_file_manager, OrganizationResult
from .category_mapper import get_category_mapper
from .date_organizer import get_date_organizer, DateFormat, DateSource
from .utils.conflict_resolver import get_conflict_resolver, ConflictStrategy


# Version information
__version__ = "1.0.0"
__app_name__ = "File Organizer Pro"


class Config:
    """Configuration class for CLI options"""
    def __init__(self):
        self.verbose = False
        self.dry_run = False
        self.source_dir = None
        self.destination_dir = None
        self.mode = "type"
        self.conflict_strategy = "rename"
        self.date_source = "auto"
        self.date_format = "YYYY-MM-DD"
        self.create_subdirs = True


# Global configuration
config = Config()


@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, help='Show version information')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--dry-run', '-n', is_flag=True, help='Preview changes without executing')
@click.option('--config-file', type=click.Path(exists=True), help='Path to configuration file')
@click.pass_context
def cli(ctx, version, verbose, dry_run, config_file):
    """
    File Organizer Pro - Intelligent file organization tool
    
    Automatically organize files by type or date with advanced features:
    - Multiple organization modes (type, date)
    - Conflict resolution strategies
    - Dry-run preview mode
    - Detailed logging and statistics
    
    Examples:
        file-organizer organize ./downloads --mode type --dry-run
        file-organizer organize ./photos --mode date --date-format YYYY-MM
        file-organizer analyze ./documents
    """
    if version:
        click.echo(f"{__app_name__} v{__version__}")
        sys.exit(0)
    
    # Setup global configuration
    config.verbose = verbose
    config.dry_run = dry_run
    
    # Initialize logging
    logger = setup_logging(verbose=verbose)
    
    if ctx.invoked_subcommand is None:
        click.echo(f"🗂️  {__app_name__} v{__version__}")
        click.echo("Use --help for available commands")


@cli.command()
@click.argument('source_directory', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--destination', '-d', type=click.Path(file_okay=False, dir_okay=True), 
              help='Destination directory (uses source if not specified)')
@click.option('--mode', '-m', type=click.Choice(['type', 'date']), default='type',
              help='Organization mode: type or date')
@click.option('--dry-run', '-n', is_flag=True, help='Preview changes without executing')
@click.option('--conflict-strategy', type=click.Choice(['skip', 'rename', 'overwrite', 'backup']), 
              default='rename', help='How to handle file conflicts')
@click.option('--date-source', type=click.Choice(['auto', 'creation', 'modification', 'filename', 'exif']),
              default='auto', help='Source for date information (date mode only)')
@click.option('--date-format', type=click.Choice(['YYYY', 'YYYY-MM', 'YYYY-MM-DD', 'YYYY-QQ', 'YYYY-WW']),
              default='YYYY-MM-DD', help='Date folder format (date mode only)')
@click.option('--no-subdirs', is_flag=True, help="Don't create category subdirectories")
@click.option('--force', is_flag=True, help='Skip safety checks')
def organize(source_directory, destination, mode, dry_run, conflict_strategy, 
            date_source, date_format, no_subdirs, force):
    """
    Organize files in the specified directory
    
    SOURCE_DIRECTORY: Directory containing files to organize
    """
    logger = get_logger()
    
    try:
        # Update global config
        config.dry_run = dry_run or config.dry_run
        config.mode = mode
        config.conflict_strategy = conflict_strategy
        config.date_source = date_source
        config.date_format = date_format
        config.create_subdirs = not no_subdirs
        
        # Display operation info
        click.echo(f"\n🗂️  {__app_name__} - File Organization")
        click.echo(f"📁 Source: {source_directory}")
        click.echo(f"📁 Destination: {destination or source_directory}")
        click.echo(f"🔧 Mode: {mode}")
        if config.dry_run:
            click.echo("🔍 DRY RUN MODE - No files will be moved")
        click.echo()
        
        # Safety checks
        if not force and not _perform_safety_checks(source_directory):
            click.echo("❌ Safety checks failed. Use --force to override.")
            sys.exit(1)
        
        # Set up conflict resolution
        resolver = get_conflict_resolver()
        resolver.default_strategy = ConflictStrategy(conflict_strategy)
        
        # Get file manager
        file_manager = get_file_manager()
        
        # Perform organization
        start_time = time.time()
        
        if mode == 'type':
            result = file_manager.organize_by_type(
                source_dir=source_directory,
                destination_dir=destination,
                dry_run=config.dry_run,
                create_subdirs=config.create_subdirs,
                progress_callback=_progress_callback
            )
        elif mode == 'date':
            result = file_manager.organize_by_date(
                source_dir=source_directory,
                destination_dir=destination,
                dry_run=config.dry_run,
                date_format=date_format,
                use_creation_date=(date_source == 'creation'),
                progress_callback=_progress_callback
            )
        else:
            raise ValueError(f"Unknown mode: {mode}")
        
        # Display results
        _display_results(result, time.time() - start_time)
        
    except Exception as e:
        logger.error(f"❌ Organization failed: {e}")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--mode', '-m', type=click.Choice(['type', 'date', 'both']), default='both',
              help='Analysis mode')
@click.option('--show-details', is_flag=True, help='Show detailed file information')
@click.option('--export', type=click.Path(), help='Export analysis to JSON file')
def analyze(directory, mode, show_details, export):
    """
    Analyze files in directory without organizing them
    
    DIRECTORY: Directory to analyze
    """
    logger = get_logger()
    
    try:
        click.echo(f"\n📊 Analyzing files in: {directory}")
        click.echo(f"🔧 Analysis mode: {mode}\n")
        
        # Get file manager for preview
        file_manager = get_file_manager()
        
        if mode in ['type', 'both']:
            click.echo("📁 File Type Analysis:")
            type_preview = file_manager.get_organization_preview(directory, "type")
            _display_preview(type_preview, "type")
            click.echo()
        
        if mode in ['date', 'both']:
            click.echo("📅 Date Analysis:")
            date_preview = file_manager.get_organization_preview(directory, "date")
            _display_preview(date_preview, "date")
            
            # Additional date analysis
            date_organizer = get_date_organizer()
            validator = get_validator()
            source_path = validator.validate_source_directory(directory)
            
            # Get all files
            files = []
            for file_path in source_path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    files.append(str(file_path))
            
            if files:
                date_analysis = date_organizer.analyze_date_distribution(files)
                _display_date_analysis(date_analysis)
        
        # Export results if requested
        if export:
            import json
            export_data = {
                "directory": directory,
                "analysis_mode": mode,
                "timestamp": time.time(),
                "type_preview": type_preview if mode in ['type', 'both'] else None,
                "date_preview": date_preview if mode in ['date', 'both'] else None
            }
            
            with open(export, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            click.echo(f"📄 Analysis exported to: {export}")
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--mode', '-m', type=click.Choice(['type', 'date']), default='type',
              help='Preview mode')
@click.option('--date-format', type=click.Choice(['YYYY', 'YYYY-MM', 'YYYY-MM-DD']),
              default='YYYY-MM-DD', help='Date format for preview')
@click.option('--limit', type=int, default=10, help='Limit number of files shown per category')
def preview(directory, mode, date_format, limit):
    """
    Preview organization without making changes
    
    DIRECTORY: Directory to preview
    """
    try:
        click.echo(f"\n🔍 Preview: {mode} organization of {directory}")
        click.echo(f"📋 Showing up to {limit} files per category\n")
        
        file_manager = get_file_manager()
        preview_data = file_manager.get_organization_preview(directory, mode)
        
        if "error" in preview_data:
            click.echo(f"❌ Error: {preview_data['error']}")
            return
        
        click.echo(f"📊 Total files: {preview_data['total_files']}")
        click.echo(f"📁 Estimated folders: {preview_data['estimated_folders']}")
        click.echo()
        
        # Show category breakdown
        for category, stats in preview_data['categories'].items():
            file_count = stats.get('file_count', 0)
            size_mb = stats.get('total_size_mb', 0)
            click.echo(f"📁 {category}: {file_count} files ({size_mb:.1f} MB)")
        
    except Exception as e:
        click.echo(f"❌ Preview failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--show-categories', is_flag=True, help='Show available file categories')
@click.option('--show-stats', is_flag=True, help='Show conflict resolution statistics')
@click.option('--show-formats', is_flag=True, help='Show available date formats')
def info(show_categories, show_stats, show_formats):
    """Show information about File Organizer Pro"""
    
    click.echo(f"\n🗂️  {__app_name__} v{__version__}")
    click.echo("=" * 50)
    
    if show_categories:
        click.echo("\n📁 Available File Categories:")
        category_mapper = get_category_mapper()
        categories = category_mapper.get_all_categories()
        
        for category, extensions in categories.items():
            ext_display = ", ".join(extensions[:5])
            if len(extensions) > 5:
                ext_display += f" ... (+{len(extensions) - 5} more)"
            click.echo(f"  {category}: {ext_display}")
    
    if show_stats:
        click.echo("\n📊 Conflict Resolution Statistics:")
        resolver = get_conflict_resolver()
        stats = resolver.get_conflict_stats()
        
        click.echo(f"  Total conflicts resolved: {stats['total_conflicts']}")
        for strategy, count in stats['resolution_strategies'].items():
            click.echo(f"  {strategy}: {count}")
    
    if show_formats:
        click.echo("\n📅 Available Date Formats:")
        formats = [
            ("YYYY", "Annual folders (2024)"),
            ("YYYY-MM", "Monthly folders (2024-01)"),
            ("YYYY-MM-DD", "Daily folders (2024-01-15)"),
            ("YYYY-QQ", "Quarterly folders (2024-Q1)"),
            ("YYYY-WW", "Weekly folders (2024-W03)")
        ]
        
        for fmt, description in formats:
            click.echo(f"  {fmt}: {description}")
    
    if not any([show_categories, show_stats, show_formats]):
        click.echo("\n📖 Use --help with any command for detailed usage")
        click.echo("🔧 Use --show-categories, --show-stats, or --show-formats for more info")


def _perform_safety_checks(directory: str) -> bool:
    """Perform safety checks before organization"""
    logger = get_logger()
    
    try:
        click.echo("🛡️  Performing safety checks...")
        
        # Basic path validation
        validator = get_validator()
        source_path = validator.validate_source_directory(directory)
        
        # Check if safe to organize
        if not is_safe_to_organize(directory):
            click.echo("⚠️  Warning: Directory may contain system or locked files")
            if not click.confirm("Continue anyway?"):
                return False
        
        # Scan for potential issues
        safety_info = validator.scan_directory_safety(source_path)
        
        if safety_info["warnings"]:
            click.echo(f"⚠️  Found {len(safety_info['warnings'])} potential issues:")
            for warning in safety_info["warnings"][:3]:  # Show first 3
                click.echo(f"   • {warning}")
            
            if len(safety_info["warnings"]) > 3:
                click.echo(f"   ... and {len(safety_info['warnings']) - 3} more")
            
            if not click.confirm("Continue despite warnings?"):
                return False
        
        click.echo("✅ Safety checks passed")
        return True
        
    except ValidationError as e:
        click.echo(f"❌ Safety check failed: {e}")
        return False


def _progress_callback(progress: float, current_file: str, category: str):
    """Progress callback for file operations"""
    if config.verbose:
        filename = Path(current_file).name
        click.echo(f"📁 {filename} → {category} ({progress:.1%})")


def _display_results(result: OrganizationResult, elapsed_time: float):
    """Display organization results"""
    summary = result.get_summary()
    
    click.echo("\n" + "=" * 50)
    click.echo("📊 ORGANIZATION RESULTS")
    click.echo("=" * 50)
    
    if result.dry_run:
        click.echo("🔍 DRY RUN - No files were actually moved")
    
    click.echo(f"📄 Total files: {summary['total_files']}")
    click.echo(f"✅ Processed: {summary['processed_files']}")
    click.echo(f"⏭️  Skipped: {summary['skipped_files']}")
    click.echo(f"❌ Errors: {summary['error_files']}")
    click.echo(f"📁 Folders created: {summary['categories_created']}")
    click.echo(f"🔄 Conflicts resolved: {summary['conflicts_resolved']}")
    click.echo(f"💾 Total size: {summary['total_size_mb']} MB")
    click.echo(f"⏱️  Time: {summary['operation_time']}s")
    click.echo(f"📈 Success rate: {summary['success_rate']}%")
    
    # Show category breakdown
    if summary['processed_categories']:
        click.echo(f"\n📁 Categories processed:")
        for category, stats in summary['processed_categories'].items():
            size_mb = round(stats['size'] / (1024 * 1024), 1)
            click.echo(f"   {category}: {stats['count']} files ({size_mb} MB)")
    
    # Show errors if any
    if result.errors:
        click.echo(f"\n❌ Errors encountered:")
        for error in result.errors[:5]:  # Show first 5 errors
            click.echo(f"   • {Path(error['file']).name}: {error['error']}")
        
        if len(result.errors) > 5:
            click.echo(f"   ... and {len(result.errors) - 5} more errors")


def _display_preview(preview_data: dict, mode: str):
    """Display preview information"""
    if "error" in preview_data:
        click.echo(f"❌ Error: {preview_data['error']}")
        return
    
    click.echo(f"📊 Total files: {preview_data['total_files']}")
    click.echo(f"📁 Would create: {preview_data['estimated_folders']} folders")
    
    # Show top categories
    categories = preview_data.get('categories', {})
    if categories:
        sorted_categories = sorted(categories.items(), 
                                 key=lambda x: x[1].get('file_count', 0), 
                                 reverse=True)
        
        click.echo("📋 Top categories:")
        for category, stats in sorted_categories[:5]:
            file_count = stats.get('file_count', 0)
            size_mb = stats.get('total_size_mb', 0)
            click.echo(f"   {category}: {file_count} files ({size_mb:.1f} MB)")


def _display_date_analysis(analysis: dict):
    """Display detailed date analysis"""
    click.echo(f"\n📅 Detailed Date Analysis:")
    click.echo(f"   Files with dates: {analysis['files_with_dates']}")
    click.echo(f"   Files without dates: {analysis['files_without_dates']}")
    
    if analysis['date_range']['earliest'] and analysis['date_range']['latest']:
        earliest = analysis['date_range']['earliest'].strftime("%Y-%m-%d")
        latest = analysis['date_range']['latest'].strftime("%Y-%m-%d")
        click.echo(f"   Date range: {earliest} to {latest}")
    
    # Show date sources
    click.echo(f"   Date sources used:")
    for source, count in analysis['date_sources'].items():
        click.echo(f"     {source}: {count} files")
    
    # Show yearly distribution
    if analysis['yearly_distribution']:
        click.echo(f"   Files by year:")
        sorted_years = sorted(analysis['yearly_distribution'].items())
        for year, count in sorted_years[-5:]:  # Last 5 years
            click.echo(f"     {year}: {count} files")


def main():
    """Main entry point"""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n⏹️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
