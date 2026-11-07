"""Move vowels that sit on the letter before a bare vav onto the vav. String work only.

Full run, 2026-11-07: 24.6% of rows spelled holam male and shuruq as a vowel on the previous letter plus an unpointed vav
(לִלְמֹוד, כֻּולָּם). Rules, only where the vav has no point of its own:
  holam, hataf qamats or qamats qatan + vav  ->  vav with holam   (לִלְמוֹד)
  qubuts + vav                               ->  vav with dagesh  (כּוּלָּם)
A vav with its own vowel is consonantal and stays (לֹוֶה), as does the doubled vav of full spelling (מְקַוֶּוה).
The original is kept as `hebrew_nikud_raw`; the Hebrew letters must not change.

  python3 scripts/fix_vav.py data/graded.jsonl data/graded.fixed.jsonl
"""
import json, re, sys

POINTS = "ְ-ׇֽֿׁׂ"
MARKS = "[ּׁׂ]*"  # dagesh and shin/sin dots stay on their letter
HOLAM2 = re.compile(f"({MARKS})[ֳׇֹ]({MARKS})ו(?![{POINTS}])")
SHURUQ = re.compile(f"({MARKS})ֻ({MARKS})ו(?![{POINTS}])")
LETTERS = re.compile("[^א-ת]")


def fix(s):
    s = HOLAM2.sub(lambda m: f"{m[1]}{m[2]}וֹ", s)
    return SHURUQ.sub(lambda m: f"{m[1]}{m[2]}וּ", s)


def main(src, dst):
    n = changed = 0
    with open(src, encoding="utf8") as f, open(dst, "w", encoding="utf8") as o:
        for line in f:
            r = json.loads(line)
            new = fix(r["hebrew_nikud"])
            assert LETTERS.sub("", new) == LETTERS.sub("", r["hebrew_nikud"]), r["source_id"]
            n += 1
            changed += new != r["hebrew_nikud"]
            r["hebrew_nikud_raw"], r["hebrew_nikud"] = r["hebrew_nikud"], new
            o.write(json.dumps(r, ensure_ascii=False) + "\n")
    print({"rows": n, "changed": changed})


if __name__ == "__main__":
    main(*sys.argv[1:3])
