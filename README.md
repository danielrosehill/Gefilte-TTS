# Gefilte TTS

A personal Hebrew text-to-speech voice built from a non-native speaker's reading of Hebrew. Work in progress.

## Pipeline

Tatoeba Hebrew sentences → nikud on Modal (`scripts/modal_nikud.py`) → `scripts/fix_vav.py` → `scripts/grade.py` → `scripts/publish_sentences.py`, to [`danielrosehill/Gefilte-Hebrew-Sentences`](https://huggingface.co/datasets/danielrosehill/Gefilte-Hebrew-Sentences). Data files stay out of git, on residencehome in `data/`. Recording happens in the capture app's Hebrew STT project.

`modal_nikud.py` writes vowels on the letter before a silent vav, so its output always goes through `fix_vav.py`.
