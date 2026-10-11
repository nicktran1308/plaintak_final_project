#!/usr/bin/env python3
"""
Turn downloaded MedlinePlus documents into aligned EN/VI text for PlainTalk.

Outputs medlineplus-vi/pairs.jsonl, one record per aligned block:
    {"id","topic","title","kind","en","vi"}

Bilingual PDFs (Health Information Translations) interleave English and
Vietnamese, so blocks are classified per line by Vietnamese-specific
characters, then consecutive EN/VI runs are zipped together.

Paired PDFs give only a document-level pair; sentence alignment for those is a
separate step (see note at bottom of this file).

Usage:
    pip install pdfplumber beautifulsoup4 --break-system-packages
    python extract_pairs.py
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

OUT = Path("medlineplus-vi")

# Characters that appear in Vietnamese but not in English.
VN_CHARS = set(
    "ăâđêôơưĂÂĐÊÔƠƯ"
    "áàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩị"
    "óòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
    "ÁÀẢÃẠẮẰẲẴẶẤẦẨẪẬÉÈẺẼẸẾỀỂỄỆÍÌỈĨỊ"
    "ÓÒỎÕỌỐỒỔỖỘỚỜỞỠỢÚÙỦŨỤỨỪỬỮỰÝỲỶỸỴ"
)


def vn_score(text):
    """Fraction of alphabetic characters that are Vietnamese-specific."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if c in VN_CHARS) / len(letters)


def is_vietnamese(line, threshold=0.02):
    """
    Vietnamese lines almost always carry diacritics. The threshold is low
    because short lines ('Bác sĩ') have few marked characters overall.
    """
    return vn_score(line) >= threshold


def read_pdf(path):
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return "\n".join((p.extract_text() or "") for p in pdf.pages)
    except ImportError:
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
    except Exception as e:
        print(f"  cannot read {path.name}: {e}", file=sys.stderr)
        return ""


def read_html(path):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    for t in soup(["script", "style", "nav", "header", "footer"]):
        t.decompose()
    return soup.get_text("\n")


def read_any(path):
    if not path.exists():
        return ""
    # The manifest carries one format per record, so a document whose English
    # link is HTML and Vietnamese link is a PDF gets the wrong extension on one
    # side. Trust the bytes rather than the suffix.
    is_pdf = path.open("rb").read(5) == b"%PDF-"
    return read_pdf(path) if is_pdf else read_html(path)


def clean_lines(text):
    lines = []
    for raw in text.splitlines():
        s = " ".join(raw.split())
        if len(s) < 3:
            continue
        if re.fullmatch(r"[\d\W_]+", s):        # page numbers, rules
            continue
        if re.match(r"^(Page \d+|\d+ of \d+)$", s, re.I):
            continue
        lines.append(s)
    return lines


def split_bilingual(text):
    """
    Group consecutive lines into EN and VI runs, then pair adjacent runs.
    Health Information Translations documents alternate language by block.
    """
    lines = clean_lines(text)
    runs = []
    for line in lines:
        lang = "vi" if is_vietnamese(line) else "en"
        if runs and runs[-1][0] == lang:
            runs[-1][1].append(line)
        else:
            runs.append([lang, [line]])

    pairs = []
    for i in range(len(runs) - 1):
        a_lang, a_txt = runs[i]
        b_lang, b_txt = runs[i + 1]
        if a_lang == "en" and b_lang == "vi":
            en, vi = " ".join(a_txt), " ".join(b_txt)
            # Guard against pairing a heading with a whole page of body text.
            if 10 <= len(en) and 10 <= len(vi) and 0.3 <= len(vi) / len(en) <= 3.0:
                pairs.append((en, vi))
    return pairs


def strip_bullet(text):
    return re.sub(r"^(?:Ì|•|▪|◦|\*)\s+", "", text)


def _group_lines(words, tol=3.0):
    """Cluster words into visual lines by their top coordinate."""
    lines = []
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if lines and abs(w["top"] - lines[-1]["top"]) <= tol:
            lines[-1]["words"].append(w)
            lines[-1]["bottom"] = max(lines[-1]["bottom"], w["bottom"])
        else:
            lines.append({"top": w["top"], "bottom": w["bottom"], "words": [w]})
    for ln in lines:
        ln["text"] = " ".join(
            w["text"] for w in sorted(ln["words"], key=lambda w: w["x0"])
        )
    return lines


