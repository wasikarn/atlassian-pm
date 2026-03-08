#!/usr/bin/env python3
"""Target project architecture context provider.

Scans service directories from project-config.json and outputs
architecture hints for Explore agents. Not a hook — called by skills
that need target project context before exploration.

Usage:
    python3 .claude/hooks/target-project-context.py [service_tag]
    python3 .claude/hooks/target-project-context.py              # all services
    python3 .claude/hooks/target-project-context.py BE           # backend only
    python3 .claude/hooks/target-project-context.py FE-Admin     # admin frontend only
"""

import json
import sys
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent.parent / "project-config.json"

# Framework detection patterns → scan strategies
FRAMEWORK_PATTERNS = {
    "adonisjs": {
        "detect": ["@adonisjs/core"],
        "scan_dirs": [
            ("app/Controllers", "controller"),
            ("app/Models", "model"),
            ("app/Services", "service"),
            ("app/Modules", "module"),
            ("app/UseCases", "usecase"),
            ("app/Repositories", "repository"),
            ("app/Validators", "validator"),
            ("app/Jobs", "job"),
            ("app/Middleware", "middleware"),
        ],
        "key_files": ["start/routes.ts", "config/database.ts", "package.json", "tsconfig.json"],
    },
    "nestjs": {
        "detect": ["@nestjs/core"],
        "scan_dirs": [
            ("src/modules", "module"),
            ("src/common", "common"),
            ("src/config", "config"),
        ],
        "key_files": ["package.json", "prisma/schema.prisma", "tsconfig.json"],
    },
    "nextjs": {
        "detect": ["next"],
        "scan_dirs": [
            ("src/app", "page"),
            ("src/pages", "page"),
            ("src/components", "component"),
            ("src/hooks", "hook"),
            ("src/lib", "lib"),
            ("src/services", "service"),
            ("src/store", "store"),
            ("app", "page"),
            ("pages", "page"),
            ("components", "component"),
        ],
        "key_files": ["package.json", "next.config.js", "next.config.mjs", "tsconfig.json"],
    },
}


def expand_home(path_str: str) -> Path:
    """Expand ~ in path."""
    return Path(path_str).expanduser()


def detect_framework(path: Path) -> str:
    """Detect framework from package.json dependencies."""
    pkg_path = path / "package.json"
    if not pkg_path.exists():
        return "unknown"
    try:
        with open(pkg_path) as f:
            pkg = json.load(f)
        deps = set(pkg.get("dependencies", {}).keys())
        for fw_name, fw_config in FRAMEWORK_PATTERNS.items():
            if any(dep in deps for dep in fw_config["detect"]):
                return fw_name
    except (json.JSONDecodeError, OSError):
        pass
    return "unknown"


def scan_directory(path: Path, dir_rel: str, dir_type: str) -> list:
    """Scan a directory and return its contents summary."""
    target = path / dir_rel
    if not target.exists():
        return []

    items = []
    for entry in sorted(target.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            file_count = sum(1 for _ in entry.rglob("*") if _.is_file())
            items.append({"name": entry.name, "type": dir_type, "files": file_count})
        elif entry.is_file() and entry.suffix in (".ts", ".tsx", ".js", ".jsx"):
            items.append({"name": entry.stem, "type": dir_type})
    return items


def scan_service(tag: str, name: str, path_str: str) -> dict:
    """Scan a service directory for architecture markers."""
    path = expand_home(path_str)
    if not path.exists():
        return {"tag": tag, "name": name, "path": str(path), "exists": False}

    framework = detect_framework(path)
    fw_config = FRAMEWORK_PATTERNS.get(framework, {})

    result = {
        "tag": tag,
        "name": name,
        "path": str(path),
        "exists": True,
        "framework": framework,
        "components": [],
        "key_files": [],
    }

    # Scan framework-specific directories
    for dir_rel, dir_type in fw_config.get("scan_dirs", []):
        items = scan_directory(path, dir_rel, dir_type)
        if items:
            result["components"].append(
                {
                    "directory": dir_rel,
                    "type": dir_type,
                    "count": len(items),
                    "items": [i["name"] for i in items[:15]],  # Top 15
                }
            )

    # Check key files
    for marker in fw_config.get("key_files", ["package.json"]):
        if (path / marker).exists():
            result["key_files"].append(marker)

    return result


def main() -> None:
    if not CONFIG_PATH.exists():
        print(json.dumps({"error": f"Config not found: {CONFIG_PATH}"}))
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    services = config.get("services", {}).get("tags", [])

    # Filter by tag if provided
    filter_tag = sys.argv[1] if len(sys.argv) > 1 else None
    if filter_tag:
        if not filter_tag.startswith("["):
            filter_tag = f"[{filter_tag}]"
        services = [s for s in services if s["tag"] == filter_tag]

    results = []
    for svc in services:
        if svc.get("path"):
            results.append(scan_service(svc["tag"], svc["name"], svc["path"]))

    output = {
        "context": "target-project-architecture",
        "services": results,
        "hint": "Use component/model names as Explore search terms for targeted file discovery.",
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
