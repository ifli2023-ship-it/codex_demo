from pathlib import Path

from app.services.analyzer import duplicate_rate, static_analysis
from app.utils.github import normalize_github_url


def test_normalize_github_url_accepts_https_and_git_suffix():
    normalized, clone_url = normalize_github_url("https://github.com/facebook/react.git")
    assert normalized == "facebook/react"
    assert clone_url == "https://github.com/facebook/react.git"


def test_static_analysis_detects_python_metrics(tmp_path: Path):
    (tmp_path / "app.py").write_text(
        "def a(x):\n"
        "    if x:\n"
        "        return 1\n"
        "    return 0\n",
        encoding="utf-8",
    )
    result = static_analysis(tmp_path)
    assert result["primary_language"] == "Python"
    assert result["source_file_count"] == 1
    assert result["top_complexity_functions"][0]["complexity"] == 2


def test_duplicate_rate_counts_repeated_lines():
    lines = ["const duplicatedLine = true;"] * 4 + ["const uniqueLine = false;"]
    assert duplicate_rate(lines) > 50
