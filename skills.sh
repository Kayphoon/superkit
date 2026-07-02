#!/bin/bash
# SuperWiki 安装脚本
# 用法: ./skills.sh [项目路径]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_NAME="superwiki"

install_global_link() {
    LABEL="$1"
    SKILLS_DIR="$2"
    LINK_PATH="$SKILLS_DIR/$SKILL_NAME"

    mkdir -p "$SKILLS_DIR"
    echo "安装 $SKILL_NAME 到 $SKILLS_DIR... ($LABEL)"

    if [ -L "$LINK_PATH" ]; then
        LINK_TARGET="$(readlink "$LINK_PATH")"
        if [ "$LINK_TARGET" = "$SCRIPT_DIR" ]; then
            echo "⏭️  符号链接已存在: $LINK_PATH"
        else
            echo "⚠️  符号链接已存在但指向 $LINK_TARGET，跳过: $LINK_PATH"
        fi
    elif [ -e "$LINK_PATH" ]; then
        echo "⚠️  路径已存在且不是符号链接，跳过: $LINK_PATH"
    else
        ln -s "$SCRIPT_DIR" "$LINK_PATH"
        echo "✅ 创建符号链接: $LINK_PATH -> $SCRIPT_DIR"
    fi
}

# 安装 skill 到常见全局 skill 根目录
install_global_link "OpenCode" "$HOME/.config/opencode/skills"
install_global_link "Claude Code" "$HOME/.claude/skills"
install_global_link "agent-compatible" "$HOME/.agents/skills"
install_global_link "Codex" "${CODEX_HOME:-$HOME/.codex}/skills"

# 如果指定了项目路径，初始化该项目
if [ -n "$1" ]; then
    echo ""
    echo "初始化项目: $1"
    "$SCRIPT_DIR/superwiki-init" "$1"
fi

echo ""
echo "安装完成！"
echo ""
echo "使用方式:"
echo "  1. 在项目中初始化: $SCRIPT_DIR/superwiki-init /path/to/project"
echo "  2. 加载 skill: skill(name=\"$SKILL_NAME\")"
