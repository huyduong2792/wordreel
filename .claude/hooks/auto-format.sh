#!/usr/bin/env bash
# PostToolUse hook: auto-format.sh
# Runs formatters after Edit/Write operations
# Non-blocking - always exits 0

get_file_path() {
    cat
}

get_file_ext() {
    local file_path="$1"
    echo "${file_path##*.}"
}

run_black() {
    local file_path="$1"
    if command -v black >/dev/null 2>&1; then
        black "$file_path" 2>/dev/null
    fi
}

run_prettier() {
    local file_path="$1"
    if command -v prettier >/dev/null 2>&1; then
        prettier --write "$file_path" 2>/dev/null
    fi
}

main() {
    local file_path
    local ext
    file_path=$(get_file_path)
    ext=$(get_file_ext "$file_path")

    case "$ext" in
        py)
            run_black "$file_path"
            ;;
        ts|tsx|js|jsx)
            run_prettier "$file_path"
            ;;
    esac
}

main "$@"
