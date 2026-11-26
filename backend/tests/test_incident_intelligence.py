import unittest

from app.services.incident_intelligence import build_incident_intelligence


class IncidentIntelligenceTests(unittest.TestCase):
    def test_empty_timeline_reports_insufficient_evidence(self):
        result = build_incident_intelligence({"timeline": []})

        self.assertEqual(result["score"], 0)
        self.assertEqual(result["confidence"], "low")
        self.assertEqual(result["counts"], {
            "changes": 0,
            "anomalies": 0,
            "fixes": 0,
            "resolved": False,
        })
        self.assertIn("Insufficient", result["summary"])

    def test_change_and_anomaly_are_correlated_without_claiming_causation(self):
        result = build_incident_intelligence({
            "timeline": [
                {"type": "change"},
                {"type": "anomaly"},
            ]
        })

        self.assertEqual(result["score"], 85)
        self.assertEqual(result["confidence"], "high")
        self.assertIn("does not", result["summary"])
        self.assertEqual(result["counts"]["changes"], 1)
        self.assertEqual(result["counts"]["anomalies"], 1)

    def test_fix_and_resolution_contribute_to_score(self):
        result = build_incident_intelligence({
            "timeline": [
                {"type": "change"},
                {"type": "fix"},
                {"type": "resolved"},
            ]
        })

        self.assertEqual(result["score"], 45)
        self.assertEqual(result["confidence"], "medium")
        self.assertEqual(result["counts"]["fixes"], 1)
        self.assertTrue(result["counts"]["resolved"])

    def test_score_is_capped_at_one_hundred(self):
        result = build_incident_intelligence({
            "timeline": (
                [{"type": "change"}] * 5
                + [{"type": "anomaly"}] * 5
                + [{"type": "fix"}] * 5
                + [{"type": "resolved"}]
            )
        })

        self.assertEqual(result["score"], 100)
        self.assertEqual(result["confidence"], "high")


if __name__ == "__main__":
    unittest.main()
