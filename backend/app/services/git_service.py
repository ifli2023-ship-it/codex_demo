import shutil
import subprocess
from pathlib import Path


def run_git(args: list[str], cwd: Path | None = None, timeout: int = 120) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=True,
    )
    return completed.stdout


def shallow_clone(clone_url: str, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        run_git(["clone", "--depth", "100", "--single-branch", clone_url, str(destination)], timeout=300)
    except subprocess.CalledProcessError:
        if destination.exists():
            shutil.rmtree(destination)
        run_git(["clone", "--depth", "100", clone_url, str(destination)], timeout=300)


def git_history(root: Path) -> dict:
    log = run_git(["log", "--date=short", "--pretty=format:%H%x09%an%x09%ad"], cwd=root)
    commits = []
    contributors: dict[str, int] = {}
    weekly: dict[str, int] = {}
    recent_30 = 0
    from datetime import date, datetime, timedelta

    today = date.today()
    for line in log.splitlines():
        sha, author, day = line.split("\t", 2)
        commit_date = datetime.strptime(day, "%Y-%m-%d").date()
        iso_year, iso_week, _ = commit_date.isocalendar()
        week_key = f"{iso_year}-W{iso_week:02d}"
        contributors[author] = contributors.get(author, 0) + 1
        weekly[week_key] = weekly.get(week_key, 0) + 1
        if commit_date >= today - timedelta(days=30):
            recent_30 += 1
        commits.append({"sha": sha, "author": author, "date": day, "week": week_key})

    changed = run_git(["log", "--name-only", "--pretty=format:"], cwd=root)
    change_counts: dict[str, int] = {}
    for line in changed.splitlines():
        path = line.strip()
        if path:
            change_counts[path] = change_counts.get(path, 0) + 1

    high_risk = []
    for file_path, changes in change_counts.items():
        full_path = root / file_path
        if full_path.exists() and full_path.is_file():
            size = full_path.stat().st_size
            high_risk.append(
                {
                    "path": file_path,
                    "changes": changes,
                    "size_bytes": size,
                    "risk_score": changes * 0.7 + min(size / 2000, 100) * 0.3,
                }
            )
    high_risk.sort(key=lambda item: item["risk_score"], reverse=True)

    return {
        "commit_count": len(commits),
        "contributors": sorted(
            [{"name": name, "commits": count} for name, count in contributors.items()],
            key=lambda item: item["commits"],
            reverse=True,
        )[:25],
        "weekly_heatmap": [{"week": week, "commits": count} for week, count in sorted(weekly.items())],
        "recent_30_days_commits": recent_30,
        "high_risk_files": high_risk[:20],
    }
