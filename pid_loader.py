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
                    # CSV files without headers; define the column order manually
                    csv_reader = csv.reader(csv_file)
                    for row in csv_reader:
                        # Assign values from columns
                        pid_id = row[0]       # Column 0: id
                        name = row[1]         # Column 1: name
                        pid = row[2]          # Column 2: pid
                        equation = row[3]     # Column 3: equation
                        min_value = row[4]    # Column 4: min
                        max_value = row[5]    # Column 5: max
                        unit = row[6]         # Column 6: unit
                        filter_value = row[7] # Column 7: filter

                        # Add the PID to the dictionary
                        if pid_id not in pid_list:
                            pid_list[pid] = {}

                        pid_list[pid][pid_id] = {
                            "name": name,
                            "equation": equation,
                            "min": min_value,
                            "max": max_value,
                            "unit": unit,
                            "filter": filter_value,
                            "pid_id": pid_id
                        }
    except Exception as e:
        print(f"Failed to load PIDs: {e}")
        exit(1)
    return pid_list
