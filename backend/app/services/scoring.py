from app.models.schemas import ScoreBreakdown


def clamp(value: float, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, round(value)))


def score_size(total_lines: int, file_count: int, avg_function_length: float) -> int:
    penalty = 0
    if total_lines > 100_000:
        penalty += 12
    if total_lines > 500_000:
        penalty += 10
    if file_count > 5_000:
        penalty += 8
    penalty += max(0, avg_function_length - 40) * 0.8
    return clamp(100 - penalty)


def score_complexity(top_complexities: list[dict]) -> int:
    if not top_complexities:
        return 92
    worst = max(item.get("complexity", 0) for item in top_complexities)
    avg_top = sum(item.get("complexity", 0) for item in top_complexities) / len(top_complexities)
    return clamp(100 - worst * 2.2 - avg_top * 1.2)


def score_duplication(duplicate_rate: float) -> int:
    return clamp(100 - duplicate_rate * 2.5)


def score_activity(recent_commits: int, contributor_count: int) -> int:
    recent_score = min(65, recent_commits * 4)
    contributor_score = min(35, contributor_count * 7)
    return clamp(recent_score + contributor_score)


def score_dependencies(vulnerabilities: list[dict], dependency_count: int) -> int:
    severity_penalty = 0
    weights = {"CRITICAL": 25, "HIGH": 15, "MODERATE": 8, "MEDIUM": 8, "LOW": 3}
    for vuln in vulnerabilities:
        severity = str(vuln.get("severity", "LOW")).upper()
        severity_penalty += weights.get(severity, 5)
    if dependency_count == 0:
        return 85
    return clamp(100 - severity_penalty)


def aggregate_scores(
    total_lines: int,
    file_count: int,
    avg_function_length: float,
    top_complexities: list[dict],
    duplicate_rate: float,
    recent_commits: int,
    contributor_count: int,
    vulnerabilities: list[dict],
    dependency_count: int,
    readme_score: int,
) -> tuple[int, ScoreBreakdown]:
    breakdown = ScoreBreakdown(
        size=score_size(total_lines, file_count, avg_function_length),
        complexity=score_complexity(top_complexities),
        duplication=score_duplication(duplicate_rate),
        activity=score_activity(recent_commits, contributor_count),
        dependencies=score_dependencies(vulnerabilities, dependency_count),
        readme=clamp(readme_score),
    )
    weights = {
        "size": 0.15,
        "complexity": 0.22,
        "duplication": 0.15,
        "activity": 0.16,
        "dependencies": 0.18,
        "readme": 0.14,
    }
    total = sum(getattr(breakdown, name) * weight for name, weight in weights.items())
    return clamp(total), breakdown
