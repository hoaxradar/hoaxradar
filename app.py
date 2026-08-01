from flask import Flask, render_template, request, jsonify
import os
import re
import json
from datetime import datetime
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch
import torch.nn.functional as F
from transformers import AutoConfig

# Version: 1.0.2 - Live production release
app = Flask(__name__)

# Jalur file penyimpanan JSON
HISTORY_FILE = os.path.join(os.path.dirname(__file__), 'history.json')

# ─── Fungsi Utilitas JSON (Penyimpanan Riwayat) ──────────────────────────────
def save_to_json(new_data):
    try:
        # 1. Baca data yang sudah ada jika file tersedia
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                try:
                    history_list = json.load(f)
                except json.JSONDecodeError:
                    history_list = []
        else:
            history_list = []

        # 2. Masukkan data baru di posisi paling atas (terbaru muncul duluan)
        history_list.insert(0, new_data)

        # 3. Batasi riwayat maksimal 20 item agar file tidak bengkak
        history_list = history_list[:20]

        # 4. Tulis kembali ke file JSON
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history_list, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"[WARNING] Gagal menyimpan riwayat ke JSON: {e}")

def read_from_json():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

# ─── Load Model ─────────────────────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model', 'hoaxmodel')
MODEL_FILE = os.path.join(MODEL_PATH, 'model.safetensors')
MODEL_URL = "https://media.githubusercontent.com/media/hoaxradar/hoaxradar/main/model/hoaxmodel/model.safetensors"

model = None
tokenizer = None  

def download_model_if_needed():
    os.makedirs(MODEL_PATH, exist_ok=True)
    # Jika file tidak ada atau ukurannya < 1MB (artinya cuma file pointer LFS 134 byte)
    if not os.path.exists(MODEL_FILE) or os.path.getsize(MODEL_FILE) < 1000000:
        print("[INFO] Memulai unduh model.safetensors (498MB) dari server...")
        import urllib.request
        try:
            req = urllib.request.Request(MODEL_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(MODEL_FILE, 'wb') as out_file:
                import shutil
                shutil.copyfileobj(response, out_file)
            print("[OK] Unduh file model selesai!")
        except Exception as e:
            print(f"[ERROR] Gagal mengunduh model: {e}")
            if os.path.exists(MODEL_FILE) and os.path.getsize(MODEL_FILE) < 1000000:
                try:
                    os.remove(MODEL_FILE)
                except Exception:
                    pass

def load_model():
    global model, tokenizer
    try:
        download_model_if_needed()
        config = AutoConfig.from_pretrained(MODEL_PATH)
        config.id2label = {0: "HOAX", 1: "FAKTA"}
        config.label2id = {"HOAX": 0, "FAKTA": 1}
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
        model = AutoModelForSequenceClassification.from_pretrained(
            MODEL_PATH, 
            config=config,
            low_cpu_mem_usage=True
        )
        model.eval()
        print("[OK] Model IndoBERT berhasil dimuat dengan konfigurasi yang benar!")
    except Exception as e:
        import traceback
        print(f"[ERROR] Error memuat model: {e}")
        traceback.print_exc()

load_model()

# ─── Logic Analisis ─────────────────────────────────────────────────────────
def analyze_text(text):
    if model is None or tokenizer is None:
        return {'status': 'error', 'message': 'Model tidak dimuat'}

    hoax_prob = 50.0
    real_prob = 50.0

    try:
        # Konfigurasi thread CPU untuk kecepatan maksimal
        if hasattr(torch, 'set_num_threads'):
            torch.set_num_threads(max(1, os.cpu_count() or 2))

        # Tokenisasi
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=256)

        with torch.inference_mode():
            outputs = model(**inputs)
            raw_probs = F.softmax(outputs.logits, dim=-1).squeeze()
            probs = raw_probs.tolist() if raw_probs.ndim > 0 else [raw_probs.item()]
            prediction_idx = torch.argmax(outputs.logits, dim=-1).item()

        # Ambil probabilitas dasar dari model ML (Index 0 = HOAX, Index 1 = FAKTA)
        if isinstance(probs, list) and len(probs) >= 2:
            hoax_prob = probs[0] * 100
            real_prob = probs[1] * 100
        elif isinstance(probs, list) and len(probs) == 1:
            hoax_prob = probs[0] * 100
            real_prob = 100.0 - hoax_prob
        else:
            hoax_prob = 50.0
            real_prob = 50.0

        # ─── HYBRID AI ENGINE: Heuristic Rules + Machine Learning ───
        indicators = []
        heuristic_risk_bonus = 0

        # Rule 1: Kata Sensasional & Tanda Seru
        sensational_matches = re.findall(r'(!|\bWAJIB\b|\bVIRAL\b|\bGAWAT\b|\bBONGKAR\b|\bHOAKS\b|\bHEBOH\b|\bGEMPAR\b|\bGEMPARKAN\b)', text.upper())
        sensational_count = len(sensational_matches)
        if sensational_count > 0:
            heuristic_risk_bonus += min(sensational_count * 15, 45)
            indicators.append({'type': 'warning', 'text': f'Terdeteksi {sensational_count} kata sensasional/provokatif (HEBOH/GAWAT/!)'})

        # Rule 2: Ajakan Pesan Berantai & Media Sosial
        chain_matches = re.findall(r'(\bBAGIKAN\b|\bBAGIKANNYA\b|\bSEBARKAN\b|\bWHATSAPP\b|\bGRUP WA\b|\bGROUP WA\b|\bBERANTAI\b|\bSEBELUM DIHAPUS\b|\bVIRALKAN\b)', text.upper())
        if chain_matches:
            heuristic_risk_bonus += 35
            indicators.append({'type': 'warning', 'text': 'Terdeteksi klausa ajakan menyebarkan pesan berantai (WhatsApp / Media Sosial)'})

        # Rule 3: Klaim Absurd & Fiktif
        absurd_matches = re.findall(r'(\bDINOSAURUS\b|\bNAGA\b|\bALIEN\b|\bUFO\b|\bFIKTIF\b|\b5G\b|\bBUMI DATAR\b|\bPSEUDOSAINS\b|\bGORONG-GORONG RAKSASA\b)', text.upper())
        if absurd_matches:
            heuristic_risk_bonus += 50
            matched_words = ", ".join(list(set(absurd_matches)))
            indicators.append({'type': 'warning', 'text': f'Terdeteksi kata klaim fiktif/absurd: {matched_words}'})

        # Rule 4: Elemen Jurnalistik Formil
        if re.search(r'\b(JAKARTA|SURABAYA|BANDUNG|MEDAN|SEMARANG|MAKASSAR|Pemerintah|Dinas|Kementerian|Kepolisian|Wakapol|Polri|Presiden|Gubernur)\b', text):
            indicators.append({'type': 'info', 'text': 'Struktur penulisan menggunakan format/gaya jurnalistik'})

        # Kombinasikan Skor Model ML + Heuristic Risk Bonus
        if heuristic_risk_bonus > 0:
            hoax_prob = min(99.9, hoax_prob + heuristic_risk_bonus)
            real_prob = max(0.1, 100.0 - hoax_prob)

        risk_score = int(round(hoax_prob))
        is_hoax = risk_score >= 50

        # LOGIKA PENENTUAN STATUS
        if risk_score < 30:
            risk_level = 'AMAN'
            risk_color = 'safe'
            verdict = 'VALID'
            if not indicators:
                indicators.append({'type': 'safe', 'text': 'Tidak ditemukan indikator disinformasi pada teks'})
        elif risk_score < 70:
            risk_level = 'PERLU DIPERIKSA'
            risk_color = 'warning'
            verdict = 'VALID/MERAGUKAN'
        else:
            risk_level = 'TINGGI'
            risk_color = 'danger'
            verdict = 'HOAKS'

        # Ekstrak metrik tambahan untuk memperkaya riwayat
        word_count = len(text.split())
        char_count = len(text)
        confidence_score = round(max(hoax_prob, real_prob), 1)

        result = {
            'status': 'success',
            'is_hoax': is_hoax,
            'verdict': verdict,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_color': risk_color,
            'hoax_probability': round(hoax_prob, 1),
            'real_probability': round(real_prob, 1),
            'indicators': indicators,
            'analyzed_at': datetime.now().strftime('%d %B %Y, %H:%M WIB'),
            'stats': {
                'word_count': word_count,
                'char_count': char_count,
                'sensational_words': sensational_count,
                'confidence': confidence_score
            }
        }


        # --- SIMPAN DATA KE RIWAYAT JSON ---
        history_entry = {
            'text': text,
            'verdict': verdict,
            'risk_level': risk_level,
            'risk_color': risk_color,
            'hoax_probability': round(hoax_prob, 1),
            'real_probability': round(real_prob, 1),
            'word_count': word_count,
            'analyzed_at': result['analyzed_at']
        }
        save_to_json(history_entry)

        return result
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

