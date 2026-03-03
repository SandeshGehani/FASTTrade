const NAVBAR_PLACEHOLDER_ID = 'navbar';
const NAVBAR_TEMPLATE_URL = 'partials/navbar.html';
const PROFILE_PLACEHOLDER = 'static/images/default.png';

async function loadNavbarTemplate() {
  try {
    const response = await fetch(NAVBAR_TEMPLATE_URL, { cache: 'no-store' });
    if (!response.ok) throw new Error('Failed to fetch navbar template');
    return await response.text();
  } catch (error) {
    console.error('Navbar template load failed:', error);
    return '';
  }
}

function submitSearch(value) {
  const query = value.trim();
  const destination = query ? `listing.html?search=${encodeURIComponent(query)}` : 'listing.html';
  window.location.href = destination;
}

function setActiveLinks(container) {
  const path = window.location.pathname.toLowerCase();
  const mappings = [
    { key: 'index', match: ['/', '/index.html'] },
    { key: 'listing', match: ['/listing'] },
    { key: 'about', match: ['/about'] },
    { key: 'messages', match: ['/messages'] },
    { key: 'profile', match: ['/profile'] }
  ];
  const active = mappings.find(item => item.match.some(segment => path.endsWith(segment)));
  if (!active) return;
  container.querySelectorAll(`[data-route="${active.key}"]`).forEach(link => link.classList.add('active'));
}

function toggleAuthSections(container, isLoggedIn, isAdmin) {
  const toggle = (selector, show) => {
    container.querySelectorAll(selector).forEach(el => {
      el.style.display = show ? '' : 'none';
    });
  };
  toggle('[data-auth-section="guest"]', !isLoggedIn);
  toggle('[data-auth-section="authenticated"]', isLoggedIn);
  toggle('[data-mobile-section="guest"]', !isLoggedIn);
  toggle('[data-mobile-section="authenticated"]', isLoggedIn);
  toggle('[data-admin-link]', isLoggedIn && isAdmin);
}

let cleanupProfileListeners = null;

function initProfileControls(container, state) {
  const profileImg = container.querySelector('[data-profile-image]');
  if (profileImg) {
    const userProfileImage = state.user?.profile_image || localStorage.getItem('profile_image');
    profileImg.src = userProfileImage || PROFILE_PLACEHOLDER;
    profileImg.onerror = () => {
      profileImg.src = PROFILE_PLACEHOLDER;
    };
  }

  const profileTrigger = container.querySelector('[data-profile-trigger]');
  const dropdown = container.querySelector('[data-profile-dropdown]');
  if (cleanupProfileListeners) {
    cleanupProfileListeners();
    cleanupProfileListeners = null;
  }
  if (profileTrigger && dropdown) {
    const toggleDropdown = (event) => {
      event.stopPropagation();
      dropdown.classList.toggle('open');
      profileTrigger.setAttribute('aria-expanded', dropdown.classList.contains('open'));
    };
    const handleOutsideClick = (event) => {
      if (!dropdown.contains(event.target) && !profileTrigger.contains(event.target)) {
        dropdown.classList.remove('open');
        profileTrigger.setAttribute('aria-expanded', 'false');
      }
    };
    profileTrigger.addEventListener('click', toggleDropdown);
    document.addEventListener('click', handleOutsideClick);
    cleanupProfileListeners = () => {
      profileTrigger.removeEventListener('click', toggleDropdown);
      document.removeEventListener('click', handleOutsideClick);
    };
  }
}

