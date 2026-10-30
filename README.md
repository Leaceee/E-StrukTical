# E-StrukTical — Struk Digital, Poin Ramah Lingkungan

E-StrukTical merupakan aplikasi berbasis web untuk membantu pengguna mengelola struk belanja digital, menyimpan riwayat transaksi, mengumpulkan poin, dan menukarkan poin dengan hadiah yang tersedia.

## Fitur Aplikasi

- Registrasi dan login pengguna.
- Pengelolaan struk digital.
- Penyimpanan riwayat transaksi.
- Perhitungan dan pengumpulan poin.
- Katalog hadiah.
- Penukaran poin dengan hadiah.

## Teknologi yang Digunakan

- Python
- Flask
- MySQL
- SQLAlchemy
- HTML, CSS, dan JavaScript

## Persyaratan

- Python
- MySQL Server
- pip

## Instalasi

1. Clone repository:

   ```bash
   git clone https://github.com/USERNAME/E-StrukTical.git
   cd E-StrukTical
   ```

2. Buat virtual environment:

   ```bash
   python -m venv .venv
   ```

3. Aktifkan virtual environment:

   ```bash
   .venv\Scripts\activate
   ```

4. Instal dependensi:

   ```bash
   pip install -r requirements.txt
   ```

5. Siapkan konfigurasi `.env` berdasarkan `.env.example`.

6. Siapkan database MySQL sesuai konfigurasi aplikasi.

7. Jalankan aplikasi:

   ```bash
   python app.py
   ```

## Keamanan

- Jangan mengunggah file `.env`.
- Jangan membagikan password database.
- Jangan mengunggah data transaksi pribadi.
- Gunakan konfigurasi lokal yang aman.

## Status Proyek

Selesai — E-StrukTical dikembangkan sebagai proyek aplikasi web pengelolaan struk digital dan sistem poin.