import streamlit as st
import requests
import folium
import urllib.parse
from streamlit_folium import st_folium
from streamlit_javascript import st_javascript
from datetime import datetime
from main import get_area_code, get_weather_api, get_geo_from_ip

st.title("Prakiraan Cuaca Interaktif")

# === Ambil Lokasi Browser atau fallback ke IP ===
geo = st_javascript("""
async function main() {
  if (navigator.geolocation) {
    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude });
        },
        (err) => {
          resolve(null);
        }
      );
    });
  } else {
    return null;
  }
}
main();
""")

# Initialize session state for pinpoint lat/lon
if "pinpoint_lat" not in st.session_state:
    st.session_state["pinpoint_lat"] = None
if "pinpoint_lon" not in st.session_state:
    st.session_state["pinpoint_lon"] = None

final_lat = None
final_lon = None

if isinstance(geo, dict) and "lat" in geo and "lon" in geo:
    final_lat = geo["lat"]
    final_lon = geo["lon"]
    st.success(f"Lokasi Anda: {final_lat}, {final_lon}")
    st.session_state["pinpoint_lat"] = final_lat
    st.session_state["pinpoint_lon"] = final_lon
else:
    st.toast("Tidak bisa mendapatkan lokasi dari browser, mencoba dari IP...", icon="⚠️")
    geo = get_geo_from_ip()
    if geo and "lat" in geo and "lon" in geo:
        final_lat = geo["lat"]
        final_lon = geo["lon"]
        st.success(f"Lokasi berdasarkan IP: {final_lat}, {final_lon}")
        st.session_state["pinpoint_lat"] = final_lat
        st.session_state["pinpoint_lon"] = final_lon
    else:
        st.error("Tidak dapat mendeteksi lokasi sama sekali.")

# === Input dari Klik Peta ===
st.subheader("Cari dari Klik Peta")

# Inisialisasi klik sebelumnya agar tidak repeat
if "last_clicked_coords" not in st.session_state:
    st.session_state["last_clicked_coords"] = None

start_lat = st.session_state["pinpoint_lat"] or -6.2
start_lon = st.session_state["pinpoint_lon"] or 106.8
m = folium.Map(location=[start_lat, start_lon], zoom_start=11)

# Pasang marker pinpoint kalau sudah ada
if st.session_state["pinpoint_lat"] and st.session_state["pinpoint_lon"]:
    folium.Marker(
        [st.session_state["pinpoint_lat"], st.session_state["pinpoint_lon"]],
        tooltip="Pinpoint Lokasi",
        icon=folium.Icon(color="red", icon="map-marker"),
    ).add_to(m)

map_data = st_folium(m, height=400, width=600)

# if map_data and "last_clicked" in map_data and map_data["last_clicked"]:
#     lat_click = map_data["last_clicked"]["lat"]
#     lon_click = map_data["last_clicked"]["lng"]

#     # st.info(f"Koordinat klik peta: lat={lat_click}, lon={lon_click}")
#     # final_lat = lat_click
#     # final_lon = lon_click

#     if (
#         st.session_state["pinpoint_lat"] != lat_click or
#         st.session_state["pinpoint_lon"] != lon_click
#     ):
#         st.session_state["pinpoint_lat"] = lat_click
#         st.session_state["pinpoint_lon"] = lon_click
#         st.info(f"Koordinat klik peta: lat={lat_click}, lon={lon_click}")

# === Tangani klik peta ===
if map_data and map_data.get("last_clicked"):
    lat_click = map_data["last_clicked"]["lat"]
    lon_click = map_data["last_clicked"]["lng"]

    # Cek apakah klik berbeda dari sebelumnya
    if st.session_state["last_clicked_coords"] != (lat_click, lon_click):
        st.session_state["pinpoint_lat"] = lat_click
        st.session_state["pinpoint_lon"] = lon_click
        st.session_state["last_clicked_coords"] = (lat_click, lon_click)
        st.info(f"Koordinat klik peta: lat={lat_click}, lon={lon_click}")

final_lat = st.session_state["pinpoint_lat"]
final_lon = st.session_state["pinpoint_lon"]

# === Input dari Pencarian Teks ===
st.subheader("Cari dari Teks")
query = st.text_input("Masukkan nama lokasi")
selected_location = None

