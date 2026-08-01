from flask import Flask, render_template, request, jsonify
import os
import re
import json
from datetime import datetime
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch
import torch.nn.functional as F
from transformers import AutoConfig

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

    try:
        # Tokenisasi
        inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=256)
        
        with torch.no_grad():
            outputs = model(**inputs)
            probs = F.softmax(outputs.logits, dim=-1).squeeze().tolist()
            prediction_idx = torch.argmax(outputs.logits, dim=-1).item()

        # Ambil label dari config model
        label = model.config.id2label.get(prediction_idx, "HOAX" if prediction_idx == 0 else "FAKTA")
        
        # Logika Penentuan
        is_hoax = "HOAX" in label.upper()
        
        # Hitung probabilitas
        hoax_prob = probs[0] * 100 if "HOAX" in model.config.id2label.get(0, "HOAX").upper() else probs[1] * 100
        real_prob = 100 - hoax_prob
        
        risk_score = int(hoax_prob)
        
        # LOGIKA PENENTUAN STATUS
        if risk_score < 30:
            risk_level = 'AMAN'
            risk_color = 'safe'
            verdict = 'VALID'
        elif risk_score < 70:
            risk_level = 'PERLU DIPERIKSA'
            risk_color = 'warning'
            verdict = 'VALID/MERAGUKAN'
        else:
            risk_level = 'TINGGI'
            risk_color = 'danger'
            verdict = 'HOAKS'

        # Ekstrak metrik tambahan untuk memperkaya riwayat
        # Hitung metrik tambahan
        word_count = len(text.split())
        char_count = len(text)
        confidence_score = round(max(hoax_prob, real_prob), 1)
        
        # Hitung perkiraan kata sensasional (misal teks mengandung kata tanda seru, kapital, atau kata bombastis)
        sensational_count = len(re.findall(r'(!|\bWAJIB\b|\bVIRAL\b|\bGAWAT\b|\bBONGKAR\b|\bHOAKS\b)', text.upper()))

        result = {
            'status': 'success',
            'is_hoax': is_hoax,
            'verdict': verdict,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_color': risk_color,
            'hoax_probability': round(hoax_prob, 1),
            'real_probability': round(real_prob, 1),
            'analyzed_at': datetime.now().strftime('%d %B %Y, %H:%M WIB'),
            # TAMBAHKAN MODIFIKASI INI AGAR TERKIRIM KE FRONTEND:
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

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    text = data.get('text', '')
    if len(text) < 10:
        return jsonify({'status': 'error', 'message': 'Teks terlalu pendek'})
    
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