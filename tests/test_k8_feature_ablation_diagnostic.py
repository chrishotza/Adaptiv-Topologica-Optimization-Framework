import json

from experiments.k8_feature_ablation_diagnostic import run

def test_k8_feature_ablation_diagnostic(tmp_path):
    records = []
    strategies = ['bloc', 'metis']
    for corpus in ('a', 'b'):
        for i in range(10):
            records.append({
                'graph_id': f'{corpus}/g{i}',
                'corpus': corpus,
                'topology': {
                    'density': float(i), 'avg_degree': 1.0, 'degree_std': 1.0,
                    'hub_ratio': 1.0, 'degree_gini': 0.0, 'clustering': 0.0,
                    'transitivity': 0.0, 'core_number': 1.0, 'diameter': 1.0,
                    'avg_path_length': 1.0, 'modularity': 0.0,
                },
                'oracle_strategy': strategies[i % 2],
                'strategy_means': {'bloc': 10.0, 'metis': 11.0},
            })
    path = tmp_path / 'benchmark.json'
    path.write_text(json.dumps({'k': 8, 'commit_sha': 'fixture', 'graph_manifest': records}), encoding='utf-8')
    result = run(path)
    assert 'all' in result['ablations']
    assert result['primary_all_features']['overall']['graphs'] == 20
    assert len(result['ablations']) >= 7