"""Publish the pointed sentence bank to danielrosehill/Gefilte-Hebrew-Sentences, tabs `sentences` and `takes`.

  with-secrets uv run --no-project --with pyarrow --with huggingface_hub python3 scripts/publish_sentences.py data/graded.fixed.jsonl

The `takes` tab fills from the capture app (Voice-Training-Recorder, mode `hebrew`, publishHebrew in app/api/publish.js).
A sentence id is he_ plus the sha1 of the unpointed Hebrew. About 2% go to test, by hash. Rerun only rewrites `sentences/`.
"""
import hashlib, io, json, os, sys
import pyarrow as pa, pyarrow.parquet as pq
from huggingface_hub import HfApi, CommitOperationAdd

REPO = "danielrosehill/Gefilte-Hebrew-Sentences"
CARD = """---
license: cc-by-2.0
language:
- he
- en
task_categories:
- automatic-speech-recognition
- text-to-speech
pretty_name: Gefilte Hebrew Sentences
tags:
- hebrew
- nikud
- non-native-speech
- accented-speech
size_categories:
- 10K<n<100K
configs:
- config_name: sentences
  default: true
  data_files:
  - split: train
    path: sentences/train.parquet
  - split: test
    path: sentences/test.parquet
- config_name: takes
  data_files:
  - split: train
    path: data/train-*.parquet
  - split: test
    path: data/test-*.parquet
---
# Gefilte Hebrew Sentences

Modern, everyday Hebrew sentences with nikud and an English translation, graded 1 to 5 by how hard they are to read aloud for a
non-native speaker, plus recordings of them.

**Why it exists.** Most Hebrew speech data comes from native speakers. This set is for a personal model of one immigrant's Hebrew:
accented, with imperfect pronunciation. That speech is part of everyday Hebrew too. The nikud is there so the reader can get the
vowels right, and the grades let him work up from the easy sentences. The model it feeds is **Gefilte**.

## Tabs

| Tab | Rows |
| --- | --- |
| `sentences` | {rows} sentences, with `takes` = 0 until read. |
| `takes` | One row per recording, joined on `sentence_id`. Empty until the first push. |

## Columns (`sentences`)

`id`, `text` (Hebrew without nikud), `text_nikud`, `english`, `difficulty` (1 easiest to 5), `difficulty_score`, `syllables`, `split`,
`takes`, `tatoeba_id`, `tatoeba_author`, `english_tatoeba_id`, `english_author`.

## How it was made

- **Sentences and translations:** [Tatoeba](https://tatoeba.org), Hebrew sentences with an English link. Long sentences, unusual
  characters and the repetitive "Tom" sentences were dropped.
- **Nikud:** machine-made with [`dicta-il/dictabert-large-char-menaked`](https://huggingface.co/dicta-il/dictabert-large-char-menaked)
  (CC BY 4.0), then a string fix that moves holam and shuruq onto the vav. It is **not checked by a human**, so expect some wrong vowels.
- **Grades:** a script, not a person: length, syllables, rare words and sounds that are hard from an English start. The five grades
  are equal fifths of this set, so they rank sentences against each other.

## Licence and attribution

Tatoeba sentences are [CC BY 2.0 FR](https://tatoeba.org/en/terms_of_use). Each row names its Tatoeba id and author. A row's author may be
`\\\\N` where Tatoeba lists none. Recordings are by Daniel Rosehill.
"""


def main(src):
    rows = [json.loads(l) for l in open(src, encoding="utf8")]
    out = {"train": [], "test": []}
    for r in rows:
        h = hashlib.sha1(r["hebrew"].encode()).hexdigest()
        split = "test" if int(h[:8], 16) % 50 == 0 else "train"
        out[split].append({"id": "he_" + h[:12], "text": r["hebrew"], "text_nikud": r["hebrew_nikud"], "english": r["english"],
            "difficulty": int(r["difficulty"]), "difficulty_score": float(r["difficulty_score"]), "syllables": int(r["syllables"]), "split": split,
            "takes": 0, "tatoeba_id": str(r["source_id"]), "tatoeba_author": r["source_author"],
            "english_tatoeba_id": str(r["english_source_id"]), "english_author": r["english_author"]})
    assert len({x["id"] for v in out.values() for x in v}) == len(rows), "id collision"
    ops = []
    for split, v in out.items():
        b = io.BytesIO(); pq.write_table(pa.Table.from_pylist(v), b)
        ops.append(CommitOperationAdd(f"sentences/{split}.parquet", b.getvalue()))
    S = "string"
    cols = [["id", S], ["sentence_id", S], ["text", S], ["text_nikud", S], ["english", S], ["difficulty", "int64"], ["prompt_id", S], ["prompt_set", S],
            ["tatoeba_id", S], ["tatoeba_author", S], ["english_tatoeba_id", S], ["english_author", S], ["duration_s", "float64"], ["speaker", S], ["speaker_id", S],
            ["speaker_gender", S], ["room", S], ["environment", S], ["conditions", "list<string>"], ["noise_flags", "list<string>"], ["noise_level", S],
            ["background_speech_languages", "list<string>"], ["sample_rate", "int64"], ["bit_depth", "int64"], ["audio_format", S], ["device", S], ["microphone", S], ["recorded_at", S]]
    ops.append(CommitOperationAdd("meta/schema.json", json.dumps({"version": 1, "columns": cols}, indent=1).encode()))
    ops.append(CommitOperationAdd("meta/train.jsonl", b"")); ops.append(CommitOperationAdd("meta/test.jsonl", b""))
    ops.append(CommitOperationAdd("README.md", CARD.replace("{rows}", f"{len(rows):,}").encode()))
    api = HfApi(token=os.environ["HF_TOKEN"])
    api.create_repo(REPO, repo_type="dataset", private=False, exist_ok=True)
    c = api.create_commit(REPO, repo_type="dataset", operations=ops, commit_message="Sentence bank: Tatoeba Hebrew with nikud, translations and grades")
    print({k: len(v) for k, v in out.items()}, c.commit_url)


if __name__ == "__main__":
    main(sys.argv[1])
