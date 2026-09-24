import json

from experiments.k8_routing_diagnostic import run

def test_k8_diagnostic_preserves_global_endpoint(tmp_path):
    path = tmp_path / 'benchmark.json'
    records = []
    for corpus in ('a', 'b'):
        for index in range(10):
            records.append({
                'graph_id': f'{corpus}/g{index}',
                'corpus': corpus,
                'topology': {
                    'density': float(index), 'avg_degree': 1.0, 'degree_std': 1.0,
                    'hub_ratio': 0.0, 'degree_gini': 0.0, 'clustering': 0.0,
                    'transitivity': 0.0, 'core_number': 1.0, 'diameter': 1.0,
                    'avg_path_length': 1.0, 'modularity': 0.0,
                },
                'oracle_strategy': 'bloc',
                'strategy_means': {'bloc': 10.0, 'metis': 12.0},
            })
    path.write_text(json.dumps({'k': 8, 'commit_sha': 'fixture', 'graph_manifest': records}), encoding='utf-8')
    result = run(path)
    assert result['graphs'] == 20
    assert result['global']['centroid']['graphs'] == 20
    assert set(result['by_corpus']) == {'a', 'b'}
    assert len(result['top_outliers']) == 5