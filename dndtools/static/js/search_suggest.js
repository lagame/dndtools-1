(() => {
  for (const form of document.querySelectorAll('[data-search-suggest]')) {
    const input = form.querySelector('input[name="q"]');
    const list = form.querySelector('[role="listbox"]');
    const status = form.querySelector('[role="status"]');
    let controller;
    let timer;
    let sequence = 0;
    let active = -1;

    function hide() {
      list.hidden = true;
      list.replaceChildren();
      status.hidden = true;
      input.setAttribute('aria-expanded', 'false');
      input.removeAttribute('aria-activedescendant');
      active = -1;
    }

    function showStatus(message) {
      status.textContent = message;
      status.hidden = false;
    }

    function select(index) {
      const options = [...list.querySelectorAll('[role="option"]')];
      if (!options.length) return;
      active = (index + options.length) % options.length;
      options.forEach((option, position) => option.setAttribute('aria-selected', String(position === active)));
      input.setAttribute('aria-activedescendant', options[active].id);
      options[active].scrollIntoView({block: 'nearest'});
    }

    input.addEventListener('input', () => {
      clearTimeout(timer);
      controller?.abort();
      const current = ++sequence;
      const query = input.value.trim();
      hide();
      if (query.length < 2) return;
      showStatus('Searching…');
      timer = setTimeout(async () => {
        controller = new AbortController();
        try {
          const response = await fetch(`${form.dataset.suggestUrl}?q=${encodeURIComponent(query)}`, {signal: controller.signal});
          if (!response.ok) throw new Error('Suggestion request failed');
          const data = await response.json();
          if (current !== sequence || input.value.trim() !== query) return;
          for (const [index, item] of data.results.entries()) {
            const row = document.createElement('li');
            const link = document.createElement('a');
            const detail = document.createElement('small');
            link.id = `${list.id}-option-${index}`;
            link.setAttribute('role', 'option');
            link.setAttribute('aria-selected', 'false');
            link.href = item.url;
            link.textContent = item.title;
            detail.textContent = [item.category, item.book, item.edition].filter(Boolean).join(' · ');
            link.append(detail);
            row.append(link);
            list.append(row);
          }
          list.hidden = !data.results.length;
          status.hidden = true;
          if (!data.results.length) showStatus('No suggestions. Press Enter to search all content.');
          input.setAttribute('aria-expanded', String(data.results.length > 0));
        } catch (error) {
          if (error.name !== 'AbortError' && current === sequence) {
            hide();
            showStatus('Suggestions unavailable. Press Enter to search the catalog.');
          }
        }
      }, 250);
    });

    input.addEventListener('keydown', event => {
      if (event.key === 'Escape') { hide(); return; }
      if (list.hidden) return;
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        select(active + (event.key === 'ArrowDown' ? 1 : -1));
      } else if (event.key === 'Enter' && active >= 0) {
        event.preventDefault();
        list.querySelectorAll('[role="option"]')[active].click();
      }
    });
    document.addEventListener('click', event => { if (!form.contains(event.target)) hide(); });
    form.addEventListener('submit', () => { clearTimeout(timer); controller?.abort(); });
  }
})();
