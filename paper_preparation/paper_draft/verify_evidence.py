"""Read-only checks of saved evidence; no search, generation, or source mutation.

Run with the repository .venv Python (analysis dependencies already installed).
"""
from pathlib import Path
import hashlib
import json
import sys
import warnings

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'paper_preparation/scripts'))
import build_paper_tables_and_figures as prep


def main():
    warnings.filterwarnings('ignore', message='Mean of empty slice', category=RuntimeWarning)
    runs = pd.read_csv(prep.DATA / 'history/three_workers/search_comparison/search_runs.csv')
    base = pd.read_csv(prep.DATA / 'history/three_workers/reproduction/baseline_runs.csv')
    refs = pd.read_csv(ROOT / 'results/raw/optimal_costs.csv')
    report = prep.verify_raw(runs, base)
    old = json.loads((ROOT / 'paper_preparation/VALIDATION.json').read_text())
    for name, expected in old['source_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    df = prep.attach_references(runs, refs)
    q = prep.quality_table(df)
    prepared_q = pd.read_csv(ROOT / 'paper_preparation/tables/appendix/A4_quality.csv')
    pd.testing.assert_frame_equal(q[prepared_q.columns].reset_index(drop=True), prepared_q, check_dtype=False)
    pairs = prep.paired_vs_astar(df)
    pd.testing.assert_frame_equal(pairs, pd.read_csv(prep.DATA / 'history/three_workers/search_comparison/paired/paired_vs_astar.csv'), check_dtype=False)
    prepared_ida = pd.read_csv(ROOT / 'paper_preparation/tables/appendix/A7_ida_overhead.csv')
    pd.testing.assert_frame_equal(prep.ida_vs_astar(df)[prepared_ida.columns], prepared_ida, check_dtype=False)
    for h, expected in [('deepseek-r1', [64, 65, 70, 69, 24]), ('hmax', [19, 14, 15, 16, 7])]:
        for method, n in zip(prep.METHODS, expected):
            a = df[(df.heuristic_id == h) & (df.method == method)]
            assert a.solved.sum() == n
            assert len(a) == (30 if method == 'ida_star' else 90)
    assert runs.status.value_counts().to_dict() == {'timeout':404, 'success':363, 'memory_limit':13}
    assert refs.reference_status.value_counts().to_dict() == {'unknown_timeout':43,'not_requested':30,'proven':17}
    assert refs[refs.optimality_proven].difficulty.eq('easy').all()
    assert refs[refs.optimality_proven].groupby('domain').size().to_dict() == {'blocksworld':2,'miconic':10,'transport':5}
    assert refs[refs.optimality_proven].cross_check.value_counts().to_dict() == {'match':14,'ucs_only':3}
    assert (df.gap_pct.dropna() >= 0).all()
    init = runs[runs.initial_h.notna()].drop_duplicates(['domain','problem_id','heuristic_id'])[['domain','problem_id','heuristic_id','initial_h']]
    init = init.merge(refs[refs.optimality_proven][['domain','problem_id','optimal_cost']], on=['domain','problem_id'])
    r1 = init[init.heuristic_id == 'deepseek-r1']
    assert len(r1) == 17 and (r1.initial_h > r1.optimal_cost + 1e-9).sum() == 15
    assert np.isclose((r1.initial_h / r1.optimal_cost).median(), 1.1764705882352942)
    assert np.isclose((r1.initial_h / r1.optimal_cost).max(), 2.1)
    hm = init[init.heuristic_id == 'hmax']
    assert len(hm) == 17 and (hm.initial_h > hm.optimal_cost + 1e-9).sum() == 0
    # Saved hashes use canonical action names without a trailing newline.
    for row in runs[runs.solved].itertuples():
        plan = prep.RAW / 'plans' / f'{row.run_id}.soln'
        names = [s.strip() for s in plan.read_text().splitlines() if s.strip()]
        assert hashlib.sha256('\n'.join(names).encode()).hexdigest() == row.plan_sha256
    manifest = json.loads((ROOT / 'artifacts/upstream/deepseek-r1/provenance.json').read_text())
    for item in manifest['heuristics']:
        assert hashlib.sha256((ROOT / 'artifacts/upstream/deepseek-r1' / item['filename']).read_bytes()).hexdigest() == item['sha256']
    # These are absence checks, not an assertion that experiments never ran elsewhere.
    assert not list((prep.RAW / 'batches').glob('m3-*.json'))
    assert pd.read_csv(ROOT / 'paper_preparation/tables/appendix/T4_independent_trials_PENDING.csv').empty
    report.update({
        'audit_date':'2026-11-18',
        'source_hashes_match_preparation':True,
        'matched_plan_hashes_checked':363,
        'quality_and_pairs_recomputed':True,
        'proven_reference_count':17,
        'reference_status_counts':refs.reference_status.value_counts().to_dict(),
        'llm_initial_overestimates':15,
        'hmax_initial_overestimates':0,
        'new_trial_batches_found':0,
        'pending_trial_table_observations':0,
        'new_planner_runs':0,
        'source_sha256':old['source_sha256'],
    })
    (HERE / 'EVIDENCE_CHECKS.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'source_sha256'}, indent=2))


if __name__ == '__main__':
    main()
