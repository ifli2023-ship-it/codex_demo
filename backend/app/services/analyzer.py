import ast
import hashlib
import re
import shutil
import uuid
from pathlib import Path

from app.core import settings
from app.models.schemas import Report
from app.services.dependencies import parse_dependencies, query_osv
from app.services.git_service import git_history, shallow_clone
from app.services.queue import JobStore, utc_now_iso
from app.services.readme_quality import llm_readme_score, read_readme
from app.services.scoring import aggregate_scores


LANGUAGE_EXTENSIONS = {
    "Python": {".py"},
    "JavaScript/TypeScript": {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"},
    "Go": {".go"},
    "Rust": {".rs"},
}

SKIP_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    "target",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".next",
    "coverage",
}


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    allowed = set().union(*LANGUAGE_EXTENSIONS.values())
    for path in root.rglob("*"):
        if len(files) >= settings.max_scan_files:
            break
        if should_skip(path.relative_to(root)) or not path.is_file():
            continue
        if path.suffix in allowed and path.stat().st_size <= settings.max_file_bytes:
            files.append(path)
    return files


def code_lines(text: str) -> list[str]:
    result = []
    for line in text.splitlines():
        clean = line.strip()
        if not clean or clean.startswith(("#", "//", "/*", "*")):
            continue
        result.append(clean)
    return result


def detect_language(files: list[Path]) -> tuple[str, dict[str, int]]:
    counts = {language: 0 for language in LANGUAGE_EXTENSIONS}
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        loc = len(code_lines(text))
        for language, exts in LANGUAGE_EXTENSIONS.items():
            if path.suffix in exts:
                counts[language] += loc
    language = max(counts.items(), key=lambda item: item[1])[0] if any(counts.values()) else "Unknown"
    return language, counts


def python_functions(path: Path, text: str) -> list[dict]:
    functions: list[dict] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return functions
    branch_nodes = (ast.If, ast.For, ast.While, ast.Try, ast.ExceptHandler, ast.BoolOp, ast.IfExp, ast.Match)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", node.lineno)
            complexity = 1 + sum(1 for child in ast.walk(node) if isinstance(child, branch_nodes))
            functions.append(
                {
                    "name": node.name,
                    "path": str(path),
                    "line": node.lineno,
                    "length": max(1, end - node.lineno + 1),
                    "complexity": complexity,
                }
            )
    return functions


FUNC_RE = re.compile(
    r"(?P<prefix>function\s+(?P<jsname>[A-Za-z0-9_$]+)|(?P<go>func\s+(?:\([^)]+\)\s*)?(?P<goname>[A-Za-z0-9_]+))|(?P<rust>fn\s+(?P<rsname>[A-Za-z0-9_]+)))"
)


def brace_functions(path: Path, text: str) -> list[dict]:
    functions: list[dict] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = FUNC_RE.search(line)
        if not match:
            continue
        name = match.group("jsname") or match.group("goname") or match.group("rsname") or "anonymous"
        depth = 0
        started = False
        end_index = index
        body_lines = []
        for cursor in range(index, min(len(lines), index + 600)):
            body_lines.append(lines[cursor])
            depth += lines[cursor].count("{")
            if "{" in lines[cursor]:
                started = True
            depth -= lines[cursor].count("}")
            if started and depth <= 0:
                end_index = cursor
                break
        body = "\n".join(body_lines)
        complexity = 1 + len(re.findall(r"\b(if|for|while|case|catch|match|&&|\|\|)\b", body))
        functions.append(
            {
                "name": name,
                "path": str(path),
                "line": index + 1,
                "length": max(1, end_index - index + 1),
                "complexity": complexity,
            }
        )
    return functions


