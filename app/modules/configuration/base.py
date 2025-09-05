# modules/configuration/base.py
import sys
import os
# Determine the root directory based on whether the code is frozen (e.g., PyInstaller .exe)
if getattr(sys, 'frozen', False):  # Check if running as an executable
    BASE_DIR = os.path.dirname(sys.executable)  # Use the directory of the executable
else:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

# Add the current directory to the Python module search path for flexibility
sys.path.append(BASE_DIR)
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
