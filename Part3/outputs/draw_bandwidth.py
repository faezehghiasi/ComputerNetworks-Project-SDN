import re
import matplotlib.pyplot as plt

# Read the log file and extract bandwidth rates for dp=2, port=3
log_file = "ryu_log.txt"  # make sure this is the correct path

rates = []
with open(log_file, 'r') as file:
    for line in file:
        if "dp=2 port=3" in line:
            match = re.search(r"rate=([\d.]+)", line)
            if match:
                rates.append(float(match.group(1)))

# Create time points assuming one sample per second
time_points = list(range(1, len(rates) + 1))

# Plot the bandwidth over time
plt.figure(figsize=(10, 5))
plt.plot(time_points, rates, marker='o', label='Measured Bandwidth')
plt.axhline(y=50, color='red', linestyle='--', label='Detection Threshold (50 Mb/s)')
plt.title("Bandwidth Over Time on dp=2 port=3 (UDP Flood Detection)")
plt.xlabel("Time (seconds)")
plt.ylabel("Bandwidth (Mb/s)")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

