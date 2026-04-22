/* ── app.js — CD BOT frontend logic ──────────────────────────────────────── */

const API = '';   // Same origin — FastAPI serves both frontend and API

// ── State ──────────────────────────────────────────────────────────────────
let recipientCount   = 0;
let authPollInterval = null;
let totalRecipients  = 0;
let processedCount   = 0;

// ── Sender helpers ─────────────────────────────────────────────────────────
function getSelectedSenderUPN() {
  return $('sender-select').value;
}

function getSelectedSenderFirstName() {
  const opt = $('sender-select').selectedOptions[0];
  return opt ? opt.dataset.name : 'Sanjay';
}

function handleSenderChange() {
  // Update Regards line in textarea if it has content
  const ta = $('raw-message');
  if (ta.value) {
    const firstName = getSelectedSenderFirstName();
    ta.value = ta.value.replace(/^Regards,\s*.+$/m, `Regards,\n${firstName}`);
  }
}

// ── Utility ────────────────────────────────────────────────────────────────
function $(id) { return document.getElementById(id); }

function showEl(id)  { $(id).classList.remove('hidden'); }
function hideEl(id)  { $(id).classList.add('hidden'); }
function toggleEl(id){ $(id).classList.toggle('hidden'); }

// ── On load: check model status ────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', async () => {
  try {
    const res  = await fetch(`${API}/model/status`);
    const data = await res.json();
    const lbl  = $('model-status-label');
    if (data.available) {
      lbl.textContent = '⚡ Phi-3 model ready';
      lbl.style.color = '#107c10';
    } else {
      lbl.textContent = '⚠️ Model not found — message will not be reformatted';
      lbl.style.color = '#a04800';
    }
  } catch { /* backend not yet reachable */ }
});

// ── STEP 1 — File upload ───────────────────────────────────────────────────
const uploadArea = $('upload-area');
const fileInput  = $('file-input');

uploadArea.addEventListener('dragover', e => {
  e.preventDefault();
  uploadArea.classList.add('drag-over');
});
uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('drag-over'));
uploadArea.addEventListener('drop', e => {
  e.preventDefault();
  uploadArea.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f) uploadFile(f);
});

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) uploadFile(fileInput.files[0]);
});

async function uploadFile(file) {
  if (!file.name.endsWith('.xlsx')) {
    alert('Please upload an .xlsx file.');
    return;
  }

  const fd = new FormData();
  fd.append('file', file);

  try {
    const res  = await fetch(`${API}/upload`, { method: 'POST', body: fd });
    const data = await res.json();

    if (!res.ok) {
      alert('Upload error: ' + (data.detail || 'Unknown error'));
      return;
    }

    recipientCount  = data.count;
    totalRecipients = data.count;

    $('file-name-label').textContent       = file.name;
    $('recipient-count-label').textContent = `${data.count} recipient${data.count !== 1 ? 's' : ''} loaded`;
    $('file-info').classList.add('visible');

    // Pre-fill message textarea with a personalised template
    const senderName = getSelectedSenderFirstName();
    $('raw-message').value =
`Hi {name},

[Write your message body here]

Regards,
${senderName}`;

    // Hint below textarea
    const hint = $('name-hint');
    if (hint) {
      hint.textContent = `💡 {name} will be replaced with each recipient's first name (e.g. "${data.first_name || 'Munal'}")`;
      hint.style.display = 'block';
    }

  } catch (err) {
    alert('Failed to upload file: ' + err.message);
  }
}

// ── STEP 2 — Format message ────────────────────────────────────────────────
async function handleFormat() {
  const raw = $('raw-message').value.trim();
  if (!raw) { alert('Please enter a message first.'); return; }

  const btn = $('btn-format');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner" style="border-color:#fff3;border-top-color:#fff;"></span> Formatting…';

  try {
    const res  = await fetch(`${API}/format-message`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ message: raw }),
    });
    const data = await res.json();

    if (!res.ok) {
      alert('Format error: ' + (data.detail || 'Unknown error'));
      return;
    }

    // Populate editor
    const editor = $('editor');
    // Convert plain text newlines to <br> for display
    editor.innerHTML = escapeHtml(data.formatted).replace(/\n/g, '<br>');

    // SLM badge
    const badge = $('slm-badge');
    if (data.model_used) {
      badge.className  = 'slm-badge used';
      badge.textContent = '⚡ Phi-3 formatted';
    } else {
      badge.className  = 'slm-badge skipped';
      badge.textContent = '⚠️ Model unavailable — original shown';
    }

    // Warning
    if (data.warning) {
      $('preview-warn').textContent = data.warning;
      showEl('preview-warn');
    } else {
      hideEl('preview-warn');
    }

    showEl('card-preview');
    $('card-preview').scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    alert('Failed to format message: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span>✨</span> Format &amp; Preview';
  }
}

