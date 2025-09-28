#!/usr/bin/env python3
"""
SL1S Sanitizer - Validates SL1S 3D printing files against common issues
Checks for proper structure, file presence, naming conventions, and configuration consistency
"""

import os
import sys
import zipfile
import configparser
from pathlib import Path
import re

class SL1SSanitizer:
    def __init__(self, sl1s_file_path):
        self.sl1s_file_path = Path(sl1s_file_path)
        self.errors = []
        self.warnings = []
        self.image_files = []
        self.config = None
        
    def validate_sl1s_file(self):
        """Main validation function that runs all checks"""
        print(f"Validating SL1S file: {self.sl1s_file_path}")
        print("=" * 60)
        
        # Run all validation checks
        self._check_file_exists()
        if self.errors:
            return self._generate_report()
            
        self._check_zip_structure()
        self._check_required_files()
        self._extract_config()
        self._check_image_files()
        self._check_config_consistency()
        
        return self._generate_report()
    
    def _check_file_exists(self):
        """Check if the SL1S file exists"""
        if not self.sl1s_file_path.exists():
            self.errors.append(f"SL1S file not found: {self.sl1s_file_path}")
    
    def _check_zip_structure(self):
        """Check if zip file has proper structure (no subfolder at root)"""
        try:
            with zipfile.ZipFile(self.sl1s_file_path, 'r') as zip_ref:
                # Get all file paths in the zip
                file_list = zip_ref.namelist()
                
                # Check if there's a single subfolder containing all files
                root_files = [f for f in file_list if '/' not in f or f.count('/') == 1]
                if not root_files:
                    self.errors.append("Zip file appears to be empty or has nested folder structure")
                    return
                
                # Check if files are directly in root or in a single subfolder
                # Ignore thumbnail and preview folders as they are standard
                has_subfolder = any('/' in f and not f.startswith(('thumbnail/', 'preview/')) for f in file_list)
                if has_subfolder:
                    # Get all folder names, excluding thumbnail and preview folders
                    folders = {f.split('/')[0] for f in file_list if '/' in f and not f.startswith(('thumbnail/', 'preview/'))}
                    if folders:
                        for folder_name in folders:
                            self.warnings.append(f"Files are contained in subfolder '{folder_name}'. This may cause issues with some slicers.")
        except zipfile.BadZipFile:
            self.errors.append("File is not a valid ZIP archive")
        except Exception as e:
            self.errors.append(f"Error reading ZIP file: {str(e)}")
    
    def _check_required_files(self):
        """Check if required files (config.ini, prusaslicer.ini) are present"""
        required_files = ['config.ini', 'prusaslicer.ini']
        
        try:
            with zipfile.ZipFile(self.sl1s_file_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                for required_file in required_files:
                    # Check if file exists in root or in any subfolder (excluding thumbnails)
                    found = any(required_file in f and f.endswith(required_file) and not f.startswith('thumbnail/') for f in file_list)
                    if not found:
                        self.errors.append(f"Required file missing: {required_file}")
        except Exception as e:
            self.errors.append(f"Error checking required files: {str(e)}")
    
    def _extract_config(self):
        """Extract and parse config.ini file - handle different formats"""
        try:
            with zipfile.ZipFile(self.sl1s_file_path, 'r') as zip_ref:
                # Find config.ini in the archive (excluding thumbnail folder)
                config_files = [f for f in zip_ref.namelist() if f.endswith('config.ini') and not f.startswith('thumbnail/')]
                if not config_files:
                    self.errors.append("config.ini file not found in archive")
                    return
                
                # Use the first config.ini found
                config_file = config_files[0]
                with zip_ref.open(config_file) as f:
                    config_content = f.read().decode('utf-8')
                
                # Try to parse as standard INI format first
                self.config = configparser.ConfigParser()
                try:
                    self.config.read_string(config_content)
                except configparser.MissingSectionHeaderError:
                    # If it fails, it might be a simple key=value format without sections
                    # Let's create a default section and parse it
                    self.config = configparser.ConfigParser()
                    wrapped_content = '[DEFAULT]\n' + config_content
                    self.config.read_string(wrapped_content)
                    
        except Exception as e:
            self.errors.append(f"Error reading config.ini: {str(e)}")
    
    def _is_thumbnail_or_preview_file(self, file_path):
        """Check if file is a thumbnail or preview (should be ignored for validation)"""
        return file_path.startswith(('thumbnail/', 'preview/'))
    
    def _is_layer_image(self, file_path):
        """Check if file is a layer image (should be validated)"""
        # Layer images are typically in root or in a job folder, not in thumbnail/preview folders
        return (file_path.lower().endswith(('.png', '.jpg', '.jpeg')) 
                and not self._is_thumbnail_or_preview_file(file_path)
                and not '/' in file_path)  # Layer images are usually in root
    
    def _check_image_files(self):
        """Check image files for proper naming and numbering - only layer images, not thumbnails"""
        try:
            with zipfile.ZipFile(self.sl1s_file_path, 'r') as zip_ref:
                # Find all layer image files (excluding thumbnails and previews)
                image_files = [f for f in zip_ref.namelist() if self._is_layer_image(f)]
                self.image_files = image_files
                
                if not image_files:
                    self.warnings.append("No layer image files found in archive")
                    return
                
                # Extract base name and check numbering
                pattern = r'(.+?)(\d{5})\.(png|jpg|jpeg)$'
                
                base_names = set()
                numbers = []
                
                for img_file in image_files:
                    # Get just the filename for pattern matching (remove path)
                    filename = os.path.basename(img_file)
                    match = re.search(pattern, filename, re.IGNORECASE)
                    if not match:
                        self.errors.append(f"Layer image file doesn't match naming pattern (should be name#####.png): {img_file}")
                        continue
                    
                    base_name = match.group(1)
                    number_str = match.group(2)
                    
                    base_names.add(base_name)
                    numbers.append(int(number_str))
                
                # Check for consistent base names
                if len(base_names) > 1:
                    self.errors.append(f"Multiple image base names found: {base_names}. All layer images should have the same base name.")
                
                # Check numbering sequence
                if numbers:
                    numbers.sort()
                    expected_sequence = list(range(numbers[0], numbers[0] + len(numbers)))
                    
                    if numbers != expected_sequence:
                        missing = set(expected_sequence) - set(numbers)
                        if missing:
                            self.errors.append(f"Missing layer image numbers: {sorted(missing)}")
                    
                    # Check if starts with 00000
                    if numbers[0] != 0:
                        self.warnings.append(f"Layer image numbering doesn't start at 00000 (starts at {numbers[0]:05d})")
                    
                    # Check for five-digit format
                    for num in numbers:
                        if num < 0 or num > 99999:
                            self.errors.append(f"Layer image number out of five-digit range: {num}")
                
        except Exception as e:
            self.errors.append(f"Error checking image files: {str(e)}")
    
    def _get_config_value(self, section, key, default=None):
        """Safely get config value, handling different section formats"""
        if not self.config:
            return default
        
        # Try the specified section first
        if self.config.has_section(section) and key in self.config[section]:
            return self.config[section][key]
        
        # Try DEFAULT section (for files without explicit sections)
        if self.config.has_section('DEFAULT') and key in self.config['DEFAULT']:
            return self.config['DEFAULT'][key]
        
        # Try any section that might contain the key
        for sec in self.config.sections():
            if key in self.config[sec]:
                return self.config[sec][key]
        
        return default
    
    def _check_config_consistency(self):
        """Check consistency between config.ini and image files"""
        if not self.config:
            return
            
        try:
            # Check jobDir matches image base name
            job_dir = self._get_config_value('layerRenderParams', 'jobDir')
            if job_dir:
                if self.image_files:
                    # Extract base name from first layer image
                    first_image = self.image_files[0]
                    filename = os.path.basename(first_image)
                    pattern = r'(.+?)\d{5}\.(png|jpg|jpeg)$'
                    match = re.search(pattern, filename, re.IGNORECASE)
                    
                    if match:
                        image_base = match.group(1).rstrip('_').rstrip('-')
                        config_base = job_dir.rstrip('_').rstrip('-')
                        
                        if image_base != config_base:
                            self.errors.append(f"Layer image base name '{image_base}' doesn't match jobDir '{config_base}' in config.ini")
            
            # Check numFast matches total number of layer images
            num_fast_str = self._get_config_value('layerRenderParams', 'numFast')
            if num_fast_str:
                try:
                    num_fast = int(num_fast_str)
                    image_count = len(self.image_files)
                    
                    if num_fast != image_count:
                        self.errors.append(f"numFast in config.ini ({num_fast}) doesn't match number of layer image files ({image_count})")
                    
                    # Verify that last image number is numFast-1
                    if self.image_files:
                        pattern = r'.+?(\d{5})\.(png|jpg|jpeg)$'
                        numbers = []
                        for img_file in self.image_files:
                            filename = os.path.basename(img_file)
                            match = re.search(pattern, filename, re.IGNORECASE)
                            if match:
                                numbers.append(int(match.group(1)))
                        
                        if numbers:
                            max_number = max(numbers)
                            if max_number != num_fast - 1:
                                self.errors.append(f"Last layer image number ({max_number}) doesn't match numFast-1 ({num_fast - 1})")
                                
                except ValueError:
                    self.errors.append("numFast in config.ini is not a valid integer")
                    
        except Exception as e:
            self.errors.append(f"Error checking config consistency: {str(e)}")
    
    def _generate_report(self):
        """Generate validation report"""
        print("VALIDATION REPORT")
        print("=" * 60)
        
        if not self.errors and not self.warnings:
            print("✅ SL1S file is valid and meets all criteria!")
            return True
        
        if self.errors:
            print("❌ ERRORS:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print("⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        print("=" * 60)
        
        if self.errors:
            print(f"❌ Validation failed with {len(self.errors)} error(s)")
            return False
        else:
            print(f"✅ Validation passed with {len(self.warnings)} warning(s)")
            return True

def main():
    """Main function for command line usage"""
    if len(sys.argv) != 2:
        print("Usage: python sl1s_sanitizer.py <path_to_sl1s_file>")
        print("Example: python sl1s_sanitizer.py my_print.sl1s")
        sys.exit(1)
    
    sl1s_file = sys.argv[1]
    
    if not sl1s_file.lower().endswith('.sl1s'):
        print("Warning: File doesn't have .sl1s extension")
    
    sanitizer = SL1SSanitizer(sl1s_file)
    is_valid = sanitizer.validate_sl1s_file()
    
    sys.exit(0 if is_valid else 1)

if __name__ == "__main__":
    main()
    