(() => {
  if (window.parent === window) return;
  document.documentElement.dataset.embedded = 'true';
  const reportHeight = () => {
    const height = Math.ceil(document.documentElement.scrollHeight);
    window.parent.postMessage({ type: 'dnd-discussion-height', height }, location.origin);
  };
  new ResizeObserver(reportHeight).observe(document.body);
  window.addEventListener('load', reportHeight);
  reportHeight();
})();