function handleReformat() {
  $('raw-message').scrollIntoView({ behavior: 'smooth' });
  $('raw-message').focus();
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Toolbar helpers ────────────────────────────────────────────────────────
function fmt(cmd) {
  document.execCommand(cmd, false, null);
  $('editor').focus();
}

function fmtLink() {
  const url = prompt('Enter URL:');
  if (url) {
    document.execCommand('createLink', false, url);
    // Make link open in new tab
    const links = $('editor').querySelectorAll('a:not([target])');
    links.forEach(a => { a.target = '_blank'; a.rel = 'noopener'; });
  }
  $('editor').focus();
}

// ── STEP 3 — Send ──────────────────────────────────────────────────────────
async function handleSend() {
  const message = $('editor').innerHTML.trim();
  if (!message || message === '<br>') {
    alert('Message is empty. Please format a message first.');
    return;
  }
  if (recipientCount === 0) {
    alert('No recipients loaded. Please upload a file first.');
    return;
  }

  // 1. Store message + sender on server
  try {
    const res  = await fetch(`${API}/prepare`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ message, sender_upn: getSelectedSenderUPN() }),
    });
    const data = await res.json();
    if (!res.ok) { alert('Error: ' + (data.detail || 'Unknown')); return; }
  } catch (err) {
    alert('Failed to prepare broadcast: ' + err.message);
    return;
  }

  // 2. Initiate auth
  try {
    const res  = await fetch(`${API}/auth/initiate`);
    const data = await res.json();

    if (!res.ok) { alert('Auth error: ' + (data.detail || 'Unknown')); return; }

    // Show modal
    $('auth-code-display').textContent = data.user_code;
    const link = $('auth-url-link');
    link.href        = data.verification_uri;
    link.textContent = data.verification_uri;
    $('auth-modal').classList.add('visible');

    // Poll for auth status
    startAuthPolling();

  } catch (err) {
    alert('Failed to initiate auth: ' + err.message);
  }
}

function startAuthPolling() {
  if (authPollInterval) clearInterval(authPollInterval);

  authPollInterval = setInterval(async () => {
    try {
      const res  = await fetch(`${API}/auth/status`);
      const data = await res.json();

      if (data.status === 'success') {
        clearInterval(authPollInterval);
        $('auth-status-text').textContent = '✅ Authenticated! Starting broadcast…';
        setTimeout(() => {
          $('auth-modal').classList.remove('visible');
          startBroadcastStream();
        }, 900);
      } else if (data.status === 'failed') {
        clearInterval(authPollInterval);
        $('auth-status-text').textContent = '❌ Authentication failed. Please try again.';
      }
    } catch { /* polling — ignore transient errors */ }
  }, 2000);
}

// ── STEP 4 — SSE broadcast stream ─────────────────────────────────────────
function startBroadcastStream() {
  const logSection = $('log-section');
  const logPanel   = $('log-panel');
  const progBar    = $('progress-bar');
  const progLabel  = $('prog-label');
  const progFrac   = $('prog-fraction');

  logSection.classList.remove('hidden');
  logSection.style.display = 'block';
  logPanel.innerHTML = '';
  processedCount = 0;

  progLabel.textContent = 'Broadcasting…';
  progFrac.textContent  = `0 / ${totalRecipients}`;
  progBar.style.width   = '0%';

  logSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

  const es = new EventSource(`${API}/stream`);

  es.onmessage = (event) => {
    const data = JSON.parse(event.data);
    appendLog(data, logPanel);

    // Update progress for per-recipient events
    if (['sent', 'validate'].includes(data.type) && data.status === 'fail') {
      processedCount++;
      updateProgress(progBar, progLabel, progFrac);
    }
    if (data.type === 'sent' && data.status === 'ok') {
      processedCount++;
      updateProgress(progBar, progLabel, progFrac);
    }

    if (data.type === 'complete') {
      es.close();
      progBar.style.width   = '100%';
      progLabel.textContent = `Done — ${data.sent}/${data.total} delivered`;
      progFrac.textContent  = `${data.sent} / ${data.total}`;
    }
  };

  es.onerror = () => {
    appendLog({ type: 'fail', status: 'fail', text: 'Connection lost. Broadcast may have ended.' }, logPanel);
    es.close();
  };
}

function updateProgress(bar, label, frac) {
  const pct = totalRecipients > 0
    ? Math.round((processedCount / totalRecipients) * 100)
    : 0;
  bar.style.width   = pct + '%';
  label.textContent = `Broadcasting… ${pct}%`;
  frac.textContent  = `${processedCount} / ${totalRecipients}`;
}

// ── Log entry renderer ─────────────────────────────────────────────────────
const LOG_ICONS = {
  ok:         '✅',
  fail:       '❌',
  info:       'ℹ️',
  processing: '➡️',
  complete:   '🎯',
};

function appendLog(data, panel) {
  const entry = document.createElement('div');
  entry.className = `log-entry ${data.status || 'info'} ${data.type || ''}`;

  const icon = LOG_ICONS[data.status] || LOG_ICONS[data.type] || '•';

  let html = `<span class="log-icon">${icon}</span>`;
  html    += `<span class="log-text">${escapeHtml(data.text)}`;
  if (data.upn && !data.text.includes(data.upn)) {
    html += ` <span class="log-upn">${escapeHtml(data.upn)}</span>`;
  }
  html += `</span>`;

  entry.innerHTML = html;
  panel.appendChild(entry);
  panel.scrollTop = panel.scrollHeight;
}
