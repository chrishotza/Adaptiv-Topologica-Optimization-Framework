from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from atof.routing import FEATURE_ABLATIONS, LearnedTopologyRouter
from atof.statistics import bootstrap_mean_ci

RESAMPLES = 5000
BOOTSTRAP_SEED = 2024

def _mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0

def _regret(record, strategy):
    oracle = record['oracle_strategy']
    oracle_cut = float(record['strategy_means'][oracle])
    selected_cut = float(record['strategy_means'][strategy])
    return (selected_cut - oracle_cut) / oracle_cut if oracle_cut else 0.0

def _summary(values):
    values = list(values)
    low, high = bootstrap_mean_ci(values, resamples=RESAMPLES, seed=BOOTSTRAP_SEED)
    return {'graphs': len(values), 'mean_relative_regret': _mean(values), 'bootstrap_95_ci': [low, high]}

def _evaluate(records_by_corpus, features):
    values = []
    by_corpus = {}
    for heldout, test_records in sorted(records_by_corpus.items()):
        training = [r for corpus, rs in records_by_corpus.items() if corpus != heldout for r in rs]
        router = LearnedTopologyRouter(features=features, scale_mode='iqr', metric='l2').fit(training)
        fold = []
        for record in test_records:
            selected = router.predict(record['topology'])
            value = _regret(record, selected)
            values.append(value)
            fold.append(value)
        by_corpus[heldout] = _summary(fold)
    return _summary(values), by_corpus

def run(path: Path):
    payload = json.loads(path.read_text(encoding='utf-8'))
    if payload.get('k') != 8:
        raise AssertionError('expected k=8 benchmark')
    records_by_corpus = defaultdict(list)
    for record in payload.get('graph_manifest', []):
        records_by_corpus[str(record['corpus'])].append(record)
    if sum(len(v) for v in records_by_corpus.values()) != 20:
        raise AssertionError('expected 20 graph records')
    results = {}
    for name, features in FEATURE_ABLATIONS.items():
        overall, by_corpus = _evaluate(records_by_corpus, features)
        results[name] = {'features': list(features), 'overall': overall, 'by_corpus': by_corpus}
    return {
        'schema_version': '1.0',
        'protocol': 'k=8 cross-corpus routing feature ablation diagnostic; primary benchmark unchanged',
        'benchmark_commit': payload.get('commit_sha'),
        'primary_all_features': results['all'],
        'ablations': results,
        'interpretation_boundary': [
            'All-features remains the primary endpoint.',
            'Ablation results are post-hoc diagnostics on the same frozen solver outcomes.',
            'No ablation is promoted to production/default behavior by this analysis.',
        ],
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--benchmark', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.benchmark)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    ranked = sorted(result['ablations'].items(), key=lambda item: item[1]['overall']['mean_relative_regret'])
    print(json.dumps({name: data['overall'] for name, data in ranked}, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())