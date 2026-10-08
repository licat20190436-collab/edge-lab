import time
import csv
import urllib.request
import os

OUTPUT = os.path.expanduser("~/metrics.csv")
INTERVAL = 1  # collect every second

def fetch_metric(metrics_text, name):
    for line in metrics_text.splitlines():
        if line.startswith(name + " ") or line.startswith(name + "{"):
            if line.startswith("#"):
                continue
            parts = line.split()
            try:
                return float(parts[-1])
            except:
                continue
    return None

def collect():
    url = "http://localhost:9100/metrics"
    with urllib.request.urlopen(url, timeout=3) as r:
        text = r.read().decode()
    return text

def main():
    write_header = not os.path.exists(OUTPUT)
    with open(OUTPUT, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow([
                "timestamp",
                "cpu_idle",
                "mem_available_mb",
                "mem_total_mb",
                "tcp_connections",
            ])
        print(f"Collecting metrics, writing to {OUTPUT} — Ctrl+C to stop")
        while True:
            try:
                text = collect()
                ts = time.strftime("%Y-%m-%d %H:%M:%S")

                cpu_idle = fetch_metric(text, 'node_cpu_seconds_total{cpu="0",mode="idle"}')
                mem_avail = fetch_metric(text, "node_memory_MemAvailable_bytes")
                mem_total = fetch_metric(text, "node_memory_MemTotal_bytes")
                tcp_conn  = fetch_metric(text, "node_netstat_Tcp_CurrEstab")

                mem_avail_mb = round(mem_avail / 1024 / 1024, 1) if mem_avail else None
                mem_total_mb = round(mem_total / 1024 / 1024, 1) if mem_total else None

                writer.writerow([ts, cpu_idle, mem_avail_mb, mem_total_mb, tcp_conn])
                f.flush()

                print(f"{ts} | CPU idle={cpu_idle} | MEM avail={mem_avail_mb}MB | TCP={tcp_conn}")
            except Exception as e:
                print(f"Collection error: {e}")
            time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
