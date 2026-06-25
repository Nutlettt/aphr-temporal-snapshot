#!/usr/bin/env python3
"""Build static APHR website pages from event/product manifests."""

from __future__ import annotations

import argparse
from datetime import datetime
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


def _render_breadcrumb(crumbs: List[Dict[str, str]]) -> str:
    parts = []
    for index, crumb in enumerate(crumbs):
        if index:
            parts.append('<span class="crumb-separator">›</span>')

        label = escape(str(crumb["label"]))
        href = crumb.get("href")
        classes = ["crumb"]
        if crumb.get("optional"):
            classes.append("optional-crumb")
        if not href:
            classes.append("crumb-current")

        class_attr = " ".join(classes)
        if href:
            parts.append(
                f'<a class="{class_attr}" href="{escape(href, quote=True)}">{label}</a>'
            )
        else:
            parts.append(f'<span class="{class_attr}">{label}</span>')

    return '<nav class="global-breadcrumb" aria-label="Breadcrumb">' + "".join(parts) + "</nav>"


def _render_topbar(crumbs: List[Dict[str, str]]) -> str:
    return f"""
<div class="global-topbar">
  {_render_breadcrumb(crumbs)}
  <button type="button" class="content-menu-button" data-site-nav-open="site-content-drawer" aria-label="Open contents" title="Contents" data-tooltip="Contents">
    <span class="hamburger" aria-hidden="true"><span></span></span>
  </button>
</div>
""".strip()


def _render_content_drawer(links: List[Dict[str, str]]) -> str:
    rendered_links = "\n".join(
        (
            f'<a href="{escape(link["href"], quote=True)}" data-site-nav-close>'
            f'{escape(link["label"])}</a>'
        )
        for link in links
    )
    return f"""
<div class="site-nav-shell" id="site-content-drawer" aria-hidden="true">
  <div class="site-nav-backdrop" data-site-nav-close></div>
  <aside class="site-nav-panel" role="dialog" aria-modal="true" aria-labelledby="site-nav-title">
    <div class="site-nav-header">
      <h2 id="site-nav-title">Contents</h2>
      <button type="button" class="site-nav-close" data-site-nav-close aria-label="Close contents">&times;</button>
    </div>
    <nav class="site-toc-links">{rendered_links}</nav>
  </aside>
</div>
""".strip()


def _home_crumbs(home_href: str | None = None) -> List[Dict[str, str]]:
    return [
        {"label": "APHR Events", "href": home_href or ""},
    ]


def _clean_current_crumbs(crumbs: List[Dict[str, str]]) -> List[Dict[str, str]]:
    cleaned = []
    for crumb in crumbs:
        item = dict(crumb)
        if item.get("href") == "":
            item.pop("href")
        cleaned.append(item)
    return cleaned


def _product_type(value: str) -> str:
    labels = {
        "snapshot_briefing": "Snapshot briefing",
        "temporal_recon": "Temporal reconnaissance product",
    }
    return labels.get(value, value.replace("_", " ").title() if value else "Product")


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    return None


def _sort_datetime(value: Any) -> str:
    parsed = _parse_datetime(value)
    if parsed:
        return parsed.isoformat()
    return str(value or "")


def _format_month_day_year(value: datetime) -> str:
    return f"{value.strftime('%b')} {value.day}, {value.year}"


def _format_date(value: Any) -> str:
    parsed = _parse_datetime(value)
    if parsed:
        return _format_month_day_year(parsed)
    return str(value or "")


def _format_timeline_date(value: Any) -> str:
    parsed = _parse_datetime(value)
    if parsed:
        return f"{parsed.strftime('%b')}<span>{parsed.day}, {parsed.year}</span>"
    return escape(str(value or ""))


def _format_generated(value: Any) -> str:
    parsed = _parse_datetime(value)
    if not parsed:
        return str(value or "")
    if parsed.hour == 0 and parsed.minute == 0 and parsed.second == 0:
        return _format_month_day_year(parsed)
    zone = " UTC" if parsed.tzinfo else ""
    return f"{_format_month_day_year(parsed)} {parsed.strftime('%H:%M')}{zone}"


