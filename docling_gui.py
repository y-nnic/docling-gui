#!/usr/bin/env python3
"""
Docling GUI — OCR checkbox + MD to HTML conversion

Usage:
    cd ~/docling
    source .venv/bin/activate
    python docling_gui.py

Notes:
- This GUI invokes the installed `docling` CLI in the same venv.
- Poppler should be installed (brew install poppler) for docling's PDF handling.
- For MD→HTML conversion, install pandoc (brew install pandoc).
"""

import sys, os, time, shutil, subprocess, webbrowser
from pathlib import Path
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QFileDialog, QProgressBar, QListWidget, QListWidgetItem,
    QMessageBox, QCheckBox, QComboBox, QTabWidget
)

ROOT = Path.cwd()
OUTPUT_BASE = ROOT / "docling_gui_output"
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
DOCLING_CMD = "docling"  # must be available in the environment used to start the app

class WorkerSignals(QObject):
    line = pyqtSignal(str)
    finished = pyqtSignal(bool, object)

class DoclingWorker(QThread):
    def __init__(self, filepath: str, outdir: Path, ocr_auto: bool = False, export_json: bool = False, export_txt: bool = False, verbose: bool = False):
        super().__init__()
        self.filepath = filepath
        self.outdir = outdir
        self.ocr_auto = ocr_auto
        self.export_json = export_json
        self.export_txt = export_txt
        self.verbose = verbose
        self.signals = WorkerSignals()

    def _run_cmd_stream(self, cmd):
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=os.environ.copy())
        if proc.stdout:
            for line in proc.stdout:
                clean_line = line.rstrip()
                self.signals.line.emit(clean_line)
        proc.wait()
        return proc.returncode

    def run(self):
        start = time.perf_counter()
        try:
            if self.verbose:
                self.signals.line.emit("="*80)
                self.signals.line.emit(f"DOCLING PROCESSING - VERBOSE MODE")
                self.signals.line.emit(f"Input: {self.filepath}")
                self.signals.line.emit(f"Output: {self.outdir}")
                self.signals.line.emit("="*80)
            
            # Step 1: Prepare output directory
            if self.verbose:
                self.signals.line.emit("\n[STEP 1/5] Preparing output directory...")
            
            if self.outdir.exists():
                if self.verbose:
                    self.signals.line.emit(f"  - Removing existing directory: {self.outdir}")
                shutil.rmtree(self.outdir)
            self.outdir.mkdir(parents=True, exist_ok=True)
            if self.verbose:
                self.signals.line.emit(f"  - Created directory: {self.outdir}")

            # Step 2: Build Docling command
            if self.verbose:
                self.signals.line.emit("\n[STEP 2/5] Building Docling command...")
            
            cmd = [DOCLING_CMD, self.filepath, "--output", str(self.outdir)]
            
            if self.ocr_auto:
                cmd += ["--ocr"]
                if self.verbose:
                    self.signals.line.emit("  - OCR enabled: auto")
            
            if self.verbose:
                self.signals.line.emit(f"  - Command: {' '.join(cmd)}")
            else:
                self.signals.line.emit(f"[CMD] {' '.join(cmd)}")
            
            # Step 3: Run Docling
            if self.verbose:
                self.signals.line.emit("\n[STEP 3/5] Running Docling CLI...")
                self.signals.line.emit("-"*80)
                self.signals.line.emit("RAW DOCLING OUTPUT:")
                self.signals.line.emit("-"*80)
            
            rc = self._run_cmd_stream(cmd)
            
            if self.verbose:
                self.signals.line.emit("-"*80)
                self.signals.line.emit(f"Docling exit code: {rc}")

            elapsed = time.perf_counter() - start
            
            if self.verbose:
                self.signals.line.emit(f"\n[STEP 4/5] Post-processing outputs (took {elapsed:.1f}s)...")
            else:
                self.signals.line.emit(f"[DONE] Took {elapsed:.1f}s - output in: {self.outdir}")

            # Find MD file
            md_file = None
            for p in self.outdir.rglob("*.md"):
                md_file = p
                if self.verbose:
                    self.signals.line.emit(f"  - Found MD file: {md_file.name} ({md_file.stat().st_size} bytes)")
                break
            
            if not md_file and self.verbose:
                self.signals.line.emit("  - WARNING: No MD file found!")
            
            html_file = None
            json_file = None
            txt_file = None
            
            if md_file:
                if not self.verbose:
                    self.signals.line.emit(f"[INFO] Found MD file: {md_file.name}")
                
                # Convert MD to HTML using pandoc
                html_file = md_file.with_suffix('.html')
                try:
                    if self.verbose:
                        self.signals.line.emit(f"  - Converting to HTML using pandoc...")
                    
                    pandoc_cmd = ["pandoc", str(md_file), "-f", "markdown", "-t", "html", "-s", "-o", str(html_file)]
                    
                    if self.verbose:
                        self.signals.line.emit(f"    Command: {' '.join(pandoc_cmd)}")
                    else:
                        self.signals.line.emit(f"[CMD] Converting to HTML: pandoc {md_file.name} → {html_file.name}")
                    
                    result = subprocess.run(pandoc_cmd, capture_output=True, text=True)
                    if result.returncode == 0:
                        if self.verbose:
                            self.signals.line.emit(f"  - SUCCESS: Created HTML ({html_file.stat().st_size} bytes)")
                        else:
                            self.signals.line.emit(f"[SUCCESS] Created HTML: {html_file.name}")
                    else:
                        if self.verbose:
                            self.signals.line.emit(f"  - ERROR: Pandoc failed with exit code {result.returncode}")
                            self.signals.line.emit(f"    {result.stderr}")
                        else:
                            self.signals.line.emit(f"[WARN] Pandoc conversion failed: {result.stderr}")
                        html_file = None
                except FileNotFoundError:
                    msg = "Pandoc not installed. Install with: brew install pandoc"
                    if self.verbose:
                        self.signals.line.emit(f"  - ERROR: {msg}")
                    else:
                        self.signals.line.emit(f"[WARN] {msg}")
                    html_file = None
                
                # Export to JSON if requested
                if self.export_json:
                    if self.verbose:
                        self.signals.line.emit(f"  - Exporting to JSON...")
                    
                    json_file = md_file.with_suffix('.json')
                    try:
                        # Check if docling already created a JSON file
                        existing_json = None
                        for p in self.outdir.rglob("*.json"):
                            existing_json = p
                            break
                        
                        if existing_json and existing_json.exists():
                            json_file = existing_json
                            if self.verbose:
                                self.signals.line.emit(f"  - Using existing JSON: {json_file.name} ({json_file.stat().st_size} bytes)")
                            else:
                                self.signals.line.emit(f"[INFO] JSON file already exists: {json_file.name}")
                        else:
                            # Create a simple JSON structure from MD
                            import json
                            json_data = {
                                "source": str(self.filepath),
                                "content": md_file.read_text(encoding='utf-8'),
                                "format": "markdown",
                                "processing_time": elapsed,
                                "ocr_enabled": self.ocr_auto
                            }
                            json_file.write_text(json.dumps(json_data, indent=2, ensure_ascii=False), encoding='utf-8')
                            if self.verbose:
                                self.signals.line.emit(f"  - SUCCESS: Created JSON ({json_file.stat().st_size} bytes)")
                            else:
                                self.signals.line.emit(f"[SUCCESS] Created JSON: {json_file.name}")
                    except Exception as e:
                        if self.verbose:
                            self.signals.line.emit(f"  - ERROR: JSON export failed: {e}")
                        else:
                            self.signals.line.emit(f"[ERROR] JSON export failed: {e}")
                        json_file = None
                
                # Export to TXT if requested
                if self.export_txt:
                    if self.verbose:
                        self.signals.line.emit(f"  - Exporting to TXT...")
                    
                    txt_file = md_file.with_suffix('.txt')
                    try:
                        # Convert MD to plain text using pandoc
                        pandoc_cmd = ["pandoc", str(md_file), "-f", "markdown", "-t", "plain", "-o", str(txt_file)]
                        if self.verbose:
                            self.signals.line.emit(f"    Command: {' '.join(pandoc_cmd)}")
                        
                        result = subprocess.run(pandoc_cmd, capture_output=True, text=True)
                        if result.returncode == 0:
                            if self.verbose:
                                self.signals.line.emit(f"  - SUCCESS: Created TXT ({txt_file.stat().st_size} bytes)")
                            else:
                                self.signals.line.emit(f"[SUCCESS] Created TXT: {txt_file.name}")
                        else:
                            # Fallback: just copy MD content as is
                            txt_file.write_text(md_file.read_text(encoding='utf-8'), encoding='utf-8')
                            if self.verbose:
                                self.signals.line.emit(f"  - Created TXT using fallback method ({txt_file.stat().st_size} bytes)")
                            else:
                                self.signals.line.emit(f"[SUCCESS] Created TXT (fallback): {txt_file.name}")
                    except Exception as e:
                        if self.verbose:
                            self.signals.line.emit(f"  - ERROR: TXT export failed: {e}")
                        else:
                            self.signals.line.emit(f"[ERROR] TXT export failed: {e}")
                        txt_file = None

            # If no HTML was created, try to find any existing HTML/MD/JSON
            if html_file is None or not html_file.exists():
                for p in self.outdir.rglob("*.html"):
                    html_file = p
                    break
                if html_file is None:
                    html_file = md_file  # fallback to MD file

            if self.verbose:
                self.signals.line.emit(f"\n[STEP 5/5] Summary")
                self.signals.line.emit(f"  - Total processing time: {elapsed:.1f}s")
                self.signals.line.emit(f"  - Output directory: {self.outdir}")
                self.signals.line.emit(f"  - Files created:")
                if md_file: self.signals.line.emit(f"    ✓ {md_file.name}")
                if html_file and html_file != md_file: self.signals.line.emit(f"    ✓ {html_file.name}")
                if json_file: self.signals.line.emit(f"    ✓ {json_file.name}")
                if txt_file: self.signals.line.emit(f"    ✓ {txt_file.name}")
                self.signals.line.emit("="*80)

            # Store all created files for later reference
            self.created_files = {
                'html': html_file,
                'md': md_file,
                'json': json_file,
                'txt': txt_file
            }

            self.signals.finished.emit(True, html_file)
        except Exception as e:
            self.signals.line.emit(f"[ERROR] {e}")
            if self.verbose:
                import traceback
                self.signals.line.emit(f"\nFull traceback:")
                self.signals.line.emit(traceback.format_exc())
            self.signals.finished.emit(False, None)

