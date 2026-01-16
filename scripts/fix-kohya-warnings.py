#!/usr/bin/env python3
"""
Fix Kohya SS pkg_resources deprecation warning by patching the source file.
This script adds warning suppression at the top of the problematic file.
"""

import os
import sys
import shutil
from pathlib import Path

def fix_pkg_resources_warning():
    """Apply patch to suppress pkg_resources warnings in Kohya SS."""
    
    # Target file that contains the problematic import
    setup_common_file = Path("/opt/pilot/repos/kohya_ss/setup/setup_common.py")
    
    if not setup_common_file.exists():
        print(f"Warning: {setup_common_file} not found, skipping patch")
        return False
    
    print(f"Patching {setup_common_file} to suppress pkg_resources warning...")
    
    # Create backup
    backup_file = setup_common_file.with_suffix('.py.backup')
    if not backup_file.exists():
        shutil.copy2(setup_common_file, backup_file)
        print(f"Created backup: {backup_file}")
    
    # Read the original file
    try:
        with open(setup_common_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {setup_common_file}: {e}")
        return False
    
    # Check if already patched
    if 'warnings.filterwarnings("ignore", category=UserWarning, module=".*pkg_resources.*")' in content:
        print("File already patched")
        return True
    
    # Add warning suppression at the top
    warning_suppression = '''import warnings
# Suppress pkg_resources deprecation warning
warnings.filterwarnings("ignore", category=UserWarning, module=".*pkg_resources.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module=".*pkg_resources.*")

'''
    
    # Insert the warning suppression at the beginning
    if content.startswith('#!'):
        # If it's a script with shebang, insert after the first line
        lines = content.split('\n', 1)
        content = lines[0] + '\n' + warning_suppression + (lines[1] if len(lines) > 1 else '')
    else:
        # Otherwise, prepend at the very beginning
        content = warning_suppression + content
    
    # Write the patched file
    try:
        with open(setup_common_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patch applied successfully")
        return True
    except Exception as e:
        print(f"Error writing patched file: {e}")
        return False

def main():
    """Main function."""
    print("Fixing Kohya SS pkg_resources deprecation warning...")
    
    success = fix_pkg_resources_warning()
    
    if success:
        print("✅ Kohya SS warning fix completed successfully")
        sys.exit(0)
    else:
        print("❌ Failed to apply Kohya SS warning fix")
        sys.exit(1)

if __name__ == "__main__":
    main()
