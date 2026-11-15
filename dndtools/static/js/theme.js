(() => {
  const key = 'dnd_theme_v1';
  const valid = new Set(['modern', 'simple', 'classic']);
  const identityStylesheet = document.getElementById('identity-stylesheet');
  let theme = 'modern';
  try {
    const stored = localStorage.getItem(key);
    if (valid.has(stored)) theme = stored;
  } catch (_) {
    // The current page can still switch themes when storage is unavailable.
  }

  function apply(value) {
    theme = value;
    document.documentElement.dataset.theme = value;
    identityStylesheet.disabled = value !== 'modern';
  }

  apply(theme);
  document.addEventListener('DOMContentLoaded', () => {
    const picker = document.getElementById('theme-select');
    picker.value = theme;
    picker.parentElement.hidden = false;
    picker.addEventListener('change', () => {
      if (!valid.has(picker.value)) return;
      apply(picker.value);
      try { localStorage.setItem(key, picker.value); } catch (_) { /* no storage */ }
    });
  });
})();