# ─── Routes ──────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    model_status = 'loaded' if model is not None else 'missing'
    # Ambil data riwayat saat halaman pertama kali dimuat
    histories = read_from_json()
    return render_template('index.html', model_status=model_status, histories=histories)

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

@app.route('/analyze', methods=['POST'])
def analyze():
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Format data tidak valid'}), 400
    data = request.get_json()
    text = data.get('text', '')
    if not isinstance(text, str):
        return jsonify({'status': 'error', 'message': 'Format teks harus berupa string'}), 400
    if len(text) < 10:
        return jsonify({'status': 'error', 'message': 'Teks terlalu pendek (minimal 10 karakter)'})
    if len(text) > 10000:
        return jsonify({'status': 'error', 'message': 'Teks terlalu panjang (maksimal 10.000 karakter)'}), 400
    
    return jsonify(analyze_text(text))

@app.route('/delete_history', methods=['POST'])
def delete_history():
    try:
        data = request.get_json()
        target_time = data.get('analyzed_at')
        
        # Baca data riwayat saat ini
        histories = read_from_json() # Atau sesuaikan dengan nama fungsi pembaca JSON
        
        # Filter data: simpan semua KECUALI yang memiliki timestamp yang cocok
        updated_histories = [item for item in histories if item.get('analyzed_at') != target_time]
        
        # Tulis kembali ke file history.json
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(updated_histories, f, indent=4, ensure_ascii=False)
            
        return jsonify({'status': 'success', 'message': 'Riwayat berhasil dihapus'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
@app.route('/history')
def history():
    # Mengambil data riwayat dari file JSON untuk dikirim ke template HTML
    model_status = 'loaded' if model is not None else 'missing'
    histories = read_from_json()
    return render_template('history.html', model_status=model_status, histories=histories)

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=debug_mode, host='0.0.0.0', port=port)