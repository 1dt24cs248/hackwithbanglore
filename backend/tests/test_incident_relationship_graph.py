from fastapi.testclient import TestClient

from app.main import app
from app.services.incident_library import _load_records, relationship_graph


def test_graph_edges_are_deterministic_and_backed_by_record_fields():
    first = relationship_graph()
    assert first == relationship_graph()
    assert first["patterns_shown"] <= 8

    records = {record.id: record for record in _load_records()}
    nodes = {node["id"]: node for node in first["nodes"]}
    incident_nodes = [node for node in first["nodes"] if node["node_type"] == "incident"]
    assert all(any(edge["source"] == node["id"] for edge in first["edges"]) for node in incident_nodes)

    for edge in first["edges"]:
        incident = records[edge["source"]]
        pattern = nodes[edge["target"]]
        assert pattern["node_type"] == "pattern"
        assert edge["evidence_basis"] != "technical_root_cause"
        if edge["relation"] == "shared_infrastructure":
            assert any(value.strip().casefold() == pattern["label"].strip().casefold() for value in incident.infrastructure)
            assert edge["evidence"] == f"Both reports list '{pattern['label']}' as affected infrastructure."
        else:
            assert edge["relation"] == "same_category"
            assert incident.category.strip().casefold() == pattern["label"].strip().casefold()
            assert edge["evidence"] == f"Both incidents are filed under the library category '{pattern['label']}'."


def test_relationship_graph_endpoint_returns_envelope():
    response = TestClient(app).get("/api/library/relationship-graph?max_patterns=8")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "data" in body
    assert body["data"]["patterns_shown"] <= 8
    assert body["data"]["total_library_incidents"] == 35
