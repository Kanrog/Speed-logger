# Speedtest Monitor

By Kanrog Creations

A lightweight, Dockerized network speed monitor featuring a web dashboard and intelligent bandwidth management. Designed for home servers to document unstable internet connections without constantly congesting the local network. 

To accurately measure a 1Gbps connection, a speedtest must completely saturate your bandwidth, causing latency spikes and buffering for all other devices. This application solves that by running frequent lightweight checks that abort if your speed is acceptable, only running heavy, full-bandwidth tests when the connection drops below your threshold or during your scheduled full-test windows.

## Features
* **Smart Threshold Testing:** Runs frequent checks but only logs detailed metrics if speeds fall below your defined limit (e.g., 100Mbps), saving your bandwidth.
* **Scheduled Full Tests:** Configure specific times of day to run complete benchmark tests regardless of the threshold.
* **Web Dashboard:** Interactive chart to visualize the last 24 hours of ping, download, and upload speeds.
* **Data Export & Management:** Download your historical data as a CSV file to send to your ISP, configure data retention limits, or wipe the database directly from the UI.
* **Easy Deployment:** Single-command installation, update, and removal scripts using Docker.

## Installation

Clone the repository to your server (such as CasaOS or any Debian-based system) and run the install script:

```bash
git clone https://github.com/Kanrog/Speed-logger.git
cd Speed-logger
bash install.sh
```
The script will prompt you for a port number (default is 8080) and automatically build and start the Docker container.

## Management Commands

This repository includes standalone scripts for easy management:

* **Update:** Pulls the latest code from GitHub and rebuilds the container.
  ```bash
  bash update.sh
  ```
* **Uninstall:** Stops and removes the container. Your database will safely remain in the `./data` folder.
  ```bash
  bash uninstall.sh
  ```

## Configuration
All settings can be adjusted directly from the web dashboard:
* **Interval:** How often the standard threshold check runs.
* **Threshold:** The minimum acceptable download speed (in Mbps).
* **Full Test Times:** Comma-separated times (HH:MM) for mandatory full tests.
* **Data Retention:** How many days to keep the historical data before automatically deleting it.

© 2026 Kanrog Creations