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
    all_runs = pd.read_csv(prep.DATA / 'search_comparison/search_runs.csv')
    base = pd.read_csv(prep.DATA / 'reproduction/baseline_runs.csv')
    refs = pd.read_csv(ROOT / 'results/raw/optimal_costs.csv')
    report = prep.verify_raw(all_runs, base) or {}
    old = json.loads((ROOT / 'paper_preparation/VALIDATION.json').read_text())
    for name, expected in old['source_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    runs = all_runs[all_runs.heuristic_id != 'hff'].reset_index(drop=True)
    df = prep.attach_references(runs, refs)
    q = prep.quality_table(df)
    prepared_q = pd.read_csv(ROOT / 'paper_preparation/tables/appendix/A4_quality.csv')
    pd.testing.assert_frame_equal(q[prepared_q.columns].reset_index(drop=True), prepared_q, check_dtype=False)
    pairs = prep.paired_vs_astar(df)
    committed_pairs = pd.read_csv(prep.DATA / 'search_comparison/paired/paired_vs_astar.csv')
    pd.testing.assert_frame_equal(pairs, committed_pairs[committed_pairs.heuristic != 'hff'].reset_index(drop=True), check_dtype=False)
    prepared_ida = pd.read_csv(ROOT / 'paper_preparation/tables/appendix/A7_ida_overhead.csv')
    pd.testing.assert_frame_equal(prep.ida_vs_astar(df)[prepared_ida.columns], prepared_ida, check_dtype=False)
    # Coverage quoted in the abstract, Section 5 and Table 1 (final 8-worker runs).
    for h, expected in [('deepseek-r1', [62, 63, 67, 67, 23]), ('hmax', [19, 13, 14, 15, 7])]:
        for method, n in zip(prep.METHODS, expected):
            a = df[(df.heuristic_id == h) & (df.method == method)]
            assert a.solved.sum() == n, (h, method, a.solved.sum())
            assert len(a) == (30 if method == 'ida_star' else 90)
    assert base.groupby('heuristic').solved.sum().to_dict() == {'hff': 37, 'hmax': 19, 'llm-r1': 62}
    assert runs.status.value_counts().to_dict() == {'timeout': 430, 'success': 350}
    assert refs.reference_status.value_counts().to_dict() == {'unknown_timeout': 43, 'not_requested': 30, 'proven': 17}
    assert refs[refs.optimality_proven].difficulty.eq('easy').all()
    assert refs[refs.optimality_proven].groupby('domain').size().to_dict() == {'blocksworld': 2, 'miconic': 10, 'transport': 5}
    assert refs[refs.optimality_proven].cross_check.value_counts().to_dict() == {'match': 14, 'ucs_only': 3}
    assert (df.gap_pct.dropna() >= 0).all()
    init = runs[runs.initial_h.notna()].drop_duplicates(['domain', 'problem_id', 'heuristic_id'])[['domain', 'problem_id', 'heuristic_id', 'initial_h']]
    init = init.merge(refs[refs.optimality_proven][['domain', 'problem_id', 'optimal_cost']], on=['domain', 'problem_id'])
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
    # Heuristic-reliability numbers quoted in Section 5.3 and Appendix G.
    m3 = ROOT / 'results/derived/heuristic_reliability'
    trial_runs = pd.read_csv(m3 / 'trial_heuristic_runs.csv')
    assert len(trial_runs) == 1170
    stability = pd.read_csv(m3 / 'trial_stability_summary.csv')
    stability = stability[stability.scope == 'all'].set_index('algorithm')
    expected = {'gbfs': (64, 67, 73, 68.0, 4.58, 62), 'astar': (55, 51, 74, 60.0, 12.29, 63),
                'weighted_astar-w1.5': (68, 64, 74, 68.67, 5.03, 67), 'weighted_astar-w2': (69, 67, 74, 70.0, 3.61, 67),
                'ida_star': (30, 25, 23, 26.0, 3.61, 23)}
    for algorithm, (t1, t2, t3, mean, sd, archived) in expected.items():
        row = stability.loc[algorithm]
        assert (row.trial_01, row.trial_02, row.trial_03, row.archived) == (t1, t2, t3, archived), algorithm
        assert np.isclose(row['mean'], mean) and np.isclose(row.sd_ddof1, sd), algorithm
    over = pd.read_csv(m3 / 'overestimation_summary.csv').set_index(['domain', 'heuristic_trial_id'])
    assert over.sampled_states.groupby('heuristic_trial_id').sum().eq(345).all()
    assert over.eligible_states.groupby('heuristic_trial_id').sum().eq(305).all()
    rates = {('blocksworld', 'archived'): .619, ('miconic', 'archived'): .9243, ('transport', 'archived'): .5,
             ('miconic', 'trial-01'): 0.0, ('miconic', 'trial-02'): 0.0, ('miconic', 'trial-03'): .9892,
             ('transport', 'trial-01'): 1.0, ('transport', 'trial-03'): 1.0}
    for key, rate in rates.items():
        assert np.isclose(over.loc[key, 'overestimate_rate'], rate), key
    assert over.loc[('transport', 'trial-03'), 'max_overestimate'] == 400005
    candidates = pd.read_csv(m3 / 'overestimation_all_candidates.csv')
    never = candidates[candidates.overestimate_rate == 0]
    assert len(candidates) == 90 and len(never) == 40
    assert never.groupby('domain').size().reindex(['blocksworld', 'miconic', 'transport'], fill_value=0).tolist() == [20, 20, 0]
    assert never.selected.sum() == 2
    report.update({
        'audit_date': '2026-11-23',
        'workers': 8,
        'source_hashes_match_preparation': True,
        'matched_plan_hashes_checked': int(runs.solved.sum()),
        'quality_and_pairs_recomputed': True,
        'proven_reference_count': 17,
        'reference_status_counts': refs.reference_status.value_counts().to_dict(),
        'llm_initial_overestimates': 15,
        'hmax_initial_overestimates': 0,
        'trial_runs': int(len(trial_runs)),
        'sampled_states': 345,
        'sampled_states_with_proven_h_star': 305,
        'new_planner_runs': 0,
        'source_sha256': old['source_sha256'],
    })
    (HERE / 'EVIDENCE_CHECKS.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'source_sha256'}, indent=2))


if __name__ == '__main__':
    main()
