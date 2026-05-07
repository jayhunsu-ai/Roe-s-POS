#!/usr/bin/env python3
"""
Run script for POS Client Application
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import and run the application
from pos_client import main

if __name__ == "__main__":
    main()