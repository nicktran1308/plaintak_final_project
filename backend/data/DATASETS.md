# Manual dataset downloads (no Cursor needed)

Run these yourself in a terminal. Working directory: `plaintalk-data/`.

## 1. PLABA  (~15 MB)
Web download, no API.
1. Open https://osf.io/rnpmf/
2. Download `data.json` and every `.csv`
3. Put them in `plaintalk-data/plaba/`

Verify:
    python -c "import json;d=json.load(open('plaba/data.json'));print(len(d),'entries')"

## 2. Cochrane  (~20 MB)
    pip install datasets --break-system-packages
    python - <<'EOF'
    from datasets import load_dataset
    import json, pathlib
    ds = load_dataset("GEM/cochrane_simplification")
    out = pathlib.Path("cochrane"); out.mkdir(exist_ok=True)
    for split in ds:
        with open(out / f"{split}.jsonl", "w", encoding="utf-8") as f:
            for r in ds[split]:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(split, len(ds[split]))
    EOF

If the GEM name 404s, get it from https://gem-benchmark.com/data_cards/cochrane-simplification

## 3. Med-EASi  (~3 MB)
    python - <<'EOF'
    from datasets import load_dataset
    import json, pathlib
    ds = load_dataset("cbasu/Med-EASi")
    out = pathlib.Path("med-easi"); out.mkdir(exist_ok=True)
    for split in ds:
        with open(out / f"{split}.jsonl", "w", encoding="utf-8") as f:
            for r in ds[split]:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(split, len(ds[split]))
    EOF

## 4. Models  (~1 GB) -- do this one FIRST, it is the one that breaks
scispaCy pins hard against a specific spaCy version. Use a venv.

    python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
    pip install spacy==3.7.4
    pip install scispacy==0.5.4
    pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_core_sci_md-0.5.4.tar.gz
    pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.4/en_ner_bc5cdr_md-0.5.4.tar.gz
    pip install medspacy

Verify:
    python -c "import spacy; nlp=spacy.load('en_ner_bc5cdr_md'); print([(e.text,e.label_) for e in nlp('Take metformin 500 mg twice daily.').ents])"

Expect metformin tagged CHEMICAL. If the version numbers above have moved on,
check https://allenai.github.io/scispacy/ for the current release URLs rather
than guessing.

The gate runs WITHOUT scispaCy (regex core covers doses, frequencies, dates,
numbers). scispaCy only adds drug-name recognition, so do not let an install
problem block you.