def _compact_meta_bits(*values: str) -> str:
    return "\n".join(
        f"<span>{escape(value)}</span>" for value in values if value
    )


def _clean_event_meta_bit(value: str) -> str:
    cleaned = " ".join(value.split())
    cleaned = cleaned.replace(" local time", "")
    return cleaned.strip()


def _extract_event_meta(event: Dict[str, Any]) -> List[str]:
    meta = str(event.get("meta", ""))
    bits = []
    for bit in meta.split("·"):
        cleaned = _clean_event_meta_bit(bit)
        if cleaned:
            bits.append(cleaned)
    return bits[:3]


def _event_meta_text(event: Dict[str, Any]) -> str:
    bits = _extract_event_meta(event)
    if bits:
        return " · ".join(bits)

    fallback = []
    if event.get("event_date"):
        fallback.append(_format_date(event["event_date"]))
    if event.get("event_type"):
        fallback.append(str(event["event_type"]))
    return " · ".join(fallback)


def _product_counts(product: Dict[str, Any]) -> Dict[str, Any]:
    return product.get("counts", {}) or {}


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
    return _sort_datetime(event.get("event_date") or event.get("sort_date"))


def _product_sort_key(product: Dict[str, Any]) -> str:
    return _sort_datetime(product.get("generated_at") or product.get("title") or product.get("slug"))


def _render_home_timeline(events: Iterable[Dict[str, Any]]) -> str:
    items = []
    for event in sorted(events, key=_event_sort_key, reverse=True):
        slug = event["slug"]
        title = escape(str(event.get("title", slug)))
        tag = str(event.get("tag", event.get("event_type", "APHR event")))
        event_type = str(event.get("event_type", "APHR event"))
        date = _format_date(event.get("event_date") or event.get("sort_date"))
        timeline_date = _format_timeline_date(event.get("event_date") or event.get("sort_date"))
        products = event.get("products", [])
        product_count = len(products)
        has_snapshot_products = any(
            str(product.get("product_type", "")).startswith("snapshot")
            for product in products
        )
        if product_count and has_snapshot_products:
            product_label = (
                f"{product_count} snapshot"
                if product_count == 1
                else f"{product_count} snapshots"
            )
        elif product_count:
            product_label = (
                f"{product_count} product"
                if product_count == 1
                else f"{product_count} products"
            )
        else:
            product_label = ""
        meta_bits = _extract_event_meta(event) or [date]
        if product_label:
            meta_bits.append(product_label)
        button = escape(str(event.get("button_label", "Open event briefing")))
        items.append(
            f"""
      <article class="timeline-item event-timeline-item">
        <div class="timeline-index" aria-hidden="true">
          <div class="timeline-dot"></div>
          <div class="timeline-date">{timeline_date}</div>
        </div>
        <div class="timeline-body">
          <div class="timeline-kicker">{escape(event_type)} · {escape(tag)}</div>
          <h2 class="timeline-title">{title}</h2>
          <div class="timeline-meta">{_compact_meta_bits(*meta_bits)}</div>
          <a class="timeline-link" href="events/{escape(slug, quote=True)}/">{button}<span aria-hidden="true">&rarr;</span></a>
        </div>
      </article>
            """.strip()
        )
    return "\n\n".join(items)


