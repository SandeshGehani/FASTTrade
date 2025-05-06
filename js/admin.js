function adminData() {
    return {
        activeTab: 'listings',
        searchQuery: '',
        listings: [],
        users: [],
        filteredListings: [],
        filteredUsers: [],
        error: null,

        async init() {
            // Check if user is admin
            const token = localStorage.getItem('access_token');
            if (!token) {
                window.location.href = 'login.html';
                return;
            }

            try {
                const response = await fetch('/api/auth/me', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (!response.ok) {
                    throw new Error('Failed to fetch user data');
                }

                const data = await response.json();
                if (data.user.email !== 'k232004@nu.edu.pk') {
                    window.location.href = 'index.html';
                    return;
                }

                // Fetch initial data
                await this.fetchListings();
                await this.fetchUsers();
            } catch (error) {
                console.error('Error:', error);
                window.location.href = 'login.html';
            }
        },

        async fetchListings() {
            try {
                const page = 1;
                const limit = 20;
                const response = await fetch(`/api/admin/listings?page=${page}&limit=${limit}`, {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                    }
                });

                if (!response.ok) {
                    throw new Error('Failed to fetch listings');
                }

                const data = await response.json();
                this.listings = data.listings;
                this.filteredListings = [...this.listings];
            } catch (error) {
                console.error('Error fetching listings:', error);
                this.error = 'Failed to load listings. Please try again.';
            }
        },

        async fetchUsers() {
            try {
                const response = await fetch('/api/admin/users', {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                    }
                });

                if (!response.ok) {
                    throw new Error('Failed to fetch users');
                }

                const data = await response.json();
                this.users = data.users;
                this.filteredUsers = [...this.users];
            } catch (error) {
                console.error('Error fetching users:', error);
                alert('Failed to fetch users. Please try again.');
            }
        },

        searchListings() {
            if (!this.searchQuery) {
                this.filteredListings = [...this.listings];
                return;
            }

            const query = this.searchQuery.toLowerCase();
            this.filteredListings = this.listings.filter(listing => 
                listing.title.toLowerCase().includes(query) ||
                listing.description.toLowerCase().includes(query) ||
                listing.seller_id.toString().includes(query)
            );
        },

        searchUsers() {
            if (!this.searchQuery) {
                this.filteredUsers = [...this.users];
                return;
            }

            const query = this.searchQuery.toLowerCase();
            this.filteredUsers = this.users.filter(user => 
                user.full_name.toLowerCase().includes(query) ||
                user.email.toLowerCase().includes(query) ||
                user.phone.toLowerCase().includes(query)
            );
        },

        showDeleteConfirm: false,
        itemToDelete: null,
        deleteType: '',

        confirmDelete(item, type) {
            this.itemToDelete = item;
            this.deleteType = type;
            this.showDeleteConfirm = true;
        },

        async deleteItem() {
            if (!this.itemToDelete) return;

            try {
                let response;
                if (this.deleteType === 'listing') {
                    response = await fetch(`/api/admin/listings/${this.itemToDelete.id}`, {
                        method: 'DELETE',
                        headers: {
                            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                        }
                    });
                } else if (this.deleteType === 'user') {
                    response = await fetch(`/api/admin/users/${this.itemToDelete.id}`, {
                        method: 'DELETE',
                        headers: {
                            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                        }
                    });
                }

                if (!response.ok) {
                    throw new Error(`Failed to delete ${this.deleteType}`);
                }

                // Remove from local state
                if (this.deleteType === 'listing') {
                    this.listings = this.listings.filter(l => l.id !== this.itemToDelete.id);
                    this.filteredListings = this.filteredListings.filter(l => l.id !== this.itemToDelete.id);
                } else if (this.deleteType === 'user') {
                    this.users = this.users.filter(u => u.id !== this.itemToDelete.id);
                    this.filteredUsers = this.filteredUsers.filter(u => u.id !== this.itemToDelete.id);
                }
                
                this.showDeleteConfirm = false;
                this.itemToDelete = null;
                this.deleteType = '';
                alert(`${this.deleteType} deleted successfully`);
            } catch (error) {
                console.error(`Error deleting ${this.deleteType}:`, error);
                alert(`Failed to delete ${this.deleteType}. Please try again.`);
            }
        }
    };
} 