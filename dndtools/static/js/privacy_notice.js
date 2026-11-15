(() => {
  const notice = document.getElementById('privacy-notice');
  const dismiss = document.getElementById('privacy-notice-dismiss');
  if (!notice || !dismiss) return;

  const key = 'dnd_privacy_notice_v1';
  const lifetime = 180 * 24 * 60 * 60 * 1000;
  try {
    const stored = localStorage.getItem(key);
    const acknowledgedAt = Number(stored);
    const age = Date.now() - acknowledgedAt;
    if (stored && acknowledgedAt > 0 && age >= 0 && age < lifetime) {
      notice.hidden = true;
    } else if (stored) {
      localStorage.removeItem(key);
    }
  } catch (_) {
    // The notice remains usable when browser storage is unavailable.
  }

  dismiss.addEventListener('click', () => {
    try { localStorage.setItem(key, String(Date.now())); } catch (_) { /* no storage */ }
    notice.hidden = true;
  });
})();