def duplicate_rate(normalized_lines: list[str]) -> float:
    candidates = [line for line in normalized_lines if len(line) >= 12]
    if not candidates:
        return 0.0
    seen: dict[str, int] = {}
    for line in candidates:
        digest = hashlib.sha1(re.sub(r"\s+", " ", line).encode("utf-8")).hexdigest()
        seen[digest] = seen.get(digest, 0) + 1
    duplicate_lines = sum(count for count in seen.values() if count > 1)
    return round(duplicate_lines / len(candidates) * 100, 2)


def static_analysis(root: Path) -> dict:
    files = source_files(root)
    language, language_lines = detect_language(files)
    functions: list[dict] = []
    all_lines: list[str] = []
    total_lines = 0
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = code_lines(text)
        total_lines += len(lines)
        all_lines.extend(lines)
        relative = path.relative_to(root)
        if path.suffix == ".py":
            functions.extend(python_functions(relative, text))
        else:
            functions.extend(brace_functions(relative, text))
    avg_length = round(sum(item["length"] for item in functions) / len(functions), 2) if functions else 0
    top_complexity = sorted(functions, key=lambda item: item["complexity"], reverse=True)[:10]
    return {
        "language_lines": language_lines,
        "primary_language": language,
        "source_file_count": len(files),
        "total_code_lines": total_lines,
        "average_function_length": avg_length,
        "top_complexity_functions": top_complexity,
        "duplicate_code_rate": duplicate_rate(all_lines),
        "scan_limit_reached": len(files) >= settings.max_scan_files,
    }


def analyze_repository(job_store: JobStore, job_id: str, repo_url: str, normalized_repo: str, clone_url: str) -> Report:
    work_root = Path(settings.work_dir)
    repo_path = work_root / job_id
    try:
        job_store.update_job(job_id, status="running", step="Cloning repository", progress=8)
        shallow_clone(clone_url, repo_path)

        job_store.update_job(job_id, step="Scanning code", progress=28)
        static = static_analysis(repo_path)

        job_store.update_job(job_id, step="Analyzing git history", progress=48)
        history = git_history(repo_path)

        job_store.update_job(job_id, step="Checking dependencies", progress=64)
        deps = parse_dependencies(repo_path)
        vulns, vuln_error = query_osv(deps)
        dependency_report = {
            "dependency_count": len(deps),
            "dependencies": deps[:200],
            "vulnerabilities": vulns,
            "vulnerability_error": vuln_error,
        }

        job_store.update_job(job_id, step="Scoring README", progress=78)
        readme = read_readme(repo_path)
        readme_report = llm_readme_score(readme, settings.openai_api_key)

        job_store.update_job(job_id, step="Calculating health score", progress=90)
        score, breakdown = aggregate_scores(
            total_lines=static["total_code_lines"],
            file_count=static["source_file_count"],
            avg_function_length=static["average_function_length"],
            top_complexities=static["top_complexity_functions"],
            duplicate_rate=static["duplicate_code_rate"],
            recent_commits=history["recent_30_days_commits"],
            contributor_count=len(history["contributors"]),
            vulnerabilities=vulns,
            dependency_count=len(deps),
            readme_score=int(readme_report.get("score", 0)),
        )
        report = Report(
            id=str(uuid.uuid4()),
            repo_url=repo_url,
            normalized_repo=normalized_repo,
            analyzed_at=utc_now_iso(),
            language=static["primary_language"],
            score=score,
            score_breakdown=breakdown,
            summary={
                "commit_count": history["commit_count"],
                "contributors": len(history["contributors"]),
                "recent_30_days_commits": history["recent_30_days_commits"],
                "vulnerability_count": len(vulns),
                "readme_score": readme_report.get("score", 0),
            },
            static_analysis=static,
            git_history=history,
            dependencies=dependency_report,
            readme_quality=readme_report,
        )
        job_store.save_report(report)
        job_store.update_job(
            job_id,
            status="completed",
            step="Completed",
            progress=100,
            report_id=report.id,
        )
        job_store.set_cached_job(normalized_repo, job_id)
        return report
    finally:
        if repo_path.exists():
            shutil.rmtree(repo_path, ignore_errors=True)
