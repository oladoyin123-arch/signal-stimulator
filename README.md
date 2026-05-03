# Signal Strength Simulator

A web application that simulates cellular network signal strength based on real GPS location and network type.

## Live App
https://signal-simulator-production.up.railway.app

## What it does
- Detects your real network type (2G, 3G, 4G, 5G) from your device
- Captures your real GPS location using the browser Geolocation API
- Calculates distance to nearest cell tower using the Haversine formula
- Calculates signal strength using the Free Space Path Loss formula
- Shows signal quality and estimated download speed

## Formula Used
FSPL (dB) = 20 x log10(distance) + 20 x log10(frequency) - 27.55
Received Signal (dBm) = TX Power - Path Loss - Environment Loss

## Signal Quality Scale

| dBm Range   | Quality    |
|-------------|------------|
| Above -70   | Excellent  |
| -70 to -80  | Good       |
| -80 to -90  | Fair       |
| -90 to -100 | Poor       |
| Below -100  | No service |

## Tools Used
- Python 3
- Flask
- HTML, CSS, JavaScript
- GitHub
- Railway (deployment)

## How to run locally
pip install flask gunicorn
python app.py

Then open http://127.0.0.1:5000