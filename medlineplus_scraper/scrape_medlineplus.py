#!/usr/bin/env python3
"""
Scrape the MedlinePlus Vietnamese index into aligned English/Vietnamese document pairs.

MedlinePlus is only an index; the documents live on cdc.gov, fda.gov, cancer.org,
immunize.org, storage.googleapis.com (Health Information Translations), etc.

Two record kinds are produced:
  paired    - separate EN and VI files that share a title prefix
  bilingual - ONE file containing both languages (usually Health Information
              Translations). Highest value for glossary building, since the
              alignment is inside the document.

Usage:
    python scrape_medlineplus.py --index          # parse index -> manifest.jsonl
    python scrape_medlineplus.py --download       # fetch files listed in manifest
    python scrape_medlineplus.py --index --download
"""

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

INDEX_URL = "https://medlineplus.gov/languages/vietnamese.html"
OUT = Path("medlineplus-vi")
UA = "PlainTalk-research-scraper/1.0 (CSUF CPSC 597; academic use)"
DELAY = 1.0  # seconds between requests. Be polite.

# Link-text suffixes, longest first so "Bilingual PDF" wins over "PDF".
SUFFIXES = [
    (" - Tiếng Việt (Vietnamese) Bilingual PDF", "bilingual", "pdf"),
    (" - Tiếng Việt (Vietnamese) Bilingual HTML", "bilingual", "html"),
    (" - Tiếng Việt (Vietnamese) PDF", "vi", "pdf"),
    (" - Tiếng Việt (Vietnamese) HTML", "vi", "html"),
    (" - English PDF", "en", "pdf"),
    (" - English HTML", "en", "html"),
]


def classify(link_text):
    """Return (title, lang, fmt) or None if this anchor is not a document link."""
    t = " ".join(link_text.split())
    for suffix, lang, fmt in SUFFIXES:
        if t.endswith(suffix):
            return t[: -len(suffix)].strip(), lang, fmt
    return None


def parse_index(html):
    """
    Parse the index into records. Deliberately markup-agnostic: it keys off the
    link TEXT, not CSS classes, so it survives site redesigns.
    """
    soup = BeautifulSoup(html, "html.parser")
    records, topic = {}, None

    for el in soup.find_all(["h2", "h3", "h4", "a"]):
        if el.name in ("h2", "h3", "h4"):
            text = " ".join(el.get_text().split())
            # Skip the A-Z jump headers and boilerplate
            if text and len(text) > 2 and "Expand Section" not in text:
                topic = text
            continue

        href = el.get("href")
        if not href or href.startswith("#"):
            continue
        hit = classify(el.get_text())
        if not hit:
            continue
        title, lang, fmt = hit

        key = (topic, title)
        rec = records.setdefault(
            key,
            {"topic": topic, "title": title, "kind": None, "format": fmt,
             "en_url": None, "vi_url": None, "bilingual_url": None, "source": None},
        )
        if lang == "en":
            rec["en_url"] = href
        elif lang == "vi":
            rec["vi_url"] = href
        else:
            rec["bilingual_url"] = href
        rec["format"] = fmt

    out = []
    for rec in records.values():
        if rec["bilingual_url"]:
            rec["kind"] = "bilingual"
        elif rec["en_url"] and rec["vi_url"]:
            rec["kind"] = "paired"
        else:
            rec["kind"] = "unpaired"  # only one language available; keep for reference
        rec["id"] = hashlib.md5(
            f"{rec['topic']}|{rec['title']}".encode("utf-8")
        ).hexdigest()[:12]
        out.append(rec)

    # The index lists the same document under every topic it belongs to, so the
    # (topic, title) key above yields several records pointing at identical
    # URLs. Keep the first and drop the rest, otherwise the same file is
    # downloaded repeatedly and floods pairs.jsonl with duplicate blocks.
    deduped, seen = [], set()
    for rec in out:
        key = (rec["bilingual_url"], rec["en_url"], rec["vi_url"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(rec)
    return deduped


def fname(rec, lang, url):
    ext = ".pdf" if rec["format"] == "pdf" else ".html"
    safe = re.sub(r"[^A-Za-z0-9]+", "_", rec["title"])[:60].strip("_")
    return f"{rec['id']}_{safe}{ext}"


def fetch(session, url, dest, timeout=45):
    if dest.exists() and dest.stat().st_size > 0:
        return "skip"
    try:
        r = session.get(url, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
        return "ok"
    except Exception as e:
        print(f"    FAIL {urlparse(url).netloc}: {e}", file=sys.stderr)
        return "fail"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", action="store_true", help="parse the index page")
    ap.add_argument("--download", action="store_true", help="download the documents")
    ap.add_argument("--limit", type=int, default=0, help="only fetch N records (testing)")
    ap.add_argument("--kinds", default="bilingual,paired",
                    help="comma list: bilingual,paired,unpaired")
    args = ap.parse_args()
    if not (args.index or args.download):
        ap.error("pass --index and/or --download")

    OUT.mkdir(parents=True, exist_ok=True)
    manifest = OUT / "manifest.jsonl"
    session = requests.Session()
    session.headers["User-Agent"] = UA

    if args.index:
        print(f"Fetching index: {INDEX_URL}")
        resp = session.get(INDEX_URL, timeout=60)
        # Server sends "text/html" with no charset, so requests falls back to
        # ISO-8859-1 and mangles the Vietnamese link text the suffixes match on.
        resp.encoding = "utf-8"
        html = resp.text
        recs = parse_index(html)
        with manifest.open("w", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        counts = {}
        for r in recs:
            counts[r["kind"]] = counts.get(r["kind"], 0) + 1
        print(f"Wrote {len(recs)} records to {manifest}")
        print(f"  {counts}")

    if args.download:
        wanted = set(args.kinds.split(","))
        recs = [json.loads(l) for l in manifest.open(encoding="utf-8")]
        recs = [r for r in recs if r["kind"] in wanted]
        if args.limit:
            recs = recs[: args.limit]
        print(f"Downloading {len(recs)} records ({', '.join(sorted(wanted))})")

        tally = {"ok": 0, "skip": 0, "fail": 0}
        for i, rec in enumerate(recs, 1):
            jobs = []
            if rec["kind"] == "bilingual":
                jobs.append(("bilingual", rec["bilingual_url"]))
            else:
                if rec["en_url"]:
                    jobs.append(("en", rec["en_url"]))
                if rec["vi_url"]:
                    jobs.append(("vi", rec["vi_url"]))
            for lang, url in jobs:
                dest = OUT / lang / fname(rec, lang, url)
                res = fetch(session, url, dest)
                tally[res] += 1
                if res == "ok":
                    time.sleep(DELAY)
            if i % 25 == 0:
                print(f"  [{i}/{len(recs)}] {tally}")
        print(f"Done: {tally}")
        print(f"Files under {OUT}/bilingual, {OUT}/en, {OUT}/vi")


if __name__ == "__main__":
    main()
