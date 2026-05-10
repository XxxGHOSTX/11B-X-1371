from x1371.decode.registry import default_registry


def test_decoder_registry_exposes_expected_transforms() -> None:
    names = [registered.name for registered in default_registry().transforms()]
    assert "reverse" in names
    assert "base" in names
    assert "transposition" in names