def _render_product_timeline_item(event: Dict[str, Any], product: Dict[str, Any]) -> str:
    slug = str(product["slug"])
    title = escape(str(product.get("title", slug)))
    product_type = escape(_product_type(str(product.get("product_type", ""))))
    generated_at = product.get("generated_at")
    latest = slug == event.get("latest_product_slug")
    stats = _product_counts(product)
    meta_bits = []
    if generated_at:
        meta_bits.append(f"Generated { _format_generated(generated_at) }")
    if stats.get("sources") is not None:
        meta_bits.append(f"Sources: {stats['sources']}")
    if stats.get("facts_cited") is not None and stats.get("facts_total") is not None:
        meta_bits.append(f"Facts cited: {stats['facts_cited']}/{stats['facts_total']}")
    timeline_date = _format_timeline_date(generated_at or product.get("title") or product.get("slug"))
    tag = "Latest " + product_type if latest else product_type
    return f"""
      <article class="timeline-item product-timeline-item">
        <div class="timeline-index" aria-hidden="true">
          <div class="timeline-dot"></div>
          <div class="timeline-date">{timeline_date}</div>
        </div>
        <div class="timeline-body">
          <div class="timeline-kicker">{escape(tag)}</div>
          <h2 class="timeline-title">{title}</h2>
          <div class="timeline-meta">{_compact_meta_bits(*meta_bits)}</div>
          <a class="timeline-link" href="products/{escape(slug, quote=True)}/">Open snapshot<span aria-hidden="true">&rarr;</span></a>
        </div>
      </article>
    """.strip()


def _render_product_meta(event: Dict[str, Any], manifest: Dict[str, Any]) -> str:
    pills = []
    if manifest.get("generated_at"):
        pills.append(f"Generated {manifest['generated_at']}")
    counts = manifest.get("counts", {})
    if counts.get("sources") is not None:
        pills.append(f"{counts['sources']} sources")
    if counts.get("facts_cited") is not None and counts.get("facts_total") is not None:
        pills.append(f"{counts['facts_cited']}/{counts['facts_total']} facts cited")
    return "\n          ".join(f"<span>{escape(str(pill))}</span>" for pill in pills)


def _product_toc(manifest: Dict[str, Any]) -> List[Dict[str, str]]:
    links = [{"label": "Overview", "href": "#product-overview"}]
    for section in manifest.get("sections", []):
        section_id = section.get("id")
        title = section.get("title")
        if section_id and title:
            links.append({"label": str(title), "href": f"#{section_id}"})
    return links


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
            "topbar": _render_topbar(
                _clean_current_crumbs(
                    _home_crumbs("../../../../")
                    + [
                        {
                            "label": str(event.get("title", event["slug"])),
                            "href": "../../",
                        },
                        {"label": product_title},
                    ]
                )
            ),
            "content_drawer": _render_content_drawer(_product_toc(manifest)),
            "brand_strip": BRAND_STRIP,
            "product_type": escape(product_type),
            "event_title": escape(str(event.get("title", manifest.get("event_title", "")))),
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

    product_timeline = "\n\n".join(
        _render_product_timeline_item(event, product)
        for product in sorted(products, key=_product_sort_key, reverse=True)
    )
    page = _template(
        "event.html",
        {
            "page_title": escape(str(event.get("title", event["slug"])) + " · APHR"),
            "topbar": _render_topbar(
                _clean_current_crumbs(
                    _home_crumbs("../../")
                    + [{"label": str(event.get("title", event["slug"]))}]
                )
            ),
            "content_drawer": _render_content_drawer(
                [
                    {"label": "Event Overview", "href": "#event-overview"},
                    {"label": "Snapshots", "href": "#snapshots"},
                ]
            ),
            "brand_strip": BRAND_STRIP,
            "event_type": escape(str(event.get("event_type", "APHR event"))),
            "event_title": escape(str(event.get("title", event["slug"]))),
            "event_description": escape(_event_meta_text(event)),
            "product_timeline": product_timeline,
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
            "page_title": "APHR Events",
            "topbar": _render_topbar(
                _clean_current_crumbs(
                    [
                        {"label": "APHR Events"},
                    ]
                )
            ),
            "content_drawer": _render_content_drawer(
                [
                    {"label": "Overview", "href": "#overview"},
                    {"label": "Events", "href": "#events"},
                    {"label": "Credits", "href": "#site-footer"},
                ]
            ),
            "brand_strip": BRAND_STRIP,
            "event_timeline": _render_home_timeline(events),
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
