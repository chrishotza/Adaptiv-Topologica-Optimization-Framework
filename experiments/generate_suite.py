from __future__ import annotations

from pathlib import Path

import networkx as nx


def build_suite(seed: int = 42) -> dict[str, nx.Graph]:
    """Build a deterministic synthetic topology suite."""
    return {
        "path": nx.path_graph(64),
        "cycle": nx.cycle_graph(64),
        "grid": nx.convert_node_labels_to_integers(nx.grid_2d_graph(8, 8)),
        "erdos_renyi": nx.erdos_renyi_graph(64, 0.08, seed=seed),
        "barabasi_albert": nx.barabasi_albert_graph(64, 3, seed=seed),
        "watts_strogatz": nx.watts_strogatz_graph(64, 4, 0.15, seed=seed),
        "stochastic_block": nx.stochastic_block_model(
            [16, 16, 16, 16],
            [
                [0.25, 0.02, 0.02, 0.02],
                [0.02, 0.25, 0.02, 0.02],
                [0.02, 0.02, 0.25, 0.02],
                [0.02, 0.02, 0.02, 0.25],
            ],
            seed=seed,
        ),
    }


def save_edge_lists(output_dir: str | Path = "data/synthetic") -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for name, graph in build_suite().items():
        nx.write_edgelist(graph, output / f"{name}.edgelist", data=False)


if __name__ == "__main__":
    save_edge_lists()
    print("Synthetic topology suite written to data/synthetic/")
