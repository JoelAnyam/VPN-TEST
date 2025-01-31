import os
import subprocess
import csv
import matplotlib.pyplot as plt
from datetime import datetime
import threading
import pandas as pd
import numpy as np

# Constants for the testing environment
SERVER_IP = "{SERVER_IP}"  # Replace with your server's IP
NETWORK_INTERFACE = "{NETWORK_INTERFACE}"  # Replace with your network interface
RESULTS_FILE = "vpn_test_results.csv"

# Test scenarios
SCENARIOS = ["baseline", "file_transfer", "mixed_workload", "high_latency"]

# Commands for different metrics and actions
COMMANDS = {
    "throughput_tcp": f"iperf3 -c {SERVER_IP} -p 5201 -t 10",
    "throughput_udp": f"iperf3 -c {SERVER_IP} -p 5201 -u -b 0 -t 10",
    "latency": f"ping -c 10 {SERVER_IP}",
    "file_transfer_upload": f"scp /path/to/local/file user@{SERVER_IP}:/path/to/remote/destination",
    "file_transfer_download": f"scp user@{SERVER_IP}:/path/to/remote/file /path/to/local/destination",
    "video_streaming": f"ffplay http://{SERVER_IP}/path/to/video -loglevel quiet",
}


# Helper function to execute a shell command
def run_command(command):
    try:
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        print(f"Command: {command}\nOutput:\n{result.stdout}\nError:\n{result.stderr}")
        return result.stdout.strip()
    except Exception as e:
        print(f"Error executing {command}: {e}")
        return None


# Function to parse throughput from iperf3 output
def parse_iperf3_output(output):
    try:
        lines = output.split("\n")
        for line in reversed(lines):
            if "receiver" in line:
                parts = line.split()
                return float(parts[6])  # Extract throughput value
    except Exception as e:
        print(f"Error parsing iperf3 output: {e}")
    return None


# Function to parse ping results
def parse_ping(output):
    try:
        lines = output.split("\n")
        for line in lines:
            if "min/avg/max" in line:
                values = line.split("=")[1].strip().split("/")
                avg_latency = float(values[1])  # Average latency
                jitter = float(values[2]) - float(values[1])  # Jitter = max - avg
                return avg_latency, jitter
    except Exception as e:
        print(f"Error parsing ping output: {e}")
    return None, None


# Function to simulate network conditions
def simulate_network_conditions(latency=0, loss=0):
    run_command(f"sudo tc qdisc add dev {NETWORK_INTERFACE} root netem delay {latency}ms loss {loss}%")


# Function to reset network conditions
def reset_network_conditions():
    run_command(f"sudo tc qdisc del dev {NETWORK_INTERFACE} root netem")


# Function to log results with invalid data handling
def log_results(scenario, metric, value):
    if value is None or isinstance(value, str) and not value.replace(".", "", 1).isdigit():
        print(f"?? Skipping invalid data: Scenario={scenario}, Metric={metric}, Value={value}")
        value = np.nan  # Replace invalid values with NaN

    print(f"? Logging: Scenario={scenario}, Metric={metric}, Value={value}")
    
    with open(RESULTS_FILE, mode="a") as file:
        writer = csv.writer(file)
        writer.writerow([datetime.now(), scenario, metric, value])


# Function to run mixed workload tasks concurrently
def run_mixed_workload():
    tasks = {
        "file_transfer_upload": lambda: run_command(COMMANDS["file_transfer_upload"]),
        "file_transfer_download": lambda: run_command(COMMANDS["file_transfer_download"]),
        "video_streaming": lambda: run_command(COMMANDS["video_streaming"]),
        "throughput_tcp": lambda: run_command(COMMANDS["throughput_tcp"]),
    }

    threads = []
    results = {}

    for name, task in tasks.items():
        def task_wrapper(task_name=name, task_func=task):
            result = task_func()
            results[task_name] = result

        thread = threading.Thread(target=task_wrapper, daemon=True)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join(timeout=30)  
        if thread.is_alive():
            print(f"?? Thread {thread.name} did not finish in time.")

    for name, result in results.items():
        log_results("mixed_workload", name, result or "Failed")


# Main testing function
def run_tests():
    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, mode="w") as file:
            writer = csv.writer(file)
            writer.writerow(["Timestamp", "Scenario", "Metric", "Value"])

    for scenario in SCENARIOS:
        print(f"?? Running scenario: {scenario}")

        if scenario == "high_latency":
            simulate_network_conditions(latency=100, loss=1)

        if scenario == "file_transfer":
            output = run_command(COMMANDS["file_transfer_upload"])
            log_results(scenario, "file_transfer_upload", "Completed" if output else "Failed")

            output = run_command(COMMANDS["file_transfer_download"])
            log_results(scenario, "file_transfer_download", "Completed" if output else "Failed")

        elif scenario == "mixed_workload":
            run_mixed_workload()

        else:
            for protocol in ["throughput_tcp", "throughput_udp"]:
                output = run_command(COMMANDS[protocol])
                throughput = parse_iperf3_output(output) if output else None
                log_results(scenario, protocol, throughput)

            output = run_command(COMMANDS["latency"])
            avg_latency, jitter = parse_ping(output) if output else (None, None)
            log_results(scenario, "latency", avg_latency)
            log_results(scenario, "jitter", jitter)

        if scenario == "high_latency":
            reset_network_conditions()


# Visualization function with invalid data handling
def visualize_results():
    df = pd.read_csv(RESULTS_FILE)

    # Convert "Value" to numeric, replacing invalid entries with NaN
    df["Value"] = pd.to_numeric(df["Value"], errors="coerce")

    # Filter out NaN values for clean plotting
    df_clean = df.dropna()

    for (scenario, metric), group in df_clean.groupby(["Scenario", "Metric"]):
        plt.figure()
        plt.plot(range(len(group)), group["Value"], marker="o", linestyle="-")
        plt.title(f"{scenario} - {metric}")
        plt.xlabel("Iterations")
        plt.ylabel(metric)

        plt.ylim(0, group["Value"].max() * 1.2)  

        plt.savefig(f"{scenario}_{metric}.png")
        plt.close()

    print("? Visualization completed. Charts saved.")


# Run tests and visualize results
if __name__ == "__main__":
    run_tests()
    visualize_results()
