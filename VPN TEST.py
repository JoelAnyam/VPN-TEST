import subprocess
import time
import csv
from datetime import datetime
import os
import statistics
import paramiko
import logging
from typing import Dict, List, Tuple

class VPNTester:
    def __init__(self, server_ip: str, username: str, key_path: str, protocol: str = "wireguard"):
        """
        Initialize VPN testing environment
        
        Args:
            server_ip: IP address of the VPN server
            username: SSH username
            key_path: Path to SSH private key
            protocol: VPN protocol to test ("wireguard" or "openvpn")
        """
        self.server_ip = server_ip
        self.username = username
        self.key_path = key_path
        self.protocol = protocol
        self.results_dir = f"results_{protocol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            filename=f"{self.results_dir}/vpn_test.log",
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize SSH client
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
    def connect_ssh(self) -> None:
        """Establish SSH connection to server"""
        try:
            self.ssh.connect(
                self.server_ip,
                username=self.username,
                key_filename=self.key_path
            )
            self.logger.info(f"Successfully connected to {self.server_ip}")
        except Exception as e:
            self.logger.error(f"Failed to connect to {self.server_ip}: {str(e)}")
            raise

    def measure_throughput(self, duration: int = 60) -> Dict[str, float]:
        """
        Measure network throughput using iperf3
        
        Args:
            duration: Test duration in seconds
            
        Returns:
            Dictionary containing TCP and UDP throughput results
        """
        results = {}
        
        # TCP throughput
        try:
            cmd = f"iperf3 -c {self.server_ip} -p 5201 -t {duration}"
            output = subprocess.check_output(cmd.split()).decode()
            tcp_throughput = float(output.split('sender')[-1].split()[4])
            results['tcp_throughput'] = tcp_throughput
        except Exception as e:
            self.logger.error(f"TCP throughput measurement failed: {str(e)}")
            results['tcp_throughput'] = None

        # UDP throughput
        try:
            cmd = f"iperf3 -c {self.server_ip} -u -b 0 -t {duration}"
            output = subprocess.check_output(cmd.split()).decode()
            udp_throughput = float(output.split('sender')[-1].split()[4])
            results['udp_throughput'] = udp_throughput
        except Exception as e:
            self.logger.error(f"UDP throughput measurement failed: {str(e)}")
            results['udp_throughput'] = None

        return results

    def measure_latency(self, count: int = 100) -> Dict[str, float]:
        """
        Measure network latency and jitter using ping
        
        Args:
            count: Number of ping requests
            
        Returns:
            Dictionary containing latency and jitter measurements
        """
        try:
            cmd = f"ping -c {count} {self.server_ip}"
            output = subprocess.check_output(cmd.split()).decode()
            
            # Parse ping output
            lines = output.split('\n')
            latencies = []
            for line in lines:
                if 'time=' in line:
                    latency = float(line.split('time=')[1].split()[0])
                    latencies.append(latency)
            
            avg_latency = statistics.mean(latencies)
            jitter = statistics.stdev(latencies)
            
            return {
                'latency': avg_latency,
                'jitter': jitter
            }
        except Exception as e:
            self.logger.error(f"Latency measurement failed: {str(e)}")
            return {
                'latency': None,
                'jitter': None
            }

    def measure_system_resources(self, duration: int = 60) -> Dict[str, float]:
        """
        Measure CPU and memory utilization using sar
        
        Args:
            duration: Monitoring duration in seconds
            
        Returns:
            Dictionary containing CPU and memory usage statistics
        """
        try:
            # CPU utilization
            cmd = f"sar -u 1 {duration}"
            output = subprocess.check_output(cmd.split()).decode()
            cpu_usage = float(output.split('\n')[-2].split()[2])
            
            # Memory utilization
            cmd = f"sar -r 1 {duration}"
            output = subprocess.check_output(cmd.split()).decode()
            mem_usage = float(output.split('\n')[-2].split()[2])
            
            return {
                'cpu_usage': cpu_usage,
                'memory_usage': mem_usage
            }
        except Exception as e:
            self.logger.error(f"System resource measurement failed: {str(e)}")
            return {
                'cpu_usage': None,
                'memory_usage': None
            }

    def test_file_transfer(self, file_size_mb: int = 5000) -> Dict[str, float]:
        """
        Test file transfer performance
        
        Args:
            file_size_mb: Size of test file in MB
            
        Returns:
            Dictionary containing transfer speed and completion time
        """
        try:
            # Create test file
            test_file = f"/tmp/test_file_{file_size_mb}MB"
            subprocess.run(f"dd if=/dev/zero of={test_file} bs=1M count={file_size_mb}".split())
            
            # Upload test
            start_time = time.time()
            subprocess.run(f"scp {test_file} {self.username}@{self.server_ip}:/tmp/".split())
            upload_time = time.time() - start_time
            
            # Download test
            start_time = time.time()
            subprocess.run(f"scp {self.username}@{self.server_ip}:/tmp/test_file_{file_size_mb}MB /tmp/download_test".split())
            download_time = time.time() - start_time
            
            # Clean up
            os.remove(test_file)
            os.remove("/tmp/download_test")
            
            return {
                'upload_speed': file_size_mb / upload_time,
                'download_speed': file_size_mb / download_time
            }
        except Exception as e:
            self.logger.error(f"File transfer test failed: {str(e)}")
            return {
                'upload_speed': None,
                'download_speed': None
            }

    def simulate_mixed_workload(self, duration: int = 300) -> Dict[str, float]:
        """
        Simulate mixed workload with concurrent operations
        
        Returns:
            Dictionary containing performance metrics during mixed workload
        """
        try:
            # Start HTTP requests
            ab_process = subprocess.Popen(
                f"ab -n 100 -c 10 http://{self.server_ip}/".split()
            )
            
            # Start video streaming
            ffplay_process = subprocess.Popen(
                f"ffplay rtsp://{self.server_ip}/test.mp4".split(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Measure system performance during mixed workload
            resources = self.measure_system_resources(duration)
            throughput = self.measure_throughput(30)
            latency = self.measure_latency(50)
            
            # Clean up processes
            ab_process.terminate()
            ffplay_process.terminate()
            
            return {
                **resources,
                **throughput,
                **latency
            }
        except Exception as e:
            self.logger.error(f"Mixed workload simulation failed: {str(e)}")
            return {}

    def simulate_network_conditions(self, latency_ms: int = 100, packet_loss: float = 1.0) -> None:
        """
        Simulate poor network conditions using tc
        
        Args:
            latency_ms: Additional latency in milliseconds
            packet_loss: Packet loss percentage
        """
        try:
            interface = subprocess.check_output("ip route | grep default | awk '{print $5}'", shell=True).decode().strip()
            
            # Add latency
            subprocess.run(f"sudo tc qdisc add dev {interface} root netem delay {latency_ms}ms".split())
            
            # Add packet loss
            subprocess.run(f"sudo tc qdisc change dev {interface} root netem loss {packet_loss}%".split())
            
            self.logger.info(f"Network conditions simulated: {latency_ms}ms latency, {packet_loss}% packet loss")
        except Exception as e:
            self.logger.error(f"Failed to simulate network conditions: {str(e)}")

    def reset_network_conditions(self) -> None:
        """Reset network conditions to normal"""
        try:
            interface = subprocess.check_output("ip route | grep default | awk '{print $5}'", shell=True).decode().strip()
            subprocess.run(f"sudo tc qdisc del dev {interface} root".split())
            self.logger.info("Network conditions reset to normal")
        except Exception as e:
            self.logger.error(f"Failed to reset network conditions: {str(e)}")

    def run_complete_test(self, iterations: int = 20) -> None:
        """
        Run complete test suite with specified number of iterations
        
        Args:
            iterations: Number of test iterations
        """
        results = []
        
        for i in range(iterations):
            self.logger.info(f"Starting iteration {i+1}/{iterations}")
            
            iteration_results = {
                'iteration': i+1,
                'timestamp': datetime.now().isoformat(),
                'protocol': self.protocol
            }
            
            # Baseline performance
            self.reset_network_conditions()
            iteration_results.update(self.measure_throughput())
            iteration_results.update(self.measure_latency())
            iteration_results.update(self.measure_system_resources())
            
            # File transfer
            transfer_results = self.test_file_transfer()
            iteration_results.update(transfer_results)
            
            # Mixed workload
            mixed_results = self.simulate_mixed_workload()
            iteration_results.update({
                'mixed_' + k: v for k, v in mixed_results.items()
            })
            
            # High latency/packet loss scenario
            self.simulate_network_conditions()
            adverse_results = self.measure_throughput()
            iteration_results.update({
                'adverse_' + k: v for k, v in adverse_results.items()
            })
            
            results.append(iteration_results)
            
            # Save results after each iteration
            self.save_results(results)
            
            self.logger.info(f"Completed iteration {i+1}/{iterations}")
            
        self.analyze_results(results)

    def save_results(self, results: List[Dict]) -> None:
        """
        Save test results to CSV file
        
        Args:
            results: List of result dictionaries
        """
        filepath = os.path.join(self.results_dir, 'test_results.csv')
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)

    def analyze_results(self, results: List[Dict]) -> None:
        """
        Analyze test results and generate summary statistics
        
        Args:
            results: List of result dictionaries
        """
        summary = {}
        
        # Calculate statistics for numerical metrics
        for key in results[0].keys():
            if key not in ['iteration', 'timestamp', 'protocol']:
                values = [r[key] for r in results if r[key] is not None]
                if values:
                    summary[key] = {
                        'mean': statistics.mean(values),
                        'median': statistics.median(values),
                        'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
                        'min': min(values),
                        'max': max(values)
                    }
        
        # Save summary statistics
        with open(os.path.join(self.results_dir, 'summary_statistics.csv'), 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Metric', 'Mean', 'Median', 'Std Dev', 'Min', 'Max'])
            for metric, stats in summary.items():
                writer.writerow([metric] + list(stats.values()))

def main():
    # Configuration
    SERVER_IP = "your_server_ip"
    USERNAME = "your_username"
    KEY_PATH = "path_to_ssh_key"
    
    # Test WireGuard
    wireguard_tester = VPNTester(SERVER_IP, USERNAME, KEY_PATH, "wireguard")
    wireguard_tester.connect_ssh()
    wireguard_tester.run_complete_test()
    
    # Test OpenVPN
    openvpn_tester = VPNTester(SERVER_IP, USERNAME, KEY_PATH, "openvpn")
    openvpn_tester.connect_ssh()
    openvpn_tester.run_complete_test()

if __name__ == "__main__":
    main()