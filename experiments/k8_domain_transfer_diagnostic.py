from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from atof.routing import LearnedTopologyRouter, NearestTopologyRouter
from atof.statistics import bootstrap_mean_ci

FEATURES = (
    "density", "avg_degree", "degree_std", "hub_ratio", "degree_gini",
    "clustering", "transitivity", "core_number", "diameter",
    "avg_path_length", "modularity",
)
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

def _loo_by_corpus(records_by_corpus, router_cls):
    by_corpus = {}
    all_values = []
    for corpus, records in sorted(records_by_corpus.items()):
        values = []
        for heldout in records:
            training = [record for record in records if record is not heldout]
            router = router_cls(features=FEATURES, scale_mode='iqr', metric='l2').fit(training)
            selected = router.predict(heldout['topology'])
            values.append(_regret(heldout, selected))
        by_corpus[corpus] = _summary(values)
        all_values.extend(values)
    return _summary(all_values), by_corpus

def run(path: Path):
    payload = json.loads(path.read_text(encoding='utf-8'))
    if payload.get('k') != 8:
        raise AssertionError('expected k=8 benchmark')
    manifest = payload.get('graph_manifest', [])
    if len(manifest) != 20:
        raise AssertionError('expected 20 graph records')
    records_by_corpus = defaultdict(list)
    for record in manifest:
        records_by_corpus[str(record['corpus'])].append(record)
    centroid, centroid_by_corpus = _loo_by_corpus(records_by_corpus, LearnedTopologyRouter)
    nearest, nearest_by_corpus = _loo_by_corpus(records_by_corpus, NearestTopologyRouter)
    cross = float(payload['evaluation']['macro']['centroid_mean_relative_regret'])
    return {
        'schema_version': '1.0',
        'protocol': 'k=8 within-corpus leave-one-graph-out diagnostic',
        'benchmark_commit': payload.get('commit_sha'),
        'cross_corpus_primary_centroid_mean_relative_regret': cross,
        'within_corpus': {'centroid': centroid, 'nearest': nearest},
        'within_corpus_by_corpus': {'centroid': centroid_by_corpus, 'nearest': nearest_by_corpus},
        'within_minus_cross_centroid': centroid['mean_relative_regret'] - cross,
        'interpretation_boundary': [
            'The cross-corpus 20-graph benchmark remains the primary endpoint.',
            'Within-corpus LOO is a diagnostic of domain-local transfer using the same frozen graph outcomes.',
            'Small corpus sizes, especially 3-4 graphs, make per-corpus estimates exploratory.',
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
    print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())