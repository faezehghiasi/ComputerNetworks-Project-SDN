#!/usr/bin/env python3

import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path

def save_graph(G, name, out_dir="outputs"):
    out = Path(out_dir)
    out.mkdir(exist_ok=True)
    labels = {n: "{}\nDeg:{}".format(n, d) for n, d in G.degree}
    nx.set_node_attributes(G, labels, name="label")
    diam = nx.diameter(G)
    fault_tol = nx.edge_connectivity(G)
    pos = nx.spring_layout(G, seed=42)
    plt.figure(figsize=(8,6))
    nx.draw_networkx_nodes(G, pos, node_size=800, node_color='lightblue')
    nx.draw_networkx_edges(G, pos)
    node_labels = nx.get_node_attributes(G, 'label')
    nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=8)
    plt.title("{}\nDiameter: {} | Fault Tolerance (lambda): {}".format(name, diam, fault_tol))
    plt.axis('off')
    png_path = out / (name + ".png")
    plt.savefig(str(png_path), bbox_inches='tight')
    plt.close()
    print("[+] Graph for {} -> {}".format(name, png_path))

def linear_graph(n=4):
    G = nx.path_graph(n)
    return G

def minimal_graph():
    G = nx.complete_graph(2)
    return G

def tree_graph(depth=2, fanout=2):
    return nx.balanced_tree(r=fanout, h=depth)

def torus_graph(m=3, n=3):
    return nx.grid_2d_graph(m, n, periodic=True)

def full_graph(n=5):
    return nx.complete_graph(n)

if __name__ == "__main__":
    save_graph(linear_graph(5), "Linear")
    save_graph(minimal_graph(), "Minimal")
    save_graph(tree_graph(2, 2), "Tree")
    save_graph(torus_graph(3, 3), "Torus")
    save_graph(full_graph(5), "Full")
