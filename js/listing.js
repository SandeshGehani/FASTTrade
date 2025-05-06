// Marketplace page functionality
function marketplaceData() {
  return {
    // Sorting
    sortOption: "newest",

    // Pagination
    currentPage: 1,
    itemsPerPage: 8,

    // Modal state
    detailsModalOpen: false,
    selectedItem: null,

    // Real listings data
    listings: [],

    // Handle Add Listing button click
    handleAddListingClick() {
      const token = localStorage.getItem('access_token');
      if (!token) {
        const currentPath = window.location.pathname;
        // Only redirect if we're not already on the login page
        if (!window.location.pathname.includes('login.html')) {
          window.location.href = `login.html?next=${encodeURIComponent(currentPath)}`;
        }
        return;
      }
      window.location.href = 'create-listing.html';
    },

    async fetchListings() {
      try {
        const res = await fetch(`/api/listings?sort_by=${this.sortOption}`);
        const data = await res.json();
        this.listings = data.listings || [];
      } catch (e) {
        console.error('Failed to fetch listings:', e);
        this.listings = [];
      }
    },

    // Computed property for filtered listings
    get filteredListings() {
      const result = [...this.listings];
      // Apply pagination
      const startIndex = (this.currentPage - 1) * this.itemsPerPage;
      const endIndex = startIndex + this.itemsPerPage;
      return result.slice(startIndex, endIndex);
    },

    // Computed property for total pages
    get totalPages() {
      return Math.ceil(this.listings.length / this.itemsPerPage);
    },

    // Sort listings
    sortListings() {
      this.currentPage = 1;
      this.fetchListings();
    },

    // Pagination methods
    nextPage() {
      if (this.currentPage < this.totalPages) {
        this.currentPage++;
        window.scrollTo(0, 0);
      }
    },

    prevPage() {
      if (this.currentPage > 1) {
        this.currentPage--;
        window.scrollTo(0, 0);
      }
    },

    // Require login before viewing details or messaging
    requireLogin(action) {
      if (!localStorage.getItem('access_token')) {
        const currentPath = window.location.pathname;
        window.location.href = `login.html?next=${encodeURIComponent(currentPath)}`;
        return false;
      }
      return action();
    },

    // Open details modal with login check
    openDetailsModal(item) {
      this.requireLogin(() => {
        this.selectedItem = item;
        this.detailsModalOpen = true;
        setTimeout(() => {
          const modalContent = document.querySelector(".modal-content");
          if (modalContent && window.gsap) {
            window.gsap.fromTo(modalContent, { y: 100, opacity: 0 }, { y: 0, opacity: 1, duration: 0.3 });
          }
        }, 10);
      });
    },

    // Go to details page with login check
    goToDetails(item) {
      this.requireLogin(() => {
        this.openDetailsModal(item);
      });
    },

    // Message seller with login check
    messageSeller(item) {
      this.requireLogin(() => {
        // Redirect to messages page with seller's ID and product ID
        window.location.href = `messages.html?user_id=${item.seller_id}&product_id=${item.id}`;
      });
    },

    // Init
    async init() {
      await this.fetchListings();
    },
  };
}

document.addEventListener('alpine:init', () => {
  Alpine.data('marketplaceData', marketplaceData);
});

function listingData() {
    return {
        title: '',
        description: '',
        price: '',
        category: '',
        conditionRating: 0,
        images: [],
        sellerRating: 0,
        ratingCount: 0,
        isSubmitting: false,
        
        async init() {
            // Fetch seller rating if user is logged in
            if (localStorage.getItem('access_token')) {
                try {
                    const res = await fetch('/api/user/rating', {
                        headers: {
                            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                        }
                    });
                    if (res.ok) {
                        const data = await res.json();
                        this.sellerRating = data.rating;
                        this.ratingCount = data.count;
                    }
                } catch (err) {
                    console.error('Failed to fetch seller rating:', err);
                }
            }
        },
        
        async handleImageUpload(event) {
            const files = event.target.files;
            if (!files) return;
            
            // Check if adding these files would exceed the limit
            if (this.images.length + files.length > 5) {
                alert('You can only upload up to 5 images');
                return;
            }
            
            for (const file of files) {
                // Validate file type
                if (!file.type.startsWith('image/')) {
                    alert('Only image files are allowed');
                    continue;
                }
                
                // Validate file size (max 5MB)
                if (file.size > 5 * 1024 * 1024) {
                    alert('Image size must be less than 5MB');
                    continue;
                }
                
                // Create preview URL
                const reader = new FileReader();
                reader.onload = (e) => {
                    this.images.push({
                        file,
                        url: e.target.result
                    });
                };
                reader.readAsDataURL(file);
            }
            
            // Reset input to allow selecting the same file again
            event.target.value = '';
        },
        
        removeImage(index) {
            this.images.splice(index, 1);
        },
        
        async submitListing() {
            if (this.isSubmitting) return;
            
            // Validate required fields
            if (!this.title || !this.description || !this.price || !this.category || !this.conditionRating) {
                alert('Please fill in all required fields');
                return;
            }
            
            // Validate images
            if (this.images.length === 0) {
                alert('Please upload at least one image');
                return;
            }
            
            this.isSubmitting = true;
            
            try {
                // Create FormData for multipart/form-data
                const formData = new FormData();
                formData.append('title', this.title);
                formData.append('description', this.description);
                formData.append('price', this.price);
                formData.append('category', this.category);
                formData.append('condition_rating', this.conditionRating);
                
                // Append images
                this.images.forEach((image, index) => {
                    formData.append(`images[${index}]`, image.file);
                });
                
                const res = await fetch('/api/listings', {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                    },
                    body: formData
                });
                
                if (!res.ok) {
                    throw new Error('Failed to create listing');
                }
                
                // Redirect to the new listing page
                const data = await res.json();
                window.location.href = `/listing-detail.html?id=${data.id}`;
            } catch (err) {
                console.error('Error creating listing:', err);
                alert('Failed to create listing. Please try again.');
            } finally {
                this.isSubmitting = false;
            }
        }
    };
}
