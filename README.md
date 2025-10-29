# Docling GUI - PDF to HTML/MD/JSON/TXT Converter

A user-friendly graphical interface for [Docling](https://github.com/DS4SD/docling), IBM's document understanding AI model.

## Features

- 📄 Convert PDFs and images to HTML, Markdown, JSON, and TXT
- 🔍 OCR support for scanned documents
- 📊 Batch processing with progress tracking
- 🎯 Detailed verbose mode to understand Docling's processing
- 📁 Drag & drop support
- 🔄 Multi-format export (MD, HTML, JSON, TXT)

## Requirements

- macOS 10.15+ (Catalina or later)
- Python 3.9 or higher
- Homebrew (for dependencies)

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/y-nnic/docling-gui.git
cd docling-gui
```

### 2. Run Installation Script
```bash
chmod +x install.sh
./install.sh
```

### 3. Start the Application

Double-click `start_docling_gui.command` or run:
```bash
./start_docling_gui.command
```

## Usage

1. **Add Files**: Click "Add Files" or drag & drop PDFs/images
2. **Configure Options**: Enable OCR, select export formats
3. **Process**: Click "Start Processing"
4. **View Results**: Double-click output files to open them

## Output

Files are saved in: `docling_gui_output/[filename]/`

## Credits

- [Docling](https://github.com/DS4SD/docling) - IBM's document understanding AI
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/)
- [Pandoc](https://pandoc.org/)

## License

MIT License

cat > ~/docling/requirements.txt << 'EOF'
docling>=2.0.0
PyQt6>=6.6.0
