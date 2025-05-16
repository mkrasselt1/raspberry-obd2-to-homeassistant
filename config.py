import json

CONFIG_FILE = "config.json"

def load_config(filename=CONFIG_FILE):
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Configuration file '{filename}' not found. Exiting...")
        exit(1)
