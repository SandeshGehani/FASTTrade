const AuthManager = (() => {
  const state = {
    token: null,
    user: null,
    initialized: false
  };

  const listeners = [];
  let initPromise = null;

  function notify() {
    const snapshot = getState();
    listeners.forEach((cb) => {
      try {
        cb(snapshot);
      } catch (error) {
        console.error('Auth listener failed', error);
      }
    });
  }

  async function fetchCurrentUser() {
    if (!state.token) {
      state.user = null;
      return null;
    }

    try {
      const response = await fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${state.token}` }
      });
      if (!response.ok) {
        throw new Error('Auth check failed');
      }
      const data = await response.json();
      if (data?.user) {
        state.user = data.user;
        localStorage.setItem('user', JSON.stringify(data.user));
        localStorage.setItem('profile_image', data.user.profile_image || '');
        return state.user;
      }
    } catch (error) {
      clearSession(false);
      console.warn('Failed to refresh auth state:', error.message);
      toast?.show?.('Session expired. Please log in again.', 'error');
    }
    return null;
  }

  function clearSession(redirect = true) {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    localStorage.removeItem('profile_image');
    state.token = null;
    state.user = null;
    if (redirect) {
      window.location.href = 'login.html';
    }
  }

  async function init() {
    if (initPromise) return initPromise;
    initPromise = (async () => {
      state.token = localStorage.getItem('access_token');
      if (state.token) {
        await fetchCurrentUser();
      } else {
        try {
          state.user = JSON.parse(localStorage.getItem('user') || 'null');
        } catch {
          state.user = null;
        }
      }
      state.initialized = true;
      notify();
      return getState();
    })();
    return initPromise;
  }

  function getState() {
    return {
      token: state.token,
      user: state.user,
      initialized: state.initialized
    };
  }

  function onChange(callback) {
    if (typeof callback !== 'function') return;
    listeners.push(callback);
    if (state.initialized) {
      callback(getState());
    }
  }

  function requireLogin(options = {}) {
    const { redirect = true, next = window.location.pathname + window.location.search } = options;
    if (!state.token) {
      if (redirect) {
        window.location.href = `login.html?next=${encodeURIComponent(next)}`;
      }
      return false;
    }
    return true;
  }

  function requireAdmin(options = {}) {
    if (!requireLogin(options)) return false;
    if (state.user?.role !== 'admin') {
      toast?.show?.('Admin access required.', 'error');
      if (options.redirect !== false) {
        window.location.href = options.fallback || 'index.html';
      }
      return false;
    }
    return true;
  }

  function logout() {
    clearSession();
  }

  function isAdmin() {
    return state.user?.role === 'admin';
  }

  return {
    init,
    getState,
    onChange,
    requireLogin,
    requireAdmin,
    logout,
    isAdmin,
    refreshUser: fetchCurrentUser
  };
})();

window.auth = AuthManager;
document.addEventListener('DOMContentLoaded', () => {
  auth.init();
});

