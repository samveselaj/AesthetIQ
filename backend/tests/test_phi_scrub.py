import pytest

from app.services.phi_scrub import scrub_phi


def test_strips_top_level_keys():
    out = scrub_phi({"name": "Sasha", "ssn": "111-22-3333", "dob": "1990-01-01"})
    assert "ssn" not in out
    assert "dob" not in out
    assert out["name"] == "Sasha"


def test_strips_nested_keys():
    out = scrub_phi(
        {"form": {"first_name": "Jay", "Insurance": "Aetna", "MRN": "x123"}}
    )
    assert "Insurance" not in out["form"]
    assert "MRN" not in out["form"]
    assert out["form"]["first_name"] == "Jay"


def test_handles_lists():
    out = scrub_phi(
        {"items": [{"date_of_birth": "x"}, {"keep": "y"}]}
    )
    assert "date_of_birth" not in out["items"][0]
    assert out["items"][1]["keep"] == "y"


def test_passthrough_for_non_dict():
    assert scrub_phi(None) is None  # type: ignore[arg-type]
    assert scrub_phi("string") == "string"  # type: ignore[arg-type]


def test_case_insensitive_match():
    out = scrub_phi({"DOB": "1990", "Medical_Record_Number": "x"})
    assert "DOB" not in out
    assert "Medical_Record_Number" not in out
