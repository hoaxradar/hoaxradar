/* ═══════════════════════════════════════════════════════════
   HOAXRADAR — Main JavaScript
   ═══════════════════════════════════════════════════════════ */

// ─── Navbar scroll effect ─────────────────────────────────
window.addEventListener('scroll', () => {
  const navbar = document.getElementById('navbar');
  if (navbar) {
    navbar.classList.toggle('scrolled', window.scrollY > 20);
  }
});

// ─── Character counter ────────────────────────────────────
const textarea = document.getElementById('newsInput');
const charCount = document.getElementById('charCount');

if (textarea) {
  textarea.addEventListener('input', () => {
    const count = textarea.value.length;
    if (charCount) charCount.textContent = count.toLocaleString('id');

    // Color feedback
    if (count > 9000) {
      charCount.style.color = 'var(--red-alert)';
    } else if (count > 7000) {
      charCount.style.color = 'var(--amber)';
    } else {
      charCount.style.color = 'var(--gray-400)';
    }
  });
}

// ─── Example texts ────────────────────────────────────────
const examples = {
  hoax: `GAWAT!! DARURAT NASIONAL!! Pemerintah diam-diam telah menandatangani perjanjian rahasia yang akan menjual seluruh pulau Indonesia kepada negara asing pada tahun 2025! Ini sudah terbukti dan dikonfirmasi oleh sumber dalam pemerintah yang tidak mau disebutkan namanya! SEBARKAN SEBELUM DIHAPUS!! Mereka tidak ingin kita tahu tentang ini! Ribuan orang sudah ditangkap karena menyebarkan informasi ini! Simpan screenshot ini sebelum dihapus! Ini sudah viral di seluruh dunia tapi media Indonesia menutup-nutupinya!!`,

  valid: `Pemerintah Provinsi Jawa Timur mengumumkan program bantuan sosial terbaru untuk masyarakat terdampak bencana alam yang terjadi minggu lalu. Program ini mencakup bantuan tunai sebesar Rp 500.000 per kepala keluarga dan akan disalurkan melalui kantor kecamatan setempat mulai pekan depan. Gubernur Jawa Timur menyatakan bahwa data penerima telah diverifikasi oleh Dinas Sosial dan akan diprioritaskan untuk keluarga yang paling terdampak berdasarkan survei lapangan.`
};

function loadExample(type) {
  if (textarea) {
    textarea.value = examples[type];
    charCount.textContent = textarea.value.length.toLocaleString('id');

    // Scroll to detector
    document.getElementById('detector')?.scrollIntoView({ behavior: 'smooth', block: 'start' });

    showToast(type === 'hoax' ? '📋 Contoh berita hoaks dimuat' : '📋 Contoh berita valid dimuat');
  }
}

function clearInput() {
  if (textarea) {
    textarea.value = '';
    if (charCount) charCount.textContent = '0';
    resetResult();
    textarea.focus();
  }
}

// ─── Analyze ──────────────────────────────────────────────
async function analyzeNews() {
  const text = textarea?.value?.trim();
  if (!text) {
    showToast('⚠️ Masukkan teks berita terlebih dahulu', 'warning');
    textarea?.focus();
    return;
  }
  if (text.length < 10) {
    showToast('⚠️ Teks terlalu pendek (minimal 10 karakter)', 'warning');
    return;
  }

  setLoading(true);
  showScanning();

  try {
    const response = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });

    const data = await response.json();

    if (data.status === 'error') {
      showError(data.message);
      return;
    }

    displayResult(data);

  } catch (err) {
    console.error(err);
    showError('Gagal terhubung ke server. Pastikan Flask sudah berjalan.');
  } finally {
    setLoading(false);
  }
}

