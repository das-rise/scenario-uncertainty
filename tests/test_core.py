import pytest

from scenario_uncertainty import Basis, Level, Q, Stat, Unit, parse_schema_id, schema_id


def test_q_round_trip_and_string_forms():
    q = Q(0.57, "px", "rms", "image", "measured", n=40)
    assert q.unit is Unit.PX and q.level is Level.IMAGE
    assert Q.from_dict(q.to_dict()) == q
    assert q.to_dict() == {"value": 0.57, "unit": "px", "stat": "rms", "level": "image", "basis": "measured", "n": 40}


def test_q_rejects_unknown_descriptors():
    with pytest.raises(ValueError):
        Q(1.0, "deg", Stat.SIGMA, Level.OBJECT, Basis.ASSUMED)  # angles are radians only


def test_schema_ids():
    assert schema_id("video", 1) == "scenario-uncertainty/video/1"
    assert parse_schema_id("scenario-uncertainty/video/1") == ("video", 1)
    assert parse_schema_id("savant-quality/video/1") is None
