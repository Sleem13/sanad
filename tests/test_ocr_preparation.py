import pytest
from PIL import Image

from sanad.engines.image_preparation import prepare, original_polygon
from sanad.engines.image_preparation import merge_readings


def line(text, score, y=0):
    return {"text": text, "score": score, "polygon": [[0,y],[100,y],[100,y+10],[0,y+10]]}


def test_disagreement_retains_both_readings_and_requires_review():
    result = merge_readings([line("قراءة ناقصة", .5)], [line("قراءة أفضل ٣٥", .9)])[0]
    assert result["text"] == "قراءة أفضل ٣٥"
    assert result["requires_review"]
    assert set(result["flags"]) == {"ocr_disagreement", "numbers_need_review"}
    assert [x["text"] for x in result["alternatives"]] == ["قراءة ناقصة", "قراءة أفضل ٣٥"]


def test_other_rows_and_short_fragments_cannot_replace_a_line():
    original = line("هذه جملة كاملة وليست كلمة واحدة", .5)
    assert merge_readings([original], [line("كلمة", .99)])[0]["text"] == original["text"]
    assert merge_readings([original], [line("نص مختلف", .99, 20)])[0]["alternatives"] == []


def test_arabic_letter_disagreement_is_not_normalized_away():
    result = merge_readings([line("الأعلى", .95)], [line("الأعلي", .96)])[0]
    assert result["text"] == "الأعلى" and result["requires_review"]


def test_small_photo_is_enlarged_without_changing_source_or_coordinate_frame():
    source = Image.new("RGB", (390, 512), "white")
    working, metadata = prepare(source)
    assert source.size == (390, 512) and working.height == 1200
    # Separate actual X/Y scales account for integer resize rounding.
    points = [[working.width * .1, working.height * .2], [working.width, working.height]]
    restored = original_polygon(points, metadata)
    assert restored[0] == pytest.approx([39, 102.4])
    assert restored[1] == pytest.approx([390, 512])


def test_large_page_and_baseline_do_not_change_resolution():
    large = Image.new("RGB", (1800, 2400))
    working, metadata = prepare(large)
    assert working.size == large.size and metadata["scale_x"] == 1
    small = Image.new("RGB", (200, 300))
    assert prepare(small, "baseline")[0].size == small.size
    with pytest.raises(ValueError):
        prepare(small, "invented")
