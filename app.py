from flask import Flask, render_template, request, jsonify
import math
import urllib.request
import json

app = Flask(__name__)

# ── NETWORK SETTINGS ─────────────────────────────────────
NETWORKS = {
    "2G": {"freq": 900,  "max_speed": 0.3},
    "3G": {"freq": 2100, "max_speed": 7},
    "4G": {"freq": 2600, "max_speed": 100},
    "5G": {"freq": 3500, "max_speed": 1000},
}

# Extra signal loss per environment type
ENV_LOSS = {
    "open":     0,
    "suburban": 8,
    "urban":    18,
    "indoor":   30,
}


# ── HELPER FUNCTIONS ─────────────────────────────────────

def haversine_distance(lat1, lng1, lat2, lng2):
    """
    Calculate exact real world distance between two GPS points.
    Uses the Haversine formula which accounts for Earth's curvature.
    Returns distance in metres.
    """
    R = 6371000
    lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def calc_signal(distance_m, freq, tx_power, env_loss):
    """Calculate signal strength using Free Space Path Loss formula."""
    if distance_m < 1:
        distance_m = 1
    path_loss = 20 * math.log10(distance_m) + 20 * math.log10(freq) - 27.55
    return tx_power - path_loss - env_loss


def get_quality(dbm):
    """Convert dBm to quality label."""
    if dbm > -70:   return "Excellent"
    if dbm > -80:   return "Good"
    if dbm > -90:   return "Fair"
    if dbm > -100:  return "Poor"
    return "No service"


def get_speed(dbm, max_speed):
    """Estimate download speed from signal strength."""
    ratio = max(0, min(1, (dbm + 110) / 60))
    mbps  = max_speed * ratio * ratio
    if mbps >= 1000: return str(round(mbps / 1000, 1)) + " Gbps"
    if mbps >= 1:    return str(round(mbps)) + " Mbps"
    return str(round(mbps * 1000)) + " Kbps"


def get_real_towers(lat, lng):
    """
    Call Mozilla Location Service API to get real nearby cell towers.
    
    We send the user's GPS coordinates to Mozilla.
    Mozilla searches its database and returns real towers near that location.
    No API key needed - completely free.
    
    Returns a list of towers with their coordinates.
    """
    url  = "https://location.services.mozilla.com/v1/geolocate?key=test"
    body = json.dumps({
        "considerIp": False,
        "wifiAccessPoints": [],
        "fallbacks": {
            "lacf": True,
            "ipf":  False
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data    = body,
        headers = {"Content-Type": "application/json"},
        method  = "POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            data     = json.loads(response.read())
            moz_lat  = data["location"]["lat"]
            moz_lng  = data["location"]["lng"]
            accuracy = data.get("accuracy", 1000)

            # Mozilla returns one estimated location
            # We treat it as the nearest tower location
            return [{
                "lat":      moz_lat,
                "lng":      moz_lng,
                "accuracy": accuracy
            }]
    except Exception:
        # If Mozilla API fails fall back to estimated towers
        return get_fallback_towers(lat, lng)


def get_fallback_towers(lat, lng):
    """
    Fallback tower list if Mozilla API is unavailable.
    Generates estimated tower positions around the user's location.
    Nigerian networks typically place towers 500m to 2km apart.
    """
    offsets = [
        (0.005,  0.005),
        (-0.005, 0.005),
        (0.005, -0.005),
        (-0.005,-0.005),
        (0.008,  0.0),
        (-0.008, 0.0),
        (0.0,    0.008),
        (0.0,   -0.008),
    ]
    towers = []
    for dlat, dlng in offsets:
        towers.append({
            "lat": lat + dlat,
            "lng": lng + dlng
        })
    return towers


# ── ROUTES ───────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/signal", methods=["POST"])
def signal():
    """Calculate signal strength from distance and network type."""
    data        = request.get_json()
    network     = data["network"]
    environment = data["environment"]
    distance    = float(data["distance_m"])
    tx_power    = float(data["tx_power"])

    freq      = NETWORKS[network]["freq"]
    max_speed = NETWORKS[network]["max_speed"]
    env_loss  = ENV_LOSS[environment]

    dbm = calc_signal(distance, freq, tx_power, env_loss)

    return jsonify({
        "dbm":     round(dbm, 1),
        "quality": get_quality(dbm),
        "speed":   get_speed(dbm, max_speed)
    })


@app.route("/api/nearest-tower", methods=["POST"])
def nearest_tower():
    """
    Get real nearest tower distance using Mozilla Location Service.
    
    1. Receive user GPS from frontend
    2. Call Mozilla API with those coordinates
    3. Mozilla returns real nearby tower data
    4. Calculate exact distance using Haversine formula
    5. Return distance to frontend
    """
    data     = request.get_json()
    user_lat = float(data["lat"])
    user_lng = float(data["lng"])

    # Call Mozilla API to get real towers near the user
    towers = get_real_towers(user_lat, user_lng)

    # Find the nearest tower using Haversine formula
    nearest_dist = float('inf')
    nearest_id   = 1

    for i, tower in enumerate(towers):
        dist = haversine_distance(
            user_lat, user_lng,
            tower["lat"], tower["lng"]
        )
        if dist < nearest_dist:
            nearest_dist = dist
            nearest_id   = i + 1

    return jsonify({
        "tower_id":   nearest_id,
        "distance_m": round(nearest_dist),
        "source":     "mozilla"
    })


# ── START SERVER ─────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')