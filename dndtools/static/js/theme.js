(() => {
  const key = 'dnd_theme_v2';
  const valid = new Set(['standard', 'modern', 'simple']);
  const identityStylesheet = document.getElementById('identity-stylesheet');
  const siteIcon = document.getElementById('site-icon');
  let theme = 'standard';
  try {
    const stored = localStorage.getItem(key);
    if (valid.has(stored)) {
      theme = stored;
    } else {
      const old = localStorage.getItem('dnd_theme_v1');
      const migrated = new Map([['modern', 'standard'], ['simple', 'simple'], ['classic', 'modern']]).get(old);
      if (migrated) {
        theme = migrated;
        localStorage.setItem(key, migrated);
        localStorage.removeItem('dnd_theme_v1');
      }
    }
  } catch (_) {
    // The current page can still switch themes when storage is unavailable.
  }

  function apply(value) {
    theme = value;
    document.documentElement.dataset.theme = value;
    if (value === 'standard') {
      identityStylesheet.href = identityStylesheet.dataset.href;
    } else {
      identityStylesheet.removeAttribute('href');
    }
    siteIcon.href = value === 'simple' ? 'data:,' : siteIcon.dataset.href;
  }

  function syncImages() {
    for (const image of document.querySelectorAll('img[data-theme-src]')) {
      if (theme === 'simple') image.removeAttribute('src');
      else if (!image.hasAttribute('src')) image.src = image.dataset.themeSrc;
    }
  }

  apply(theme);
  document.addEventListener('DOMContentLoaded', () => {
    const picker = document.getElementById('theme-select');
    syncImages();
    picker.value = theme;
    picker.parentElement.hidden = false;
    picker.addEventListener('change', () => {
      if (!valid.has(picker.value)) return;
      apply(picker.value);
      syncImages();
      try { localStorage.setItem(key, picker.value); } catch (_) { /* no storage */ }
    });
  });
})();
