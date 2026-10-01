/**
 * Training Center Client Logic.
 * Handles hyperparameter dispatch, non-blocking progress polling, and log streaming.
 */

let currentLang = localStorage.getItem('traffic_assistant_lang') || 'vi';
let i18nData = {};
let pollingInterval = null;

async function loadI18n(lang) {
  try {
    const res = await fetch(`/locales/${lang}.json`);
    i18nData = await res.json();
    currentLang = lang;
    localStorage.setItem('traffic_assistant_lang', lang);
    applyI18n();
  } catch (e) {
    console.error('Failed to load i18n:', e);
  }
}

function applyI18n() {
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    const key = el.getAttribute('data-i18n');
    if (i18nData[key]) el.textContent = i18nData[key];
  });
  document.getElementById('btn-lang-vi').className =
    currentLang === 'vi'
      ? 'px-2.5 py-1 text-xs font-semibold rounded-md bg-blue-600 text-white'
      : 'px-2.5 py-1 text-xs font-semibold rounded-md text-gray-400 hover:text-white';
  document.getElementById('btn-lang-en').className =
    currentLang === 'en'
      ? 'px-2.5 py-1 text-xs font-semibold rounded-md bg-blue-600 text-white'
      : 'px-2.5 py-1 text-xs font-semibold rounded-md text-gray-400 hover:text-white';
}

async function fetchStatus() {
  try {
    const res = await fetch('/api/v1/training/status');
    if (!res.ok) return;
    const data = await res.json();

    document.getElementById('metric-version').textContent = data.current_version;
    document.getElementById('metric-accuracy').textContent = `${(data.metrics.accuracy * 100).toFixed(1)}%`;
    document.getElementById('metric-latency').textContent = `${data.metrics.inference_latency_ms.toFixed(1)} ms`;
    document.getElementById('metric-samples').textContent = `${data.sample_count} mẫu`;

    const progressBar = document.getElementById('progress-bar-fill');
    progressBar.style.width = `${data.progress_percentage}%`;

    const badge = document.getElementById('training-badge');
    const btnLabel = document.getElementById('train-btn-label');
    const btn = document.getElementById('btn-trigger-train');

    if (data.is_training) {
      badge.textContent = `Đang huấn luyện (${data.progress_percentage}%)`;
      badge.className = 'px-2.5 py-1 text-xs font-mono rounded-full bg-purple-950 text-purple-300 border border-purple-800 animate-pulse';
      btn.disabled = true;
      btn.classList.add('opacity-50', 'cursor-not-allowed');
      btnLabel.textContent = i18nData['training_running'] || 'Đang Huấn Luyện...';
    } else {
      badge.textContent = 'Trạng thái: Sẵn sàng';
      badge.className = 'px-2.5 py-1 text-xs font-mono rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800';
      btn.disabled = false;
      btn.classList.remove('opacity-50', 'cursor-not-allowed');
      btnLabel.textContent = i18nData['btn_start_training'] || 'Bắt Đầu Huấn Luyện Mô Hình';
    }

    // Render Logs
    const term = document.getElementById('log-terminal');
    term.innerHTML = '';
    data.recent_logs.forEach((log) => {
      const p = document.createElement('p');
      if (log.includes('[ERROR]')) p.className = 'text-red-400';
      else if (log.includes('[SUCCESS]')) p.className = 'text-emerald-400 font-bold';
      else if (log.includes('[EPOCH')) p.className = 'text-blue-300';
      else p.className = 'text-gray-300';
      p.textContent = log;
      term.appendChild(p);
    });
    term.scrollTop = term.scrollHeight;
  } catch (e) {
    console.error('Error fetching training status:', e);
  }
}

async function triggerTraining() {
  const epochs = parseInt(document.getElementById('train-epochs').value) || 10;
  const lr = parseFloat(document.getElementById('train-lr').value) || 0.001;
  const batch = parseInt(document.getElementById('train-batch').value) || 16;
  const useLora = document.getElementById('cb-use-lora').checked;
  const loraRank = parseInt(document.getElementById('train-lora-rank').value) || 8;

  const payload = {
    hyperparameters: {
      architecture: useLora ? 'peft_lora_light' : 'tfidf_classifier',
      epochs: epochs,
      learning_rate: lr,
      batch_size: batch,
      use_peft_lora: useLora,
      lora_rank: loraRank,
      early_stopping_patience: 3,
    },
  };

  try {
    const res = await fetch('/api/v1/training/train', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await res.json();
    fetchStatus();
  } catch (e) {
    alert('Không thể kết nối API Training: ' + e.message);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  loadI18n(currentLang);
  fetchStatus();
  pollingInterval = setInterval(fetchStatus, 1000);

  document.getElementById('btn-lang-vi').addEventListener('click', () => loadI18n('vi'));
  document.getElementById('btn-lang-en').addEventListener('click', () => loadI18n('en'));
  document.getElementById('btn-trigger-train').addEventListener('click', triggerTraining);
});
