from app.services.scoring import aggregate_scores, score_complexity, score_dependencies, score_duplication


def test_score_duplication_penalizes_high_duplicate_rate():
    assert score_duplication(0) == 100
    assert score_duplication(30) < 40


def test_score_complexity_tracks_worst_functions():
    low = score_complexity([{"complexity": 3}, {"complexity": 4}])
    high = score_complexity([{"complexity": 40}, {"complexity": 25}])
    assert low > high


def test_score_dependencies_penalizes_severe_vulnerabilities():
    score = score_dependencies([{"severity": "CRITICAL"}, {"severity": "HIGH"}], 12)
    assert score == 60


def test_aggregate_scores_returns_breakdown_and_total():
    total, breakdown = aggregate_scores(
        total_lines=1000,
        file_count=30,
        avg_function_length=12,
        top_complexities=[{"complexity": 5}],
        duplicate_rate=5,
        recent_commits=4,
        contributor_count=3,
        vulnerabilities=[],
        dependency_count=10,
        readme_score=80,
    )
    assert 0 <= total <= 100
    assert breakdown.readme == 80
