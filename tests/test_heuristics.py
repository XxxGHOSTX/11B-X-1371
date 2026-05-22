from x1371.heuristics import registry


def test_heuristic_registry_returns_multiple_leads() -> None:
    leads = registry.run("artifact", "AAAA BBBB CCCC 010101")
    analyzers = {lead.analyzer for lead in leads}
    assert "entropy" in analyzers
    assert "encoding_classifier" in analyzers
    assert any(lead.details for lead in leads)


def test_pgp_artifact_heuristic_detects_public_key_block() -> None:
    pgp_text = "-----BEGIN PGP PUBLIC KEY BLOCK-----\nmQINBF...\n-----END PGP PUBLIC KEY BLOCK-----"
    leads = registry.run("msg003", pgp_text)
    pgp_leads = [lead for lead in leads if lead.analyzer == "pgp_artifact"]
    assert pgp_leads, "pgp_artifact analyzer should be registered"
    lead = pgp_leads[0]
    assert lead.details["count"] == 1
    assert "-----BEGIN PGP PUBLIC KEY BLOCK-----" in lead.details["pgp_blocks"]
    assert lead.summary == "PGP block(s) detected"


def test_pgp_artifact_heuristic_no_false_positive() -> None:
    leads = registry.run("poem", "Roses are red, violets are blue.")
    pgp_leads = [lead for lead in leads if lead.analyzer == "pgp_artifact"]
    assert pgp_leads
    assert pgp_leads[0].details["count"] == 0
    assert pgp_leads[0].summary == "No PGP blocks detected"
