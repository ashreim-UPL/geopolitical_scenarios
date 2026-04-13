from fastapi.testclient import TestClient

from geostate_api.main import app


def test_issue_catalog_available() -> None:
    client = TestClient(app)
    response = client.get("/v1/issues")
    assert response.status_code == 200
    payload = response.json()
    assert "issues" in payload
    assert len(payload["issues"]) > 0


def test_analyze_demo_mode() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/analyze",
        json={"selected_issues": ["red-sea-shipping", "iran-israel-dynamics"], "use_live": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "demo"
    assert payload["current_state"]["label"]
    assert len(payload["scenarios"]) > 0
    assert "scenario_methods" in payload
    assert "next_scenario_forecast" in payload
    assert payload["next_scenario_forecast"]["horizon_steps"] == 4
    assert len(payload["next_scenario_forecast"]["actor_moves"]) >= 5
    assert len(payload["signals"]) > 0
    assert "overall_criticality" in payload
    assert "conflict_escalation" in payload
    assert payload["conflict_escalation"]["band"] in {"Low", "Guarded", "Elevated", "High", "Critical"}
    assert "expert_review" in payload
    assert len(payload["expert_review"]["panel"]) >= 5
    assert payload["overall_criticality"]["band"] in {"Low", "Guarded", "Elevated", "High", "Critical"}
    assert "impacts" in payload
    assert payload["impacts"]["prediction"]["most_likely_scenario"]
    assert len(payload["impacts"]["regions_world"]) > 0
    assert len(payload["impacts"]["sectors"]) > 0
    assert "countries_by_region" in payload["impacts"]
    sector_labels = {row["label"] for row in payload["impacts"]["sectors"]}
    assert "Hospitality" in sector_labels
    assert "Tourism" in sector_labels
    assert "F&B, Restaurants, Nightlife" in sector_labels
    assert "Luxury Shopping" in sector_labels
    assert "Real Estate" in sector_labels
    assert len(payload["impacts"]["three_sector_model"]) == 3
    assert "maslow_hierarchy" in payload["impacts"]


def test_force_distribution_constraints() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/analyze",
        json={"selected_issues": ["us-china-technology"], "use_live": False},
    )
    assert response.status_code == 200
    payload = response.json()
    forces = payload["forces"]
    force_map = {row["name"]: row["score"] for row in forces}

    total = sum(force_map.values())
    assert abs(total - 1.0) < 1e-6
    assert force_map["ideological"] > 0
    assert force_map["military"] < 1.0


def test_criticality_bounds_and_formula() -> None:
    client = TestClient(app)
    response = client.post("/v1/analyze", json={"selected_issues": ["red-sea-shipping"], "use_live": False})
    assert response.status_code == 200
    payload = response.json()
    criticality = payload["overall_criticality"]
    assert 0 <= criticality["score"] <= 1
    assert criticality["formula"]["regional_war_escalation"] == 0.4


def test_lens_reweights_formula_and_impacts() -> None:
    client = TestClient(app)

    region_resp = client.post(
        "/v1/analyze",
        json={
            "selected_issues": ["red-sea-shipping", "gulf-energy-security"],
            "use_live": False,
            "lens": "region",
            "focus": "Gulf",
        },
    )
    assert region_resp.status_code == 200
    region_payload = region_resp.json()
    assert region_payload["lens"]["type"] == "region"
    assert region_payload["overall_criticality"]["formula"]["maritime_infrastructure_shock"] == 0.35

    country_resp = client.post(
        "/v1/analyze",
        json={
            "selected_issues": ["us-china-technology"],
            "use_live": False,
            "lens": "country",
            "focus": "India",
        },
    )
    assert country_resp.status_code == 200
    country_payload = country_resp.json()
    assert country_payload["lens"]["type"] == "country"
    assert country_payload["overall_criticality"]["formula"]["military_force"] == 0.3
    country_labels = [row["label"] for row in country_payload["impacts"]["countries"][:5]]
    assert "India" in country_labels


def test_maslow_hierarchy_is_max_biased() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/analyze",
        json={"selected_issues": ["russia-ukraine-war", "iran-israel-dynamics"], "use_live": False},
    )
    assert response.status_code == 200
    payload = response.json()
    hierarchy = payload["impacts"]["maslow_hierarchy"]
    assert hierarchy["dominant_score"] >= hierarchy["weighted_score"]
    assert hierarchy["hierarchy_score"] >= hierarchy["weighted_score"]


def test_consistency_note_for_high_tension_stable_plateau() -> None:
    client = TestClient(app)
    response = client.post(
        "/v1/analyze",
        json={"selected_issues": ["iran-israel-dynamics", "russia-ukraine-war"], "use_live": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "consistency_notes" in payload
