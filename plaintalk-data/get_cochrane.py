"""
Cochrane paragraph-level simplification (Devaraj et al., NAACL 2021).

The HuggingFace repo GEM/cochrane-simplification uses a loading script, which
newer `datasets` versions no longer support, so we pull the line-aligned split
files straight from the authors' GitHub instead.
"""
import json, pathlib, urllib.request

BASE = ("https://raw.githubusercontent.com/AshOlogn/"
        "Paragraph-level-Simplification-of-Medical-Texts/main/data/data-1024")

out = pathlib.Path("cochrane"); out.mkdir(exist_ok=True)

def get(url):
    with urllib.request.urlopen(url) as r:
        return r.read().decode("utf-8").splitlines()

for split, name in [("train", "train"), ("val", "validation"), ("test", "test")]:
    src = get(f"{BASE}/{split}.source")
    tgt = get(f"{BASE}/{split}.target")
    doi = get(f"{BASE}/{split}.doi")
    assert len(src) == len(tgt) == len(doi), f"{split}: length mismatch"

    with open(out / f"{name}.jsonl", "w", encoding="utf-8") as f:
        for i, (s, t, d) in enumerate(zip(src, tgt, doi)):
            f.write(json.dumps({
                "gem_id": f"cochrane-{name}-{i}",
                "doi": d.strip(),
                "source": s.strip(),
                "target": t.strip(),
            }, ensure_ascii=False) + "\n")
    print(f"{name}: {len(src)}")