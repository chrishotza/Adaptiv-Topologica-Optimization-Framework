from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from atof.routing import LearnedTopologyRouter
from atof.statistics import bootstrap_mean_ci

FEATURES = (
    "density", "avg_degree", "degree_std", "hub_ratio", "degree_gini",
    "clustering", "transitivity", "core_number", "diameter",
    "avg_path_length", "modularity",
)
BOOTSTRAP_SEED = 2024
RESAMPLES = 5000

def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0

def _regret(record: dict, selected: str) -> float:
    oracle = record["oracle_strategy"]
    oracle_cut = float(record["strategy_means"][oracle])
    selected_cut = float(record["strategy_means"][selected])
    return (selected_cut - oracle_cut) / oracle_cut if oracle_cut else 0.0

def _predict(records_by_corpus: dict[str, list[dict]]) -> list[dict]:
    rows = []
    for heldout, test_records in sorted(records_by_corpus.items()):
        training = [
            record
            for corpus, corpus_records in records_by_corpus.items()
            if corpus != heldout
            for record in corpus_records
        ]
        router = LearnedTopologyRouter(features=FEATURES, scale_mode='iqr', metric='l2').fit(training)
        counts = Counter(record['oracle_strategy'] for record in training)
        majority = min(counts, key=lambda strategy: (-counts[strategy], strategy))
        for record in test_records:
            centroid = router.predict(record['topology'])
            rows.append({
                'graph_id': record['graph_id'],
                'corpus': heldout,
                'centroid': centroid,
                'majority': majority,
                'oracle': record['oracle_strategy'],
                'centroid_regret': _regret(record, centroid),
                'majority_regret': _regret(record, majority),
            })
    return rows

def _summary(rows: list[dict], key: str) -> dict:
    values = [float(row[key]) for row in rows]
    low, high = bootstrap_mean_ci(values, resamples=RESAMPLES, seed=BOOTSTRAP_SEED)
    return {'graphs': len(values), 'mean_relative_regret': _mean(values), 'bootstrap_95_ci': [low, high]}

def run(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding='utf-8'))
    if payload.get('k') != 8:
        raise AssertionError(f"expected k=8, got {payload.get('k')}")
    if len(payload.get('graph_manifest', [])) != 20:
        raise AssertionError('expected 20 graph records')
    records_by_corpus: dict[str, list[dict]] = defaultdict(list)
    for record in payload['graph_manifest']:
        records_by_corpus[str(record['corpus'])].append(record)
    rows = _predict(dict(records_by_corpus))
    global_summary = {
        'centroid': _summary(rows, 'centroid_regret'),
        'majority': _summary(rows, 'majority_regret'),
        'centroid_minus_majority_mean_relative_regret': _mean(
            row['centroid_regret'] - row['majority_regret'] for row in rows
        ),
    }
    by_corpus = {}
    for corpus in sorted(records_by_corpus):
        fold_rows = [row for row in rows if row['corpus'] == corpus]
        by_corpus[corpus] = {
            'centroid': _summary(fold_rows, 'centroid_regret'),
            'majority': _summary(fold_rows, 'majority_regret'),
            'graphs': [row['graph_id'] for row in fold_rows],
        }
    leave_out_corpus = {}
    for excluded in sorted(records_by_corpus):
        kept = [row for row in rows if row['corpus'] != excluded]
        leave_out_corpus[excluded] = _summary(kept, 'centroid_regret')
    outliers = sorted(
        ({'graph_id': row['graph_id'], 'corpus': row['corpus'], 'centroid': row['centroid'], 'oracle': row['oracle'], 'centroid_regret': row['centroid_regret']} for row in rows),
        key=lambda item: item['centroid_regret'],
        reverse=True,
    )[:5]
    return {
        'schema_version': '1.0',
        'protocol': 'k=8 routing diagnostic sensitivity; primary benchmark unchanged',
        'benchmark_commit': payload.get('commit_sha'),
        'graphs': len(rows),
        'global': global_summary,
        'by_corpus': by_corpus,
        'leave_out_corpus': leave_out_corpus,
        'top_outliers': outliers,
        'interpretation_boundary': [
            'The global k=8 benchmark remains the primary endpoint.',
            'Corpus-stratified and leave-one-corpus-out views are diagnostics, not selective replacement endpoints.',
            'No rows are removed from the primary benchmark.',
        ],
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--benchmark', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.benchmark)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result['global'], indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())