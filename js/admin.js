function adminData() {
    return {
        activeTab: 'listings',
        searchQuery: '',
        listings: [],
        users: [],
        transactions: [],
        actions: [],
        categories: [],
        filteredListings: [],
        filteredUsers: [],
        metrics: {
            totalListings: 0,
            soldListings: 0,
            totalUsers: 0,
            totalTransactions: 0,
            totalVolume: 0
        },
        categoryStats: [],
        error: null,
        isLoading: false,

        authHeaders() {
            const { token } = auth.getState();
            if (!token) {
                auth.requireLogin();
                return null;
            }
            return { 'Authorization': `Bearer ${token}` };
        },

        async init() {
            await auth.init();
            if (!auth.requireAdmin({ redirect: false })) {
                window.location.href = 'index.html';
                return;
            }

            try {
                this.isLoading = true;
                await Promise.all([
                    this.fetchCategories(),
                    this.fetchListings(),
                    this.fetchUsers(),
                    this.fetchTransactions(),
                    this.fetchActions()
                ]);
                this.computeMetrics();
            } catch (error) {
                console.error('Error:', error);
                toast?.show?.('Failed to load admin dashboard.', 'error');
                window.location.href = 'login.html';
            } finally {
                this.isLoading = false;
            }
        },

        async fetchCategories() {
            try {
                const res = await fetch('/api/categories');
                const data = await res.json();
                this.categories = data.categories || [];
            } catch (error) {
                console.error('Error fetching categories:', error);
            }
        },

        async fetchListings() {
            try {
                const page = 1;
                const limit = 100;
                const headers = this.authHeaders();
                if (!headers) return;
                const response = await fetch(`/api/admin/listings?page=${page}&limit=${limit}`, {
                    headers
                });

                if (!response.ok) {
                    throw new Error('Failed to fetch listings');
                }

                const data = await response.json();
                this.listings = data.listings || [];
                this.filteredListings = [...this.listings];
            } catch (error) {
                console.error('Error fetching listings:', error);
                this.error = 'Failed to load listings. Please try again.';
            }
        },

        async fetchUsers() {
            try {
                const headers = this.authHeaders();
                if (!headers) return;
                const response = await fetch('/api/admin/users', { headers });

                if (!response.ok) {
                    throw new Error('Failed to fetch users');
                }

                const data = await response.json();
                this.users = data.users || [];
                this.filteredUsers = [...this.users];
            } catch (error) {
                console.error('Error fetching users:', error);
                toast?.show?.('Failed to fetch users. Please try again.', 'error');
            }
        },

        async fetchTransactions() {
            try {
                const headers = this.authHeaders();
                if (!headers) return;
                const response = await fetch('/api/transactions?scope=all', { headers });
                if (!response.ok) throw new Error('Failed to fetch transactions');
                const data = await response.json();
                this.transactions = data.transactions || [];
            } catch (error) {
                console.error('Error fetching transactions:', error);
            }
        },

        async fetchActions() {
            try {
                const headers = this.authHeaders();
                if (!headers) return;
                const response = await fetch('/api/admin/actions?limit=50', { headers });
                if (!response.ok) throw new Error('Failed to fetch admin actions');
                const data = await response.json();
                this.actions = data.actions || [];
            } catch (error) {
                console.error('Error fetching admin actions:', error);
            }
        },

        computeMetrics() {
            const soldListings = this.listings.filter(l => l.status === 'sold').length;
            const volume = this.transactions.reduce((sum, t) => sum + (t.amount || 0), 0);
            this.metrics = {
                totalListings: this.listings.length,
                soldListings,
                totalUsers: this.users.length,
                totalTransactions: this.transactions.length,
                totalVolume: volume
            };

            const categoryMap = {};
            this.listings.forEach(listing => {
                if (!listing.category_id) return;
                categoryMap[listing.category_id] = (categoryMap[listing.category_id] || 0) + 1;
            });
            this.categoryStats = Object.entries(categoryMap)
                .map(([categoryId, count]) => {
                    const category = this.categories.find(c => c.id === Number(categoryId));
                    return {
                        id: categoryId,
                        name: category ? category.name : `Category ${categoryId}`,
                        count
                    };
                })
                .sort((a, b) => b.count - a.count)
                .slice(0, 5);
        },

        setActiveTab(tab) {
            this.activeTab = tab;
            this.searchQuery = '';
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
                listing.seller_id?.toString().includes(query)
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
                user.phone?.toLowerCase().includes(query)
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
                const headers = this.authHeaders();
                if (!headers) return;
                if (this.deleteType === 'listing') {
                    response = await fetch(`/api/admin/listings/${this.itemToDelete.id}`, {
                        method: 'DELETE',
                        headers
                    });
                } else if (this.deleteType === 'user') {
                    response = await fetch(`/api/admin/users/${this.itemToDelete.id}`, {
                        method: 'DELETE',
                        headers
                    });
                }

                if (!response || !response.ok) {
                    throw new Error(`Failed to delete ${this.deleteType}`);
                }

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
                this.computeMetrics();
                toast?.show?.('Deleted successfully', 'success');
            } catch (error) {
                console.error(`Error deleting ${this.deleteType}:`, error);
                toast?.show?.(`Failed to delete ${this.deleteType}. Please try again.`, 'error');
            }
        },

        formatDate(value) {
            return value ? new Date(value).toLocaleString() : '—';
        }
    };
} 