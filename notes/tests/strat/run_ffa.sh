for v in s_base s_hide s_search_on s_close s_duck30 s_picky; do
  python sim/inproc.py --bot $v=sim/versions/$v/bot.py --count 1 --bot hunter=sim/bots/hunter.py --count 4 --bot camper=sim/bots/camper.py --count 4 --bot rusher=sim/bots/rusher.py --count 4 --bot example=python/example_bot.py --count 3 --matches 112 --jobs 14 --seed 1 --rotate --out notes/tests/strat/ffa_$v.json > notes/tests/strat/ffa_$v.log 2>&1
  python -c "import json;s=json.load(open('notes/tests/strat/ffa_$v.json'))['summary'];print('$v',s.get('$v'))"
done
