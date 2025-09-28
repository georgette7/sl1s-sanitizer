# SL1S File Sanitizer

A Python script to validate SL1S 3D printing files against common issues and ensure proper structure.

## Features

- Validates ZIP structure and file organization
- Checks for required files (config.ini, prusaslicer.ini)
- Verifies image naming conventions (five-digit numbering)
- Ensures config.ini consistency with image files
- Handles thumbnail folders appropriately

## Usage

```bash
python sl1s_sanitizer.py <path_to_sl1s_file>
