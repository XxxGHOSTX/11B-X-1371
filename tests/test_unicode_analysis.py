from x1371.unicode_analysis import analyze_unicode, zero_width_stego_extract


def test_unicode_anomaly_detection_finds_invisibles_and_scripts() -> None:
    result = analyze_unicode("A\u200bБ")
    assert result["invisible_characters"]
    assert "LATIN" in result["scripts"]
    assert "CYRILLIC" in result["scripts"]
    assert result["homoglyph_suspicion"]


def test_analyze_unicode_includes_zero_width_stego_key() -> None:
    result = analyze_unicode("hello")
    assert "zero_width_stego" in result
    assert result["zero_width_stego"]["found"] is False


def test_zero_width_stego_extract_detects_payload() -> None:
    # Encode "Hi" (0x48 0x69) using ZWNJ=0, ZWJ=1: 01001000 01101001
    bits = "0100100001101001"
    stego_text = "".join("\u200d" if b == "1" else "\u200c" for b in bits)
    carrier = f"visible{stego_text}text"
    result = zero_width_stego_extract(carrier)
    assert result["found"] is True
    assert result["char_count"] == 16
    decoded_values = [attempt["result"] for attempt in result["attempts"]]
    assert any("Hi" in v for v in decoded_values)


def test_zero_width_stego_extract_no_payload() -> None:
    result = zero_width_stego_extract("plain text with no invisible chars")
    assert result["found"] is False
    assert result["char_count"] == 0
    assert result["attempts"] == []
