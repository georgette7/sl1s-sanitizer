#!/usr/bin/env python3
"""
Test script for SL1S Sanitizer
"""

import tempfile
import zipfile
import os
from pathlib import Path

def create_test_sl1s(filename, has_errors=False):
    """Create a test SL1S file for testing"""
    with zipfile.ZipFile(filename, 'w') as zipf:
        # Add config.ini
        config_content = """[layerRenderParams]
jobDir = my_print
numFast = 5
exposureTime = 10
"""
        zipf.writestr('config.ini', config_content)
        
        # Add prusaslicer.ini
        zipf.writestr('prusaslicer.ini', '[settings]')
        
        # Add image files
        base_name = "my_print_" if not has_errors else "wrong_name_"
        for i in range(5):
            zipf.writestr(f'{base_name}{i:05d}.png', 'fake image data')

if __name__ == "__main__":
    # Test with valid file
    print("Testing with valid SL1S file...")
    create_test_sl1s('test_valid.sl1s')
    
    from sl1s_sanitizer import SL1SSanitizer
    sanitizer = SL1SSanitizer('test_valid.sl1s')
    sanitizer.validate_sl1s_file()
    
    # Cleanup
    os.remove('test_valid.sl1s')