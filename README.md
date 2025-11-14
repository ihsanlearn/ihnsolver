<pre align="center">
.__.__                        .__
|__|  |__   ____   __________ |  |___  __ ___________
|  |  |  \ /    \ /  ___/  _ \|  |\  \/ // __ \_  __ \
|  |   Y  \  |  \\___ (  <_> )  |_\   /\  ___/|  | \/
|__|___|  /___|  /____  >____/|____/\_/  \___  >__|
       \/     \/     \/                     \/
</pre>
<h1 align="center">ihnsolver</h1>
<p align="center">
  <strong>Resolver & Live Host Prober Hibrida Profesional (Milik Ihsan)</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT">
  <img src="https://img.shields.io/badge/Owner-Ihsan-red?style=for-the-badge" alt="Owner: Ihsan">
  <img src="https://img.shields.io/badge/Requires-Rich-purple?style=for-the-badge" alt="Requires: Rich">
</p>

`ihnsolver` adalah alat Python profesional untuk menyelesaikan (resolve) daftar *hostname* dan mendeteksi host mana yang menyajikan layanan HTTP/HTTPS.

Alat ini adalah *porting* dan penyempurnan dari *workflow* bash yang ada, dengan cerdas menggunakan `dnsx` dan `httpx` jika tersedia, atau beralih ke *fallback* *native* Python yang andal.

---

## ✨ Fitur Utama

* **Mesin Hibrida:** Secara otomatis menggunakan `dnsx` dan `httpx` dari ProjectDiscovery jika terdeteksi di `$PATH` Anda, untuk kecepatan dan akurasi sidik jari maksimum.
* **Fallback yang Mulus:** Jika *binary* tidak ditemukan, `ihnsolver` beralih ke resolver DNS dan *socket prober* berbasis Python yang konkuren dan andal.
* **UI Terminal Profesional:** Dibangun dengan `rich` untuk *output* baris perintah yang indah, jelas, dan profesional, lengkap dengan *progress bar* dan ringkasan berwarna.
* **Output Ganda:** Menghasilkan dua file penting:
    1.  `live-hosts.txt`: Daftar host yang bersih dan ternormalisasi (tanpa skema/port).
    2.  `httpx-alive.txt`: Menjaga *output* `httpx` mentah yang asli (jika digunakan) atau *output* probe kustom yang informatif.
* **Pemfilteran Fleksibel:** Mendukung pemfilteran input dengan *regex* (`-p`), pengambilan sampel (`-S`), dan kontrol *concurrency* (`-t`).

## 🎯 Rasional Desain: Pendekatan Hibrida

Alat ini sengaja dirancang untuk **lebih memilih *binary* ProjectDiscovery** (`dnsx`, `httpx`) ketika ada. Mengapa?

1.  **Konsistensi:** Memastikan *bug hunter* yang terbiasa dengan *output* mentah `httpx` mendapatkan format yang sama persis.
2.  **Kecepatan & Sidik Jari:** Memanfaatkan pengoptimalan dan teknik *fingerprinting* canggih dari alat-alat standar industri tersebut.

Ketika *binary* tersebut **tidak ada**, `ihnsolver` tidak gagal. Ia beralih ke mode *fallback* *native* Python, menyediakan fungsionalitas inti (resolusi DNS dan *probing* port HTTP/S) sehingga *workflow* Anda tetap berjalan di lingkungan apa pun.

## 🚀 Instalasi

1.  Kloning repositori ini (atau simpan *script*-nya).
2.  Buat dan aktifkan *virtual environment* (direkomendasikan):

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  Instal dependensi (hanya `rich`):

    ```bash
    pip install rich
    # Atau dari requirements.txt jika Anda membuatnya
    # pip install -r requirements.txt
    ```

4.  **(Opsional tapi Direkomendasikan)** Untuk fungsionalitas penuh, instal `dnsx` dan `httpx` dari ProjectDiscovery dan pastikan keduanya ada di `$PATH` Anda.

## 💻 Penggunaan

Penggunaan dasar, membaca dari `subdomains.txt` dan menyimpan ke `live-hosts.txt`:

```bash
python3 ihnsolver.py
