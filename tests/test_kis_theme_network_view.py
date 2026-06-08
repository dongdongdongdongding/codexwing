from ui.kis_theme_network_view import build_kis_theme_network_plot_payload


def test_network_plot_payload_filters_low_confidence_valuechain_and_context_toggle():
    payload = {
        "nodes": [
            {"id": "ticker:005930.KS", "label": "삼성전자", "type": "ticker", "weight": 1},
            {"id": "ticker:095610.KQ", "label": "테스", "type": "ticker", "weight": 1},
            {"id": "ticker:000660.KS", "label": "SK하이닉스", "type": "ticker", "weight": 1},
            {"id": "theme:AI반도체", "label": "AI반도체", "type": "theme", "weight": 2},
        ],
        "edges": [
            {
                "source": "ticker:095610.KQ",
                "target": "ticker:005930.KS",
                "edge_kind": "verified_valuechain",
                "relationship": "equipment_supplier_to_customer",
                "confidence": 0.99,
                "weight": 2,
            },
            {
                "source": "ticker:000660.KS",
                "target": "ticker:005930.KS",
                "edge_kind": "verified_valuechain",
                "relationship": "low_confidence_peer",
                "confidence": 0.94,
                "weight": 1,
            },
            {
                "source": "theme:AI반도체",
                "target": "ticker:005930.KS",
                "edge_kind": "theme_membership",
                "relationship": "theme_contains_ticker",
                "confidence": 0.9,
                "weight": 1,
            },
        ],
    }

    context_payload = build_kis_theme_network_plot_payload(payload, include_context_edges=True, confidence_floor=0.95)
    assert context_payload["summary"]["verified_valuechain_edges"] == 1
    assert context_payload["summary"]["context_edges"] == 1
    assert {edge["relationship"] for edge in context_payload["edges"]} == {
        "equipment_supplier_to_customer",
        "theme_contains_ticker",
    }

    valuechain_only = build_kis_theme_network_plot_payload(payload, include_context_edges=False, confidence_floor=0.95)
    assert valuechain_only["summary"]["verified_valuechain_edges"] == 1
    assert valuechain_only["summary"]["context_edges"] == 0
    assert [edge["relationship"] for edge in valuechain_only["edges"]] == ["equipment_supplier_to_customer"]
