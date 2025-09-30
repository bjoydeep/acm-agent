#!/usr/bin/env python3
"""
ACM Agent Runner
Entry point for the ACM chatbot application
"""

import sys
import os

# Add src to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    from src.app import main
    main()