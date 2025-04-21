# Add the app module to the Python path
import sys
import os

# Get the absolute path to the backend directory
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add the backend directory to the Python path if it's not already there
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)