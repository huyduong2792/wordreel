#!/usr/bin/env bash
# PreToolUse hook: protect-files.sh
# Blocks edits to protected files (.env, migrations, credentials)
# Exit 2 = block, Exit 0 = allow

PROTECTED_PATTERNS=(
    ".env"
    ".env.local"
    ".env.production"
    "credentials"
    "secrets"
    "migration"
)

get_file_path() {
    # Claude Opus passes the file path as stdin
    cat
}

check_protected() {
    local file_path="$1"

    # Check if the file matches any protected pattern
    for pattern in "${PROTECTED_PATTERNS[@]}"; do
        if [[ "$file_path" == *"$pattern"* ]]; then
            echo "ERROR: Editing protected file: $file_path" >&2
            echo "Protected files (${PROTECTED_PATTERNS[*]}) cannot be edited." >&2
            echo "If you need to modify this file, please do so manually." >&2
            return 1
        fi
    done
    return 0
}

main() {
    local file_path
    file_path=$(get_file_path)

    if check_protected "$file_path"; then
        exit 0
    else
        exit 2
    fi
}

main "$@"
