import csv
import os

def load_pids_from_folder(folder_path):
    """Load PID definitions from all CSV files in a folder."""
    pid_list = {}
    try:
        for file_name in os.listdir(folder_path):
            if file_name.endswith(".csv"):
                file_path = os.path.join(folder_path, file_name)
                print(f"Loading PIDs from {file_path}...")
                with open(file_path, mode="r") as csv_file:
                    csv_reader = csv.DictReader(csv_file)
                    for row in csv_reader:
                        mode = row["Mode"]
                        pid = row["PID"]
                        name = row["Name"]
                        unit = row["Unit"]
                        mqtt_id = row["MQTT_ID"]

                        if mode not in pid_list:
                            pid_list[mode] = {}
                        pid_list[mode][pid] = {
                            "name": name,
                            "unit": unit,
                            "mqtt_id": mqtt_id
                        }
    except Exception as e:
        print(f"Failed to load PIDs: {e}")
        exit(1)
    return pid_list
