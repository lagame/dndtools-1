(() => {
    const progress = document.querySelector('[data-import-progress]');
    if (!progress) return;

    const count = progress.querySelector('[data-import-count]');
    const statusUrl = new URL(window.location.href);
    statusUrl.search = '?status=1';

    async function poll() {
        if (!document.hidden) {
            try {
                const response = await fetch(statusUrl, {cache: 'no-store'});
                if (response.redirected || response.status === 403 || response.status === 404) return;
                if (response.ok) {
                    const status = await response.json();
                    if (status.state !== progress.dataset.state || !status.working) {
                        window.location.reload();
                        return;
                    }
                    if (count && count.textContent !== String(status.processed)) {
                        count.textContent = status.processed;
                    }
                }
            } catch {
                // Reconnect on the next poll. The request never controls the worker.
            }
        }
        window.setTimeout(poll, 4000);
    }

    window.setTimeout(poll, 2000);
})();
