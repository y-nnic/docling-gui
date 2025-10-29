#!/bin/bash

echo "======================================"
echo "Docling GUI - Installation Script"
echo "======================================"
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "Please install Python 3.9 or higher from python.org"
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Check if brew is installed
if ! command -v brew &> /dev/null; then
    echo "⚠️  Homebrew not found. Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi

echo "✓ Homebrew found"

# Install system dependencies
echo ""
echo "Installing system dependencies..."
brew install poppler pandoc

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv .venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo ""
echo "Installing Python packages..."
pip install -r requirements.txt

# Create launcher script
echo ""
echo "Creating launcher script..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cat > "$SCRIPT_DIR/start_docling_gui.command" << 'LAUNCHER'
#!/bin/bash
cd "$SCRIPT_DIR"
source .venv/bin/activate
python docling_gui.py
LAUNCHER

chmod +x "$SCRIPT_DIR/start_docling_gui.command"

echo ""
echo "======================================"
echo "✅ Installation complete!"
echo "======================================"
echo ""
echo "To start the application:"
echo "Double-click 'start_docling_gui.command'"
echo ""
