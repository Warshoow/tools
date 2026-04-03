#!/bin/bash
# .devcontainer/setup-dev.sh

# Installer Claude Code
curl -fsSL https://claude.ai/install.sh | bash

# Autoriser Git à lire le repo monté
git config --global --add safe.directory /app

# Prompt Git dans le terminal
cat >> /root/.bashrc << 'EOF'
parse_git_branch() { git branch 2>/dev/null | grep "^*" | sed "s/* //"; }
export PS1="\[\033[01;34m\]\w\[\033[33m\] (\$(parse_git_branch))\[\033[00m\] \$ "
EOF