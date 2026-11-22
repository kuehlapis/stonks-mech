$ErrorActionPreference = "Stop"

# 16 paired seeds, 32 raw matches per candidate/arm; seed 11, rotate.
# --workers parallelizes candidate arms; --jobs parallelizes matches within a sequential arm.
python sim/screener.py --candidate c_aim --candidate b_rear --candidate m_boost `
  --seed 11 --seeds 16 --jobs 4 --workers 2 `
  --out notes/tests/paired-screen-latest.json
