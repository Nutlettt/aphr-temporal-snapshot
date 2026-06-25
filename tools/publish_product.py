#!/usr/bin/env python3
"""Publish an APHR web bundle into this static website."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Dict, List

from build_site import build_site

ROOT = Path(__file__).resolve().parents[1]


def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, help="Directory with content.html and manifest.json.")
    parser.add_argument("--event-slug", required=True, help="Website event slug.")
    parser.add_argument("--product-slug", required=True, help="Website product slug.")
    parser.add_argument("--event-title", default=None, help="Display title for the event.")
    parser.add_argument("--event-date", default=None, help="Display/sort date for the event.")
    parser.add_argument("--event-type", default="Earthquake", help="Event type label.")
    parser.add_argument("--event-meta", default=None, help="Short metadata line for homepage card.")
    parser.add_argument("--event-description", default=None, help="Event page and homepage description.")
    parser.add_argument("--event-tag", default=None, help="Homepage tag for this event.")
    parser.add_argument("--product-title", default=None, help="Display title for this product.")
    parser.add_argument("--product-summary", default=None, help="Short product-card summary.")
    parser.add_argument("--set-latest", action="store_true", help="Make this the latest product.")
    parser.add_argument("--build", action="store_true", help="Rebuild static pages after publishing.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing product directory.")
    return parser.parse_args(argv)


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _copy_bundle(bundle_dir: Path, destination: Path, force: bool) -> None:
    if not (bundle_dir / "content.html").exists():
        raise FileNotFoundError(f"Missing content.html in bundle: {bundle_dir}")
    if not (bundle_dir / "manifest.json").exists():
        raise FileNotFoundError(f"Missing manifest.json in bundle: {bundle_dir}")
    if destination.exists():
        if not force:
            raise FileExistsError(f"Product directory exists: {destination}. Use --force.")
        shutil.rmtree(destination)

    destination.mkdir(parents=True)
    shutil.copy2(bundle_dir / "content.html", destination / "content.html")
    shutil.copy2(bundle_dir / "manifest.json", destination / "manifest.json")
    if (bundle_dir / "assets").exists():
        shutil.copytree(bundle_dir / "assets", destination / "assets")


def _format_product_type(value: str) -> str:
    labels = {
        "snapshot_briefing": "Snapshot briefing",
        "temporal_recon": "Temporal reconnaissance product",
    }
    return labels.get(value, value.replace("_", " ").title() if value else "Product")


def _default_event_meta(manifest: Dict[str, Any], event_date: str) -> str:
    counts = manifest.get("counts", {})
    bits: List[str] = []
    if event_date:
        bits.append(event_date)
    if counts.get("sources") is not None:
        bits.append(f"{counts['sources']} sources")
    if counts.get("facts_cited") is not None and counts.get("facts_total") is not None:
        bits.append(f"{counts['facts_cited']}/{counts['facts_total']} facts cited")
    return " · ".join(bits)


def _default_product_summary(manifest: Dict[str, Any]) -> str:
    counts = manifest.get("counts", {})
    source_count = counts.get("sources")
    fact_count = counts.get("facts_cited")
    total_facts = counts.get("facts_total")
    if source_count is not None and fact_count is not None and total_facts is not None:
        return (
            "Website-ready APHR snapshot briefing with "
            f"{source_count} sources and {fact_count}/{total_facts} cited facts."
        )
    return "Website-ready APHR product generated from a report bundle."


def _upsert_product(products: List[Dict[str, Any]], product: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [item for item in products if item.get("slug") != product["slug"]] + [product]


def publish(args: argparse.Namespace) -> Path:
    bundle_dir = Path(args.bundle)
    source_manifest = _read_json(bundle_dir / "manifest.json")

    event_dir = ROOT / "events" / args.event_slug
    product_dir = event_dir / "products" / args.product_slug
    _copy_bundle(bundle_dir, product_dir, force=args.force)

    manifest_path = product_dir / "manifest.json"
    manifest = _read_json(manifest_path)
    manifest["event_slug"] = args.event_slug
    manifest["product_slug"] = args.product_slug
    if args.event_title:
        manifest["event_title"] = args.event_title
    if args.event_date:
        manifest["event_date"] = args.event_date
    if args.product_title:
        manifest["title"] = args.product_title
    _write_json(manifest_path, manifest)

    event_json_path = event_dir / "event.json"
    event = _read_json(event_json_path) if event_json_path.exists() else {}
    event_date = args.event_date or manifest.get("event_date") or source_manifest.get("event_date") or ""
    event_title = (
        args.event_title
        or event.get("title")
        or manifest.get("event_title")
        or args.event_slug
    )
    event.update(
        {
            "schema_version": "1.0",
            "slug": args.event_slug,
            "title": event_title,
            "event_type": args.event_type,
            "event_date": event_date,
            "tag": args.event_tag or event.get("tag") or _format_product_type(manifest.get("product_type", "")),
            "meta": args.event_meta or event.get("meta") or _default_event_meta(manifest, event_date),
            "description": args.event_description
            or event.get("description")
            or f"Automated APHR products for {event_title}.",
        }
    )

    product = {
        "slug": args.product_slug,
        "title": args.product_title or manifest.get("title") or args.product_slug,
        "product_type": manifest.get("product_type", ""),
        "generated_at": manifest.get("generated_at"),
        "counts": manifest.get("counts", {}),
        "summary": args.product_summary or _default_product_summary(manifest),
        "manifest_path": f"products/{args.product_slug}/manifest.json",
    }
    event["products"] = _upsert_product(event.get("products", []), product)
    if args.set_latest or not event.get("latest_product_slug"):
        event["latest_product_slug"] = args.product_slug
    _write_json(event_json_path, event)

    if args.build:
        build_site()

    return product_dir


def main(argv=None) -> int:
    args = _parse_args(argv)
    product_dir = publish(args)
    print("=" * 72)
    print("PRODUCT PUBLISHED")
    print(f"  product: {product_dir}")
    print(f"  event:   {ROOT / 'events' / args.event_slug / 'event.json'}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
