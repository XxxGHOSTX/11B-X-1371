from x1371.heuristics import registry


def test_heuristic_registry_returns_multiple_leads() -> None:
    leads = registry.run("artifact", "AAAA BBBB CCCC 010101")
    analyzers = {lead.analyzer for lead in leads}
    assert "entropy" in analyzers
    assert "encoding_classifier" in analyzers
    assert any(lead.details for lead in leads)
