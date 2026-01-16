#!/usr/bin/env python3
"""
Kohya SS wrapper script that filters out pkg_resources deprecation warnings.
This script launches Kohya GUI and suppresses the annoying warnings.
"""

import sys
import os
import subprocess
import re
import warnings
from pathlib import Path

def filter_warnings():
    """Configure warning filters to suppress pkg_resources warnings."""
    # Suppress pkg_resources warnings at the Python level
    warnings.filterwarnings("ignore", category=UserWarning, module=".*pkg_resources.*")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module=".*pkg_resources.*")
    warnings.filterwarnings("ignore", message=".*pkg_resources is deprecated.*")
    
    # Also set environment variable for additional suppression
    os.environ['PYTHONWARNINGS'] = (
        "ignore::UserWarning:pkg_resources,"
        "ignore::DeprecationWarning:pkg_resources,"
        "ignore::UserWarning",
        "ignore::DeprecationWarning"
    )

def run_kohya():
    """Run Kohya GUI with warning suppression."""
    
    # Apply warning filters
    filter_warnings()
    
    # Kohya GUI script path
    kohya_script = "/opt/pilot/repos/kohya_ss/kohya_gui.py"
    
    if not Path(kohya_script).exists():
        print(f"Error: Kohya GUI script not found at {kohya_script}")
        sys.exit(1)
    
    # Command line arguments
    host = os.environ.get("HOST", "0.0.0.0")
    port = os.environ.get("KOHYA_PORT", "6666")
    
    cmd = [
        sys.executable, "-u", kohya_script,
        "--listen", host,
        "--server_port", port
    ]
    
    print(f"Starting Kohya GUI with warning suppression...")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        # Run Kohya with output filtering
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Filter output line by line
        warning_pattern = re.compile(
            r'.*pkg_resources.*deprecated.*|'
            r'.*UserWarning.*pkg_resources.*|'
            r'.*DeprecationWarning.*pkg_resources.*'
        )
        
        for line in process.stdout:
            # Skip warning lines
            if warning_pattern.search(line):
                continue
            # Print all other lines
            print(line.rstrip())
        
        # Wait for process to complete
        return_code = process.wait()
        sys.exit(return_code)
        
    except KeyboardInterrupt:
        print("\nShutting down Kohya GUI...")
        process.terminate()
        sys.exit(0)
    except Exception as e:
        print(f"Error running Kohya GUI: {e}")
        sys.exit(1)

def main():
    """Main entry point."""
    run_kohya()

if __name__ == "__main__":
    main()
