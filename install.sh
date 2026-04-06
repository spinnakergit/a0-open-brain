#!/bin/bash
# Install the Open Brain plugin into an Agent Zero instance.
#
# Usage:
#   ./install.sh                          # Auto-detect Agent Zero root
#   ./install.sh /path/to/agent-zero      # Install to specified path

set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -n "${1:-}" ]; then
    A0_ROOT="$1"
elif [ -d "/a0/plugins" ]; then
    A0_ROOT="/a0"
elif [ -d "/git/agent-zero/plugins" ]; then
    A0_ROOT="/git/agent-zero"
else
    echo "Error: Cannot find Agent Zero. Pass the path as argument."
    exit 1
fi

PLUGIN_DIR="$A0_ROOT/usr/plugins/open_brain"

echo "=== Open Brain Plugin Installer ==="
echo "Source:  $SCRIPT_DIR"
echo "Target:  $PLUGIN_DIR"
echo ""

mkdir -p "$PLUGIN_DIR"

echo "Copying plugin files..."
cp -r "$SCRIPT_DIR/plugin.yaml" "$PLUGIN_DIR/"
cp -r "$SCRIPT_DIR/default_config.yaml" "$PLUGIN_DIR/"
cp -r "$SCRIPT_DIR/initialize.py" "$PLUGIN_DIR/"
cp -r "$SCRIPT_DIR/helpers" "$PLUGIN_DIR/"
cp -r "$SCRIPT_DIR/tools" "$PLUGIN_DIR/"
cp -r "$SCRIPT_DIR/prompts" "$PLUGIN_DIR/"
cp -r "$SCRIPT_DIR/api" "$PLUGIN_DIR/"
cp -r "$SCRIPT_DIR/webui" "$PLUGIN_DIR/"

[ -d "$SCRIPT_DIR/extensions" ] && cp -r "$SCRIPT_DIR/extensions" "$PLUGIN_DIR/"
[ -d "$SCRIPT_DIR/docs" ] && cp -r "$SCRIPT_DIR/docs" "$PLUGIN_DIR/"
[ -f "$SCRIPT_DIR/README.md" ] && cp "$SCRIPT_DIR/README.md" "$PLUGIN_DIR/"
[ -f "$SCRIPT_DIR/LICENSE" ] && cp "$SCRIPT_DIR/LICENSE" "$PLUGIN_DIR/"

mkdir -p "$PLUGIN_DIR/data"
chmod 700 "$PLUGIN_DIR/data"

SKILLS_DIR="$A0_ROOT/usr/skills"
echo "Copying skills..."
for skill_dir in "$SCRIPT_DIR/skills"/*/; do
    skill_name="$(basename "$skill_dir")"
    mkdir -p "$SKILLS_DIR/$skill_name"
    cp -r "$skill_dir"* "$SKILLS_DIR/$skill_name/"
done

echo "Installing dependencies..."
python3 "$PLUGIN_DIR/initialize.py" || python "$PLUGIN_DIR/initialize.py"

touch "$PLUGIN_DIR/.toggle-1"

SYMLINK="$A0_ROOT/plugins/open_brain"
if [ ! -e "$SYMLINK" ]; then
    ln -sf "$PLUGIN_DIR" "$SYMLINK"
    echo "Created symlink: $SYMLINK -> $PLUGIN_DIR"
fi

if [ "$A0_ROOT" = "/a0" ] && [ -d "/git/agent-zero/usr" ]; then
    GIT_PLUGIN="/git/agent-zero/usr/plugins/open_brain"
    mkdir -p "$(dirname "$GIT_PLUGIN")"
    cp -r "$PLUGIN_DIR" "$GIT_PLUGIN" 2>/dev/null || true
fi

echo ""
echo "=== Installation complete ==="
echo "Plugin installed to: $PLUGIN_DIR"
echo ""
echo "Next steps:"
echo "  1. Configure credentials in the Open Brain plugin settings (WebUI)"
echo "  2. Restart Agent Zero to load the plugin"
