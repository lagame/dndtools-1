(() => {
  const notice = document.getElementById('privacy-notice');
  const dismiss = document.getElementById('privacy-notice-dismiss');
  if (!notice || !dismiss) return;

  const key = 'dnd_privacy_notice_v1';
  const lifetime = 180 * 24 * 60 * 60 * 1000;
  const syncShortcutPosition = () => {
    document.documentElement.style.setProperty('--privacy-notice-height', notice.hidden ? '0px' : `${notice.offsetHeight}px`);
  };
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
  syncShortcutPosition();
  window.addEventListener('resize', syncShortcutPosition);
  if (window.ResizeObserver) new ResizeObserver(syncShortcutPosition).observe(notice);

  dismiss.addEventListener('click', () => {
    try { localStorage.setItem(key, String(Date.now())); } catch (_) { /* no storage */ }
    notice.hidden = true;
    syncShortcutPosition();
  });
})();
