# VPN-TEST

This release introduces the initial version of the VPN testing automation tool. The key features and capabilities include:

**Features**

    Automated VPN Performance Testing:
        Measures throughput (TCP/UDP) using iperf3.
        Captures latency using ping tests.
        Monitors CPU and memory usage during tests.

    Network Simulation:
        Simulates high-latency and packet-loss conditions using tc.

    Data Analysis & Visualization:
        Generates detailed bar plots comparing WireGuard and OpenVPN performance metrics.
        Visualizations include throughput, latency, CPU usage, and memory usage.

**Improvements**

    Provides repeatable and consistent test setups with configurable parameters.
    Ensures automated result saving for deeper analysis.

**Usage**

    Run the tests for WireGuard and OpenVPN protocols and visualize performance comparisons.
    Ideal for benchmarking VPN protocols under varying network conditions.


[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.14673412.svg)](https://doi.org/10.5281/zenodo.14673412)
