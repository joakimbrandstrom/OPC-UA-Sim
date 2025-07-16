from opcua import Server
import pandas as pd
import time
import os

# Path to the CSV file
csv_file = "machine-data.csv"

# Check if the CSV file exists
if not os.path.exists(csv_file):
    print(f"Error: The file '{csv_file}' was not found.")
    exit()

# Load CSV
df = pd.read_csv(csv_file)

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
print("Server started")

try:
    while True:
        df = pd.read_csv(csv_file)
        df = df.fillna(0)  # Handle any missing values

        for _, row in df.iterrows():
            for col, var_node in node_map.items():
                if col.lower() != "sitetime":
                    value = float(row[col])
                    var_node.set_value(value)
            time.sleep(1)  # 1s between rows

        print("CSV data processed. Waiting for 10 seconds before the next cycle.")
        time.sleep(10)

except KeyboardInterrupt:
    print("Server stopped")
finally:
    server.stop()