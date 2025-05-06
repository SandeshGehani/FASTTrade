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

    // Fetch user data from backend
    async fetchUserData() {
      const token = localStorage.getItem('access_token');
      console.log("Fetching user data with token:", token);

      if (!token) {
        console.log("No access token found, redirecting to login");
        window.location.href = '/login.html';
        return;
      }

      try {
        console.log("Making request to /api/auth/me");
        const response = await fetch('/api/auth/me', {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });

        console.log("Response status:", response.status);
        const data = await response.json();
        console.log("Response data:", data);

        if (!response.ok) {
          console.log("API request failed:", data.error);
          throw new Error(data.error || 'Failed to fetch user data');
        }

        if (data.user) {
          console.log("User data received:", data.user);
          this.userData.fullName = data.user.full_name;
          this.userData.phone = data.user.phone;
          this.userData.email = data.user.email;
          this.profileImage = data.user.profile_image || null;
          // Update localStorage with latest info
          localStorage.setItem('user', JSON.stringify(data.user));
          localStorage.setItem('profile_image', data.user.profile_image || '');
        } else {
          console.log("No user data in response");
          window.location.href = '/login.html';
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
        window.location.href = '/login.html';
      }
    },

    // Trigger file input click
    triggerFileInput() {
      document.getElementById("profile-image-upload").click()
    },

    // Handle image upload
    async handleImageUpload(event) {
      const file = event.target.files[0]
      if (!file) return

      if (!file.type.startsWith("image/")) {
        alert("Please select an image file")
        return
      }

      const formData = new FormData()
      formData.append('image', file)
      const token = localStorage.getItem('access_token')
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
        this.profileImage = data.profile_image
        localStorage.setItem('profile_image', data.profile_image || '');
        alert('Profile image updated!')
      } catch (error) {
        alert(error.message)
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
    saveProfile() {
      this.validatePhone()

      if (this.userData.newPassword) {
        this.validatePassword()
        this.validateConfirmPassword()
      }

      if (this.phoneError || this.passwordError || this.confirmPasswordError) {
        return
      }

      this.isSubmitting = true

      // Simulate API call
      setTimeout(() => {
        console.log("Profile updated:", this.userData)

        // Reset password fields
        this.userData.currentPassword = ""
        this.userData.newPassword = ""
        this.userData.confirmPassword = ""

        this.isSubmitting = false

        // Show success message
        alert("Profile updated successfully!")
      }, 1500)
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

document.addEventListener('DOMContentLoaded', function() {
  if (window.profileData) {
    const pd = profileData();
    pd.fetchUserData();
  }
});