function initNavbarEvents(container) {
  const mobileToggle = container.querySelector('[data-nav-toggle]');
  const mobileMenu = container.querySelector('[data-mobile-menu]');
  if (mobileToggle && mobileMenu) {
    const toggleMenu = (event) => {
      event.stopPropagation();
      const isOpen = mobileMenu.classList.toggle('open');
      mobileToggle.classList.toggle('active', isOpen);
      // Change icon from bars to X when open
      const icon = mobileToggle.querySelector('i');
      if (icon) {
        if (isOpen) {
          icon.classList.remove('fa-bars');
          icon.classList.add('fa-times');
        } else {
          icon.classList.remove('fa-times');
          icon.classList.add('fa-bars');
        }
      }
    };
    
    mobileToggle.addEventListener('click', toggleMenu);
    
    // Close menu when clicking outside
    document.addEventListener('click', (event) => {
      if (!mobileMenu.contains(event.target) && !mobileToggle.contains(event.target)) {
        if (mobileMenu.classList.contains('open')) {
          mobileMenu.classList.remove('open');
          mobileToggle.classList.remove('active');
          const icon = mobileToggle.querySelector('i');
          if (icon) {
            icon.classList.remove('fa-times');
            icon.classList.add('fa-bars');
          }
        }
      }
    });
    
    // Close menu when clicking on a link inside
    mobileMenu.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        mobileMenu.classList.remove('open');
        mobileToggle.classList.remove('active');
        const icon = mobileToggle.querySelector('i');
        if (icon) {
          icon.classList.remove('fa-times');
          icon.classList.add('fa-bars');
        }
      });
    });
  }

  container.querySelectorAll('[data-chat-button]').forEach(button => {
    button.addEventListener('click', () => {
      window.location.href = 'messages.html';
    });
  });

  container.querySelectorAll('[data-login-btn]').forEach(button => {
    button.addEventListener('click', () => {
      window.location.href = 'login.html';
    });
  });

  container.querySelectorAll('[data-logout]').forEach(button => {
    button.addEventListener('click', (event) => {
      event.preventDefault();
      auth.logout();
    });
  });

  container.querySelectorAll('[data-nav-search-btn]').forEach(button => {
    const input = button.closest('.search-input-wrapper')?.querySelector('[data-nav-search-input]');
    if (input) {
      button.addEventListener('click', () => submitSearch(input.value));
      input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
          event.preventDefault();
          submitSearch(input.value);
        }
      });
    }
  });
}

async function updateUnreadBadge(container) {
  if (!container) {
    container = document.getElementById(NAVBAR_PLACEHOLDER_ID);
  }
  if (!container) return;
  
  const badge = container.querySelector('[data-unread-badge]');
  if (!badge) return;
  
  try {
    const token = auth.getState().token;
    if (!token) {
      badge.style.display = 'none';
      return;
    }
    
    const response = await fetch('/api/messages/unread-count', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    if (!response.ok) {
      console.error('Failed to fetch unread count');
      return;
    }
    
    const data = await response.json();
    const unreadCount = data.unread_count || 0;
    
    if (unreadCount > 0) {
      badge.textContent = unreadCount > 99 ? '99+' : unreadCount.toString();
      badge.style.display = 'flex';
    } else {
      badge.style.display = 'none';
    }
  } catch (error) {
    console.error('Error updating unread badge:', error);
  }
}

// Make it globally accessible
window.updateUnreadBadge = updateUnreadBadge;

async function initNavbar() {
  const placeholder = document.getElementById(NAVBAR_PLACEHOLDER_ID);
  if (!placeholder) return;

  placeholder.innerHTML = await loadNavbarTemplate();
  if (!placeholder.innerHTML.trim()) return;

  await auth.init();
  const state = auth.getState();
  const isLoggedIn = Boolean(state.token && state.user);
  const isAdmin = auth.isAdmin();

  const renderState = (currentState) => {
    setActiveLinks(placeholder);
    toggleAuthSections(placeholder, Boolean(currentState.token && currentState.user), auth.isAdmin());
    initProfileControls(placeholder, currentState);
  };

  renderState(state);
  initNavbarEvents(placeholder);
  auth.onChange(renderState);
  
  // Update unread badge if logged in
  if (isLoggedIn) {
    updateUnreadBadge(placeholder);
    // Update badge every 30 seconds
    setInterval(() => updateUnreadBadge(placeholder), 30000);
  }
}

document.addEventListener('DOMContentLoaded', initNavbar);

