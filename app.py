from flask import Flask, render_template, request, jsonify
import math
import urllib.request
import json

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

def haversine_distance(lat1, lng1, lat2, lng2):
    R = 6371000
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calc_signal(distance_m, freq, tx_power, env_loss):
    if distance_m < 1:
        distance_m = 1
    path_loss = 20 * math.log10(distance_m) + 20 * math.log10(freq) - 27.55
    return tx_power - path_loss - env_loss

def get_quality(dbm):
    if dbm > -70:   return "Excellent"
    if dbm > -80:   return "Good"
    if dbm > -90:   return "Fair"
    if dbm > -100:  return "Poor"
    return "No service"

def get_speed(dbm, max_speed):
    ratio = max(0, min(1, (dbm + 110) / 60))
    mbps  = max_speed * ratio * ratio
    if mbps >= 1000: return str(round(mbps / 1000, 1)) + " Gbps"
    if mbps >= 1:    return str(round(mbps)) + " Mbps"
    return str(round(mbps * 1000)) + " Kbps"

def get_real_towers(lat, lng):
    url  = "https://location.services.mozilla.com/v1/geolocate?key=test"
    body = json.dumps({
        "considerIp": False,
        "wifiAccessPoints": [],
        "fallbacks": { "lacf": True, "ipf": False }
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data     = json.loads(response.read())
            moz_lat  = data["location"]["lat"]
            moz_lng  = data["location"]["lng"]
            accuracy = data.get("accuracy", 1000)
            return [{ "lat": moz_lat, "lng": moz_lng, "accuracy": accuracy }]
    except Exception:
        return get_fallback_towers(lat, lng)

def get_fallback_towers(lat, lng):
    offsets = [
        (0.005,  0.005), (-0.005, 0.005),
        (0.005, -0.005), (-0.005,-0.005),
        (0.008,  0.0),   (-0.008, 0.0),
        (0.0,    0.008), (0.0,   -0.008),
    ]
    return [{"lat": lat + d[0], "lng": lng + d[1]} for d in offsets]

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

@app.route("/api/nearest-tower", methods=["POST"])
def nearest_tower():
    data     = request.get_json()
    user_lat = float(data["lat"])
    user_lng = float(data["lng"])
    towers   = get_real_towers(user_lat, user_lng)
    nearest_dist = float('inf')
    nearest_idx  = 0
    for i, tower in enumerate(towers):
        dist = haversine_distance(user_lat, user_lng, tower["lat"], tower["lng"])
        if dist < nearest_dist:
            nearest_dist = dist
            nearest_idx  = i
    return jsonify({
        "tower_id":   nearest_idx + 1,
        "distance_m": round(nearest_dist),
        "tower_lat":  towers[nearest_idx]["lat"],
        "tower_lng":  towers[nearest_idx]["lng"]
    })

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')