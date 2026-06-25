#!/usr/bin/env python3
"""Build static APHR website pages from event/product manifests."""

from __future__ import annotations

import argparse
import json
from html import escape
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]

BRAND_STRIP = """
<div class="brand-strip" aria-label="Project partner logos">
  <a class="brand-logo" href="https://raw.githubusercontent.com/Nutlettt/logo-for-webs-dev/main/NSF-and-STEER.png" target="_blank" rel="noopener">
    <img src="https://raw.githubusercontent.com/Nutlettt/logo-for-webs-dev/main/NSF-and-STEER.png" alt="NSF and StEER logo">
  </a>
  <a class="brand-logo brand-logo-peer" href="https://cdn.jsdelivr.net/gh/Nutlettt/logo-for-webs-dev@main/PEER-logo.svg" target="_blank" rel="noopener">
    <img src="https://cdn.jsdelivr.net/gh/Nutlettt/logo-for-webs-dev@main/PEER-logo.svg" alt="PEER logo">
  </a>
  <a class="brand-logo" href="https://raw.githubusercontent.com/Nutlettt/logo-for-webs-dev/main/cropped-stairlab-slogan.png" target="_blank" rel="noopener">
    <img src="https://raw.githubusercontent.com/Nutlettt/logo-for-webs-dev/main/cropped-stairlab-slogan.png" alt="STAIRLab logo">
  </a>
</div>
""".strip()


def _read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _template(name: str, values: Dict[str, str]) -> str:
    text = (ROOT / "templates" / name).read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace("{{ " + key + " }}", value)
    return text


def _product_type(value: str) -> str:
    labels = {
        "snapshot_briefing": "Snapshot briefing",
        "temporal_recon": "Temporal reconnaissance product",
    }
    return labels.get(value, value.replace("_", " ").title() if value else "Product")


def _read_events() -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for event_file in sorted((ROOT / "events").glob("*/event.json")):
        event = _read_json(event_file)
        event.setdefault("slug", event_file.parent.name)
        event["_dir"] = event_file.parent
        event.setdefault("products", [])
        events.append(event)
    return events


def _event_sort_key(event: Dict[str, Any]) -> str:
    return str(event.get("event_date") or event.get("sort_date") or "")


def _render_home_cards(events: Iterable[Dict[str, Any]]) -> str:
    cards = []
    for event in sorted(events, key=_event_sort_key, reverse=True):
        slug = event["slug"]
        title = escape(str(event.get("title", slug)))
        tag = escape(str(event.get("tag", event.get("event_type", "APHR event"))))
        meta = escape(str(event.get("meta", event.get("event_date", ""))))
        description = escape(str(event.get("description", "")))
        button = escape(str(event.get("button_label", "Open event briefing")))
        cards.append(
            f"""
      <article class="card">
        <span class="tag">{tag}</span>
        <h2 class="card-title">{title}</h2>
        <p class="meta">{meta}</p>
        <p class="desc">{description}</p>
        <a class="button" href="events/{escape(slug, quote=True)}/">{button}</a>
      </article>
            """.strip()
        )
    return "\n\n".join(cards)


def _render_product_card(event: Dict[str, Any], product: Dict[str, Any]) -> str:
    slug = str(product["slug"])
    title = escape(str(product.get("title", slug)))
    product_type = escape(_product_type(str(product.get("product_type", ""))))
    generated_at = product.get("generated_at")
    latest = slug == event.get("latest_product_slug")
    stats = product.get("counts", {})
    meta_bits = []
    if generated_at:
        meta_bits.append(f"Generated: {generated_at}")
    if stats.get("sources") is not None:
        meta_bits.append(f"Sources: {stats['sources']}")
    if stats.get("facts_cited") is not None and stats.get("facts_total") is not None:
        meta_bits.append(f"Facts cited: {stats['facts_cited']}/{stats['facts_total']}")
    meta = escape(" · ".join(str(bit) for bit in meta_bits))
    summary = escape(str(product.get("summary", "")))
    tag = "Latest " + product_type if latest else product_type
    return f"""
      <article class="card">
        <span class="tag">{escape(tag)}</span>
        <h2 class="card-title">{title}</h2>
        <p class="meta">{meta}</p>
        <p class="desc">{summary}</p>
        <a class="button" href="products/{escape(slug, quote=True)}/">Open product</a>
      </article>
    """.strip()


def _render_product_meta(event: Dict[str, Any], manifest: Dict[str, Any]) -> str:
    pills = []
    event_title = event.get("title") or manifest.get("event_title")
    if event_title:
        pills.append(str(event_title))
    if manifest.get("generated_at"):
        pills.append(f"Generated {manifest['generated_at']}")
    counts = manifest.get("counts", {})
    if counts.get("sources") is not None:
        pills.append(f"{counts['sources']} sources")
    if counts.get("facts_cited") is not None and counts.get("facts_total") is not None:
        pills.append(f"{counts['facts_cited']}/{counts['facts_total']} facts cited")
    snapshot = manifest.get("snapshot", {})
    if snapshot.get("snapshot_id"):
        pills.append(f"Snapshot {snapshot['snapshot_id']}")
    return "\n          ".join(
        f'<span class="pill">{escape(str(pill))}</span>' for pill in pills
    )


def _build_product_page(event: Dict[str, Any], product: Dict[str, Any]) -> None:
    product_dir = Path(event["_dir"]) / "products" / str(product["slug"])
    content_path = product_dir / "content.html"
    manifest_path = product_dir / "manifest.json"
    if not content_path.exists() or not manifest_path.exists():
        print(f"SKIP missing product bundle: {product_dir}")
        return

    content_html = content_path.read_text(encoding="utf-8")
    manifest = _read_json(manifest_path)
    product_title = str(
        product.get("title") or manifest.get("title") or product["slug"]
    )
    product_type = _product_type(str(manifest.get("product_type", "")))
    page = _template(
        "product.html",
        {
            "page_title": escape(f"{product_title} · APHR"),
            "brand_strip": BRAND_STRIP,
            "product_type": escape(product_type),
            "product_title": escape(product_title),
            "product_meta": _render_product_meta(event, manifest),
            "content_html": content_html,
        },
    )
    _write(product_dir / "index.html", page)
    print(f"BUILT {product_dir / 'index.html'}")


def _build_event_page(event: Dict[str, Any]) -> None:
    products = event.get("products", [])
    if not products:
        print(f"PRESERVE legacy event page: {event['slug']}")
        return

    product_cards = "\n\n".join(_render_product_card(event, product) for product in products)
    page = _template(
        "event.html",
        {
            "page_title": escape(str(event.get("title", event["slug"])) + " · APHR"),
            "brand_strip": BRAND_STRIP,
            "event_type": escape(str(event.get("event_type", "APHR event"))),
            "event_title": escape(str(event.get("title", event["slug"]))),
            "event_description": escape(str(event.get("description", ""))),
            "product_cards": product_cards,
        },
    )
    _write(Path(event["_dir"]) / "index.html", page)
    print(f"BUILT {Path(event['_dir']) / 'index.html'}")


def build_site() -> None:
    events = _read_events()
    if not events:
        raise RuntimeError("No events/*/event.json files found.")

    home = _template(
        "home.html",
        {
            "page_title": "APHR Event Briefings",
            "brand_strip": BRAND_STRIP,
            "event_cards": _render_home_cards(events),
        },
    )
    _write(ROOT / "index.html", home)
    print(f"BUILT {ROOT / 'index.html'}")

    for event in events:
        for product in event.get("products", []):
            _build_product_page(event, product)
        _build_event_page(event)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    build_site()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
