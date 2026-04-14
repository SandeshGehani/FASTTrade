// Marketplace page functionality
if (typeof window !== 'undefined' && !window.setListingSearchTerm) {
  window.setListingSearchTerm = () => {};
}

function marketplaceData() {
  return {
    // Sorting & pagination
    sortOption: "newest",
    currentPage: 1,
    itemsPerPage: 9,

    // Modal state
    detailsModalOpen: false,
    selectedItem: null,

    // Data
    listings: [],
    categories: [],
    isLoading: false,
    error: null,

    // Filtering & search
    searchTerm: '',
    filters: {
      status: '',
      category: '',
      minPrice: '',
      maxPrice: ''
    },
    statusOptions: [
      { value: '', label: 'All statuses' },
      { value: 'available', label: 'Available' },
      { value: 'sold', label: 'Sold' },
      { value: 'removed', label: 'Removed' }
    ],

    // Handle Add Listing button click
    handleAddListingClick() {
      if (!auth.requireLogin({ next: 'create-listing.html' })) return;
      window.location.href = 'create-listing.html';
    },

    buildQueryParams() {
      const params = new URLSearchParams();
      if (this.searchTerm.trim()) params.append('search', this.searchTerm.trim());
      if (this.filters.status) params.append('status', this.filters.status);
      if (this.filters.category) params.append('category_id', this.filters.category);
      if (this.filters.minPrice) params.append('min_price', this.filters.minPrice);
      if (this.filters.maxPrice) params.append('max_price', this.filters.maxPrice);

      if (this.sortOption === 'price_low') {
        params.append('sort_by', 'price_low');
      } else if (this.sortOption === 'price_high') {
        params.append('sort_by', 'price_high');
      } else {
        params.append('sort_by', 'newest');
      }
      return params.toString();
    },

    async fetchListings() {
      try {
        this.isLoading = true;
        this.error = null;
        const query = this.buildQueryParams();
        const res = await fetch(`/api/listings?${query}`);
        if (!res.ok) throw new Error('Failed to fetch listings');
        const data = await res.json();
        this.listings = data.listings || [];
      } catch (e) {
        console.error('Failed to fetch listings:', e);
        this.error = 'Unable to load listings right now.';
        this.listings = [];
      } finally {
        this.isLoading = false;
      }
    },

    async fetchCategories() {
      try {
        const res = await fetch('/api/categories');
        const data = await res.json();
        this.categories = data.categories || [];
      } catch (e) {
        console.error('Failed to fetch categories:', e);
        this.categories = [];
      }
    },

    get paginatedListings() {
      const startIndex = (this.currentPage - 1) * this.itemsPerPage;
      const endIndex = startIndex + this.itemsPerPage;
      return this.listings.slice(startIndex, endIndex);
    },

    get totalPages() {
      return Math.max(1, Math.ceil(this.listings.length / this.itemsPerPage) || 1);
    },

    sortListings() {
      this.currentPage = 1;
      this.fetchListings();
    },

    applyFilters() {
      this.currentPage = 1;
      this.fetchListings();
    },

    resetFilters() {
      this.filters = { status: '', category: '', minPrice: '', maxPrice: '' };
      this.applyFilters();
    },

    updateSearchTerm(term) {
      this.searchTerm = term;
      this.currentPage = 1;
      this.fetchListings();
    },

    nextPage() {
      if (this.currentPage < this.totalPages) {
        this.currentPage++;
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    },

    prevPage() {
      if (this.currentPage > 1) {
        this.currentPage--;
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    },

    requireLogin(action) {
      const ok = auth.requireLogin();
      if (ok && typeof action === 'function') {
        action();
      }
      return ok;
    },

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

    goToDetails(item) {
      this.requireLogin(() => {
        this.openDetailsModal(item);
      });
    },

    messageSeller(item) {
      this.requireLogin(() => {
        window.location.href = `messages.html?user_id=${item.seller_id}&product_id=${item.id}`;
      });
    },

    formatStatus(status) {
      const mapping = {
        available: 'Available',
        sold: 'Sold',
        removed: 'Removed'
      };
      return mapping[status] || 'Unknown';
    },

    categoryLabel(categoryId) {
      if (!categoryId) return 'General';
      const match = this.categories.find(cat => Number(cat.id) === Number(categoryId));
      return match ? match.name : 'General';
    },

    initSearchBridge() {
      window.setListingSearchTerm = (term) => {
        this.updateSearchTerm(term || '');
      };
    },

    async init() {
      await Promise.all([this.fetchCategories(), this.fetchListings()]);
      this.initSearchBridge();
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
            await auth.init();
            const { token } = auth.getState();
            if (token) {
                try {
                    const res = await fetch('/api/user/rating', {
                        headers: { 'Authorization': `Bearer ${token}` }
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
                    toast?.show?.('Only image files are allowed', 'error');
                    continue;
                }
                
                // Validate file size (max 5MB)
                if (file.size > 5 * 1024 * 1024) {
                    toast?.show?.('Image size must be less than 5MB', 'error');
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
                toast?.show?.('Please fill in all required fields', 'error');
                return;
            }
            
            // Validate images
            if (this.images.length === 0) {
                toast?.show?.('Please upload at least one image', 'error');
                return;
            }
            
            this.isSubmitting = true;
            
            try {
                await auth.init();
                if (!auth.requireLogin()) {
                    this.isSubmitting = false;
                    return;
                }
                const { token } = auth.getState();

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
                        'Authorization': `Bearer ${token}`
                    },
                    body: formData
                });
                
                if (!res.ok) {
                    throw new Error('Failed to create listing');
                }
                
                // Redirect to the new listing page
                const data = await res.json();
                window.location.href = `listing.html?id=${data.id}`;
            } catch (err) {
                console.error('Error creating listing:', err);
                toast?.show?.('Failed to create listing. Please try again.', 'error');
            } finally {
                this.isSubmitting = false;
            }
        }
    };
}
