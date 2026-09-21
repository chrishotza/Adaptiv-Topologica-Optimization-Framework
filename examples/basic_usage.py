import networkx as nx
from atof.selector import HeuristicRegimeSelector
from atof.strategies import BLOCReloc
from atof.topology import TopologyProfiler

def main():
    graph=nx.barabasi_albert_graph(100,3,seed=42)
    profile=TopologyProfiler().profile(graph)
    recommendation=HeuristicRegimeSelector().recommend(profile)
    print("Regime:",recommendation.regime)
    print("Suggested strategy:",recommendation.primary)
    print("Reason:",recommendation.rationale)
    result=BLOCReloc(graph,k=4,seed=42,variant="affinity").refine(iterations=10)
    print("Edge cut:",result.edge_cut)
    print("Weighted objective:",round(result.weighted_cost,6))
    print("Balance error:",round(result.balance_error,6))

if __name__=="__main__": main()
