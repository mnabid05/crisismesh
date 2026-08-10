from __future__ import annotations

import argparse
import gzip
import json
import re
import time
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.training_data import (
    DatasetSource,
    TrainingExample,
    content_digest,
    parse_noaa_csv,
    usgs_examples,
    write_jsonl,
)

NOAA_INDEX = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
USGS_QUERY = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USER_AGENT = "CrisisMesh/0.3 training-pipeline github.com/mnabid05/crisismesh"


def fetch(url: str, *, attempts: int = 3) -> bytes:
    error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = Request(
                url,
                headers={
                    "Accept": "application/json,text/csv,*/*",
                    "User-Agent": USER_AGENT,
                },
            )
            with urlopen(request, timeout=45.0) as response:  # noqa: S310
                return response.read()
        except (OSError, TimeoutError) as exc:
            error = exc
            if attempt + 1 < attempts:
                time.sleep(0.5 * (2**attempt))
    raise OSError(f"failed to download {url}: {error}")


def resolve_noaa_files(index: str, years: list[int]) -> list[str]:
    resolved: list[str] = []
    for year in years:
        names = re.findall(
            rf'"(StormEvents_details-ftp_v1\.0_d{year}_c\d{{8}}\.csv\.gz)"',
            index,
        )
        if not names:
            raise ValueError(f"NOAA index does not contain a details file for {year}")
        resolved.append(f"{NOAA_INDEX}{max(names)}")
    return resolved


def collect_noaa(years: list[int]) -> tuple[list[TrainingExample], list[DatasetSource]]:
    index = fetch(NOAA_INDEX).decode("utf-8", errors="replace")
    examples: list[TrainingExample] = []
    sources: list[DatasetSource] = []
    for url in resolve_noaa_files(index, years):
        archive = fetch(url)
        csv_content = gzip.decompress(archive).decode("utf-8-sig", errors="replace")
        records = parse_noaa_csv(csv_content, source_url=url)
        examples.extend(records)
        sources.append(
            DatasetSource(
                name="NOAA Storm Events",
                url=url,
                sha256=content_digest(archive),
                records=len(records),
                collected_at=datetime.now(UTC).isoformat(),
            )
        )
    return examples, sources


def collect_noaa_archives(
    paths: list[Path],
) -> tuple[list[TrainingExample], list[DatasetSource]]:
    examples: list[TrainingExample] = []
    sources: list[DatasetSource] = []
    for path in paths:
        archive = path.read_bytes()
        url = f"{NOAA_INDEX}{path.name}"
        records = parse_noaa_csv(
            gzip.decompress(archive).decode("utf-8-sig", errors="replace"),
            source_url=url,
        )
        examples.extend(records)
        sources.append(
            DatasetSource(
                name="NOAA Storm Events",
                url=url,
                sha256=content_digest(archive),
                records=len(records),
                collected_at=datetime.now(UTC).isoformat(),
            )
        )
    return examples, sources


def collect_usgs(years: list[int]) -> tuple[list[TrainingExample], list[DatasetSource]]:
    examples: list[TrainingExample] = []
    sources: list[DatasetSource] = []
    for year in years:
        query = urlencode(
            {
                "format": "geojson",
                "starttime": f"{year}-01-01",
                "endtime": f"{year + 1}-01-01",
                "minmagnitude": 4.0,
                "orderby": "time-asc",
                "limit": 20000,
            }
        )
        url = f"{USGS_QUERY}?{query}"
        content = fetch(url)
        payload = json.loads(content)
        if not isinstance(payload, dict):
            raise ValueError("USGS returned a non-object response")
        records = usgs_examples(payload)
        examples.extend(records)
        sources.append(
            DatasetSource(
                name="USGS Earthquake Catalog",
                url=url,
                sha256=content_digest(content),
                records=len(records),
                collected_at=datetime.now(UTC).isoformat(),
            )
        )
    return examples, sources


