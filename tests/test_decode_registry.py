from x1371.decode.registry import default_registry


def test_decoder_registry_exposes_expected_transforms() -> None:
    names = [registered.name for registered in default_registry().transforms()]
    assert "reverse" in names
    assert "base" in names
    assert "transposition" in names
    assert "unicode_stego" in names


def test_unicode_stego_transform_decodes_binary_payload() -> None:
    from x1371.decode.transforms import unicode_stego_transform

    # Encode "Hi" (0x48=01001000, 0x69=01101001) with ZWNJ=0, ZWJ=1
    bits = "0100100001101001"
    carrier = "".join("\u200d" if b == "1" else "\u200c" for b in bits)
    results = list(unicode_stego_transform(carrier))
    assert results, "Should yield at least one decode attempt"
    outputs = [r.output for r in results]
    assert any("Hi" in o for o in outputs)


def test_unicode_stego_transform_no_payload() -> None:
    from x1371.decode.transforms import unicode_stego_transform

    results = list(unicode_stego_transform("plain visible text"))
    assert results == []
