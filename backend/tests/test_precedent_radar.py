from __future__ import annotations

import unittest
from types import SimpleNamespace

from app.services.precedent_radar import (
    incident_query_text,
    public_documents,
    rank_documents,
    tokenize,
)


class PrecedentRadarTests(unittest.TestCase):
    def test_synonyms_and_stopwords_are_explicitly_normalized(self):
        tokens = tokenize("PostgreSQL connections and k8s deployment config")
        self.assertIn("database", tokens)
        self.assertIn("connection", tokens)
        self.assertIn("kubernetes", tokens)
        self.assertIn("deployment", tokens)
        self.assertIn("configuration", tokens)
        self.assertNotIn("and", tokens)

    def test_tfidf_ranking_is_deterministic_and_reports_matching_signals(self):
        documents = [
            {"id": "route", "_search_text": "BGP routing configuration route withdrawal"},
            {"id": "database", "_search_text": "postgres database connection pool"},
        ]
        first = rank_documents("BGP route configuration deployment", documents, 5)
        second = rank_documents("BGP route configuration deployment", documents, 5)
        self.assertEqual(first, second)
        self.assertEqual(first[0]["id"], "route")
        self.assertGreater(first[0]["relevance_score"], 0)
        self.assertIn("routing", first[0]["matching_signals"])
        self.assertLessEqual(first[0]["relevance_score"], 100)

    def test_no_overlap_has_no_invented_zero_score_precedents(self):
        self.assertEqual(rank_documents("token expiration", [{"id": "db", "_search_text": "database pool"}], 5), [])

    def test_incident_query_omits_published_root_cause(self):
        incident = SimpleNamespace(
            title="BGP routing outage",
            description="Routes withdrawn after configuration change.",
            service_name="network",
            root_cause_summary="SECRET PUBLISHED ANSWER",
            logs=[], deployments=[],
        )
        query = incident_query_text(incident)
        self.assertIn("Routes withdrawn", query)
        self.assertNotIn("SECRET PUBLISHED ANSWER", query)

    def test_public_documents_exclude_the_current_library_incident(self):
        records = [
            {"id": "current", "sources": [], "title": "Current", "affected_services": []},
            {"id": "past", "sources": [], "title": "Past", "affected_services": []},
        ]
        docs = public_documents(records, exclude_library_id="current")
        self.assertEqual([item["id"] for item in docs], ["past"])


if __name__ == "__main__":
    unittest.main()
