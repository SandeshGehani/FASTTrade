// Create listing page functionality
function createListingData() {
  return {
    // Listing data
    listing: {
      title: "",
      price: "",
      condition: "",
      category_id: "",
      description: "",
    },

    // Image handling
    imagePreview: null,
    isSubmitting: false,
    error: null,

    // Initialize categories
    categories: [],
    async init() {
      await auth.init();
      if (!auth.requireLogin()) return;
      const { token } = auth.getState();

      try {
        const response = await fetch('/api/categories', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        if (!response.ok) throw new Error('Failed to fetch categories');
        const data = await response.json();
        this.categories = data.categories || [];
        console.log('Loaded categories:', this.categories);
      } catch (error) {
        console.error('Error fetching categories:', error);
        this.error = 'Failed to load categories. Please refresh the page.';
      }
    },

    // Trigger file input click
    triggerFileInput() {
      document.getElementById("item-image").click()
    },

    // Handle image upload
    handleImageUpload(event) {
      const file = event.target.files[0]
      if (!file) return

      if (!file.type.startsWith("image/")) {
        this.error = "Please select an image file"
        return
      }

      if (file.size > 5 * 1024 * 1024) { // 5MB limit
        this.error = "Image size must be less than 5MB"
        return
      }

      const reader = new FileReader()
      reader.onload = (e) => {
        this.imagePreview = e.target.result
        this.error = null
      }
      reader.readAsDataURL(file)
    },

    // Remove image
    removeImage() {
      this.imagePreview = null
      document.getElementById("item-image").value = ""
    },

    // Submit listing
    async submitListing() {
      await auth.init();
      if (!auth.requireLogin()) return;
      const { token } = auth.getState();

      if (!this.imagePreview) {
        this.error = "Please upload an image for your listing"
        return
      }

      if (!this.listing.title || !this.listing.price || !this.listing.condition || 
          !this.listing.category_id || !this.listing.description) {
        this.error = "Please fill in all required fields"
        return
      }

      this.isSubmitting = true
      this.error = null

      try {
        const formData = new FormData()
        formData.append('title', this.listing.title)
        formData.append('price', this.listing.price)
        formData.append('condition', this.listing.condition)
        formData.append('category_id', this.listing.category_id)
        formData.append('description', this.listing.description)
        formData.append('image', document.getElementById('item-image').files[0])

        const response = await fetch('/api/listings', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`
          },
          body: formData
        })

        if (!response.ok) {
          const error = await response.json()
          if (response.status === 401) {
            // Authentication error - redirect to login
            const currentPath = window.location.pathname;
            window.location.href = `login.html?next=${encodeURIComponent(currentPath)}`;
            return;
          }
          throw new Error(error.error || 'Failed to create listing')
        }

        const result = await response.json()
        toast?.show?.('Listing created successfully!', 'success');
        window.location.href = 'listing.html'
      } catch (error) {
        console.error('Error creating listing:', error)
        this.error = error.message
        this.isSubmitting = false
      }
    }
  }
}
