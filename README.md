# Delivery Distance Checker (Streamlit + BigQuery)

Aplikasi web sederhana untuk validasi jarak antara titik **delivery** vs **actual dropoff** berdasarkan koordinat latitude/longitude.

- Input: file Excel berisi
  - `shipment_code`
  - `delivery_latitude`, `delivery_longitude`
  - `dropoff_latitude`, `dropoff_longitude`
- Proses:
  - Data di-upload ke BigQuery (tabel sementara)
  - Jarak dihitung menggunakan fungsi geospasial `ST_DISTANCE`
- Output:
  - Tabel shipment dengan jarak di atas threshold (default 1 km)
  - Bisa di-download sebagai CSV


## 1. Cara Jalankan di Lokal

### 1.1. Clone repo

```bash
git clone https://github.com/<username>/delivery-distance-checker.git
cd delivery-distance-checker
