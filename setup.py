"""
Setup script to create a macOS .app bundle for Docling GUI
"""

from setuptools import setup

APP = ['docling_gui.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['PyQt6'],
    'plist': {
        'CFBundleName': 'Docling GUI',
        'CFBundleDisplayName': 'Docling PDF Converter',
        'CFBundleGetInfoString': "Convert PDFs to HTML/MD/JSON/TXT",
        'CFBundleIdentifier': "com.docling.gui",
        'CFBundleVersion': "1.0.0",
        'CFBundleShortVersionString': "1.0.0",
        'NSHighResolutionCapable': True,
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)