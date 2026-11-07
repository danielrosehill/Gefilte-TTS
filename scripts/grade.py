"""Grade pointed Hebrew sentences 1 (easiest) to 5 for a non-native reader. No model, string maths only.

The score mixes sentence length, syllables, rare words, long words and sounds that are hard from an English
start: word-initial shva clusters, chataf vowels, and the gutturals chet, ayin and resh. Grades are quintiles
of the score, so each level holds about a fifth of the bank.

    python3 scripts/grade.py data/points.jsonl data/graded.jsonl
"""
import collections, json, math, re, statistics, sys

VOWEL = re.compile("[ֱ-ׇֻ]|וּ(?![ְ-ׇֻ])")
CHATAF = re.compile("[ֱ-ֳ]")
INITIAL_SHVA = re.compile(r"(?:^|\s)[א-ת][ּׁׂ]*ְ")
GUTTURAL = re.compile("[חער]")
LETTERS = re.compile("[^א-ת]")
WEIGHTS = {"syllables": 1.0, "rarity": 1.3, "long_words": 0.7, "clusters": 0.7, "chataf": 0.4, "gutturals": 0.5}


def words(s):
    return [w for w in (LETTERS.sub("", x) for x in s.split()) if w]


def features(row, freq, total):
    p, ws = row["hebrew_nikud"], words(row["hebrew"])
    rare = sorted((-math.log(freq[w] / total) for w in ws), reverse=True)[:3]
    per_word = [len(VOWEL.findall(x)) for x in p.split()]
    return {"syllables": len(VOWEL.findall(p)), "rarity": sum(rare) / len(rare),
            "long_words": sum(n >= 4 for n in per_word), "clusters": len(INITIAL_SHVA.findall(p)),
            "chataf": len(CHATAF.findall(p)), "gutturals": len(GUTTURAL.findall(row["hebrew"])) / len(ws)}


def main(src, dst):
    rows = [json.loads(l) for l in open(src, encoding="utf8")]
    freq = collections.Counter(w for r in rows for w in words(r["hebrew"]))
    total = sum(freq.values())
    feats = [features(r, freq, total) for r in rows]
    stats = {k: (statistics.mean(f[k] for f in feats), statistics.pstdev(f[k] for f in feats) or 1) for k in WEIGHTS}
    scores = [sum(w * (f[k] - stats[k][0]) / stats[k][1] for k, w in WEIGHTS.items()) for f in feats]
    order = sorted(range(len(rows)), key=scores.__getitem__)
    for rank, i in enumerate(order):
        rows[i]["difficulty"] = rank * 5 // len(rows) + 1
        rows[i]["difficulty_score"] = round(scores[i], 3)
        rows[i]["syllables"] = feats[i]["syllables"]
    with open(dst, "w", encoding="utf8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("graded", len(rows), collections.Counter(r["difficulty"] for r in rows))


if __name__ == "__main__":
    main(*sys.argv[1:3])
