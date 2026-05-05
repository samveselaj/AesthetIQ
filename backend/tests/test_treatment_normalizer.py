from app.services.treatment_normalizer import (
    detect_treatment_keys,
    normalize_treatment,
    slugify_treatment_key,
)


def test_normalize_exact_match():
    assert normalize_treatment("How much is Botox?") == "botox"
    assert normalize_treatment("interested in hydrafacial") == "hydrafacial"
    assert normalize_treatment("Want to learn about laser hair removal") == "laser_hair_removal"


def test_normalize_prefers_longest_match():
    # "laser hair removal" is longer than "hair" — should win
    assert normalize_treatment("book laser hair removal") == "laser_hair_removal"


def test_normalize_filler_aliases():
    assert normalize_treatment("lip filler please") == "filler"
    assert normalize_treatment("Juvederm info") == "filler"


def test_normalize_tox_alias():
    assert normalize_treatment("dysport prices") == "botox"


def test_normalize_returns_none_when_empty():
    assert normalize_treatment("") is None
    assert normalize_treatment(None) is None


def test_normalize_returns_none_when_unrelated():
    assert normalize_treatment("just checking your hours") is None


def test_detect_multiple_treatments():
    keys = set(detect_treatment_keys("botox and filler combo?"))
    assert "botox" in keys and "filler" in keys


def test_slugify_for_custom():
    assert slugify_treatment_key("Skin Booster") == "skin_booster"
    assert slugify_treatment_key("RF-Microneedling") == "rf_microneedling"
