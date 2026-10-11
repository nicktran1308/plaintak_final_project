from datasets import load_dataset
import json, pathlib

ds = load_dataset("cbasu/Med-EASi")
out = pathlib.Path("med-easi"); out.mkdir(exist_ok=True)
for split in ds:
    with open(out / f"{split}.jsonl", "w", encoding="utf-8") as f:
        for r in ds[split]:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(split, len(ds[split]))