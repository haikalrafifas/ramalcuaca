import sqlite3
import math
import requests

# =========================
# Konstanta
# =========================
DB_PATH = "indonesia_geo.db"
WEATHER_API_URL = "https://api.bmkg.go.id/publik/prakiraan-cuaca?adm4={}"

# =========================
# Fungsi: Haversine
# =========================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Radius bumi dalam km
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c

# =========================
# Get area code for BMKG API (level-4 administrative)
# =========================
def get_area_code(lat_input, lon_input, db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.create_function("haversine", 4, haversine)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nama, latitude, longitude, haversine(latitude, longitude, ?, ?) AS jarak
        FROM t_kelurahan
        ORDER BY jarak ASC
        LIMIT 1
    """, (lat_input, lon_input))

    result = cur.fetchone()
    conn.close()

    if result:
        # format to (xx.xx.xx.xxxx)
        result = str(result[0]).zfill(10)
        return f"{result[:2]}.{result[2:4]}.{result[4:6]}.{result[6:]}"
    else:
        return None

# =========================
# Fungsi: Ambil cuaca dari BMKG
# =========================
def get_weather_api(area_code):
    print(area_code)
    url = WEATHER_API_URL.format(area_code)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code} dari BMKG"}
    except Exception as e:
        return {"error": str(e)}

# =========================
# Fungsi: Ambil lokasi dari IP
# =========================
def get_geo_from_ip():
    try:
        geo_ip = requests.get("https://ipinfo.io/json", timeout=5).json()
        lat, lon = map(float, geo_ip["loc"].split(","))
        return {"lat": lat, "lon": lon}
    except Exception as e:
        st.warning(f"Gagal mendeteksi lokasi berdasarkan IP: {e}")
        return None

# # =========================
# # Eksekusi utama (bisa ganti input untuk Streamlit, API, dsb)
# # =========================
# if __name__ == "__main__":
#     # Input manual (misal dari pinpoint peta atau GPS)
#     lat_input = -6.1492
#     lon_input = 106.8342

#     kelurahan = get_nearest_kelurahan(lat_input, lon_input)

#     if kelurahan:
#         print(f"Kelurahan terdekat: {kelurahan['nama']} (ID: {kelurahan['id']})")
#         kode_bmkg = format_kode_bmkg(kelurahan["id"])
#         print(f"Kode wilayah (BMKG): {kode_bmkg}")

#         cuaca = get_cuaca_bmkg(kode_bmkg)
#         print("Data cuaca dari BMKG:")
#         print(cuaca)

#     else:
#         print("Kelurahan terdekat tidak ditemukan.")
