# MedlinePlus Vietnamese scraper (PlainTalk)

Builds an aligned English/Vietnamese medical text corpus for the glossary and
the retrieval-augmented translation exemplars.

## Install

    pip install requests beautifulsoup4 pdfplumber --break-system-packages

## Run

    python scrape_medlineplus.py --index             # parse index -> manifest.jsonl
    python scrape_medlineplus.py --download --limit 5 # smoke test first
    python scrape_medlineplus.py --download          # full run (~1-2 hours, polite delay)
    python extract_pairs.py                          # -> pairs.jsonl

Only bilingual + paired records are downloaded by default. Add
`--kinds bilingual` to fetch only the highest-value subset.

## Output

    medlineplus-vi/
      manifest.jsonl     one record per document (topic, title, urls, kind)
      bilingual/         single PDFs containing BOTH languages
      en/  vi/           separate files for paired documents
      pairs.jsonl        aligned text: {id, topic, title, kind, en, vi}

## Record kinds

  bilingual  one file, both languages interleaved. Block-aligned automatically.
             Mostly Health Information Translations. Best source for the glossary.
  paired     separate EN and VI files. Document-level only; needs sentence
             alignment before use as exemplars.
  unpaired   only one language exists. Not downloaded by default.

## Notes

- MedlinePlus is an index only. Files come from cdc.gov, fda.gov, cancer.org,
  immunize.org, storage.googleapis.com, and others. Expect some dead links;
  failures are logged and skipped, and reruns resume where you left off.
- Rate limited to ~1 request/second. Do not remove the delay.
- These are US federal and nonprofit patient-education materials. Check the
  terms for each publisher before redistributing; using them as research inputs
  is normal, republishing the PDFs is not.
