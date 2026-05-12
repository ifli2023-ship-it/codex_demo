from pathlib import Path

import requests


README_NAMES = ("README.md", "README.rst", "README.txt", "readme.md")


def read_readme(root: Path) -> str:
    for name in README_NAMES:
        path = root / name
        if path.exists():
            return path.read_text(encoding="utf-8", errors="ignore")[:30000]
    return ""


def heuristic_readme_score(text: str) -> dict:
    lower = text.lower()
    checks = {
        "has_overview": len(text.strip()) > 300,
        "has_installation": any(term in lower for term in ("install", "installation", "getting started", "setup")),
        "has_usage": any(term in lower for term in ("usage", "example", "quickstart", "how to")),
        "has_contributing": "contribut" in lower,
        "has_license": "license" in lower,
        "has_tests": any(term in lower for term in ("test", "testing", "ci")),
    }
    score = round(sum(1 for ok in checks.values() if ok) / len(checks) * 100)
    return {
        "score": score,
        "method": "heuristic",
        "checks": checks,
        "notes": "OPENAI_API_KEY is not configured; used deterministic README rubric.",
    }


def llm_readme_score(text: str, api_key: str) -> dict:
    if not api_key or not text.strip():
        return heuristic_readme_score(text)
    prompt = (
        "Score this repository README from 0 to 100 for developer usefulness. "
        "Return compact JSON with score, checks, and notes. Consider installation, usage examples, "
        "configuration, contribution guide, testing, license, and clarity.\n\nREADME:\n"
        + text[:12000]
    )
    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4.1-mini",
                "input": prompt,
                "text": {"format": {"type": "json_object"}},
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        raw = data.get("output_text")
        if not raw:
            raw = data["output"][0]["content"][0]["text"]
        import json

        parsed = json.loads(raw)
        return {
            "score": int(parsed.get("score", 0)),
            "method": "llm",
            "checks": parsed.get("checks", {}),
            "notes": parsed.get("notes", ""),
        }
    except Exception as exc:
        fallback = heuristic_readme_score(text)
        fallback["notes"] = f"LLM scoring failed; fallback used. Reason: {exc}"
        return fallback
