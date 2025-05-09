from opcua import Server
import pandas as pd
import time

# Load CSV
df = pd.read_csv("machine-data.csv")

server = Server()
server.set_endpoint("opc.tcp://0.0.0.0:4840/")
idx = server.register_namespace("http://example.org")

root = server.get_objects_node()
asset = root.add_object(idx, "MachineA")

df = df.fillna(0)  # Handle any missing values
node_map = {}

for col in df.columns:
    if col.lower() != "sitetime":
        var_node = asset.add_variable(idx, col.strip(), float(df[col].iloc[0]))
        var_node.set_writable()
        node_map[col] = var_node

server.start()

try:
    for _, row in df.iterrows():
        for col, var_node in node_map.items():
            value = float(row[col])
            var_node.set_value(value)
        time.sleep(1)  # 1s between rows
finally:
    server.stop()