class DoclingGui(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Docling — PDF/Image to HTML Converter")
        self.resize(960, 720)
        self.setAcceptDrops(True)

        main = QVBoxLayout(self)

        header = QLabel("Drag & drop PDF/PNG files here or use the controls below")
        header.setWordWrap(True)
        main.addWidget(header)

        # Split layout: Input files (left) and Output files (right)
        split_layout = QHBoxLayout()
        
        # Left side: Input files
        left_container = QVBoxLayout()
        left_label = QLabel("Input Files")
        left_label.setStyleSheet("font-weight: bold;")
        left_container.addWidget(left_label)
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        left_container.addWidget(self.file_list)
        split_layout.addLayout(left_container)
        
        # Right side: Output files
        right_container = QVBoxLayout()
        right_label = QLabel("Output Files (double-click to open)")
        right_label.setStyleSheet("font-weight: bold;")
        right_container.addWidget(right_label)
        self.output_list = QListWidget()
        self.output_list.itemDoubleClicked.connect(self.open_output_file)
        self.output_list.setToolTip("Double-click to open file in browser/viewer")
        right_container.addWidget(self.output_list)
        split_layout.addLayout(right_container)
        
        main.addLayout(split_layout, stretch=1)

        # File management buttons row
        file_mgmt_row = QHBoxLayout()
        file_mgmt_label = QLabel("File Management:")
        file_mgmt_label.setStyleSheet("font-weight: bold;")
        file_mgmt_row.addWidget(file_mgmt_label)
        
        self.add_btn = QPushButton("Add Files")
        self.add_btn.clicked.connect(self.open_file_dialog)
        file_mgmt_row.addWidget(self.add_btn)

        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self.remove_selected)
        self.remove_btn.setToolTip("Remove selected files from input list")
        file_mgmt_row.addWidget(self.remove_btn)

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_list)
        file_mgmt_row.addWidget(self.clear_btn)

        self.folder_btn = QPushButton("Open Output Folder")
        self.folder_btn.clicked.connect(self.open_output_folder)
        self.folder_btn.setToolTip(f"Open: {OUTPUT_BASE}")
        file_mgmt_row.addWidget(self.folder_btn)
        
        file_mgmt_row.addStretch()
        main.addLayout(file_mgmt_row)

        # Sort options row
        sort_row = QHBoxLayout()
        sort_row.addWidget(QLabel("Sort by:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Added order", "Name (A-Z)", "Name (Z-A)", "Size (smallest)", "Size (largest)"])
        self.sort_combo.currentTextChanged.connect(self.sort_files)
        sort_row.addWidget(self.sort_combo)
        sort_row.addStretch()
        main.addLayout(sort_row)

        # Separator
        separator = QLabel()
        separator.setStyleSheet("background-color: #ccc; max-height: 1px;")
        separator.setMaximumHeight(1)
        main.addWidget(separator)

        # Processing control row - with prominent Start button
        processing_row = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Processing")
        self.start_btn.clicked.connect(self.start_processing)
        processing_row.addWidget(self.start_btn, stretch=2)

        self.reprocess_btn = QPushButton("Reprocess Selected")
        self.reprocess_btn.clicked.connect(self.reprocess_selected)
        self.reprocess_btn.setToolTip("Reprocess only selected files")
        processing_row.addWidget(self.reprocess_btn, stretch=1)
        
        main.addLayout(processing_row)

        # Options row: OCR checkbox + Export format checkboxes + Verbose mode
        opts = QHBoxLayout()
        self.ocr_check = QCheckBox("Enable OCR (for scanned PDFs)")
        self.ocr_check.setToolTip("If checked, enable automatic OCR for image-based PDFs")
        opts.addWidget(self.ocr_check)
        
        opts.addSpacing(20)
        
        self.verbose_check = QCheckBox("Verbose Mode (detailed logs)")
        self.verbose_check.setToolTip("Show detailed Docling processing information and raw CLI output")
        self.verbose_check.setStyleSheet("font-weight: bold; color: #0066cc;")
        opts.addWidget(self.verbose_check)
        
        opts.addSpacing(20)
        
        export_label = QLabel("Export formats:")
        export_label.setStyleSheet("font-weight: bold;")
        opts.addWidget(export_label)
        
        self.export_json_check = QCheckBox("JSON")
        self.export_json_check.setToolTip("Also export as JSON (structured document data)")
        opts.addWidget(self.export_json_check)
        
        self.export_txt_check = QCheckBox("TXT")
        self.export_txt_check.setToolTip("Also export as plain text (text only, no formatting)")
        opts.addWidget(self.export_txt_check)
        
        opts.addStretch()
        main.addLayout(opts)

        # Status label for progress
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-weight: bold; padding: 5px;")
        main.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setFormat("%v / %m files (%p%)")
        main.addWidget(self.progress)

        # Log section with tabs for regular and verbose output
        log_label = QLabel("Processing Log:")
        log_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        main.addWidget(log_label)

        self.log_tabs = QTabWidget()
        
        # Regular log tab
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(180)
        self.log_tabs.addTab(self.log, "Summary")
        
        # Verbose/Raw output tab
        self.verbose_log = QTextEdit()
        self.verbose_log.setReadOnly(True)
        self.verbose_log.setMinimumHeight(180)
        self.verbose_log.setStyleSheet("font-family: monospace; font-size: 11px;")
        self.log_tabs.addTab(self.verbose_log, "Verbose / Raw CLI Output")
        
        main.addWidget(self.log_tabs)

        # Info label
        info = QLabel("Info: MD files are automatically converted to HTML (requires pandoc)")
        info.setStyleSheet("color: #666; font-size: 11px;")
        main.addWidget(info)

        self.queue = []
        self.current_worker = None
        self.processing_times = []  # Track processing times for estimation
        self.batch_start_time = None  # Track total batch time

    def open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select files", str(Path.home()), "PDF and images (*.pdf *.png *.jpg *.jpeg)")
        for f in files:
            self.add_file(f)

    def add_file(self, path):
        p = Path(path)
        if not p.exists():
            return
        # Check if file already in queue
        if str(p) in self.queue:
            return
        self.queue.append(str(p))
        item = QListWidgetItem(p.name)
        item.setData(Qt.ItemDataRole.UserRole, str(p))
        # Store file size for sorting
        try:
            size = p.stat().st_size
            item.setData(Qt.ItemDataRole.UserRole + 1, size)
        except:
            item.setData(Qt.ItemDataRole.UserRole + 1, 0)
        self.file_list.addItem(item)

    def clear_list(self):
        self.queue.clear()
        self.file_list.clear()
        self.output_list.clear()

    def remove_selected(self):
        """Remove selected files from input list"""
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select files to remove.")
            return
        
        for item in selected_items:
            filepath = item.data(Qt.ItemDataRole.UserRole)
            # Remove from queue if present
            if filepath in self.queue:
                self.queue.remove(filepath)
            # Remove from list widget
            row = self.file_list.row(item)
            self.file_list.takeItem(row)
        
        self.log.append(f"Removed {len(selected_items)} file(s) from list")

    def reprocess_selected(self):
        """Reprocess only selected files"""
        selected_items = self.file_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select files to reprocess.")
            return
        
        # Clear queue and add only selected files
        self.queue.clear()
        for item in selected_items:
            filepath = item.data(Qt.ItemDataRole.UserRole)
            self.queue.append(filepath)
        
        self.log.append(f"Reprocessing {len(selected_items)} selected file(s)")
        self.start_processing()

    def sort_files(self, sort_option):
        """Sort files in the input list"""
        if self.file_list.count() == 0:
            return
        
        # Collect all items with their data
        items_data = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            filepath = item.data(Qt.ItemDataRole.UserRole)
            filesize = item.data(Qt.ItemDataRole.UserRole + 1)
            items_data.append((item.text(), filepath, filesize))
        
        # Sort based on selection
        if sort_option == "Name (A-Z)":
            items_data.sort(key=lambda x: x[0].lower())
        elif sort_option == "Name (Z-A)":
            items_data.sort(key=lambda x: x[0].lower(), reverse=True)
        elif sort_option == "Size (smallest)":
            items_data.sort(key=lambda x: x[2])
        elif sort_option == "Size (largest)":
            items_data.sort(key=lambda x: x[2], reverse=True)
        # "Added order" - don't sort, keep as is
        else:
            return
        
        # Rebuild list and queue
        self.file_list.clear()
        self.queue.clear()
        for name, filepath, filesize in items_data:
            self.queue.append(filepath)
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, filepath)
            item.setData(Qt.ItemDataRole.UserRole + 1, filesize)
            self.file_list.addItem(item)
        
        self.log.append(f"Sorted files by: {sort_option}")

    def open_output_file(self, item):
        """Open the output file when double-clicked"""
        filepath = item.data(Qt.ItemDataRole.UserRole)
        if filepath and Path(filepath).exists():
            try:
                webbrowser.open(Path(filepath).as_uri())
                self.log.append(f"Opened: {Path(filepath).name}")
            except Exception as e:
                self.log.append(f"Could not open file: {e}")

    def open_output_folder(self):
        """Open the main output folder in Finder/Explorer"""
        if OUTPUT_BASE.exists():
            try:
                if sys.platform == "darwin":  # macOS
                    subprocess.run(["open", str(OUTPUT_BASE)])
                elif sys.platform == "win32":  # Windows
                    os.startfile(OUTPUT_BASE)
                else:  # Linux
                    subprocess.run(["xdg-open", str(OUTPUT_BASE)])
                self.log.append(f"Opened folder: {OUTPUT_BASE}")
            except Exception as e:
                self.log.append(f"Could not open folder: {e}")
        else:
            QMessageBox.information(self, "No Output", "Output folder doesn't exist yet. Process a file first.")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local:
                self.add_file(local)

    def start_processing(self):
        if not self.queue:
            QMessageBox.information(self, "No files", "Please add files first.")
            return
        self.progress.setValue(0)
        self.progress.setMaximum(len(self.queue))
        self.start_btn.setEnabled(False)
        self.add_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
        self.reprocess_btn.setEnabled(False)
        self.log.clear()
        self.verbose_log.clear()
        self.processing_times.clear()
        self.batch_start_time = time.time()
        self.status_label.setText(f"Starting batch of {len(self.queue)} file(s)...")
        
        # Switch to verbose tab if verbose mode is enabled
        if self.verbose_check.isChecked():
            self.log_tabs.setCurrentIndex(1)  # Switch to verbose tab
        
        self._process_next()

    def _process_next(self):
        if not self.queue:
            total_time = time.time() - self.batch_start_time
            avg_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
            
            self.status_label.setText(
                f"Completed! Total: {total_time:.1f}s | Average: {avg_time:.1f}s per file"
            )
            self.log.append("All files processed.")
            self.log.append(f"Total processing time: {total_time:.1f}s")
            if self.processing_times:
                self.log.append(f"Average time per file: {avg_time:.1f}s")
            
            self.start_btn.setEnabled(True)
            self.add_btn.setEnabled(True)
            self.clear_btn.setEnabled(True)
            self.remove_btn.setEnabled(True)
            self.reprocess_btn.setEnabled(True)
            return
        
        filepath = self.queue.pop(0)
        current = self.progress.value() + 1
        total = self.progress.maximum()
        remaining = total - current + 1
        
        # Calculate estimated time remaining
        eta_text = ""
        if self.processing_times:
            avg_time = sum(self.processing_times) / len(self.processing_times)
            eta_seconds = avg_time * remaining
            eta_text = f" | ETA: {eta_seconds:.0f}s"
        
        self.status_label.setText(
            f"Processing {current}/{total}: {Path(filepath).name}{eta_text}"
        )
        self.log.append(f"Starting [{current}/{total}]: {filepath}")
        outdir = OUTPUT_BASE / Path(filepath).stem

        ocr_flag = self.ocr_check.isChecked()
        export_json = self.export_json_check.isChecked()
        export_txt = self.export_txt_check.isChecked()
        verbose_mode = self.verbose_check.isChecked()

        # Track start time for this file
        self.current_file_start = time.time()
        
        worker = DoclingWorker(filepath, outdir, ocr_auto=ocr_flag, export_json=export_json, export_txt=export_txt, verbose=verbose_mode)
        worker.signals.line.connect(self._on_worker_line)
        worker.signals.finished.connect(lambda ok, html: self._on_worker_done(ok, html, filepath, outdir))
        self.current_worker = worker
        worker.start()

    def _on_worker_line(self, line: str):
        # Always add to verbose log (raw output)
        self.verbose_log.append(line)
        
        # Add to summary log only if not in verbose mode OR if it's an important message
        if not self.verbose_check.isChecked():
            self.log.append(line)
        else:
            # In verbose mode, only show key messages in summary
            if any(keyword in line for keyword in ['[CMD]', '[DONE]', '[SUCCESS]', '[ERROR]', '[WARN]', 'Created formats']):
                self.log.append(line)

    def _on_worker_done(self, success: bool, html_path, filepath, outdir):
        # Calculate processing time for this file
        if hasattr(self, 'current_file_start'):
            processing_time = time.time() - self.current_file_start
            self.processing_times.append(processing_time)
            time_info = f" (took {processing_time:.1f}s)"
        else:
            time_info = ""
        
        if success and html_path and html_path.exists():
            # Find all created files in output directory
            md_file = None
            html_file = None
            json_file = None
            txt_file = None
            
            for p in outdir.rglob("*.md"):
                md_file = p
                break
            for p in outdir.rglob("*.html"):
                html_file = p
                break
            for p in outdir.rglob("*.json"):
                json_file = p
                break
            for p in outdir.rglob("*.txt"):
                txt_file = p
                break
            
            # Add all found files to output list
            files_added = []
            
            if md_file and md_file.exists():
                display_name = f"{Path(filepath).stem} -> {md_file.name}"
                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, str(md_file))
                item.setToolTip(f"Double-click to open: {md_file}")
                self.output_list.addItem(item)
                files_added.append("MD")
            
            if html_file and html_file.exists():
                display_name = f"{Path(filepath).stem} -> {html_file.name}"
                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, str(html_file))
                item.setToolTip(f"Double-click to open: {html_file}")
                self.output_list.addItem(item)
                files_added.append("HTML")
            
            if json_file and json_file.exists():
                display_name = f"{Path(filepath).stem} -> {json_file.name}"
                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, str(json_file))
                item.setToolTip(f"Double-click to open: {json_file}")
                self.output_list.addItem(item)
                files_added.append("JSON")
            
            if txt_file and txt_file.exists():
                display_name = f"{Path(filepath).stem} -> {txt_file.name}"
                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, str(txt_file))
                item.setToolTip(f"Double-click to open: {txt_file}")
                self.output_list.addItem(item)
                files_added.append("TXT")
            
            try:
                webbrowser.open(html_path.as_uri())
                formats = ", ".join(files_added) if files_added else "HTML"
                self.log.append(f"Created formats: {formats} | Opened in browser: {html_path.name}{time_info}")
            except Exception:
                formats = ", ".join(files_added) if files_added else "files"
                self.log.append(f"Created {formats} at: {outdir}{time_info}")
        else:
            self.log.append(f"Processing finished for {Path(filepath).name} (no output file found){time_info}")

        self.progress.setValue(self.progress.value() + 1)
        QApplication.processEvents()
        self._process_next()

def main():
    app = QApplication(sys.argv)
    win = DoclingGui()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()