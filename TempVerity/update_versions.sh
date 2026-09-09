#!/bin/sh

set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
pyproject_file="$script_dir/pyproject.toml"
frontend_dir="$script_dir/frontend"
update=false
check_frontend=true
check_python=true

usage() {
    printf 'Usage: %s [--update] [--python-only | --frontend-only]\n' "$0"
    printf 'Default: report Python and npm dependency updates without modifying files.\n'
    printf '%s\n' '--update: apply Python updates and npm updates within declared version ranges.'
    printf 'npm updates save package.json and package-lock.json; major upgrades require review.\n'
}

for argument in "$@"; do
    case "$argument" in
        --update) update=true ;;
        --python-only) check_frontend=false ;;
        --frontend-only) check_python=false ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done

if [ "$check_python" = false ] && [ "$check_frontend" = false ]; then
    usage >&2
    exit 2
fi

if [ "$check_frontend" = true ]; then
    for tool in node npm; do
        command -v "$tool" >/dev/null 2>&1 || {
            printf '%s is required for frontend dependency checks\n' "$tool" >&2
            exit 1
        }
    done
    for file in package.json package-lock.json; do
        if [ ! -f "$frontend_dir/$file" ]; then
            printf 'Missing frontend file: %s\n' "$frontend_dir/$file" >&2
            exit 1
        fi
    done
fi

if [ "$check_python" = true ]; then
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
fi

if [ "$check_frontend" = true ]; then
    printf '\nFrontend dependencies:\n'
    (
        cd "$frontend_dir"
        if [ "$update" = true ]; then
            npm update --save --package-lock=true --include=dev --ignore-scripts
            printf 'Updated package.json and package-lock.json within declared ranges.\n'
            printf 'Run npm run build and review the changes before deployment.\n'
        else
            node --input-type=commonjs <<'JS'
const { spawnSync } = require('node:child_process');
const result = spawnSync('npm', ['outdated', '--json', '--long', '--package-lock-only', '--include=dev'], { encoding: 'utf8' });
if (result.stderr) process.stderr.write(result.stderr);
let packages;
try {
    packages = JSON.parse(result.stdout || '{}');
} catch {
    console.error('Unable to parse npm dependency report.');
    process.exit(1);
}
// npm returns 1 for outdated packages as well as some registry failures.
if (result.error || packages.error || ![0, 1].includes(result.status)) {
    console.error('npm dependency check failed:', result.error?.message || packages.error || result.status);
    process.exit(1);
}
if (result.status === 1 && Object.keys(packages).length === 0) {
    console.error('npm failed without returning a dependency report.');
    process.exit(1);
}
if (Object.keys(packages).length === 0) {
    console.log('All frontend dependencies are up to date.');
} else {
    console.table(Object.entries(packages).map(([name, info]) => ({
        Package: name, Locked: info.current ?? 'Not locked',
        Wanted: info.wanted, Latest: info.latest, Type: info.type,
    })));
}
JS
            printf 'Wanted respects package.json ranges; Latest may require a major upgrade.\n'
            printf 'Run with --update to save compatible updates to package.json and package-lock.json.\n'
        fi
    )
fi
