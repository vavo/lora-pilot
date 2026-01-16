#!/usr/bin/env bash
set -euo pipefail

HOST="0.0.0.0"
PORT="${KOHYA_PORT:-6666}"
ROOT="${WORKSPACE_ROOT:-/workspace}"
APP_ROOT="${ROOT}/apps/kohya"

export PATH="/opt/venvs/core/bin:$PATH"
export PYTHONUNBUFFERED=1
export PYTHONPATH="/opt/pilot/repos/kohya_ss/sd-scripts:${PYTHONPATH:-}"

mkdir -p "$ROOT/logs" "$APP_ROOT"

# Fix setuptools deprecation warning for Kohya
# This warning comes from Kohya SS itself importing pkg_resources
echo "Applying comprehensive setuptools deprecation fix for Kohya..."

# Force install setuptools<81.0 to prevent pkg_resources deprecation warning
/opt/venvs/core/bin/pip install "setuptools<81.0" --quiet --upgrade --force-reinstall --no-warn-script-location

# Apply Python patch to suppress pkg_resources warnings at the source
PATCH_SCRIPT="/opt/pilot/scripts/fix-kohya-warnings.py"
if [ -f "$PATCH_SCRIPT" ]; then
    echo "Applying Python patch to suppress pkg_resources warning..."
    /opt/venvs/core/bin/python "$PATCH_SCRIPT"
else
    echo "Warning: Patch script not found at $PATCH_SCRIPT, using fallback method"
    
    # Fallback: Create a patch to suppress the pkg_resources warning at the source
    SETUP_COMMON_FILE="/opt/pilot/repos/kohya_ss/setup/setup_common.py"
    if [ -f "$SETUP_COMMON_FILE" ]; then
        echo "Patching $SETUP_COMMON_FILE to suppress pkg_resources warning..."
        
        # Create a backup of the original file
        cp "$SETUP_COMMON_FILE" "${SETUP_COMMON_FILE}.backup"
        
        # Apply the patch to suppress the warning
        sed -i '1i\
import warnings\
warnings.filterwarnings("ignore", category=UserWarning, module=".*pkg_resources.*")' "$SETUP_COMMON_FILE"
        
        echo "Fallback patch applied successfully"
    else
        echo "Warning: $SETUP_COMMON_FILE not found, skipping patch"
    fi
fi

# Additional suppression via environment variables
export PYTHONWARNINGS="ignore::UserWarning:pkg_resources,ignore::DeprecationWarning:pkg_resources"

# Verify the fix
SETUPTOOLS_VERSION=$(/opt/venvs/core/bin/python -c "import setuptools; print(setuptools.__version__)" 2>/dev/null || echo "unknown")
echo "Setuptools version: $SETUPTOOLS_VERSION"

cd /opt/pilot/repos/kohya_ss

# Use wrapper script for comprehensive warning suppression
WRAPPER_SCRIPT="/opt/pilot/scripts/kohya-wrapper.py"
if [ -f "$WRAPPER_SCRIPT" ]; then
    echo "Using Kohya wrapper script for comprehensive warning suppression..."
    exec /opt/venvs/core/bin/python "$WRAPPER_SCRIPT"
else
    echo "Wrapper script not found, using direct execution with environment suppression..."
    # Fallback to direct execution with environment variables
    exec /opt/venvs/core/bin/python -u kohya_gui.py \
      --listen "$HOST" \
      --server_port "$PORT"
fi
