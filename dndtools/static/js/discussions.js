(() => {
  const frames = [...document.querySelectorAll('.record-discussions-frame')];
  if (!frames.length) return;
  window.addEventListener('message', (event) => {
    if (event.origin !== location.origin || event.data?.type !== 'dnd-discussion-height') return;
    const frame = frames.find((item) => item.contentWindow === event.source);
    if (frame && Number.isFinite(event.data.height)) {
      frame.style.height = `${Math.max(320, Math.min(16000, event.data.height))}px`;
    }
  });
})();
