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

install_global_link "OpenCode" "$HOME/.config/opencode/skills"
install_global_link "Claude Code" "$HOME/.claude/skills"
install_global_link "agent-compatible" "$HOME/.agents/skills"
install_global_link "Codex" "${CODEX_HOME:-$HOME/.codex}/skills"

# 安装 memory-librarian 自定义代理到 Codex agents 目录
install_agent() {
    LABEL="$1"
    AGENTS_DIR="$2"
    AGENT_FILE="agents/memory-librarian.toml"

    if [ ! -f "$SCRIPT_DIR/$AGENT_FILE" ]; then
        return
    fi

    mkdir -p "$AGENTS_DIR"
    echo "安装 memory-librarian 代理到 $AGENTS_DIR... ($LABEL)"

    if [ -L "$AGENTS_DIR/memory-librarian.toml" ]; then
        LINK_TARGET="$(readlink "$AGENTS_DIR/memory-librarian.toml")"
        if [ "$LINK_TARGET" = "$SCRIPT_DIR/$AGENT_FILE" ]; then
            echo "  符号链接已存在: $AGENTS_DIR/memory-librarian.toml"
        else
            ln -sf "$SCRIPT_DIR/$AGENT_FILE" "$AGENTS_DIR/memory-librarian.toml"
            echo "  更新符号链接: $AGENTS_DIR/memory-librarian.toml"
        fi
    elif [ -e "$AGENTS_DIR/memory-librarian.toml" ]; then
        echo "  路径已存在且不是符号链接，跳过: $AGENTS_DIR/memory-librarian.toml"
    else
        ln -s "$SCRIPT_DIR/$AGENT_FILE" "$AGENTS_DIR/memory-librarian.toml"
        echo "  创建符号链接: $AGENTS_DIR/memory-librarian.toml"
    fi
}

install_agent "Codex" "${CODEX_HOME:-$HOME/.codex}/agents"

install_memory_hook() {
    CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"
    HOOKS_DIR="$CODEX_DIR/hooks"
    HOOK_FILE="hooks/superwiki-memory-hook.py"

    if [ ! -f "$SCRIPT_DIR/$HOOK_FILE" ]; then
        return
    fi

    mkdir -p "$HOOKS_DIR"
    echo "安装 SuperWiki memory hook 脚本到 $HOOKS_DIR..."

    if [ -L "$HOOKS_DIR/superwiki-memory-hook.py" ]; then
        ln -sf "$SCRIPT_DIR/$HOOK_FILE" "$HOOKS_DIR/superwiki-memory-hook.py"
        echo "  更新符号链接: $HOOKS_DIR/superwiki-memory-hook.py"
    elif [ -e "$HOOKS_DIR/superwiki-memory-hook.py" ]; then
        echo "  路径已存在且不是符号链接，跳过: $HOOKS_DIR/superwiki-memory-hook.py"
    else
        ln -s "$SCRIPT_DIR/$HOOK_FILE" "$HOOKS_DIR/superwiki-memory-hook.py"
        echo "  创建符号链接: $HOOKS_DIR/superwiki-memory-hook.py"
    fi

    echo "  项目级启用: superwiki-init --hook /path/to/project"
    echo "  全局启用: 手动合并 hooks/hooks.global.json 到 $CODEX_DIR/hooks.json"
}

install_memory_hook

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