def collect_usgs_files(
    paths: list[Path],
) -> tuple[list[TrainingExample], list[DatasetSource]]:
    examples: list[TrainingExample] = []
    sources: list[DatasetSource] = []
    for path in paths:
        content = path.read_bytes()
        payload = json.loads(content)
        if not isinstance(payload, dict):
            raise ValueError(f"{path} contains a non-object USGS response")
        records = usgs_examples(payload)
        examples.extend(records)
        year_match = re.search(r"(20\d{2})", path.name)
        year = int(year_match.group(1)) if year_match else 2025
        query = urlencode(
            {
                "format": "geojson",
                "starttime": f"{year}-01-01",
                "endtime": f"{year + 1}-01-01",
                "minmagnitude": 4.0,
                "orderby": "time-asc",
                "limit": 20000,
            }
        )
        sources.append(
            DatasetSource(
                name="USGS Earthquake Catalog",
                url=f"{USGS_QUERY}?{query}",
                sha256=content_digest(content),
                records=len(records),
                collected_at=datetime.now(UTC).isoformat(),
            )
        )
    return examples, sources


def balanced_examples(
    examples: list[TrainingExample],
    *,
    maximum_per_source_hazard: int,
) -> list[TrainingExample]:
    groups: dict[tuple[str, str], list[TrainingExample]] = defaultdict(list)
    for example in sorted(examples, key=lambda item: (item.occurred_at, item.event_id)):
        groups[(example.source, example.hazard)].append(example)

    selected: list[TrainingExample] = []
    for group in groups.values():
        if len(group) <= maximum_per_source_hazard:
            selected.extend(group)
            continue
        step = len(group) / maximum_per_source_hazard
        selected.extend(
            group[min(len(group) - 1, int(index * step))]
            for index in range(maximum_per_source_hazard)
        )
    return sorted(selected, key=lambda item: (item.occurred_at, item.source, item.event_id))


def write_manifest(
    path: Path,
    *,
    examples: list[TrainingExample],
    sources: list[DatasetSource],
    dataset_sha256: str,
) -> None:
    counts: dict[str, int] = defaultdict(int)
    outcomes = [0, 0, 0]
    for example in examples:
        counts[f"{example.source}:{example.hazard}"] += 1
        for index, target in enumerate(example.targets):
            outcomes[index] += int(target >= 0.5)
    manifest: dict[str, Any] = {
        "schemaVersion": "training-manifest-v1",
        "generatedAt": datetime.now(UTC).isoformat(),
        "datasetSha256": dataset_sha256,
        "records": len(examples),
        "positiveOutcomes": {"6h": outcomes[0], "24h": outcomes[1], "72h": outcomes[2]},
        "groups": dict(sorted(counts.items())),
        "sources": [asdict(source) for source in sources],
        "target": "operational escalation proxy for an already observed incident",
        "limitations": [
            "NOAA reporting and collection practices vary across time and geography.",
            "USGS impact-related fields are incomplete for many events.",
            "Outcome timing is approximated from event duration and catalog metadata.",
        ],
    }
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a versioned CrisisMesh training dataset")
    parser.add_argument("--noaa-years", nargs="+", type=int, default=[2023, 2024, 2025])
    parser.add_argument("--usgs-years", nargs="+", type=int, default=[2023, 2024, 2025])
    parser.add_argument("--noaa-archive", nargs="+", type=Path)
    parser.add_argument("--usgs-json", nargs="+", type=Path)
    parser.add_argument("--maximum-per-source-hazard", type=int, default=6000)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parents[1] / "data" / "generated",
    )
    args = parser.parse_args()

    noaa, noaa_sources = (
        collect_noaa_archives(args.noaa_archive)
        if args.noaa_archive
        else collect_noaa(args.noaa_years)
    )
    usgs, usgs_sources = (
        collect_usgs_files(args.usgs_json) if args.usgs_json else collect_usgs(args.usgs_years)
    )
    examples = balanced_examples(
        [*noaa, *usgs],
        maximum_per_source_hazard=args.maximum_per_source_hazard,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = args.output_dir / "training-v2.jsonl"
    digest = write_jsonl(dataset_path, examples)
    write_manifest(
        args.output_dir / "manifest-v2.json",
        examples=examples,
        sources=[*noaa_sources, *usgs_sources],
        dataset_sha256=digest,
    )
    print(f"wrote {len(examples)} examples to {dataset_path} ({digest[:12]})")


if __name__ == "__main__":
    main()
