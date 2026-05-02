from flask import Flask, render_template, request, jsonify
import math

app = Flask(__name__)

NETWORKS = {
    "2G": {"freq": 900,  "max_speed": 0.3},
    "3G": {"freq": 2100, "max_speed": 7},
    "4G": {"freq": 2600, "max_speed": 100},
    "5G": {"freq": 3500, "max_speed": 1000},
}

ENV_LOSS = {
    "open":     0,
    "suburban": 8,
    "urban":    18,
    "indoor":   30,
}

def calc_signal(distance_m, freq, tx_power, env_loss):
    if distance_m < 1:
        distance_m = 1
    path_loss = 20 * math.log10(distance_m) + 20 * math.log10(freq) - 27.55
    return tx_power - path_loss - env_loss

def get_quality(dbm):
    if dbm > -70:  return "Excellent"
    if dbm > -80:  return "Good"
    if dbm > -90:  return "Fair"
    if dbm > -100: return "Poor"
    return "No service"

def get_speed(dbm, max_speed):
    ratio = max(0, min(1, (dbm + 110) / 60))
    mbps  = max_speed * ratio * ratio
    if mbps >= 1000: return str(round(mbps / 1000, 1)) + " Gbps"
    if mbps >= 1:    return str(round(mbps)) + " Mbps"
    return str(round(mbps * 1000)) + " Kbps"

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/signal", methods=["POST"])
def signal():
    data        = request.get_json()
    network     = data["network"]
    environment = data["environment"]
    distance    = float(data["distance_m"])
    tx_power    = float(data["tx_power"])

    freq        = NETWORKS[network]["freq"]
    max_speed   = NETWORKS[network]["max_speed"]
    env_loss    = ENV_LOSS[environment]

    dbm = calc_signal(distance, freq, tx_power, env_loss)

    return jsonify({
        "dbm":     round(dbm, 1),
        "quality": get_quality(dbm),
        "speed":   get_speed(dbm, max_speed)
    })

if __name__ == "__main__":
    app.run(debug=True)