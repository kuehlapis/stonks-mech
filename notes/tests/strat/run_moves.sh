for v in m_boost m_hop m_both e_far; do
  python sim/inproc.py --bot $v=sim/versions/$v/bot.py --count 1 --bot squad=sim/bots/squad.py --count 15 --matches 112 --jobs 14 --seed 1 --rotate --out notes/tests/strat/sq_$v.json > notes/tests/strat/sq_$v.log 2>&1
  python -c "import json;s=json.load(open('notes/tests/strat/sq_$v.json'))['summary'];print('$v',s.get('$v'))"
done
