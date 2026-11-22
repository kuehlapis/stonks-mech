# 16-match paired strategy screener

Run a fast, no-bot-change strategy screen:

```powershell
python sim/screener.py --candidate c_aim --candidate b_rear --candidate m_boost --seed 11 --seeds 16 --jobs 4 --workers 1 --out notes/tests/paired-screen-latest.json
```

Or use `--workers 2` to run candidate arms concurrently. Candidate arms are
paired against `s_base2`; each uses seeds 11,000,000–11,000,015 in
`--rotate` slot order. The hard limit is 16 seeds. This is 32 raw matches per
candidate arm (16 candidate + 16 baseline), not a 56-match calibration batch.

Existing variants are allowed. A name containing `cover` or `ambush` is
blocked unless both:

- `notes/ideas/<name>-spec.md` exists (Builder interface/spec), and
- `notes/reviews/<name>-critic.md` exists (Critic approval).

The report includes score, paired score delta, kills, paired kill delta,
early-death share, direct and assisted squad-death causes, rear damage,
outside-zone ticks, act errors, late answers, mean/p99/max decision timing,
and wall time. It never rewrites `python/` or bot behavior.

A directory lock serializes match batches. Any `sim/inproc.py` run with
`--matches 56` or more (and every screener run) owns this lock, so a
calibration batch cannot overlap another batch. Lock timeout: 30 minutes.
