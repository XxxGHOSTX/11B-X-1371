from x1371.unicode_analysis import analyze_unicode


def test_unicode_anomaly_detection_finds_invisibles_and_scripts() -> None:
    result = analyze_unicode("A\u200bБ")
    assert result["invisible_characters"]
    assert "LATIN" in result["scripts"]
    assert "CYRILLIC" in result["scripts"]
    assert result["homoglyph_suspicion"]
