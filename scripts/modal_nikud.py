"""Point Tatoeba Hebrew sentences with DictaBERT menaked on Modal, keeping every source letter.

Run on residencehome:  modal run scripts/modal_nikud.py --limit 200 --out data/pilot.jsonl
limit 0 = the whole eligible pool. The model runs on Modal, never on the laptop.
"""
import json
import modal

MODEL = "dicta-il/dictabert-large-char-menaked"
REVISION = "4dfc20b94565d7868e1c8c00bf039d38c071a062"
BASE = "https://downloads.tatoeba.org/exports/per_language"

image = (
    modal.Image.debian_slim(python_version="3.11")
    .pip_install("torch==2.5.1", "transformers==4.46.3", "huggingface_hub==0.26.5")
    .run_commands(
        "python -c \"from huggingface_hub import snapshot_download as s; "
        f"s('{MODEL}', revision='{REVISION}')\""
    )
)
app = modal.App("gefilte-nikud", image=image)


def load_pool():
    """Eligible Hebrew sentences with their English translation and both authors."""
    import bz2, collections, csv, io, random, re, urllib.request

    def tsv(path):
        raw = urllib.request.urlopen(f"{BASE}/{path}", timeout=300).read()
        text = io.StringIO(bz2.decompress(raw).decode("utf8"), newline="\n")
        return csv.reader(text, delimiter="\t", quoting=csv.QUOTE_NONE)

    he = {r[0]: (r[2].strip(), r[3]) for r in tsv("heb/heb_sentences_detailed.tsv.bz2")}
    en = {r[0]: (r[2].strip(), r[3]) for r in tsv("eng/eng_sentences_detailed.tsv.bz2")}
    link = {}
    for r in tsv("heb/heb-eng_links.tsv.bz2"):
        if r[0] in he and r[1] in en:
            link.setdefault(r[0], r[1])
    ok = re.compile(r"^[א-ת\s,.\-–\"'׳״!:;]+$")  # no digits, Latin, nikud or questions
    tom = re.compile(r"(^|[\sהלבמשו])תום(\s|[.,!])")
    seen, rows, dropped = set(), [], collections.Counter()
    for sid, eid in link.items():
        t, author = he[sid]
        if not ok.match(t):
            dropped["characters"] += 1
        elif not 5 <= len(t.split()) <= 18:
            dropped["length"] += 1
        elif t[-1] not in ".!":
            dropped["end punctuation"] += 1
        elif t in seen:
            dropped["duplicate"] += 1
        elif tom.search(t):
            dropped["tom"] += 1
        else:
            seen.add(t)
            rows.append({"hebrew": t, "english": en[eid][0], "source_id": int(sid),
                         "source_author": author, "english_source_id": int(eid),
                         "english_author": en[eid][1]})
    random.Random(11).shuffle(rows)
    print("eligible", len(rows), "dropped", dict(dropped))
    return rows


@app.function(gpu="T4", timeout=3600)
def point(limit: int = 200, batch: int = 64):
    import re, time, torch
    from transformers import AutoModel, AutoTokenizer

    rows = load_pool()
    rows = rows[:limit] if limit else rows
    tok = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    model = AutoModel.from_pretrained(MODEL, revision=REVISION, trust_remote_code=True).eval().cuda()
    strip = lambda s: re.sub("[֑-ׇֽֿׁׂׅׄ]", "", s)
    t0, bad = time.time(), 0
    with torch.no_grad():
        for i in range(0, len(rows), batch):
            chunk = rows[i:i + batch]
            out = model.predict([r["hebrew"] for r in chunk], tok, mark_matres_lectionis="*")
            for r, p in zip(chunk, out):
                r["hebrew_nikud"] = p.replace("*", "")
                r["letters_match"] = strip(r["hebrew_nikud"]) == r["hebrew"]
                bad += not r["letters_match"]
    secs = time.time() - t0
    print(f"rows {len(rows)} letters_differ {bad} predict_sec {secs:.1f} per_row {secs/len(rows):.4f}")
    return rows


@app.local_entrypoint()
def main(limit: int = 200, out: str = "data/pilot.jsonl"):
    rows = point.remote(limit)
    with open(out, "w", encoding="utf8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("wrote", len(rows), out)
