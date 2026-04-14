(() => {
  const container = document.createElement('div');
  container.className = 'toast-container';
  document.addEventListener('DOMContentLoaded', () => {
    document.body.appendChild(container);
  });

  function createToast(message, variant = 'info', duration = 4000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${variant}`;
    toast.textContent = message;
    container.appendChild(toast);
    requestAnimationFrame(() => {
      toast.classList.add('visible');
    });

    setTimeout(() => {
      toast.classList.remove('visible');
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  window.toast = {
    show: createToast
  };
})();