if query:
    query_encoded = urllib.parse.quote(query)
    nominatim_url = f"https://nominatim.openstreetmap.org/search?q={query_encoded}&format=json&addressdetails=1&limit=5"
    try:
        res = requests.get(nominatim_url, headers={"User-Agent": "RamalCuaca/1.0 (test@gmail.com)"})
        if res.status_code == 200:
            search_results = res.json()
            options = [f"{loc['display_name']} (lat: {loc['lat']}, lon: {loc['lon']})" for loc in search_results]
            choice = st.selectbox("Pilih lokasi hasil pencarian:", options)
            idx = options.index(choice)
            selected_location = search_results[idx]
            final_lat = float(selected_location["lat"])
            final_lon = float(selected_location["lon"])
            st.info(f"Lokasi terpilih: {selected_location['display_name']}")
        else:
            st.error(f"Error Nominatim: {res.status_code}")
    except Exception as e:
        st.error(f"Error saat panggil Nominatim: {e}")

# === Ambil & Tampilkan Prakiraan Cuaca ===
if final_lat and final_lon:
    area_code = get_area_code(final_lat, final_lon)
    if area_code:
        st.write(f"Kode wilayah adm4: `{area_code}`")
        weather = get_weather_api(area_code)

        if "error" in weather:
            st.error(f"Gagal ambil data cuaca: {weather['error']}")
        else:
            st.subheader("Prakiraan Cuaca")
            if not weather["data"]:
                st.warning("Data cuaca kosong")

            lokasi = weather.get("lokasi", {})
            st.markdown(f"**Lokasi**: {lokasi.get('desa')}, {lokasi.get('kecamatan')}, {lokasi.get('kotkab')}, {lokasi.get('provinsi')}")

            data = weather["data"]
            cuaca_groups = data[0].get("cuaca", [])
            if not cuaca_groups:
                st.warning("Data cuaca tidak ditemukan")
            else:
                hari_indo = {
                    'Monday': 'Senin',
                    'Tuesday': 'Selasa',
                    'Wednesday': 'Rabu',
                    'Thursday': 'Kamis',
                    'Friday': 'Jumat',
                    'Saturday': 'Sabtu',
                    'Sunday': 'Minggu',
                }

                for group in cuaca_groups:
                    waktu_pertama = datetime.strptime(group[0]["local_datetime"], "%Y-%m-%d %H:%M:%S")
                    nama_hari = hari_indo[waktu_pertama.strftime("%A")]
                    tanggal_hari = waktu_pertama.strftime("%d %B %Y")
                    st.markdown(f"### 📅 {nama_hari}, {tanggal_hari}")

                    # st.markdown(f"### Hari ke-{hari_ke + 1}")

                    # # Ambil tanggal pertama untuk label hari
                    # waktu_pertama = datetime.strptime(group[0]["local_datetime"], "%Y-%m-%d %H:%M:%S")
                    # nama_hari = hari_indo[waktu_pertama.strftime("%A")]
                    # tanggal_hari = waktu_pertama.strftime("%d %B %Y")

                    # with st.expander(f"📅 {nama_hari}, {tanggal_hari}"):
                    for jaman in group:
                        waktu = datetime.strptime(jaman["local_datetime"], "%Y-%m-%d %H:%M:%S")
                        col1, col2 = st.columns([1, 4])
                        with col1:
                            st.image(jaman["image"], width=60)
                        with col2:
                            st.markdown(f"**🕒 {waktu.strftime('%H:%M WIB')}**")
                            st.markdown(f"- 🌦️ **Cuaca:** {jaman['weather_desc']}")
                            st.markdown(f"- 🌡️ **Suhu:** {jaman['t']}°C")
                            st.markdown(f"- 💧 **Kelembaban:** {jaman['hu']}%")
                            st.markdown(f"- 🧭 **Angin:** {jaman['wd']} ({jaman['ws']} km/jam)")
                            st.markdown(f"- 👁️ **Jarak Pandang:** {jaman['vs_text']}")

    else:
        st.warning("Tidak ditemukan kelurahan terdekat untuk koordinat tersebut.")
else:
    st.info("Tentukan lokasi menggunakan salah satu metode input di atas.")
