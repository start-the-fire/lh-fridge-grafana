#!/usr/bin/env python3
"""
TempVerity - Liebherr Laboratory & Healthcare product image fetcher

Downloads one official Liebherr product image per unique model from these
Austrian catalogue categories:
- Laborkühlschränke
- Labor-Kühl-Gefrierkombinationen
- Laborgefrierschränke
- Medikamentenkühlschränke
- Ultratiefkühlschränke

The script discovers the current models from the category pages instead of
hard-coding the catalogue, follows each product page, finds an official
assets-cdn.liebherr.com product image matching the model designation, and
stores one local image per unique model.

Usage:
    python3 download_liebherr_images.py

Optional:
    python3 download_liebherr_images.py --output ./images --zip tempverity_liebherr_images.zip
    python3 download_liebherr_images.py --only-model HMFvh 4011 --output ../data/images/catalog
"""

from __future__ import annotations

import argparse
import csv
import html
import mimetypes
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

BASE = "https://www.liebherr.com"

CATEGORIES = {
    "lab-refrigerators":
        "https://www.liebherr.com/de-at/gefrier-kuehlschraenke/laborkuehlschraenke-2224791",
    "lab-fridge-freezers":
        "https://www.liebherr.com/de-at/gefrier-kuehlschraenke/labor-kuehl-gefrierkombinationen-9104333",
    "lab-freezers":
        "https://www.liebherr.com/de-at/gefrier-kuehlschraenke/laborgefrierschraenke-2224794",
    "medical-refrigerators":
        "https://www.liebherr.com/de-at/gefrier-kuehlschraenke/medikamentenkuehlschraenke-2224797",
    "ultra-low-freezers":
        "https://www.liebherr.com/de-at/gefrier-kuehlschraenke/ultratiefkuehlschraenke-2224800",
}

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/140.0 Safari/537.36 TempVerityImageFetcher/1.0"
)

def fetch(url: str, timeout: int = 30) -> tuple[bytes, str]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,image/avif,image/webp,image/*,*/*;q=0.8",
            "Accept-Language": "de-AT,de;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
        ctype = r.headers.get("Content-Type", "")
        return data, ctype

def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()

def normalize_model(text: str) -> str | None:
    # Liebherr professional model identifiers seen in these catalogues:
    # e.g. HMTvh 1501, SRPvg 6501, SCFvh 4032, SUFsg 5001
    m = re.search(r"\b([A-Z]{2,6}[A-Za-z]{0,5}\s+\d{3,4})\b", text)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else None

def safe_filename(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model.strip())

def discover_products(category_url: str) -> dict[str, str]:
    raw, _ = fetch(category_url)
    page = raw.decode("utf-8", "replace")

    products: dict[str, str] = {}

    # Product anchors are normally /de-at/p/<slug>-<id>.
    anchor_re = re.compile(
        r'<a\b[^>]*href=["\']([^"\']*/de-at/p/[^"\']+)["\'][^>]*>(.*?)</a>',
        re.I | re.S,
    )
    for href, body in anchor_re.findall(page):
        text = strip_tags(body)
        model = normalize_model(text)
        if not model:
            # Fallback: derive from product slug if anchor text is fragmented.
            slug = urllib.parse.unquote(href).split("/p/", 1)[-1]
            candidate = slug.rsplit("-", 1)[0].replace("-", " ")
            model = normalize_model(candidate)
        if model:
            url = urllib.parse.urljoin(BASE, html.unescape(href))
            products.setdefault(model, url)

    # Fallback for JS/JSON-embedded product URLs.
    if not products:
        for href in set(re.findall(r'https?://www\.liebherr\.com/de-at/p/[^"\'<>\s]+|/de-at/p/[^"\'<>\s]+', page)):
            url = urllib.parse.urljoin(BASE, html.unescape(href).replace("\\/", "/"))
            slug = urllib.parse.unquote(url).split("/p/", 1)[-1]
            candidate = slug.rsplit("-", 1)[0].replace("-", " ")
            model = normalize_model(candidate)
            if model:
                products.setdefault(model, url)

    return products

