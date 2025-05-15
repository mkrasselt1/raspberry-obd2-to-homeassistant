import json

CONFIG_FILE = "config.json"

def load_config():
    try:
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        print(f"Configuration file '{CONFIG_FILE}' not found. Exiting...")
        exit(1)
