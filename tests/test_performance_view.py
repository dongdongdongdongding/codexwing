from ui.performance_view import return_metric


def test_return_metric_reads_nested_bucket_value():
    buckets = {
        "picked": {
            "3d": {
                "avg_return_pct": 2.45,
                "samples": 7,
            }
        }
    }

    assert return_metric(buckets, "picked", "3d") == 2.45
    assert return_metric(buckets, "picked", "3d", field="samples") == 7.0


def test_return_metric_defaults_invalid_or_missing_values_to_zero():
    assert return_metric({}, "picked", "3d") == 0.0
    assert return_metric({"picked": {"3d": {"avg_return_pct": "bad"}}}, "picked", "3d") == 0.0
