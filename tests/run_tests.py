#!/usr/bin/env python3
"""
Simple script to run all conversation flow tests
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

if __name__ == '__main__':
    import pytest
    
    # Run pytest with appropriate arguments
    exit_code = pytest.main([
        'tests/test_conversation_flows.py',
        '-v',
        '--tb=short',
        '--color=yes'
    ])
    
    sys.exit(exit_code)

