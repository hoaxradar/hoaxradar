# 🎯 HoaxRadar — Sistem Deteksi Berita Hoaks

Website deteksi berita hoaks berbasis AI menggunakan model IndoBERT dengan tampilan profesional dan fitur lengkap.

---

## 📁 Struktur Folder

```
hoax-detector/
├── app.py                  ← Flask server utama
├── requirements.txt        ← Dependensi Python
├── history.json            ← Data riwayat analisis (otomatis dibuat)
├── README.md
├── model/
│   └── hoaxmodel/          ← ⬅️ LETAKKAN FILE MODEL DI SINI
│       ├── config.json
│       ├── model.safetensors
│       ├── tokenizer.json
│       ├── tokenizer_config.json
│       ├── special_tokens_map.json
│       └── vocab.txt
├── templates/
│   ├── index.html          ← Halaman utama (deteksi + riwayat)
│   ├── history.html        ← Halaman riwayat penuh
│   └── about.html          ← Halaman tentang
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── main.js
```

---

## ⚙️ Cara Menjalankan

### 1. Masukkan Model
Pastikan semua file model IndoBERT berada di dalam folder `model/hoaxmodel/`:
```
model/hoaxmodel/config.json
model/hoaxmodel/model.safetensors
model/hoaxmodel/tokenizer.json
model/hoaxmodel/tokenizer_config.json
model/hoaxmodel/special_tokens_map.json
model/hoaxmodel/vocab.txt
```

### 2. Install Dependensi
```bash
pip install -r requirements.txt
```

### 3. Jalankan Server
```bash
python app.py
```

### 4. Buka Browser
Akses di: **http://localhost:5000**

---

## 🤖 Model yang Digunakan

HoaxRadar menggunakan **IndoBERT** (`indobenchmark/indobert-base-p1`) yang di-fine-tune untuk klasifikasi berita hoaks Indonesia.

**Stack Teknologi:**
- **Backend**: Python, Flask
- **AI/ML**: PyTorch, Hugging Face Transformers, IndoBERT
- **Frontend**: HTML, CSS, JavaScript
- **Data**: JSON (penyimpanan riwayat lokal)

---

## 🌐 Fitur Website

- ✅ Deteksi hoaks dengan skor risiko 0-100
- ✅ Visualisasi gauge probabilitas animasi
- ✅ Indikator analisis linguistik
- ✅ Statistik teks (kata, karakter, kata sensasional, kepercayaan AI)
- ✅ Riwayat pemeriksaan (simpan, lihat, hapus)
- ✅ Contoh teks hoaks dan valid
- ✅ Shortcut keyboard: Ctrl+Enter untuk analisis
- ✅ Salin hasil ke clipboard
- ✅ Halaman About
- ✅ Responsif untuk mobile
- ✅ Status model (online/offline) di navbar

---

## 🚀 Hosting

Untuk hosting online, gunakan:
- **Railway** / **Render** — gratis, mudah
- **VPS** dengan `gunicorn app:app`
- **Heroku** dengan `Procfile`

Contoh `Procfile` untuk Heroku:
```
web: gunicorn app:app
```
