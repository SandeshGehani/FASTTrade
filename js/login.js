// Login page functionality
function loginData() {
  return {
    // Login form state
    email: "",
    password: "",
    showPassword: false,
    isLoading: false,
    emailError: "",
    passwordError: "",
    loginError: "",
    rememberMe: false,
    mobileMenuOpen: false,

    // Validate login email
    validateEmail() {
      if (!this.email) {
        this.emailError = "Email is required";
        return;
      }
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(this.email)) {
        this.emailError = "Please enter a valid email address";
        return;
      }
      this.emailError = "";
    },

    // Validate login password
    validatePassword() {
      if (!this.password) {
        this.passwordError = "Password is required";
        return;
      }
      this.passwordError = "";
    },

    // Handle login
    async handleLogin() {
      this.isLoading = true;
      this.loginError = "";
      this.validateEmail();
      this.validatePassword();
      if (this.emailError || this.passwordError) {
        this.isLoading = false;
        return;
      }
      try {
        const response = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: this.email, password: this.password })
        });
        const data = await response.json();
        if (!response.ok) {
          this.loginError = data.message || "Login failed";
          this.isLoading = false;
          return;
        }
        localStorage.setItem('access_token', data.access_token);
        if (data.refresh_token) localStorage.setItem('refresh_token', data.refresh_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        localStorage.setItem('user_email', data.user.email);
        localStorage.setItem('profile_image', data.user.profile_image || '');
        // Redirect to next page or profile
        const urlParams = new URLSearchParams(window.location.search);
        let nextPage = urlParams.get('next');
        if (!nextPage) {
          nextPage = '/profile.html';
        } else {
          nextPage = decodeURIComponent(nextPage);
          if (nextPage.includes('login.html') || nextPage.includes('register.html')) {
            nextPage = '/profile.html';
          }
        }
        window.location.href = nextPage;
      } catch (e) {
        this.loginError = "An error occurred. Please try again.";
      } finally {
        this.isLoading = false;
      }
    },

    init() {
      // Check if user is already logged in
      if (localStorage.getItem('access_token')) {
        const urlParams = new URLSearchParams(window.location.search);
        const nextPage = urlParams.get('next');
        if (nextPage) {
          window.location.href = decodeURIComponent(nextPage);
        } else {
          window.location.href = '/profile.html';
        }
      }
    }
  }
}

// Initialize auth data
const authData = {
    isLogin: true,
    loading: false,
    errors: {},
    formData: {
        email: '',
        password: '',
        fullName: '',
        confirmPassword: ''
    }
};

// DOM Elements
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const toggleForms = document.querySelectorAll('.auth-footer a');
const socialButtons = document.querySelectorAll('.social-btn');
const passwordInputs = document.querySelectorAll('input[type="password"]');
const togglePasswordButtons = document.querySelectorAll('.toggle-password');

// Initialize the page
function init() {
    // Add event listeners
    toggleForms.forEach(link => {
        link.addEventListener('click', toggleAuthForm);
    });

    socialButtons.forEach(button => {
        button.addEventListener('click', handleSocialLogin);
    });

    passwordInputs.forEach(input => {
        input.addEventListener('input', validatePassword);
    });

    togglePasswordButtons.forEach(button => {
        button.addEventListener('click', togglePasswordVisibility);
    });

    // Add form submission handlers
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }

    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
}

// Toggle between login and register forms
function toggleAuthForm(event) {
    event.preventDefault();
    authData.isLogin = !authData.isLogin;
    
    // Update form visibility
    loginForm.style.display = authData.isLogin ? 'block' : 'none';
    registerForm.style.display = authData.isLogin ? 'none' : 'block';
    
    // Update toggle links
    toggleForms.forEach(link => {
        link.textContent = authData.isLogin ? 'Create an account' : 'Already have an account?';
    });
}

// Handle social login
function handleSocialLogin(event) {
    event.preventDefault();
    const provider = event.currentTarget.dataset.provider;
    
    // Show loading state
    setLoading(true);
    
    // Redirect to social login endpoint
    window.location.href = `login.html`;
}

// Toggle password visibility
function togglePasswordVisibility(event) {
    const button = event.currentTarget;
    const input = button.previousElementSibling;
    const isPassword = input.type === 'password';
    
    input.type = isPassword ? 'text' : 'password';
    button.innerHTML = isPassword ? '<i class="fas fa-eye"></i>' : '<i class="fas fa-eye-slash"></i>';
}

// Validate password
function validatePassword(event) {
    const input = event.target;
    const form = input.closest('form');
    const isRegister = form.id === 'registerForm';
    
    if (isRegister) {
        const password = form.querySelector('input[name="password"]').value;
        const confirmPassword = form.querySelector('input[name="confirmPassword"]').value;
        
        if (password && confirmPassword && password !== confirmPassword) {
            showError('confirmPassword', 'Passwords do not match');
        } else {
            clearError('confirmPassword');
        }
    }
}

// Handle login form submission
async function handleLogin(event) {
    event.preventDefault();
    setLoading(true);
    clearErrors();
    
    const formData = new FormData(loginForm);
    const data = {
        email: formData.get('email'),
        password: formData.get('password')
    };
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // Store token and redirect
            localStorage.setItem('accessToken', result.token);
            window.location.href = '/';
        } else {
            showError('email', result.message || 'Invalid credentials');
        }
    } catch (error) {
        showError('email', 'An error occurred. Please try again.');
    } finally {
        setLoading(false);
    }
}

// Handle register form submission
async function handleRegister(event) {
    event.preventDefault();
    setLoading(true);
    clearErrors();
    
    const formData = new FormData(registerForm);
    const data = {
        fullName: formData.get('fullName'),
        email: formData.get('email'),
        password: formData.get('password')
    };
    
    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // Store token and redirect
            localStorage.setItem('accessToken', result.token);
            window.location.href = '/';
        } else {
            showError('email', result.message || 'Registration failed');
        }
    } catch (error) {
        showError('email', 'An error occurred. Please try again.');
    } finally {
        setLoading(false);
    }
}

// Helper functions
function setLoading(loading) {
    authData.loading = loading;
    const buttons = document.querySelectorAll('.btn-primary');
    buttons.forEach(button => {
        button.disabled = loading;
        button.innerHTML = loading ? 
            '<i class="fas fa-spinner fa-spin"></i> Processing...' : 
            button.dataset.originalText;
    });
}

function showError(field, message) {
    authData.errors[field] = message;
    const input = document.querySelector(`[name="${field}"]`);
    if (input) {
        input.classList.add('error');
        const errorElement = input.nextElementSibling;
        if (errorElement && errorElement.classList.contains('error-message')) {
            errorElement.textContent = message;
        }
    }
}

function clearError(field) {
    delete authData.errors[field];
    const input = document.querySelector(`[name="${field}"]`);
    if (input) {
        input.classList.remove('error');
        const errorElement = input.nextElementSibling;
        if (errorElement && errorElement.classList.contains('error-message')) {
            errorElement.textContent = '';
        }
    }
}

function clearErrors() {
    Object.keys(authData.errors).forEach(field => clearError(field));
}

// Initialize the page
document.addEventListener('DOMContentLoaded', init);
