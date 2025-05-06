// Registration page functionality
function registerForm() {
  return {
    fullName: "",
    phone: "",
    email: "",
    password: "",
    confirmPassword: "",
    showPassword: false,
    showConfirmPassword: false,
    isSubmitting: false,
    showVerification: false,

    // Validation errors
    emailError: "",
    phoneError: "",
    passwordError: "",
    confirmPasswordError: "",
    pinError: "",

    // Password strength
    passwordStrength: "",
    passwordStrengthText: "",
    passwordStrengthPercent: 0,

    // Password requirements
    hasUppercase: false,
    hasNumber: false,
    hasSpecial: false,
    hasMinLength: false,

    // PIN verification
    pinDigits: ["", "", "", "", "", ""], // 6-digit OTP
    isVerifying: false,

    // Computed property for form validity
    get isFormValid() {
      return (
        this.fullName &&
        this.phone &&
        this.email &&
        this.password &&
        this.confirmPassword &&
        !this.emailError &&
        !this.phoneError &&
        !this.passwordError &&
        !this.confirmPasswordError
      )
    },

    // Validate email format and domain
    validateEmail() {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!this.email) {
        this.emailError = "";
        return;
      }
      if (!emailRegex.test(this.email)) {
        this.emailError = "Please enter a valid email address";
        return;
      }
      if (!this.email.endsWith('@nu.edu.pk')) {
        this.emailError = "Only FAST-NUCES emails (@nu.edu.pk) are allowed.";
        return;
      }
      this.emailError = "";
    },

    // Validate phone number
    validatePhone() {
      const phoneRegex = /^\d{11}$/
      if (!this.phone) {
        this.phoneError = ""
        return
      }

      if (!phoneRegex.test(this.phone)) {
        this.phoneError = "Phone number must be 11 digits"
        return
      }

      this.phoneError = ""
    },

    // Validate password strength
    validatePassword() {
      if (!this.password) {
        this.passwordError = "";
        return;
      }
      if (this.password.length < 8) {
        this.passwordError = "Password must be at least 8 characters long.";
        return;
      }
      if (!/[^A-Za-z0-9]/.test(this.password)) {
        this.passwordError = "Password must contain at least one special character.";
        return;
      }
      if (!/\d/.test(this.password)) {
        this.passwordError = "Password must contain at least one number.";
        return;
      }
      this.passwordError = "";
    },

    // Validate password confirmation
    validateConfirmPassword() {
      if (!this.confirmPassword) {
        this.confirmPasswordError = ""
        return
      }

      if (this.password !== this.confirmPassword) {
        this.confirmPasswordError = "Passwords do not match"
        return
      }

      this.confirmPasswordError = ""
    },

    // Submit registration form
    async submitRegistration() {
      this.validateEmail()
      this.validatePhone()
      this.validatePassword()
      this.validateConfirmPassword()

      if (this.emailError || this.phoneError || this.passwordError || this.confirmPasswordError) {
        return
      }

      this.isSubmitting = true

      try {
        const response = await fetch('/api/auth/register', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            full_name: this.fullName,
            email: this.email,
            password: this.password,
            phone: this.phone
          })
        })

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.error || 'Registration failed')
        }

        this.isSubmitting = false
        this.showVerification = true
        // Do NOT store tokens or redirect here. Wait for OTP verification.
      } catch (error) {
        this.isSubmitting = false
        alert(error.message)
      }
    },

    // Move focus to next input field
    moveFocus(event, index) {
      const value = event.target.value
      if (value.length === 1 && index < this.pinDigits.length - 1) {
        const nextInput = event.target.nextElementSibling
        if (nextInput) {
          nextInput.focus()
        }
      }
    },

    // Handle backspace in PIN input
    handleBackspace(event, index) {
      if (event.key === 'Backspace' && !event.target.value && index > 0) {
        const prevInput = event.target.previousElementSibling
        if (prevInput) {
          prevInput.focus()
        }
      }
    },

    // Verify PIN
    async verifyPin() {
      if (!this.isPinComplete) {
        this.pinError = "Please enter the complete PIN"
        return
      }

      this.isVerifying = true
      this.pinError = ""

      try {
        const pin = this.pinDigits.join("")
        const response = await fetch('/api/auth/verify-email', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            email: this.email,
            otp: pin
          })
        })

        const data = await response.json()

        if (!response.ok) {
          throw new Error(data.error || 'Verification failed')
        }

        // Store tokens and user data
        localStorage.setItem('access_token', data.access_token)
        localStorage.setItem('refresh_token', data.refresh_token)
        localStorage.setItem('user', JSON.stringify(data.user))
        localStorage.setItem('profile_image', data.user.profile_image || '');

        // Verify token storage
        const storedToken = localStorage.getItem('access_token');
        if (!storedToken) {
          throw new Error('Failed to store authentication token');
        }

        // Get the next page from URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        let nextPage = urlParams.get('next');
        
        // If no next page specified, default to profile
        if (!nextPage) {
          nextPage = '/profile.html';
        } else {
          // Decode the next page URL
          nextPage = decodeURIComponent(nextPage);
          // Prevent redirecting back to auth pages
          if (nextPage.includes('login.html') || nextPage.includes('register.html')) {
            nextPage = '/profile.html';
          }
        }

        window.location.href = nextPage;
      } catch (error) {
        this.isVerifying = false
        this.pinError = error.message
      }
    },

    // Computed property for PIN completion
    get isPinComplete() {
      return this.pinDigits.every(digit => digit.length === 1)
    }
  }
}
