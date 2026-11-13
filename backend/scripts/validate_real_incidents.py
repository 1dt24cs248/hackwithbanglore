"""Validate the versioned official-source incident catalog; never writes to a database."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.schemas.library import IncidentLibraryRecord  # noqa: E402
from app.services.incident_library import OFFICIAL_SOURCE_DOMAINS, library_categories  # noqa: E402

CATALOG = BACKEND_ROOT / "data" / "real_incidents.json"
def validate(check_sources: bool = False) -> tuple[list[IncidentLibraryRecord], list[str]]:
    records = [IncidentLibraryRecord.model_validate(item) for item in json.loads(CATALOG.read_text(encoding="utf-8"))]
    errors: list[str] = []
    try:
        library_categories()
    except Exception as error:
        errors.append(f"Taxonomy validation failed: {type(error).__name__}")
    root_copy = ROOT / "real_incidents.json"
    if not root_copy.exists() or root_copy.read_bytes() != CATALOG.read_bytes():
        errors.append("Root real_incidents.json deliverable is missing or differs from backend/data catalog.")
    ids: set[str] = set()
    identities: set[tuple[str, str, str]] = set()
    for record in records:
        identity = (record.company.casefold(), str(record.incident_date), record.title.casefold())
        if record.id in ids:
            errors.append(f"{record.id}: duplicate ID")
        if identity in identities:
            errors.append(f"{record.id}: duplicate incident identity")
        ids.add(record.id)
        identities.add(identity)
        if record.verification_status == "verified":
            allowed = OFFICIAL_SOURCE_DOMAINS.get(record.company, ())
            for source in record.sources:
                host = (urlparse(str(source.url)).hostname or "").lower()
                if urlparse(str(source.url)).scheme != "https" or not any(host == domain or host.endswith("." + domain) for domain in allowed):
                    errors.append(f"{record.id}: source is not on the official-domain allowlist: {source.url}")
                if check_sources:
                    try:
                        request = Request(str(source.url), headers={"User-Agent": "IncidentIQ-source-verifier/1.0"}, method="GET")
                        with urlopen(request, timeout=12) as response:
                            if response.status < 200 or response.status >= 400:
                                errors.append(f"{record.id}: source returned HTTP {response.status}: {source.url}")
                    except (HTTPError, URLError, TimeoutError) as error:
                        errors.append(f"{record.id}: source fetch failed ({type(error).__name__}): {source.url}")
    return records, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-sources", action="store_true", help="Fetch every primary source URL and report reachability")
    args = parser.parse_args()
    try:
        records, errors = validate(args.check_sources)
    except Exception as error:
        print(f"Catalog validation failed: {type(error).__name__}: {error}")
        return 1
    verified = [record for record in records if record.verification_status == "verified"]
    print(json.dumps({
        "catalog": str(CATALOG.relative_to(ROOT)), "records": len(records),
        "verified": len(verified), "verification_status_counts": dict(Counter(r.verification_status for r in records)),
        "companies": len({r.company for r in verified}),
        "categories": dict(Counter(r.category for r in verified)),
        "source_url_check_performed": args.check_sources,
        "errors": errors,
    }, indent=2, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