def _paragraphs(lines):
    """Break a column's lines into blocks on vertical gaps and bullet starts."""
    if not lines:
        return []
    heights = sorted(ln["bottom"] - ln["top"] for ln in lines)
    lh = heights[len(heights) // 2] or 10.0
    paras, cur = [], [lines[0]]
    for prev, ln in zip(lines, lines[1:]):
        head = ln["text"].lstrip()
        # "Ì" is how pdfplumber decodes the Wingdings bullet these PDFs use.
        starts_item = head.startswith(("•", "▪", "◦", "*")) or re.match(
            r"(\d+\.|Ì)\s", head
        )
        if ln["top"] - prev["bottom"] > 0.35 * lh or starts_item:
            paras.append(cur)
            cur = [ln]
        else:
            cur.append(ln)
    paras.append(cur)
    return [
        {
            "text": " ".join(l["text"] for l in p),
            "top": p[0]["top"],
            "bottom": p[-1]["bottom"],
        }
        for p in paras
    ]


def find_gutter(pages):
    """
    Return the x of the vertical gutter separating a side-by-side EN|VI layout,
    or None for a single-column document. Chooses the x crossed by the fewest
    words so a stray full-width header or footer cannot hide the gutter.
    """
    occ, width = [], pages[0].width
    for pg in pages:
        occ += [(w["x0"], w["x1"]) for w in pg.extract_words()]
    if len(occ) < 60:
        return None
    cx, span = min(
        ((x, sum(1 for a, b in occ if a < x < b))
         for x in range(int(width * 0.35), int(width * 0.65))),
        key=lambda t: t[1],
    )
    left = sum(1 for a, b in occ if b <= cx)
    right = sum(1 for a, b in occ if a >= cx)
    if span / len(occ) <= 0.02 and left > 20 and right > 20:
        if 0.25 < left / right < 4.0:
            return cx
    return None


def split_columns(path):
    """
    Health Information Translations PDFs place English and Vietnamese in two
    columns on the same row, so extract_text() reads straight across and glues
    the languages together. Read each column separately instead and pair blocks
    by vertical overlap. Returns None if the document is not two-column.
    """
    import pdfplumber

    pairs = []
    with pdfplumber.open(path) as pdf:
        pages = pdf.pages
        if not pages:
            return None
        gutter = find_gutter(pages[:3])
        if gutter is None:
            return None
        for pg in pages:
            words = pg.extract_words()
            left = _paragraphs(_group_lines([w for w in words if w["x1"] <= gutter]))
            right = _paragraphs(_group_lines([w for w in words if w["x0"] >= gutter]))
            # Vietnamese wraps longer than English, so the right column drifts
            # down the page. Give each right block to its single best-overlapping
            # left block; otherwise one block bleeds into two pairs.
            claimed = {}
            for rp in right:
                best, best_ov = None, 0.0
                for i, lp in enumerate(left):
                    ov = min(lp["bottom"], rp["bottom"]) - max(lp["top"], rp["top"])
                    if ov > best_ov:
                        best, best_ov = i, ov
                if best is not None:
                    claimed.setdefault(best, []).append(rp)

            for i, lp in enumerate(left):
                if i not in claimed:
                    continue
                en = strip_bullet(" ".join(lp["text"].split()))
                vi = strip_bullet(" ".join(" ".join(rp["text"] for rp in claimed[i]).split()))
                if len(en) < 10 or len(vi) < 10:
                    continue
                if not 0.3 <= len(vi) / len(en) <= 3.0:
                    continue
                # The left column must read as English and the right as Vietnamese.
                if is_vietnamese(en) or not is_vietnamese(vi):
                    continue
                pairs.append((en, vi))
    return pairs


def main():
    manifest = OUT / "manifest.jsonl"
    if not manifest.exists():
        sys.exit("Run scrape_medlineplus.py --index --download first.")

    recs = [json.loads(l) for l in manifest.open(encoding="utf-8")]
    by_id = {r["id"]: r for r in recs}
    out_path = OUT / "pairs.jsonl"
    n_docs = n_pairs = 0

    with out_path.open("w", encoding="utf-8") as out:
        # --- bilingual: block-level alignment inside one file ---
        for f in sorted((OUT / "bilingual").glob("*")):
            rec = by_id.get(f.name.split("_")[0])
            if not rec:
                continue
            pairs = None
            if f.suffix == ".pdf":
                try:
                    pairs = split_columns(f)
                except Exception as e:
                    print(f"  column split failed on {f.name}: {e}", file=sys.stderr)
            if not pairs:
                pairs = split_bilingual(read_any(f))
            for en, vi in pairs:
                out.write(json.dumps({
                    "id": rec["id"], "topic": rec["topic"], "title": rec["title"],
                    "kind": "bilingual", "en": en, "vi": vi,
                }, ensure_ascii=False) + "\n")
            if pairs:
                n_docs += 1
                n_pairs += len(pairs)

        # --- paired: document-level only ---
        for f in sorted((OUT / "en").glob("*")):
            rec = by_id.get(f.name.split("_")[0])
            if not rec:
                continue
            vi_files = list((OUT / "vi").glob(f"{rec['id']}_*"))
            if not vi_files:
                continue
            en, vi = read_any(f), read_any(vi_files[0])
            if len(en) < 200 or len(vi) < 200:
                continue
            out.write(json.dumps({
                "id": rec["id"], "topic": rec["topic"], "title": rec["title"],
                "kind": "document", "en": en, "vi": vi,
            }, ensure_ascii=False) + "\n")
            n_docs += 1
            n_pairs += 1

    print(f"{n_docs} documents -> {n_pairs} records in {out_path}")
    print("\nNext steps:")
    print("  - bilingual records are block-aligned and ready for exemplar retrieval")
    print("  - document records need sentence alignment; a length-ratio aligner or")
    print("    LaBSE/SBERT cosine matching over sentences both work well here")
    print("  - build the glossary by pulling recurring clinical terms from the")
    print("    bilingual blocks and verifying each by hand before use")


if __name__ == "__main__":
    main()
