# Spotify ke Discord Webhook

Otomatis memposting lagu Spotify yang sedang Anda putar ke channel Discord melalui webhook, dengan integrasi scrobble Last.fm.

## Fitur

- Warna embed dinamis - Mengekstrak warna dominan dari album art
- Integrasi Last.fm - Menampilkan jumlah total scrobble
- Aman - Menggunakan environment variables untuk kredensial
- Robust - Error handling komprehensif dan retry logic
- Efisien - Smart token refresh (hanya saat diperlukan)
- Logging - Log detail untuk debugging
- Graceful shutdown - Exit bersih dengan Ctrl+C

## Persyaratan

- Python 3.7+
- Akun Spotify Premium (untuk currently playing API)
- Discord webhook URL
- Akun Last.fm (opsional, untuk jumlah scrobble)

## Instalasi

### 1. Clone/Download repository ini

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Buat Aplikasi Spotify

1. Kunjungi [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Klik "Create an App"
3. Isi nama dan deskripsi aplikasi
4. Tambahkan `http://127.0.0.1:8888/callback` ke Redirect URIs di settings
5. Simpan **Client ID** dan **Client Secret** Anda

### 4. Dapatkan API Key Last.fm (opsional)

1. Kunjungi [Last.fm API Account](https://www.last.fm/api/account/create)
2. Buat API account
3. Simpan **API Key** Anda

### 5. Buat Discord Webhook

1. Buka pengaturan server Discord Anda
2. Navigasi ke Integrations → Webhooks
3. Klik "New Webhook"
4. Pilih channel dan copy webhook URL

### 6. Konfigurasi Environment Variables

Copy `.env.example` ke `.env`:

```bash
cp .env.example .env
```

Edit `.env` dan isi nilai Anda:

```env
DISCORD_WEBHOOK_URL=url_webhook_discord_anda
SPOTIFY_CLIENT_ID=client_id_spotify_anda
SPOTIFY_CLIENT_SECRET=client_secret_spotify_anda
LASTFM_API_KEY=api_key_lastfm_anda
LASTFM_USERNAME=username_lastfm_anda
POLLING_INTERVAL=15
```

### 7. Generate Spotify Refresh Token

Jalankan script generator token:

```bash
python get_refresh_token.py
```

Script ini akan:
- Membuka browser untuk otorisasi Spotify
- Generate refresh token
- Mencetak token ke terminal Anda

Copy `SPOTIFY_REFRESH_TOKEN` dan tambahkan ke file `.env` Anda.

## Cara Menggunakan

Jalankan script utama:

```bash
python main.py
```

Bot akan:
- Memonitor Spotify Anda untuk lagu yang sedang diputar
- Memposting lagu baru ke Discord webhook Anda
- Update setiap 15 detik (dapat dikonfigurasi)
- Log aktivitas ke console dan `spotify_discord.log`

Tekan `Ctrl+C` untuk stop dengan graceful.

## Konfigurasi

Edit nilai-nilai berikut di file `.env` Anda:

| Variable | Deskripsi | Default |
|----------|-----------|---------|
| `POLLING_INTERVAL` | Seberapa sering mengecek Spotify (detik) | 15 |

## Struktur Proyek

```
webhook-discord-spotify-2/
├── main.py                 # Aplikasi utama
├── get_refresh_token.py    # Tool generator token
├── requirements.txt        # Dependencies Python
├── .env                    # Kredensial Anda (tidak di git)
├── .env.example           # Template untuk .env
├── .gitignore             # Aturan git ignore
├── README.md              # File ini
└── spotify_discord.log    # File log yang auto-generated
```

## Troubleshooting

### "Missing required environment variables"
- Pastikan file `.env` Anda ada dan berisi semua variable yang diperlukan
- Cek typo pada nama variable

### "Failed to refresh access token"
- Verifikasi `SPOTIFY_CLIENT_ID` dan `SPOTIFY_CLIENT_SECRET` Anda benar
- Generate ulang refresh token dengan `get_refresh_token.py`

### "Failed to send Discord webhook"
- Verifikasi webhook URL Anda benar
- Cek apakah webhook belum dihapus

### Tidak ada lagu yang diposting
- Pastikan Anda benar-benar sedang memutar musik di Spotify
- Cek bahwa Anda memiliki Spotify Premium (diperlukan untuk currently playing API)
- Lihat `spotify_discord.log` untuk pesan error

### ModuleNotFoundError: No module named 'dotenv'
- Pastikan Anda menggunakan Python environment yang benar
- Coba: `python -m pip install --force-reinstall -r requirements.txt`
- Aktifkan virtual environment jika menggunakan: `.\venv\scripts\activate` (Windows) atau `source venv/bin/activate` (Linux/Mac)

## Logging

Log ditulis ke:
- **Console** - Update status real-time
- **spotify_discord.log** - Log detail untuk debugging

Level log:
- `INFO` - Operasi normal
- `WARNING` - Masalah non-kritis
- `ERROR` - Operasi gagal

## Catatan Keamanan

- **Jangan commit file `.env` Anda** - Berisi token sensitif
- File `.gitignore` sudah dikonfigurasi untuk mencegah ini
- Jaga kerahasiaan Discord webhook URL Anda
- Generate ulang token jika tidak sengaja terekspos

## Lisensi

Gratis untuk digunakan dan dimodifikasi untuk proyek personal.

## Kredit

Menggunakan API berikut:
- [Spotify Web API](https://developer.spotify.com/documentation/web-api/)
- [Last.fm API](https://www.last.fm/api)
- [Discord Webhooks](https://discord.com/developers/docs/resources/webhook)
