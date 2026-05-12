import re


GITHUB_RE = re.compile(
    r"^(?:https://github\.com/|git@github\.com:)(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


def normalize_github_url(url: str) -> tuple[str, str]:
    clean = url.strip()
    match = GITHUB_RE.match(clean)
    if not match:
        raise ValueError("Only GitHub repository URLs are supported.")
    owner = match.group("owner")
    repo = match.group("repo")
    normalized = f"{owner}/{repo}"
    clone_url = f"https://github.com/{normalized}.git"
    return normalized, clone_url
