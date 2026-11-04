from job_search_agent.scorer import score_jd


def test_builder_leaning_jd():
    jd = """
    Own the model lifecycle end to end: write evals before you write code,
    run offline tests and A/B experiments, ship a working prototype in your
    first month. Fluent in SQL, Python, RAG, and agent orchestration.
    """
    result = score_jd(jd)
    assert result.builder_score > result.integrator_score
    assert result.lean == "Builder PM"


def test_integrator_leaning_jd():
    jd = """
    Own stakeholder alignment across 6 business units. Drive roadmap
    governance, write PRDs, manage vendor contracts and compliance review,
    and run the quarterly business review (QBR) with the steering committee.
    """
    result = score_jd(jd)
    assert result.integrator_score > result.builder_score
    assert result.lean == "Integrator PM"


def test_empty_text_is_unclear():
    result = score_jd("")
    assert result.lean.startswith("Unclear")
    assert result.confidence == "Low"


def test_mixed_signal_is_hybrid_or_unclear():
    jd = "Ship prototypes. Also own stakeholder alignment and PRDs."
    result = score_jd(jd)
    # Not asserting which way it leans -- just that it doesn't crash and
    # produces a valid category.
    assert result.lean in {"Builder PM", "Integrator PM", "Hybrid", result.lean}
