(() => {
  const body = document.body;
  const sidebar = document.getElementById('catalog-sidebar');
  const toggle = document.getElementById('navigation-toggle');
  const close = document.getElementById('navigation-close');
  const backdrop = document.getElementById('navigation-backdrop');
  const compact = window.matchMedia('(max-width: 900px)');
  const background = [document.querySelector('.site-header'), document.getElementById('main'), document.querySelector('.site-footer')];

  function isOpen() {
    return compact.matches ? body.classList.contains('nav-open') : !body.classList.contains('nav-collapsed');
  }

  function sync() {
    const modal = compact.matches && isOpen();
    toggle.setAttribute('aria-expanded', String(isOpen()));
    backdrop.hidden = !modal;
    if (modal) {
      sidebar.setAttribute('role', 'dialog');
      sidebar.setAttribute('aria-modal', 'true');
    } else {
      sidebar.removeAttribute('role');
      sidebar.removeAttribute('aria-modal');
    }
    sidebar.setAttribute('aria-hidden', String(compact.matches && !modal));
    background.forEach(element => { if (element) element.inert = modal; });
  }

  function setOpen(open) {
    if (compact.matches) {
      body.classList.toggle('nav-open', open);
      sync();
      requestAnimationFrame(() => (open ? close : toggle).focus());
    } else {
      body.classList.toggle('nav-collapsed', !open);
      sync();
    }
  }

  toggle.addEventListener('click', () => setOpen(!isOpen()));
  close.addEventListener('click', () => setOpen(false));
  backdrop.addEventListener('click', () => setOpen(false));
  compact.addEventListener('change', () => {
    body.classList.remove('nav-open');
    sync();
  });
  sidebar.addEventListener('click', event => {
    const button = event.target.closest('.navigation-expand');
    if (!button) return;
    const panel = document.getElementById(button.getAttribute('aria-controls'));
    const expanded = button.getAttribute('aria-expanded') === 'true';
    button.setAttribute('aria-expanded', String(!expanded));
    panel.hidden = expanded;
    if (expanded && panel.contains(document.activeElement)) button.focus();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && compact.matches && isOpen()) {
      setOpen(false);
      return;
    }
    if (event.key !== 'Tab' || !compact.matches || !isOpen()) return;
    const focusable = [...sidebar.querySelectorAll('a[href], button:not([disabled])')]
      .filter(element => element.getClientRects().length);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus();
    }
  });
  sync();
})();
