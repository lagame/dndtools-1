(() => {
  const form = document.getElementById('requirement-builder');
  if (!form) return;

  const template = document.getElementById('requirement-node');
  const root = document.getElementById('requirement-root');
  const status = document.getElementById('requirement-status');
  const initial = JSON.parse(document.getElementById('requirement-initial').textContent);
  const controls = new WeakMap();
  const isGroup = (type) => type === 'all' || type === 'any';
  const announce = (change) => { status.textContent = status.dataset[change]; };

  function canRestore(value, depth = 0, budget = { count: 64 }) {
    if (--budget.count < 0 || depth > 8) return false;
    return !Array.isArray(value?.children)
      || value.children.every((child) => canRestore(child, depth + 1, budget));
  }

  function setPanel(panel, enabled) {
    panel.hidden = !enabled;
    for (const control of panel.querySelectorAll('input, select, textarea')) {
      control.disabled = !enabled;
    }
  }

  function updateChildren(container) {
    const siblings = [...container.children];
    siblings.forEach((node, index) => {
      const { legend, up, down, remove } = controls.get(node);
      legend.textContent = `${legend.dataset.label} ${index + 1}`;
      up.disabled = index === 0;
      down.disabled = index === siblings.length - 1;
      remove.disabled = siblings.length <= 2;
    });
  }

  function createNode(value, isRoot = false) {
    const node = template.content.firstElementChild.cloneNode(true);
    const find = (role) => node.querySelector(`[data-role="${role}"]`);
    const state = {
      legend: node.querySelector('legend'),
      type: find('type'), group: find('group'), children: find('children'),
      named: find('named'), condition: find('condition'), name: find('original_name'),
      book: find('reference_book'), page: find('reference_page'), target: find('target_id'),
      en: find('en'), pt: find('pt_br'),
      up: find('up'), down: find('down'), remove: find('remove'), add: find('add'),
    };
    controls.set(node, state);
    state.legend.dataset.label = state.legend.textContent;
    if (isRoot) {
      state.up.parentElement.hidden = true;
    } else {
      state.type.querySelector('[data-root-only]').remove();
    }
    const type = value?.op || value?.kind || 'condition';
    if ([...state.type.options].some((option) => option.value === type)) {
      state.type.value = type;
    }
    state.name.value = value?.original_name ?? '';
    state.book.value = value?.reference?.rulebook_id ?? '';
    state.page.value = value?.reference?.page ?? '';
    state.target.value = value?.target_id ?? '';
    state.en.value = value?.en ?? '';
    state.pt.value = value?.pt_br ?? '';
    if (Array.isArray(value?.children)) {
      state.children.append(...value.children.map((child) => createNode(child)));
    }

    function syncReference() {
      const hasReference = Boolean(state.book.value || state.page.value || state.target.value);
      state.book.required = hasReference;
      state.page.required = hasReference;
    }

    function applyType() {
      const type = state.type.value;
      const grouped = isGroup(type);
      const isCondition = type === 'condition';
      state.group.hidden = !grouped;
      setPanel(state.condition, isCondition);
      setPanel(state.named, !grouped && !isCondition && type !== 'none');
      state.en.required = state.pt.required = isCondition;
      state.name.required = !state.named.hidden;
      if (grouped) {
        while (state.children.childElementCount < 2) state.children.append(createNode(null));
      }
      for (const child of state.children.children) child.disabled = !grouped;
      updateChildren(state.children);
      syncReference();
    }

    function move(offset) {
      const container = node.parentElement;
      const sibling = offset < 0 ? node.previousElementSibling : node.nextElementSibling;
      if (!sibling) return;
      if (offset < 0) container.insertBefore(node, sibling);
      else container.insertBefore(sibling, node);
      updateChildren(container);
      state.type.focus();
      announce('reordered');
    }

    state.type.addEventListener('change', applyType);
    for (const field of [state.book, state.page, state.target]) field.addEventListener('input', syncReference);
    state.up.addEventListener('click', () => move(-1));
    state.down.addEventListener('click', () => move(1));
    state.remove.addEventListener('click', () => {
      const container = node.parentElement;
      if (container.childElementCount <= 2) return;
      const focusTarget = node.nextElementSibling || node.previousElementSibling;
      node.remove();
      updateChildren(container);
      controls.get(focusTarget).type.focus();
      announce('removed');
    });
    state.add.addEventListener('click', () => {
      const child = createNode(null);
      state.children.append(child);
      updateChildren(state.children);
      controls.get(child).type.focus();
      announce('added');
    });
    applyType();
    return node;
  }

  function serialize(node) {
    const state = controls.get(node);
    const type = state.type.value;
    if (isGroup(type)) return { op: type, children: [...state.children.children].map(serialize) };
    if (type === 'none') return { op: 'none' };
    if (type === 'condition') return { kind: type, en: state.en.value.trim(), pt_br: state.pt.value.trim() };
    const result = { kind: type, original_name: state.name.value.trim() };
    if (state.book.value && state.page.value) {
      result.reference = { rulebook_id: Number(state.book.value), page: Number(state.page.value) };
    }
    if (state.target.value) result.target_id = Number(state.target.value);
    return result;
  }

  root.append(createNode(initial && canRestore(initial) ? initial : { op: 'all' }, true));
  form.addEventListener('submit', () => {
    form.elements.requirements.value = JSON.stringify(serialize(root.firstElementChild));
  });
  form.hidden = false;
})();
