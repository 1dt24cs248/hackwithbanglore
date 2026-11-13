"""Catalog validation and blind-evidence contract tests."""

from __future__ import annotations

import unittest

from app.schemas.investigation import IncidentSubmission
from app.services.incident_library import (
    OFFICIAL_SOURCE_DOMAINS,
    _load_records,
    investigation_submission,
    library_categories,
)


class IncidentLibraryTests(unittest.TestCase):
    def test_all_catalog_records_have_official_sources_and_primary_category_tags(self):
        records = _load_records()
        self.assertGreaterEqual(len(records), 30)
        self.assertEqual(len({record.id for record in records}), len(records))
        self.assertEqual(len(library_categories()), 35)
        for record in records:
            self.assertIn(record.category, record.tags)
            allowed_domains = OFFICIAL_SOURCE_DOMAINS[record.company]
            for source in record.sources:
                self.assertEqual(source.url.scheme, "https")
                host = source.url.host.lower()
                self.assertTrue(any(host == domain or host.endswith("." + domain) for domain in allowed_domains))

    def test_blind_investigation_payload_matches_existing_schema_and_hides_exact_cause(self):
        for record in _load_records():
            payload = investigation_submission(record)
            validated = IncidentSubmission.model_validate(payload)
            self.assertEqual(validated.source, f"real_library:{record.id}")
            evidence = " ".join((validated.title, validated.description, *validated.error_messages)).casefold()
            if record.technical_root_cause:
                self.assertNotIn(record.technical_root_cause.casefold(), evidence, record.id)
            self.assertIsNone(validated.deployment)


if __name__ == "__main__":
    unittest.main()
