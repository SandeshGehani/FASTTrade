// Messages page functionality
function messagesData() {
  return {
    // Search query
    searchQuery: "",

    // New message inputs
    newMessage: "",
    newContactMessage: "",

    // Selected contact
    selectedContact: null,
    selectedProduct: null,
    showProductInfo: false,
    errorMessage: "",

    // Sample contacts data
    contacts: [], // Will be populated with real threads
    messages: [], // Messages with the selected contact
    userId: null,

    async init() {
      // Get user info from localStorage
      const user = JSON.parse(localStorage.getItem('user'));
      this.userId = user ? user.id : null;
      await this.fetchThreads();

      // Check for user_id parameter in URL
      const urlParams = new URLSearchParams(window.location.search);
      const targetUserId = urlParams.get('user_id');
      const productId = urlParams.get('product_id');
      
      if (targetUserId) {
        try {
        // Find the contact with matching ID
          let targetContact = this.contacts.find(contact => contact.id === parseInt(targetUserId));
        if (targetContact) {
          await this.selectContact(targetContact);
        } else {
          const res = await fetch(`/api/users/${targetUserId}`);
            if (!res.ok) {
              this.errorMessage = 'User not found or API error.';
              console.error('User fetch failed:', res.status, await res.text());
              return;
            }
          const userData = await res.json();
            if (!userData.user) {
              this.errorMessage = 'User data missing in API response.';
              console.error('User data missing:', userData);
              return;
            }
          const newContact = {
            id: parseInt(targetUserId),
            name: userData.user.full_name,
            avatar: userData.user.profile_image || `https://via.placeholder.com/50?text=${userData.user.full_name[0]}`,
            lastMessage: '',
            lastMessageTime: '',
            unreadCount: 0,
            batch: this.getBatchInfo(userData.user.email)
          };
          this.contacts.push(newContact);
          await this.selectContact(newContact);
        }

        // If product_id is provided, fetch and display product info
        if (productId) {
          await this.fetchProductInfo(productId);
            if (!this.selectedProduct) {
              this.errorMessage = 'Product not found or API error.';
            }
          }
        } catch (err) {
          this.errorMessage = 'An error occurred while loading the chat.';
          console.error('Chat init error:', err);
        }
      }
    },

    getBatchInfo(email) {
      if (!email) return '';
      const campusMap = {
        'k': 'Karachi',
        'i': 'Islamabad',
        'f': 'Faisalabad',
        'l': 'Lahore',
        'p': 'Peshawar'
      };
      const match = email.match(/^([kiflp])(\d{2})/);
      if (match) {
        const [_, campus, year] = match;
        return `${campusMap[campus.toLowerCase()]} Campus, Batch ${year}`;
      }
      return '';
    },

    async fetchProductInfo(productId) {
      try {
        const res = await fetch(`/api/listings/${productId}`);
        const data = await res.json();
        if (data.listing) {
          this.selectedProduct = data.listing;
          this.showProductInfo = true;
        }
      } catch (error) {
        console.error('Error fetching product info:', error);
      }
    },

    async fetchThreads() {
      const token = localStorage.getItem('access_token');
      if (!token) return;
      const res = await fetch('/api/messages/threads', {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const data = await res.json();
      // Fetch user info for each thread
      this.contacts = await Promise.all((data.threads || []).map(async (thread) => {
        const userRes = await fetch(`/api/users/${thread.user_id}`);
        const userData = await userRes.json();
        return {
          id: thread.user_id,
          name: userData.user.full_name,
          avatar: userData.user.profile_image || `https://via.placeholder.com/50?text=${userData.user.full_name[0]}`,
          lastMessage: thread.last_message.content,
          lastMessageTime: this.formatTime(thread.last_message.created_at),
          unreadCount: 0,
          batch: this.getBatchInfo(userData.user.email)
        };
      }));
    },

    async fetchMessages(contact) {
      const token = localStorage.getItem('access_token');
      if (!token) return;
      const res = await fetch(`/api/messages/${contact.id}`, {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const data = await res.json();
      this.messages = (data.messages || []).map(msg => ({
        text: msg.content,
        time: this.formatTime(msg.created_at),
        sent: msg.sender_id === this.userId
      }));
    },

    // Computed property for filtered contacts
    get filteredContacts() {
      if (!this.searchQuery) {
        return this.contacts
      }

      const query = this.searchQuery.toLowerCase()
      return this.contacts.filter((contact) => contact.name.toLowerCase().includes(query))
    },

    // Search contacts
    searchContacts() {
      // Reset selected contact if it's filtered out
      if (this.selectedContact && !this.filteredContacts.find((c) => c.id === this.selectedContact.id)) {
        this.selectedContact = null
      }
    },

    // Select a contact
    async selectContact(contact) {
      this.selectedContact = contact
      await this.fetchMessages(contact)

      // Mark messages as read when selecting a contact
      if (contact.unreadCount > 0) {
        contact.unreadCount = 0
      }

      // Close contacts panel on mobile
      document.querySelector(".contacts-panel").classList.remove("open")

      // Scroll to bottom of chat
      setTimeout(() => {
        const chatMessages = document.getElementById("chat-messages")
        if (chatMessages) {
          chatMessages.scrollTop = chatMessages.scrollHeight
        }
      }, 100)
    },

    // Send a new message
    async sendMessage() {
      if (!this.newMessage.trim() || !this.selectedContact) {
        return
      }

      const token = localStorage.getItem('access_token');
      if (!token) return;
      const res = await fetch(`/api/messages/${this.selectedContact.id}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({ content: this.newMessage })
      });
      if (res.ok) {
        this.newMessage = ""
        await this.fetchMessages(this.selectedContact)
        await this.fetchThreads()

        // Scroll to bottom of chat
        setTimeout(() => {
          const chatMessages = document.getElementById("chat-messages")
          if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight
          }
        }, 100)
      }
    },

    // Format time for messages
    formatTime(dateStr) {
      const date = new Date(dateStr);
      return date.toLocaleString();
    },
  }
}
