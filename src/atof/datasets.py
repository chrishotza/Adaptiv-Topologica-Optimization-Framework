from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import networkx as nx


@dataclass(frozen=True)
class GraphDataset:
    """A named reference graph with explicit provenance metadata."""

    name: str
    source: str
    reference_url: str
    loader: Callable[[], nx.Graph]
    notes: str = ""

    def load(self) -> nx.Graph:
        """Load and normalize the graph to a simple undirected graph."""
        graph = self.loader()
        if graph.is_directed():
            graph = graph.to_undirected()
        if isinstance(graph, (nx.MultiGraph, nx.MultiDiGraph)):
            graph = nx.Graph(graph)
        else:
            graph = nx.Graph(graph)
        graph.remove_edges_from(nx.selfloop_edges(graph))
        return nx.convert_node_labels_to_integers(graph, ordering="default")


def standard_reference_corpus() -> tuple[GraphDataset, ...]:
    """Return small, documented empirical reference graphs shipped by NetworkX."""
    return (
        GraphDataset(
            name="karate_club",
            source="Zachary (1977), exposed by NetworkX",
            reference_url="https://networkx.org/documentation/stable/reference/generated/networkx.generators.social.karate_club_graph.html",
            loader=nx.karate_club_graph,
            notes="Small empirical social network; node attribute club is not used by the benchmark.",
        ),
        GraphDataset(
            name="davis_southern_women",
            source="Davis (1941), exposed by NetworkX",
            reference_url="https://networkx.org/documentation/stable/reference/generated/networkx.generators.social.davis_southern_women_graph.html",
            loader=nx.davis_southern_women_graph,
            notes="Empirical bipartite social network; benchmark uses the undirected one-mode edge structure as provided.",
        ),
        GraphDataset(
            name="florentine_families",
            source="Padgett/Ansell family network, exposed by NetworkX",
            reference_url="https://networkx.org/documentation/stable/reference/generated/networkx.generators.social.florentine_families_graph.html",
            loader=nx.florentine_families_graph,
            notes="Historical family relationship network.",
        ),
        GraphDataset(
            name="les_miserables",
            source="Character coappearance network, exposed by NetworkX",
            reference_url="https://networkx.org/documentation/stable/reference/generated/networkx.generators.social.les_miserables_graph.html",
            loader=nx.les_miserables_graph,
            notes="Character coappearance network; edge weights are intentionally ignored for the unweighted benchmark metric.",
        ),
    )
