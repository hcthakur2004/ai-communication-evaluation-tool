const transcriptEl = document.getElementById('transcript');
const fileInput = document.getElementById('fileInput');
const useSemanticEl = document.getElementById('useSemantic');
const rubricPathEl = document.getElementById('rubricPath');
const scoreBtn = document.getElementById('scoreBtn');

const resultsEl = document.getElementById('results');
const overallEl = document.getElementById('overall');
const wordCountEl = document.getElementById('wordCount');
const criteriaBodyEl = document.getElementById('criteriaBody');
const toastEl = document.getElementById('toast');

fileInput.addEventListener('change', async (e) => {
  const file = e.target.files && e.target.files[0];
  if (!file) return;
  const text = await file.text();
  transcriptEl.value = text;
});

scoreBtn.addEventListener('click', async () => {
  clearToast();
  const transcript = transcriptEl.value.trim();
  if (!transcript) {
    showToast('Please paste a transcript.');
    return;
  }
  const payload = {
    transcript,
    use_semantic: useSemanticEl.checked,
  };
  const customPath = rubricPathEl.value.trim();
  if (customPath) payload.rubric_path = customPath;

  setLoading(true);
  try {
    const res = await fetch('/score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    let data;
    try { data = await res.json(); } catch (_) { data = null; }
    if (!res.ok) {
      const msg = (data && (data.detail?.[0]?.msg || data.error || data.message)) || 'Scoring failed. Please check input.';
      showToast(msg);
      return;
    }
    renderResults(data);
    // Ensure results are visible to the user
    try { resultsEl.scrollIntoView({ behavior: 'smooth', block: 'start' }); } catch (_) {}
  } catch (err) {
    console.error(err);
    showToast('Failed to score. Check backend is running.');
  } finally {
    setLoading(false);
  }
});

function renderResults(data) {
  resultsEl.hidden = false;
  overallEl.textContent = `${data.overall_score}`;
  wordCountEl.textContent = `${data.words}`;
  criteriaBodyEl.innerHTML = '';

  const rows = (data.criteria || []).map((c) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(c.criterion)}</td>
      <td><strong>${c.score}</strong></td>
      <td>${c.semantic_similarity}</td>
      <td>${(c.keyword_hits || []).join(', ')}</td>
      <td>${escapeHtml(c.feedback || '')}</td>
    `;
    return tr;
  });
  rows.forEach((tr) => criteriaBodyEl.appendChild(tr));
}

function setLoading(isLoading) {
  if (isLoading) {
    scoreBtn.disabled = true;
    scoreBtn.classList.add('loading');
  } else {
    scoreBtn.disabled = false;
    scoreBtn.classList.remove('loading');
  }
}

function showToast(message) {
  if (toastEl) {
    toastEl.textContent = message;
    toastEl.hidden = false;
  } else {
    // Fallback if toast element is missing
    alert(message);
  }
}
function clearToast() {
  if (toastEl) {
    toastEl.textContent = '';
    toastEl.hidden = true;
  }
}

function escapeHtml(str) {
  return String(str)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}