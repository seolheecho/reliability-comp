import pandas as pd

node_line_map = pd.read_csv("/Users/seolheec/Research/reliability-comp/large_scales/data3/Case 1/node_line_map.csv")

node_line_map = node_line_map.dropna(subset=["line"])
node_line_map["line"] = node_line_map["line"].astype(int)

line_to_node = (
    node_line_map[node_line_map["direction"] == "to"]
    .groupby("node")["line"]
    .apply(list)
    .to_dict()
)

line_fr_node = (
    node_line_map[node_line_map["direction"] == "fr"]
    .groupby("node")["line"]
    .apply(list)
    .to_dict()
)

NUM_NODES = 200
for n in range(1, NUM_NODES + 1):
    line_to_node.setdefault(n, [])
    line_fr_node.setdefault(n, [])


print(line_to_node)
