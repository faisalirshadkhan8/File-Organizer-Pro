#!/usr/bin/env python3
"""
File Organizer Pro - GUI Prototype
A simple graphical interface for the File Organizer Pro CLI tool.

This prototype demonstrates how to integrate the existing CLI logic
with a modern tkinter-based GUI.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
from pathlib import Path
import threading
from queue import Queue
import time

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.file_manager import get_file_manager
    from src.category_mapper import get_category_mapper, categorize_file
    from src.date_organizer import get_date_organizer, DateFormat, DateSource
    from src.utils.logger import setup_logging, get_logger
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)


class FileOrganizerGUI:
    """Main GUI application class"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("File Organizer Pro")
        self.root.geometry("800x700")
        self.root.minsize(600, 500)
        
        # Initialize backend components
        setup_logging(verbose=True)
        self.logger = get_logger()
        self.file_manager = get_file_manager()
        self.category_mapper = get_category_mapper()
        self.date_organizer = get_date_organizer()
        
        # GUI variables
        self.source_var = tk.StringVar()
        self.dest_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="type")
        self.date_format_var = tk.StringVar(value="YYYY-MM-DD")
        self.date_source_var = tk.StringVar(value="auto")
        self.conflict_var = tk.StringVar(value="rename")
        self.dry_run_var = tk.BooleanVar(value=True)
        
        # Threading
        self.result_queue = Queue()
        self.is_processing = False
        
        self.setup_ui()
        self.check_queue()
        
    def setup_ui(self):
        """Create the main user interface"""
        
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="File Organizer Pro", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Source and Destination Section
        self.create_file_selection_section(main_frame, row=1)
        
        # Settings Section  
        self.create_settings_section(main_frame, row=2)
        
        # Action Buttons
        self.create_action_buttons(main_frame, row=3)
        
        # Progress Bar
        self.progress_var = tk.StringVar(value="Ready")
        self.progress_bar = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress_bar.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # Status Label
        self.status_label = ttk.Label(main_frame, textvariable=self.progress_var)
        self.status_label.grid(row=5, column=0)
        
        # Results/Log Section
        self.create_results_section(main_frame, row=6)
        
        # Configure main frame row weights
        main_frame.rowconfigure(6, weight=1)
        
    def create_file_selection_section(self, parent, row):
        """Create file and folder selection section"""
        
        # Frame for file selection
        file_frame = ttk.LabelFrame(parent, text="📁 File Selection", padding="10")
        file_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=10)
        file_frame.columnconfigure(1, weight=1)
        
        # Source folder
        ttk.Label(file_frame, text="Source Folder:").grid(row=0, column=0, sticky=tk.W, pady=5)
        source_entry = ttk.Entry(file_frame, textvariable=self.source_var, width=50)
        source_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        ttk.Button(file_frame, text="Browse...", 
                  command=self.browse_source).grid(row=0, column=2, padx=(10, 0), pady=5)
        
        # Destination folder
        ttk.Label(file_frame, text="Destination:").grid(row=1, column=0, sticky=tk.W, pady=5)
        dest_entry = ttk.Entry(file_frame, textvariable=self.dest_var, width=50)
        dest_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        ttk.Button(file_frame, text="Browse...", 
                  command=self.browse_destination).grid(row=1, column=2, padx=(10, 0), pady=5)
        
        # Same folder option
        same_folder_cb = ttk.Checkbutton(file_frame, text="Use same folder as destination")
        same_folder_cb.grid(row=2, column=1, sticky=tk.W, pady=5)
        
    def create_settings_section(self, parent, row):
        """Create organization settings section"""
        
        settings_frame = ttk.LabelFrame(parent, text="⚙️ Organization Settings", padding="10")
        settings_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # Organization mode
        mode_frame = ttk.Frame(settings_frame)
        mode_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(mode_frame, text="Mode:").grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(mode_frame, text="By File Type", variable=self.mode_var, 
                       value="type").grid(row=0, column=1, padx=(10, 0))
        ttk.Radiobutton(mode_frame, text="By Date", variable=self.mode_var, 
                       value="date").grid(row=0, column=2, padx=(10, 0))
        
        # Date settings (only visible when date mode is selected)
        date_frame = ttk.Frame(settings_frame)
        date_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(date_frame, text="Date Format:").grid(row=0, column=0, sticky=tk.W)
        date_format_combo = ttk.Combobox(date_frame, textvariable=self.date_format_var,
                                        values=["YYYY", "YYYY-MM", "YYYY-MM-DD", "YYYY-QQ"],
                                        state="readonly", width=15)
        date_format_combo.grid(row=0, column=1, padx=(10, 0))
        
        ttk.Label(date_frame, text="Date Source:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        date_source_combo = ttk.Combobox(date_frame, textvariable=self.date_source_var,
                                        values=["auto", "creation", "modification", "filename", "exif"],
                                        state="readonly", width=15)
        date_source_combo.grid(row=0, column=3, padx=(10, 0))
        
        # Conflict resolution
        conflict_frame = ttk.Frame(settings_frame)
        conflict_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(conflict_frame, text="Conflict Strategy:").grid(row=0, column=0, sticky=tk.W)
        conflict_combo = ttk.Combobox(conflict_frame, textvariable=self.conflict_var,
                                     values=["rename", "skip", "overwrite", "backup"],
                                     state="readonly", width=15)
        conflict_combo.grid(row=0, column=1, padx=(10, 0))
        
        # Dry run option
        dry_run_cb = ttk.Checkbutton(conflict_frame, text="Dry Run (Preview Only)", 
                                    variable=self.dry_run_var)
        dry_run_cb.grid(row=0, column=2, padx=(20, 0))
        
    def create_action_buttons(self, parent, row):
        """Create action buttons"""
        
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, pady=20)
        
        ttk.Button(button_frame, text="📊 Analyze", 
                  command=self.analyze_files).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="👀 Preview", 
                  command=self.preview_organization).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="🗂️ Organize Files", 
                  command=self.organize_files).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="❌ Clear", 
                  command=self.clear_results).grid(row=0, column=3, padx=5)
        
    def create_results_section(self, parent, row):
        """Create results and log display section"""
        
        results_frame = ttk.LabelFrame(parent, text="📋 Results & Log", padding="10")
        results_frame.grid(row=row, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Text widget with scrollbar
        text_frame = ttk.Frame(results_frame)
        text_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        self.results_text = tk.Text(text_frame, wrap=tk.WORD, height=15, width=70)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=scrollbar.set)
        
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
    def browse_source(self):
        """Browse for source folder"""
        folder = filedialog.askdirectory(title="Select Source Folder")
        if folder:
            self.source_var.set(folder)
            # Auto-set destination if empty
            if not self.dest_var.get():
                self.dest_var.set(str(Path(folder) / "organized"))
            
    def browse_destination(self):
        """Browse for destination folder"""
        folder = filedialog.askdirectory(title="Select Destination Folder")
        if folder:
            self.dest_var.set(folder)
            
    def log_message(self, message):
        """Add message to results text widget"""
        self.results_text.insert(tk.END, f"{message}\n")
        self.results_text.see(tk.END)
        self.root.update_idletasks()
        
    def clear_results(self):
        """Clear results text"""
        self.results_text.delete(1.0, tk.END)
        self.progress_var.set("Ready")
        
    def validate_inputs(self):
        """Validate user inputs"""
        if not self.source_var.get():
            messagebox.showerror("Error", "Please select a source folder")
            return False
            
        if not Path(self.source_var.get()).exists():
            messagebox.showerror("Error", "Source folder does not exist")
            return False
            
        return True
        
    def analyze_files(self):
        """Analyze files in source directory"""
        if not self.validate_inputs():
            return
            
        if self.is_processing:
            messagebox.showwarning("Warning", "Another operation is in progress")
            return
            
        def worker():
            try:
                self.is_processing = True
                source_path = self.source_var.get()
                
                # Get file list
                file_paths = []
                for file_path in Path(source_path).rglob("*"):
                    if file_path.is_file():
                        file_paths.append(str(file_path))
                
                # Analyze categories
                category_stats = {}
                for file_path in file_paths:
                    category, _ = categorize_file(file_path)
                    category_stats[category] = category_stats.get(category, 0) + 1
                
                # Analyze dates if date mode
                date_stats = {}
                if self.mode_var.get() == "date":
                    date_analysis = self.date_organizer.analyze_date_distribution(file_paths)
                    date_stats = date_analysis
                
                result = {
                    'total_files': len(file_paths),
                    'categories': category_stats,
                    'date_analysis': date_stats,
                    'status': 'success'
                }
                
                self.result_queue.put(('analyze_complete', result))
                
            except Exception as e:
                self.result_queue.put(('error', str(e)))
            finally:
                self.is_processing = False
                
        self.progress_var.set("Analyzing files...")
        self.progress_bar.start()
        threading.Thread(target=worker, daemon=True).start()
        
    def preview_organization(self):
        """Preview organization results"""
        if not self.validate_inputs():
            return
            
        if self.is_processing:
            messagebox.showwarning("Warning", "Another operation is in progress")
            return
            
        def worker():
            try:
                self.is_processing = True
                source_path = self.source_var.get()
                mode = self.mode_var.get()
                
                # Get preview from file manager - use correct method name
                preview_result = self.file_manager.get_organization_preview(source_path, mode)
                
                self.result_queue.put(('preview_complete', preview_result))
                
            except Exception as e:
                self.result_queue.put(('error', str(e)))
            finally:
                self.is_processing = False
                
        self.progress_var.set("Generating preview...")
        self.progress_bar.start()
        threading.Thread(target=worker, daemon=True).start()
        
    def organize_files(self):
        """Organize files based on settings"""
        if not self.validate_inputs():
            return
            
        if self.is_processing:
            messagebox.showwarning("Warning", "Another operation is in progress")
            return
            
        # Confirm if not dry run
        if not self.dry_run_var.get():
            result = messagebox.askyesno("Confirm", 
                                       "This will move/organize your files. Continue?")
            if not result:
                return
                
        def worker():
            try:
                self.is_processing = True
                source_path = self.source_var.get()
                dest_path = self.dest_var.get() or source_path
                mode = self.mode_var.get()
                dry_run = self.dry_run_var.get()
                
                # Organize files using correct method parameters
                if mode == "type":
                    result = self.file_manager.organize_by_type(
                        source_path, dest_path, dry_run=dry_run
                    )
                else:  # date mode
                    date_format_value = self.date_format_var.get()
                    # Convert GUI format to file manager format
                    date_format_str = date_format_value
                    use_creation = self.date_source_var.get() == "creation"
                    
                    result = self.file_manager.organize_by_date(
                        source_path, dest_path, 
                        dry_run=dry_run,
                        date_format=date_format_str,
                        use_creation_date=use_creation
                    )
                
                self.result_queue.put(('organize_complete', result))
                
            except Exception as e:
                self.result_queue.put(('error', str(e)))
            finally:
                self.is_processing = False
                
        action = "Previewing" if self.dry_run_var.get() else "Organizing"
        self.progress_var.set(f"{action} files...")
        self.progress_bar.start()
        threading.Thread(target=worker, daemon=True).start()
        
    def check_queue(self):
        """Check for results from background threads"""
        try:
            while True:
                action, data = self.result_queue.get_nowait()
                
                self.progress_bar.stop()
                
                if action == 'analyze_complete':
                    self.handle_analyze_complete(data)
                elif action == 'preview_complete':
                    self.handle_preview_complete(data)
                elif action == 'organize_complete':
                    self.handle_organize_complete(data)
                elif action == 'error':
                    self.handle_error(data)
                    
        except:
            pass  # Queue is empty
            
        # Schedule next check
        self.root.after(100, self.check_queue)
        
    def handle_analyze_complete(self, data):
        """Handle analysis completion"""
        self.progress_var.set("Analysis complete")
        
        self.log_message("📊 ANALYSIS RESULTS")
        self.log_message("=" * 50)
        self.log_message(f"Total files found: {data['total_files']}")
        self.log_message(f"Categories found: {len(data['categories'])}")
        self.log_message("")
        
        self.log_message("📁 File Categories:")
        for category, count in sorted(data['categories'].items()):
            self.log_message(f"  {category}: {count} files")
        
        if data['date_analysis']:
            self.log_message("")
            self.log_message("📅 Date Analysis:")
            date_info = data['date_analysis']
            self.log_message(f"  Files with dates: {date_info.get('files_with_dates', 0)}")
            self.log_message(f"  Files without dates: {date_info.get('files_without_dates', 0)}")
            
        self.log_message("")
        
    def handle_preview_complete(self, preview_data):
        """Handle preview completion"""
        self.progress_var.set("Preview complete")
        
        self.log_message("👀 ORGANIZATION PREVIEW")
        self.log_message("=" * 50)
        
        # Check if there's an error
        if "error" in preview_data:
            self.log_message(f"❌ Error: {preview_data['error']}")
            return
        
        # Use the new structure
        total_files = preview_data.get("total_files", 0)
        estimated_folders = preview_data.get("estimated_folders", 0)
        file_mappings = preview_data.get("file_mappings", {})
        
        self.log_message(f"Total files to organize: {total_files}")
        self.log_message(f"Folders to create: {estimated_folders}")
        self.log_message("")
        
        for folder, files in file_mappings.items():
            self.log_message(f"📁 {folder}/ ({len(files)} files)")
            # Show first few files
            for file_path in files[:5]:
                filename = Path(file_path).name
                self.log_message(f"  • {filename}")
            if len(files) > 5:
                self.log_message(f"  ... and {len(files) - 5} more files")
            self.log_message("")
            
    def handle_organize_complete(self, result):
        """Handle organization completion"""
        is_dry_run = self.dry_run_var.get()
        action = "PREVIEW" if is_dry_run else "ORGANIZATION"
        
        self.progress_var.set(f"{action.title()} complete!")
        
        self.log_message(f"✅ {action} COMPLETE")
        self.log_message("=" * 50)
        
        if hasattr(result, 'total_files'):
            self.log_message(f"Files processed: {result.total_files}")
            self.log_message(f"Success rate: {result.success_rate:.1f}%")
            self.log_message(f"Errors: {len(result.errors)}")
            
            if result.errors:
                self.log_message("\n❌ Errors encountered:")
                for error in result.errors[:5]:  # Show first 5 errors
                    self.log_message(f"  • {error}")
        else:
            self.log_message("Organization completed successfully!")
            
        if not is_dry_run:
            messagebox.showinfo("Success", "Files organized successfully!")
            
    def handle_error(self, error_msg):
        """Handle errors"""
        self.progress_var.set("Error occurred")
        self.log_message(f"❌ ERROR: {error_msg}")
        messagebox.showerror("Error", f"An error occurred:\n{error_msg}")
        
    def run(self):
        """Start the GUI application"""
        self.log_message("🚀 File Organizer Pro GUI Ready!")
        self.log_message("Select a source folder to get started.")
        self.log_message("")
        self.root.mainloop()


def main():
    """Main entry point"""
    try:
        app = FileOrganizerGUI()
        app.run()
    except KeyboardInterrupt:
        print("\nGUI application interrupted by user")
    except Exception as e:
        print(f"Error starting GUI: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