def choose_product_image(product_url: str, model: str) -> tuple[str | None, dict]:
    """
    Find the best official Liebherr product image.

    Preferred source:
      The product's embedded __NEXT_DATA__ asset metadata contains entries such as:
        assetType: product_image
        mimeTypeDisplayName: JPG
        url: .../web/
        urlTemplateWithFilename:
            .../{derivate}/HMFvh%204011.{extension}

    We use this to request the native 'web' JPG instead of a generated
    1280x1280 WebP derivative.

    Returns:
        (image_url, metadata)
    """
    raw, _ = fetch(product_url)
    page = raw.decode("utf-8", "replace").replace("\\/", "/")

    # Decode the JSON-ish URL representations enough for matching.
    decoded_page = html.unescape(page)

    # Prefer appliance photos that work well as a UI product illustration.
    # Closed/empty views are preferred over open or ambient shots.
    perspective_priority = {
        "straight_closed_empty": 100,
        "oblique_closed_empty": 95,
        "straight_open_empty": 80,
        "oblique_open_empty": 75,
        "ambient": 40,
    }

    # Match individual product_image objects from the embedded JSON.
    # Keep the expression deliberately local to each object so unrelated
    # accessories/download assets cannot win.
    asset_pattern = re.compile(
        r'\{'
        r'(?=[^{}]*"assetType":"product_image")'
        r'[^{}]*?'
        r'"assetType":"product_image"'
        r'(?P<body>.*?)'
        r'"urlTemplateWithFilename":"(?P<template>https://assets-cdn\.liebherr\.com/versions/[^"]+)"'
        r'[^{}]*?'
        r'\}',
        re.I | re.S,
    )

    assets = []
    for m in asset_pattern.finditer(decoded_page):
        block = m.group(0)
        template = m.group("template").replace("\\u0026", "&")

        # Make sure the asset actually belongs to this model.
        decoded_template = urllib.parse.unquote(template)
        if model.casefold() not in decoded_template.casefold():
            continue

        mime_m = re.search(r'"mimeTypeDisplayName":"([^"]+)"', block, re.I)
        mime_name = mime_m.group(1).upper() if mime_m else "JPG"

        perspective_m = re.search(
            r'"key":"perspective","value":"([^"]+)"', block, re.I
        )
        perspective = perspective_m.group(1) if perspective_m else ""

        order_m = re.search(r'"pimOrder":(\d+)', block)
        pim_order = int(order_m.group(1)) if order_m else 999999

        size_m = re.search(r'"fileSize":(\d+)', block)
        file_size = int(size_m.group(1)) if size_m else 0

        ext = {
            "JPG": "jpg",
            "JPEG": "jpg",
            "PNG": "png",
            "WEBP": "webp",
        }.get(mime_name, mime_name.lower())

        # The console data exposes the high-quality product rendition as
        # derivate=web, while thumbnail / w-1280_h-1280_f-webp are derivatives.
        hires_url = (
            template
            .replace("{derivate}", "web")
            .replace("{extension}", ext)
        )

        assets.append({
            "url": hires_url,
            "perspective": perspective,
            "mime": mime_name,
            "file_size": file_size,
            "pim_order": pim_order,
            "source": "next_data_product_image_web",
            "score": perspective_priority.get(perspective, 60),
        })

    if assets:
        # First choose a useful closed product view; PIM ordering acts as a
        # stable secondary preference.
        assets.sort(key=lambda a: (-a["score"], a["pim_order"], -a["file_size"]))
        best = assets[0]
        return best["url"], best

    # Fallback: older/current pages may not expose the structured asset data.
    # Prefer /web/ if a template is visible, otherwise use 1280 WebP.
    templates = re.findall(
        r'https://assets-cdn\.liebherr\.com/versions/[^"\'<>\s]+/\{derivate\}/[^"\'<>\s]+?\.\{extension\}',
        decoded_page,
        flags=re.I,
    )
    model_cf = model.casefold()
    for template in templates:
        if model_cf in urllib.parse.unquote(template).casefold():
            url = template.replace("{derivate}", "web").replace("{extension}", "jpg")
            return url, {
                "url": url,
                "perspective": "",
                "mime": "JPG",
                "file_size": 0,
                "pim_order": 999999,
                "source": "url_template_web_fallback",
                "score": 0,
            }

    # Last fallback to already rendered CDN variants.
    candidates = re.findall(
        r'https://assets-cdn\.liebherr\.com/versions/[^"\'<>\s,]+',
        urllib.parse.unquote(decoded_page),
        flags=re.I,
    )

    cleaned = []
    for u in candidates:
        u = u.replace("\\u002F", "/").replace("\\u0026", "&").rstrip(")];},")
        if u not in cleaned:
            cleaned.append(u)

    def fallback_score(url: str) -> int:
        decoded = urllib.parse.unquote(url)
        basename = Path(urllib.parse.urlparse(decoded).path).name
        s = 0
        if model_cf in basename.casefold():
            s += 100
        if "/w-1280_h-1280_f-webp/" in url:
            s += 30
        elif "/thumbnail/" in url:
            s += 10
        return s

    cleaned.sort(key=fallback_score, reverse=True)
    if cleaned and fallback_score(cleaned[0]) >= 100:
        return cleaned[0], {
            "url": cleaned[0],
            "perspective": "",
            "mime": "",
            "file_size": 0,
            "pim_order": 999999,
            "source": "rendered_derivative_fallback",
            "score": fallback_score(cleaned[0]),
        }

    return None, {}

