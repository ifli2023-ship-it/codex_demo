import json
import re
from pathlib import Path

import requests


def parse_requirements(root: Path) -> list[dict]:
    path = root / "requirements.txt"
    deps: list[dict] = []
    if not path.exists():
        return deps
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#") or clean.startswith("-"):
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)\s*(?:==|~=|>=|<=|>|<)?\s*([A-Za-z0-9_.!*+-]*)?", clean)
        if match:
            deps.append({"ecosystem": "PyPI", "name": match.group(1), "version": match.group(2) or None})
    return deps


def parse_package_json(root: Path) -> list[dict]:
    path = root / "package.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError:
        return []
    deps: list[dict] = []
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        for name, version in data.get(section, {}).items():
            deps.append({"ecosystem": "npm", "name": name, "version": str(version).lstrip("^~>=<") or None})
    return deps


def parse_go_mod(root: Path) -> list[dict]:
    path = root / "go.mod"
    if not path.exists():
        return []
    deps: list[dict] = []
    in_block = False
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        clean = line.strip()
        if clean.startswith("require ("):
            in_block = True
            continue
        if in_block and clean == ")":
            in_block = False
            continue
        if clean.startswith("require "):
            clean = clean.removeprefix("require ").strip()
        if in_block or clean.startswith("github.com/") or clean.startswith("golang.org/"):
            parts = clean.split()
            if len(parts) >= 2:
                deps.append({"ecosystem": "Go", "name": parts[0], "version": parts[1].lstrip("v")})
    return deps


def parse_cargo_toml(root: Path) -> list[dict]:
    path = root / "Cargo.toml"
    if not path.exists():
        return []
    deps: list[dict] = []
    current_section = ""
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        clean = line.strip()
        if clean.startswith("[") and clean.endswith("]"):
            current_section = clean.strip("[]")
            continue
        if current_section not in {"dependencies", "dev-dependencies", "build-dependencies"}:
            continue
        if not clean or clean.startswith("#") or "=" not in clean:
            continue
        name, raw_value = clean.split("=", 1)
        name = name.strip().strip('"')
        version_match = re.search(r'version\s*=\s*"([^"]+)"', raw_value)
        version = version_match.group(1) if version_match else raw_value.strip().strip('"')
        if name:
            deps.append({"ecosystem": "crates.io", "name": name, "version": version.lstrip("^~>=<") or None})
    return deps


def parse_dependencies(root: Path) -> list[dict]:
    seen: set[tuple[str, str, str | None]] = set()
    deps: list[dict] = []
    for parser in (parse_requirements, parse_package_json, parse_go_mod, parse_cargo_toml):
        for dep in parser(root):
            key = (dep["ecosystem"], dep["name"], dep.get("version"))
            if key not in seen:
                seen.add(key)
                deps.append(dep)
    return deps


def query_osv(dependencies: list[dict], timeout: int = 15) -> tuple[list[dict], str | None]:
    if not dependencies:
        return [], None
    vulnerabilities: list[dict] = []
    queries = []
    for dep in dependencies[:1000]:
        package = {"ecosystem": dep["ecosystem"], "name": dep["name"]}
        query = {"package": package}
        if dep.get("version"):
            query["version"] = dep["version"]
        queries.append(query)
    try:
        response = requests.post("https://api.osv.dev/v1/querybatch", json={"queries": queries}, timeout=timeout)
        response.raise_for_status()
        results = response.json().get("results", [])
    except requests.RequestException as exc:
        return [], str(exc)

    for dep, result in zip(dependencies, results):
        for vuln in result.get("vulns", []):
            severity = "LOW"
            for item in vuln.get("severity", []):
                if item.get("type") == "CVSS_V3":
                    score = float(str(item.get("score", "0")).split("/")[0] or 0)
                    if score >= 9:
                        severity = "CRITICAL"
                    elif score >= 7:
                        severity = "HIGH"
                    elif score >= 4:
                        severity = "MODERATE"
            vulnerabilities.append(
                {
                    "package": dep["name"],
                    "ecosystem": dep["ecosystem"],
                    "id": vuln.get("id"),
                    "summary": vuln.get("summary", ""),
                    "severity": severity,
                    "url": f"https://osv.dev/vulnerability/{vuln.get('id')}",
                }
            )
    return vulnerabilities, None