// ─── Display result ───────────────────────────────────────
function displayResult(data) {
  hideScanning();
  hidePlaceholder();

  const content = document.getElementById('resultContent');
  if (content) content.style.display = 'block';

  // Verdict banner
  const banner = document.getElementById('verdictBanner');
  const verdictIcon = document.getElementById('verdictIcon');
  const verdictText = document.getElementById('verdictText');
  const verdictBadge = document.getElementById('verdictBadge');

  if (data.is_hoax) {
    banner.className = 'verdict-banner is-hoax';
    verdictIcon.textContent = '🚨';
    verdictText.textContent = 'BERPOTENSI HOAKS';
    verdictText.className = 'verdict-text text-danger';
    verdictBadge.textContent = 'RISIKO ' + data.risk_level;
    verdictBadge.className = 'verdict-badge badge-danger';
  } else if (data.risk_score >= 45) {
    banner.className = 'verdict-banner is-warning';
    verdictIcon.textContent = '⚠️';
    verdictText.textContent = 'PERLU DIPERIKSA';
    verdictText.className = 'verdict-text text-warning';
    verdictBadge.textContent = 'RISIKO ' + data.risk_level;
    verdictBadge.className = 'verdict-badge badge-warning';
  } else {
    banner.className = 'verdict-banner is-valid';
    verdictIcon.textContent = '✅';
    verdictText.textContent = 'KEMUNGKINAN VALID';
    verdictText.className = 'verdict-text text-safe';
    verdictBadge.textContent = 'RISIKO ' + data.risk_level;
    verdictBadge.className = 'verdict-badge badge-safe';
  }

  // Animate gauge
  animateGauge(data.hoax_probability);

  // Probability bars
  const realBar = document.getElementById('realBar');
  const hoaxBar = document.getElementById('hoaxBar');
  const realProb = document.getElementById('realProb');
  const hoaxProb = document.getElementById('hoaxProb');

  setTimeout(() => {
    if (realBar) realBar.style.width = data.real_probability + '%';
    if (hoaxBar) hoaxBar.style.width = data.hoax_probability + '%';
  }, 200);

  if (realProb) realProb.textContent = data.real_probability + '%';
  if (hoaxProb) hoaxProb.textContent = data.hoax_probability + '%';

  // Risk level
  const riskLevelBox = document.getElementById('riskLevelBox');
  const riskLevelText = document.getElementById('riskLevelText');
  if (riskLevelText) {
    riskLevelText.textContent = data.risk_level;
    const cls = data.risk_color === 'danger' ? 'level-danger'
                : data.risk_color === 'warning' ? 'level-warning' : 'level-safe';
    riskLevelText.className = 'risk-level-value ' + cls;
  }

  // Indicators
  const list = document.getElementById('indicatorsList');
  if (list && data.indicators) {
    list.innerHTML = data.indicators.map(ind => {
      const cls = ind.type === 'warning' ? 'ind-warning'
                : ind.type === 'safe' ? 'ind-safe' : 'ind-info';
      const icon = ind.type === 'warning' ? '⚠️' : ind.type === 'safe' ? '✅' : 'ℹ️';
      return `<div class="indicator-item ${cls}">${icon} ${ind.text}</div>`;
    }).join('');
  }

  // Stats
  const s = data.stats;
  setText('statWords', s?.word_count ?? '-');
  setText('statChars', s?.char_count?.toLocaleString('id') ?? '-');
  setText('statSensational', s?.sensational_words ?? '-');
  setText('statConfidence', s?.confidence ? s.confidence + '%' : '-');

  // Timestamp
  const ts = document.getElementById('resultTimestamp');
  if (ts) ts.textContent = '🕐 Dianalisis: ' + data.analyzed_at;

  // ─── LOGIKA TAMBAHAN: UPDATE TABEL RIWAYAT SECARA REALTIME ───
  const tableBody = document.getElementById('historyTableBody');
  const emptyRow = document.getElementById('emptyHistoryRow');

  if (tableBody) {
    if (emptyRow) emptyRow.remove(); // Hapus pesan kosong jika ada

    // Penentuan warna hex manual untuk menyamakan style bawaan index.html
    let colorHex = data.risk_color === 'danger' ? '#ff3b3b' : (data.risk_color === 'warning' ? '#ffb300' : '#00d4ff');
    let bgHex = data.risk_color === 'danger' ? 'rgba(255,59,59,0.15)' : (data.risk_color === 'warning' ? 'rgba(255,179,0,0.15)' : 'rgba(0,212,255,0.15)');
    let borderHex = data.risk_color === 'danger' ? 'rgba(255,59,59,0.3)' : (data.risk_color === 'warning' ? 'rgba(255,179,0,0.3)' : 'rgba(0,212,255,0.3)');

    const origText = textarea?.value?.trim() || '';
    const safeText = escapeHTML(origText.substring(0, 75) + (origText.length > 75 ? '...' : ''));
    const wCount = s?.word_count ?? origText.split(/\s+/).filter(Boolean).length;

    const newRowHTML = `
      <tr style="border-bottom: 1px solid #1e2640; transition: background 0.2s; background: #1a233a;">
        <td style="padding: 16px 20px; font-size: 13px; color: #64748b; font-family: 'JetBrains Mono', monospace;">${escapeHTML(data.analyzed_at)}</td>
        <td style="padding: 16px 20px; font-size: 14px; color: #e2e8f0;">${safeText} <span style="color: #475569; font-size: 12px;">(${wCount} kata)</span></td>
        <td style="padding: 16px 20px; font-weight: 700; font-size: 14px; color: ${colorHex};">${data.verdict}</td>
        <td style="padding: 16px 20px;">
          <span style="display: inline-block; padding: 4px 10px; font-size: 11px; font-weight: 700; border-radius: 4px; background: ${bgHex}; color: ${colorHex}; border: 1px solid ${borderHex};">
            ${data.risk_level}
          </span>
        </td>
        <td style="padding: 16px 20px; font-size: 13px; font-family: 'JetBrains Mono', monospace;">
          <span style="color: #ff3b3b;">H: ${data.hoax_probability}%</span> <span style="color: #475569;">|</span> <span style="color: #00d4ff;">V: ${data.real_probability}%</span>
        </td>
        <!-- Penambahan tombol hapus dinamis untuk data baru -->
        <td style="padding: 16px 20px; text-align: center;">
          <button onclick="deleteRow(this, '${data.analyzed_at}')" style="background: transparent; border: none; color: #64748b; cursor: pointer; font-size: 16px; transition: color 0.2s;" onmouseover="this.style.color='#ff3b3b'" onmouseout="this.style.color='#64748b'">
            🗑️
          </button>
        </td>
      </tr>
    `;

    // Sisipkan baris baru di baris teratas (paling awal) di dalam tabel riwayat
    tableBody.insertAdjacentHTML('afterbegin', newRowHTML);
  }

  // Scroll to results on mobile
  if (window.innerWidth < 1024) {
    document.getElementById('resultPanel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

// ─── Gauge animation ──────────────────────────────────────
function animateGauge(percent) {
  const arc = document.getElementById('gaugeArc');
  const valText = document.getElementById('gaugeValue');
  if (!arc || !valText) return;

  const total = 267; // Circumference of the semi-circle arc
  const target = total - (percent / 100) * total;

  let current = total;
  let currentPct = 0;
  const step = () => {
    current = Math.max(target, current - (total / 60));
    currentPct = Math.min(percent, currentPct + (percent / 60));
    arc.setAttribute('stroke-dashoffset', current);
    valText.textContent = Math.round(currentPct) + '%';
    if (current > target) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// ─── UI helpers ───────────────────────────────────────────
function setLoading(state) {
  const btn = document.getElementById('analyzeBtn');
  const btnText = btn?.querySelector('.btn-text');
  const btnLoad = btn?.querySelector('.btn-loading');
  if (!btn) return;
  btn.disabled = state;
  if (btnText) btnText.style.display = state ? 'none' : 'flex';
  if (btnLoad) btnLoad.style.display = state ? 'flex' : 'none';
}

function showScanning() {
  const ph = document.getElementById('resultPlaceholder');
  const sc = document.getElementById('scanningOverlay');
  const rc = document.getElementById('resultContent');
  if (ph) ph.style.display = 'none';
  if (sc) sc.style.display = 'flex';
  if (rc) rc.style.display = 'none';
}

function hideScanning() {
  const sc = document.getElementById('scanningOverlay');
  if (sc) sc.style.display = 'none';
}

function hidePlaceholder() {
  const ph = document.getElementById('resultPlaceholder');
  if (ph) ph.style.display = 'none';
}

function resetResult() {
  const ph = document.getElementById('resultPlaceholder');
  const sc = document.getElementById('scanningOverlay');
  const rc = document.getElementById('resultContent');
  if (ph) ph.style.display = 'flex';
  if (sc) sc.style.display = 'none';
  if (rc) rc.style.display = 'none';
}

function showError(msg) {
  hideScanning();
  hidePlaceholder();
  const rc = document.getElementById('resultContent');
  if (rc) {
    rc.style.display = 'block';
    rc.innerHTML = `
      <div style="height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:12px; text-align:center; padding:24px;">
        <div style="font-size:48px;">❌</div>
        <div style="font-size:16px; font-weight:600; color:var(--red-alert)">Terjadi Kesalahan</div>
        <div style="font-size:13px; color:var(--gray-400); max-width:280px; line-height:1.6">${msg}</div>
        <button class="btn-action" onclick="resetResult()" style="margin-top:8px">↩ Coba Lagi</button>
      </div>
    `;
  }
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function analyzeNew() {
  clearInput();
  document.getElementById('newsInput')?.focus();
}

// ─── Copy result ──────────────────────────────────────────
function copyResult() {
  const verdictText = document.getElementById('verdictText')?.textContent;
  const hoaxProb = document.getElementById('hoaxProb')?.textContent;
  const riskLevel = document.getElementById('riskLevelText')?.textContent;
  const ts = document.getElementById('resultTimestamp')?.textContent;

  const text = `HoaxRadar — Hasil Analisis\n` +
    `Verdict: ${verdictText}\n` +
    `Probabilitas Hoaks: ${hoaxProb}\n` +
    `Level Risiko: ${riskLevel}\n` +
    `${ts}\n` +
    `Verifikasi: hoaxradar.app`;

  navigator.clipboard.writeText(text)
    .then(() => showToast('✅ Hasil berhasil disalin'))
    .catch(() => showToast('❌ Gagal menyalin', 'warning'));
}

// ─── Toast notification ───────────────────────────────────
function showToast(msg, type = 'info') {
  const toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3000);
}

// ─── Keyboard shortcut: Ctrl/Cmd + Enter ─────────────────
document.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    analyzeNews();
  }
});

// ─── Utilities ────────────────────────────────────────────
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

function escapeHTML(str) {
  if (!str) return '';
  return String(str).replace(/[&<>'"]/g, 
    tag => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[tag] || tag)
  );
}

// Fungsi untuk menghapus baris riwayat
async function deleteRow(button, timestamp) {
  if (!confirm('Apakah Anda yakin ingin menghapus riwayat pemeriksaan ini?')) return;

  try {
    const response = await fetch('/delete_history', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ analyzed_at: timestamp })
    });

    const data = await response.json();

    if (data.status === 'success') {
      // Hapus baris dari elemen DOM HTML langsung
      const row = button.closest('tr');
      row.remove();
      showToast('🗑️ Riwayat berhasil dihapus');

      // Jika tabel menjadi kosong setelah dihapus, tampilkan pesan kosong kembali
      const tableBody = document.getElementById('historyTableBody');
      if (tableBody && tableBody.children.length === 0) {
        tableBody.innerHTML = `
          <tr id="emptyHistoryRow">
            <td colspan="6" style="padding: 40px; text-align: center; color: #475569; font-size: 15px;">
              🚫 Belum ada riwayat pemeriksaan teks berita di database lokal.
            </td>
          </tr>
        `;
      }
    } else {
      showToast('❌ Gagal menghapus: ' + data.message, 'warning');
    }
  } catch (err) {
    console.error(err);
    showToast('❌ Terjadi kesalahan jaringan saat menghapus', 'warning');
  }
}