from types import SimpleNamespace

import pytest

from scenario_uncertainty import Q, provenance


def test_custom_properties_use_su_namespace():
    props = provenance.custom_properties({"failed": Q(3, "1", "count", "frame", "measured")})
    assert props == {"activity:su:failed": {"value": 3, "unit": "1", "stat": "count", "level": "frame",
                                            "basis": "measured"}}


def test_grouped_summary():
    props = provenance.custom_properties({"stabilization": {"filled": Q(2, "1", "count", "frame", "measured")}})
    assert props["activity:su:stabilization"]["filled"]["value"] == 2


def test_warning_lines():
    line = provenance.warning_line(provenance.WarningCode.CALIB_SCALED, "scaled 0.4762")
    assert line == "[su:calib_scaled] scaled 0.4762"
    assert provenance.join_warnings([line, "", "[su:x] y"]) == "[su:calib_scaled] scaled 0.4762\n[su:x] y"


def test_declare_namespace_on_loaded_chain():
    prefix = {"prov": "http://www.w3.org/ns/prov#"}
    chain = SimpleNamespace(namespaces=prefix, data={"prefix": prefix})
    provenance.declare_namespace(chain)
    assert chain.data["prefix"]["su"] == provenance.NAMESPACE_URI


def test_q_dicts_are_accepted_and_validated():
    summary = {"failed": {"value": 0, "unit": "1", "stat": "count", "level": "frame", "basis": "measured"}}
    assert provenance.custom_properties({"stabilization": summary})["activity:su:stabilization"]["failed"]["value"] == 0
    with pytest.raises(ValueError):
        provenance.custom_properties({"bad": {"value": 1, "unit": "deg", "stat": "rms", "level": "frame",
                                              "basis": "measured"}})
