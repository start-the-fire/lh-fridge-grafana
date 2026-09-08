#!/bin/sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
pyproject_file="$script_dir/pyproject.toml"
frontend_dir="$script_dir/frontend"
update=false
check_frontend=true

usage() {
    printf 'Usage: %s [--update] [--python-only]\n' "$0"
}

for argument in "$@"; do
    case "$argument" in
        --update) update=true ;;
        --python-only) check_frontend=false ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done

command -v python3 >/dev/null 2>&1 || {
    printf 'python3 is required\n' >&2
    exit 1
}

if [ ! -f "$pyproject_file" ]; then
    printf 'Missing project file: %s\n' "$pyproject_file" >&2
    exit 1
fi

python3 - "$pyproject_file" "$update" <<'PY'
import json
import re
import sys
import urllib.request
from pathlib import Path

project_file = Path(sys.argv[1])
should_update = sys.argv[2] == "true"
source = project_file.read_text()

# Only inspect runtime dependencies. Dev tooling is intentionally left to its
# own release cadence unless it is added to the runtime dependency list.
runtime_block = re.search(r'^dependencies\s*=\s*\[(.*?)^\]', source, re.MULTILINE | re.DOTALL)
if runtime_block is None:
    raise SystemExit("Could not find [project].dependencies in pyproject.toml")

pattern = re.compile(r'^(\s*)"([A-Za-z0-9_.-]+)(\[[^]]+\])?>=([^"\n]+)"(\s*,?)$', re.MULTILINE)
changes = []

for match in pattern.finditer(runtime_block.group(1)):
    indent, package, extras, current, comma = match.groups()
    lookup_name = package
    try:
        with urllib.request.urlopen(
            f"https://pypi.org/pypi/{lookup_name}/json", timeout=10
        ) as response:
            latest = json.load(response)["info"]["version"]
    except Exception:
        print(f"{package}: unable to determine latest version", file=sys.stderr)
        continue

    if current == latest:
        print(f"{package}: {current} (up to date)")
        continue

    print(f"{package}: {current} -> {latest}")
    changes.append((runtime_block.start(1) + match.start(), runtime_block.start(1) + match.end(), f'{indent}"{package}{extras or ""}>={latest}"{comma}'))

if should_update:
    for start, end, new in reversed(changes):
        source = source[:start] + new + source[end:]
    project_file.write_text(source)
else:
    print("Run with --update to apply Python changes.")
PY

if [ "$check_frontend" = true ]; then
    command -v npm >/dev/null 2>&1 || {
        printf 'npm is required for frontend dependency checks\n' >&2
        exit 1
    }

    if [ ! -f "$frontend_dir/package.json" ]; then
        printf 'Missing frontend package file: %s\n' "$frontend_dir/package.json" >&2
        exit 1
    fi

    printf '\nFrontend dependencies:\n'
    (
        cd "$frontend_dir"
        if [ "$update" = true ]; then
            npm update
        else
            npm outdated || true
            printf 'Run with --update to update packages within package.json ranges.\n'
        fi
    )
fi
