for v in b_peek b_reload b_rear b_burn b_regen c_mortar b_regen_hide b_burn_quiet s_funnel s_zone_lean r_run r_run_end c_aim; do
  python sim/inproc.py --bot $v=sim/versions/$v/bot.py --count 1 --bot squad=sim/bots/squad.py --count 15 --matches 112 --jobs 14 --seed 1 --rotate --out notes/tests/strat/sq_$v.json > notes/tests/strat/sq_$v.log 2>&1
  python -c "import json;s=json.load(open('notes/tests/strat/sq_$v.json'))['summary'];print('$v',s.get('$v'))"
done
