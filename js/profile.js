// Profile page functionality
function profileData() {
  return {
    // Profile image
    profileImage: null,

    // User data
    userData: {
      fullName: "",
      phone: "",
      email: "",
      currentPassword: "",
      newPassword: "",
      confirmPassword: "",
      listingsCount: 0,
      soldCount: 0,
    },

    // Form state
    showCurrentPassword: false,
    showNewPassword: false,
    showConfirmPassword: false,
    isSubmitting: false,

    // Validation errors
    phoneError: "",
    passwordError: "",
    confirmPasswordError: "",

    // Password strength
    passwordStrength: "",
    passwordStrengthText: "",
    passwordStrengthPercent: 0,

    // Password requirements
    hasUppercase: false,
    hasNumber: false,
    hasSpecial: false,
    hasMinLength: false,

    async initProfile() {
      await auth.init();
      if (!auth.requireLogin()) return;
      await this.fetchUserData();
    },

    // Fetch user data from backend
    async fetchUserData() {
      const { token } = auth.getState();
      if (!token) {
        auth.requireLogin();
        return;
      }

      try {
        const response = await fetch('/api/auth/me', {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.error || 'Failed to fetch user data');
        }

        if (data.user) {
          this.userData.fullName = data.user.full_name;
          this.userData.phone = data.user.phone;
          this.userData.email = data.user.email;
          this.profileImage = data.user.profile_image || 'static/images/default.png';
          localStorage.setItem('user', JSON.stringify(data.user));
          localStorage.setItem('profile_image', data.user.profile_image || '');
        } else {
          auth.requireLogin();
        }

        // Fetch profile stats (listingsCount, soldCount)
        const statsRes = await fetch('/api/profile/stats', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (statsRes.ok) {
          const stats = await statsRes.json();
          this.userData.listingsCount = stats.listingsCount;
          this.userData.soldCount = stats.soldCount;
        } else {
          this.userData.listingsCount = 0;
          this.userData.soldCount = 0;
        }
      } catch (error) {
        console.error("Error fetching user data:", error);
        toast?.show?.(error.message || 'Failed to load profile.', 'error');
        auth.requireLogin();
      }
    },

    // Trigger file input click
    triggerFileInput() {
      document.getElementById("profile-image-upload").click()
    },

    // Handle image upload
    async handleImageUpload(event) {
      const file = event.target.files[0];
      if (!file) return;

      if (!file.type.startsWith("image/")) {
        toast?.show?.("Please select an image file", 'error');
        return;
      }

      const formData = new FormData()
      formData.append('image', file)
      const { token } = auth.getState();
      if (!token) {
        auth.requireLogin();
        return;
      }
      try {
        const response = await fetch('/api/profile/upload-image', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formData
        })
        const data = await response.json()
        if (!response.ok) throw new Error(data.error || 'Failed to upload image')
        this.profileImage = data.profile_image || 'static/images/default.png';
        localStorage.setItem('profile_image', data.profile_image || '');
        toast?.show?.('Profile image updated!', 'success');
      } catch (error) {
        toast?.show?.(error.message, 'error');
      }
    },

    // Validate phone number
    validatePhone() {
      const phoneRegex = /^[0-9]{11}$/
      if (!this.userData.phone) {
        this.phoneError = ""
        return
      }

      if (!phoneRegex.test(this.userData.phone)) {
        this.phoneError = "Please enter a valid 11-digit phone number"
        return
      }

      this.phoneError = ""
    },

    // Validate password
    validatePassword() {
      if (!this.userData.newPassword) {
        this.passwordStrength = ""
        this.passwordStrengthText = ""
        this.passwordStrengthPercent = 0
        this.passwordError = ""
        return
      }

      // Check requirements
      this.hasMinLength = this.userData.newPassword.length >= 6

      // Calculate strength
      let strength = 0
      if (this.hasMinLength) strength = 100

      this.passwordStrengthPercent = strength

      if (strength < 50) {
        this.passwordStrength = "weak"
        this.passwordStrengthText = "Weak"
      } else if (strength < 100) {
        this.passwordStrength = "medium"
        this.passwordStrengthText = "Medium"
      } else {
        this.passwordStrength = "strong"
        this.passwordStrengthText = "Strong"
      }

      // Set error if not meeting requirements
      if (this.userData.newPassword && !this.hasMinLength) {
        this.passwordError = "Password must be at least 6 characters long"
      } else {
        this.passwordError = ""
      }
    },

    // Validate confirm password
    validateConfirmPassword() {
      if (!this.userData.confirmPassword) {
        this.confirmPasswordError = ""
        return
      }

      if (this.userData.newPassword !== this.userData.confirmPassword) {
        this.confirmPasswordError = "Passwords do not match"
        return
      }

      this.confirmPasswordError = ""
    },

    // Save profile
    async saveProfile() {
      this.validatePhone()

      if (this.userData.newPassword) {
        this.validatePassword()
        this.validateConfirmPassword()
      }

      if (this.phoneError || this.passwordError || this.confirmPasswordError) {
        toast?.show?.('Please fix the highlighted fields.', 'error');
        return
      }

      this.isSubmitting = true

      try {
        await auth.init();
        if (!auth.requireLogin()) {
          this.isSubmitting = false;
          return;
        }
        const { token } = auth.getState();
        const payload = {
          full_name: this.userData.fullName,
          phone: this.userData.phone
        };
        if (this.userData.newPassword) {
          payload.current_password = this.userData.currentPassword;
          payload.new_password = this.userData.newPassword;
        }

        const response = await fetch('/api/profile', {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });

        const result = await response.json();
        if (!response.ok) {
          throw new Error(result.error || 'Failed to update profile');
        }

        const updatedUser = result.user;
        this.userData.fullName = updatedUser.full_name;
        this.userData.phone = updatedUser.phone;
        this.userData.email = updatedUser.email;
        this.userData.currentPassword = "";
        this.userData.newPassword = "";
        this.userData.confirmPassword = "";
        localStorage.setItem('user', JSON.stringify(updatedUser));
        toast?.show?.('Profile updated successfully!', 'success');
      } catch (error) {
        console.error('Profile update failed:', error);
        toast?.show?.(error.message, 'error');
      } finally {
        this.isSubmitting = false;
      }
    },

    // Reset form
    resetForm() {
      // Reset to original values
      this.userData = {
        fullName: "",
        phone: "",
        email: "",
        currentPassword: "",
        newPassword: "",
        confirmPassword: "",
        listingsCount: 0,
        soldCount: 0,
      }

      // Clear errors
      this.phoneError = ""
      this.passwordError = ""
      this.confirmPasswordError = ""
    },
  }
}
