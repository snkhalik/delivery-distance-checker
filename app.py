import math
import pandas as pd
import streamlit as st


# ==========================
# FUNGSI UTIL
# ==========================
def haversine_distance_km(lat1, lon1, lat2, lon2):
    """
    Hitung jarak antara dua titik (lat, lon) di permukaan bumi dalam kilometer.
    Input dalam derajat.
    """
    # radius bumi dalam km
    R = 6371.0

    # konversi ke radian
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    distance_km = R * c
    return distance_km


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalisasi nama kolom agar sesuai format standar:

      - shipment_code
      - delivery_latitude
      - delivery_longitude
      - dropoff_latitude
      - dropoff_longitude

    Kalau nama di Excel beda (misal: delivery_lat, actual_lat, dll),
    di-mapping di sini.
    """
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    col_map = {
        # shipment
        "shipment_code": "shipment_code",
        "shipment": "shipment_code",

        # delivery lat
        "delivery_lat": "delivery_latitude",
        "delivery_latitude": "delivery_latitude",
        "delivery_latitude_deg": "delivery_latitude",

        # delivery long
        "delivery_lng": "delivery_longitude",
        "delivery_long": "delivery_longitude",
        "delivery_longitude": "delivery_longitude",

        # actual/dropoff lat
        "actual_lat": "dropoff_latitude",
        "actual_latitude": "dropoff_latitude",
        "actual_dropoff_lat": "dropoff_latitude",
        "dropoff_lat": "dropoff_latitude",

        # actual/dropoff long
        "actual_lng": "dropoff_longitude",
        "actual_longitude": "dropoff_longitude",
        "actual_dropoff_long": "dropoff_longitude",
        "dropoff_lng": "dropoff_longitude",
        "dropoff_long": "dropoff_longitude",
    }

    renamed = {}
    for col in df.columns:
        if col in col_map:
            renamed[col] = col_map[col]

    df = df.rename(columns=renamed)

    required_cols = [
        "shipment_code",
        "delivery_latitude",
        "delivery_longitude",
        "dropoff_latitude",
        "dropoff_longitude",
    ]

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(
            "Kolom wajib belum lengkap.\n"
            f"Harus ada: {required_cols}\n"
            f"Kolom yang kurang: {missing}\n"
            "Silakan sesuaikan nama kolom di Excel atau update mapping di normalize_columns()."
        )

    df = df[required_cols]

    # pastikan numeric
    numeric_cols = [
        "delivery_latitude",
        "delivery_longitude",
        "dropoff_latitude",
        "dropoff_longitude",
    ]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


def compute_distances(df: pd.DataFrame) -> pd.DataFrame:
    """
    Hitung jarak delivery vs dropoff per baris, hasilkan kolom:
      - distance_km
      - distance_meters
    """
    df = df.copy()

    # buang baris yang lat/long-nya null
    df_valid = df.dropna(
        subset=[
            "delivery_latitude",
            "delivery_longitude",
            "dropoff_latitude",
            "dropoff_longitude",
        ]
    )

    # hitung jarak per baris
    def _calc_row(row):
        return haversine_distance_km(
            row["delivery_latitude"],
            row["delivery_longitude"],
            row["dropoff_latitude"],
            row["dropoff_longitude"],
        )

    df_valid["distance_km"] = df_valid.apply(_calc_row, axis=1)
    df_valid["distance_meters"] = df_valid["distance_km"] * 1000

    return df_valid


# ==========================
# STREAMLIT APP
# ==========================
def main():
    st.set_page_config(
        page_title="Validasi Titik Delivery vs Actual Dropoff (Excel-only)",
        layout="wide",
    )

    st.title("Validasi Titik Delivery vs Actual Dropoff (Excel-only)")
    st.markdown(
        """
        Aplikasi ini:
        1. Menerima upload file Excel berisi:
           - `shipment_code`
           - koordinat delivery (lat/long)
           - koordinat actual/dropoff (lat/long)
        2. Menghitung jarak antar titik di **Python** (tanpa BigQuery).
        3. Menampilkan shipment yang jaraknya **di atas threshold** (default 1 km).
        """
    )

    st.sidebar.header("Pengaturan Jarak")
    min_km = st.sidebar.number_input(
        "Minimal jarak (km) untuk ditampilkan",
        min_value=0.1,
        max_value=100.0,
        value=1.0,
        step=0.1,
    )

    uploaded_file = st.file_uploader(
        "Upload file Excel berisi data delivery vs dropoff",
        type=["xlsx", "xls"],
        accept_multiple_files=False,
    )

    if uploaded_file is None:
        st.info("Silakan upload file Excel di atas untuk mulai pengecekan.")
        return

    # Baca Excel
    st.subheader("Preview Data Excel")
    try:
        df_raw = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Gagal membaca file Excel: {e}")
        return

    st.write("Beberapa baris pertama dari file yang di-upload:")
    st.dataframe(df_raw.head())

    # Normalisasi kolom
    try:
        df_norm = normalize_columns(df_raw)
    except ValueError as e:
        st.error(str(e))
        return

    st.write("Data setelah normalisasi kolom:")
    st.dataframe(df_norm.head())

    # Hitung jarak
    with st.spinner("Menghitung jarak delivery vs dropoff..."):
        df_with_dist = compute_distances(df_norm)

    st.success("Perhitungan jarak selesai.")

    # Filter jarak > threshold
    df_result = df_with_dist[df_with_dist["distance_km"] > min_km].copy()
    df_result = df_result.sort_values("distance_km", ascending=False)

    st.subheader(f"Hasil: Shipment dengan jarak > {min_km:.2f} km")
    st.write(f"Total baris: {len(df_result):,}")

    if not df_result.empty:
        st.dataframe(df_result)

        # Download button
        csv = df_result.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download hasil (CSV)",
            data=csv,
            file_name="hasil_validasi_jarak_excel_only.csv",
            mime="text/csv",
        )
    else:
        st.info("Tidak ada shipment yang melebihi threshold jarak yang ditentukan.")


if __name__ == "__main__":
    main()