def download_image(url: str, destination_without_ext: Path) -> tuple[Path, str]:
    data, ctype = fetch(url, timeout=45)

    # Basic validation: avoid accidentally saving an HTML error page.
    ctype_low = ctype.lower()
    if "text/html" in ctype_low:
        raise RuntimeError("server returned HTML instead of an image")
    if len(data) < 1500:
        raise RuntimeError(f"image response unexpectedly small ({len(data)} bytes)")

    parsed_ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if parsed_ext not in {".webp", ".png", ".jpg", ".jpeg"}:
        parsed_ext = {
            "image/webp": ".webp",
            "image/png": ".png",
            "image/jpeg": ".jpg",
        }.get(ctype.split(";")[0].strip().lower(), ".webp")

    dest = destination_without_ext.with_suffix(parsed_ext)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest, ctype

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="tempverity_liebherr_images",
                    help="Output directory")
    ap.add_argument("--zip", default="tempverity_liebherr_images.zip",
                    help="ZIP filename; use empty string to disable")
    ap.add_argument("--delay", type=float, default=0.25,
                    help="Delay between web requests (seconds)")
    ap.add_argument("--only-model", action="append", default=[],
                    help="Download only this model; may be supplied more than once")
    args = ap.parse_args()

    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)

    manifest = []
    seen_models: set[str] = set()
    requested_models = {re.sub(r"\s+", " ", model).strip().casefold() for model in args.only_model}

    print("Discovering current Liebherr Laboratory & Healthcare catalogue...")
    for category, category_url in CATEGORIES.items():
        print(f"\n[{category}]")
        try:
            products = discover_products(category_url)
        except Exception as e:
            print(f"  ERROR fetching category: {e}", file=sys.stderr)
            continue

        print(f"  Found {len(products)} product/model links")
        for model, product_url in sorted(products.items()):
            if requested_models and re.sub(r"\s+", " ", model).strip().casefold() not in requested_models:
                continue
            if model.casefold() in seen_models:
                print(f"  SKIP duplicate model: {model}")
                continue
            seen_models.add(model.casefold())

            status = "failed"
            image_url = ""
            image_meta = {}
            filename = ""
            error = ""

            try:
                time.sleep(args.delay)
                image_url, image_meta = choose_product_image(product_url, model)
                image_url = image_url or ""
                if not image_url:
                    raise RuntimeError("no matching official product image URL found")

                dest_base = root / category / safe_filename(model)
                time.sleep(args.delay)
                dest, ctype = download_image(image_url, dest_base)
                filename = str(dest.relative_to(root))
                status = "downloaded"
                print(f"  OK  {model:<16} -> {filename}")
            except Exception as e:
                error = str(e)
                print(f"  ERR {model:<16} -> {error}", file=sys.stderr)

            manifest.append({
                "model": model,
                "category": category,
                "product_url": product_url,
                "image_url": image_url,
                "filename": filename,
                "status": status,
                "error": error,
                "image_source": image_meta.get("source", "") if "image_meta" in locals() else "",
                "perspective": image_meta.get("perspective", "") if "image_meta" in locals() else "",
                "source_mime": image_meta.get("mime", "") if "image_meta" in locals() else "",
            })

    manifest_path = root / "models.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["model", "category", "product_url", "image_url",
                        "filename", "status", "error", "image_source",
                        "perspective", "source_mime"],
        )
        writer.writeheader()
        writer.writerows(manifest)

    successes = sum(r["status"] == "downloaded" for r in manifest)
    print(f"\nFinished: {successes}/{len(manifest)} unique models downloaded.")
    print(f"Manifest: {manifest_path}")

    if args.zip:
        zip_path = Path(args.zip)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for p in root.rglob("*"):
                if p.is_file():
                    z.write(p, p.relative_to(root.parent))
        print(f"ZIP: {zip_path.resolve()}")

    return 0 if successes else 2

if __name__ == "__main__":
    raise SystemExit(main())
