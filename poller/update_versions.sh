#!/bin/sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
requirements_file="$script_dir/requirements.txt"
update=false

for argument in "$@"; do
    case "$argument" in
        --update) update=true ;;
        -*)
            printf 'Usage: %s [requirements-file] [--update]\n' "$0" >&2
            exit 2
            ;;
        *) requirements_file=$argument ;;
    esac
done

if [ ! -f "$requirements_file" ]; then
    printf 'Requirements file not found: %s\n' "$requirements_file" >&2
    exit 1
fi

command -v python3 >/dev/null 2>&1 || {
    printf 'python3 is required\n' >&2
    exit 1
}

while IFS= read -r requirement; do
    case "$requirement" in
        ''|'#'*) continue ;;
    esac

    package=${requirement%%==*}
    current=${requirement#*==}
    latest=$(python3 -c '
import json
import sys
import urllib.request

with urllib.request.urlopen(
    "https://pypi.org/pypi/%s/json" % sys.argv[1], timeout=10
) as response:
    print(json.load(response)["info"]["version"])
' "$package" 2>/dev/null || true)

    if [ -z "$latest" ]; then
        printf '%s: unable to determine latest version\n' "$package" >&2
        continue
    fi

    if [ "$current" = "$latest" ]; then
        printf '%s: %s (up to date)\n' "$package" "$current"
    else
        printf '%s: %s -> %s\n' "$package" "$current" "$latest"
        if [ "$update" = true ]; then
            escaped_package=$(printf '%s' "$package" | sed 's/[][\\.^$*]/\\&/g')
            sed "s/^${escaped_package}==.*/${package}==${latest}/" \
                "$requirements_file" > "$requirements_file.tmp"
            mv "$requirements_file.tmp" "$requirements_file"
        fi
    fi
done < "$requirements_file"

if [ "$update" = false ]; then
    printf 'Run with --update to apply changes.\n'
fi
