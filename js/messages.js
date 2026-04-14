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
    socket: null,
    socketConnected: false,
    pollTimer: null,

    async init() {
      await auth.init();
      if (!auth.requireLogin()) return;
      const state = auth.getState();
      this.userId = state.user?.id || null;
      await this.fetchThreads();
      this.initSocket();
      this.startPolling();
      window.addEventListener('beforeunload', () => this.stopPolling());

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
            avatar: userData.user.profile_image || 'static/images/default.png',
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
          } else {
            // If this is a new conversation and we have product info, send an initial message
            const existingMessages = this.messages || [];
            if (existingMessages.length === 0 && this.selectedProduct) {
              // Auto-send a message with product context (optional - you can remove this if you want manual first message)
              // For now, we'll just show the product card without auto-sending
            }
          }
        }
        } catch (err) {
          this.errorMessage = 'An error occurred while loading the chat.';
          console.error('Chat init error:', err);
        }
      }
    },

    initSocket() {
      const { token } = auth.getState();
      if (!token || typeof io === 'undefined') {
        console.warn('Socket.io not available or token missing.');
        return;
      }
      this.socket = io({ transports: ['websocket'] });
      this.socket.on('connect', () => {
        this.socketConnected = true;
        this.socket.emit('join', { token });
      });
      this.socket.on('socket_ready', () => {
        this.socketConnected = true;
      });
      this.socket.on('disconnect', () => {
        this.socketConnected = false;
      });
      this.socket.on('new_message', (payload) => this.handleIncomingMessage(payload));
      this.socket.on('read_receipt', (payload) => this.handleReadReceipt(payload));
      this.socket.on('socket_error', (payload) => {
        console.error('Socket error:', payload);
      });
    },

    handleIncomingMessage(payload) {
      const message = payload?.message;
      if (!message || !this.userId) return;
      const otherUserId = message.sender_id === this.userId ? message.receiver_id : message.sender_id;
      const normalized = {
        id: message.id,
        text: message.content,
        time: this.formatTime(message.created_at),
        sent: message.sender_id === this.userId,
        read: !!message.is_read,
        listing_id: message.listing_id
      };
      
      // If message has listing_id and we don't have product info, fetch it
      if (message.listing_id && !this.selectedProduct) {
        this.fetchProductInfo(message.listing_id);
      }

      if (this.selectedContact && this.selectedContact.id === otherUserId) {
        this.upsertMessage(normalized);
        if (!normalized.sent) {
          this.markConversationAsRead(otherUserId);
        }
      } else {
        const contact = this.contacts.find((c) => c.id === otherUserId);
        if (contact) {
          if (!normalized.sent) {
            contact.unreadCount = (contact.unreadCount || 0) + 1;
            // Update navbar badge when new message arrives
            if (typeof window.updateUnreadBadge === 'function') {
              window.updateUnreadBadge();
            }
          }
          contact.lastMessage = normalized.text;
          contact.lastMessageTime = normalized.time;
        } else {
          this.fetchThreads();
        }
      }
      this.updateThreadPreview(otherUserId, normalized);
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

    async markAsSold() {
      if (!this.selectedProduct) return;
      
      const { token } = auth.getState();
      if (!token) return;
      
      if (!confirm('Are you sure you want to mark this item as sold?')) {
        return;
      }
      
      try {
        const res = await fetch(`/api/listings/${this.selectedProduct.id}/mark-sold`, {
          method: 'PUT',
          headers: {
            'Authorization': 'Bearer ' + token
          }
        });
        
        if (!res.ok) {
          const errorData = await res.json();
          throw new Error(errorData.error || 'Failed to mark as sold');
        }
        
        const data = await res.json();
        this.selectedProduct = data.listing;
        toast.show('Item marked as sold!', 'success');
      } catch (error) {
        console.error('Error marking as sold:', error);
        toast.show(error.message || 'Failed to mark item as sold', 'error');
      }
    },

    get isSeller() {
      if (!this.selectedProduct || !this.userId) return false;
      return this.selectedProduct.seller_id === this.userId;
    },

    async fetchThreads() {
      const { token } = auth.getState();
      if (!token) return;
      try {
        const res = await fetch('/api/messages/threads', {
          headers: { 'Authorization': 'Bearer ' + token }
        });
        if (!res.ok) {
          console.error('Failed to fetch threads', await res.text());
          return;
        }
        const data = await res.json();
        const threads = data.threads || [];
        const contactPromises = threads.map(async (thread) => {
          const userRes = await fetch(`/api/users/${thread.user_id}`);
          if (!userRes.ok) {
            throw new Error(`Failed to load user ${thread.user_id}`);
          }
          const userData = await userRes.json();
          const lastMessage = thread.last_message || {};
          return {
            id: thread.user_id,
            name: userData.user.full_name,
            avatar: userData.user.profile_image || 'static/images/default.png',
            lastMessage: lastMessage.content || '',
            lastMessageTime: lastMessage.created_at ? this.formatTime(lastMessage.created_at) : '',
            unreadCount: thread.unread_count || 0,
            batch: this.getBatchInfo(userData.user.email)
          };
        });
        this.contacts = await Promise.all(contactPromises);
        if (this.selectedContact) {
          const updated = this.contacts.find((c) => c.id === this.selectedContact.id);
          if (updated) {
            this.selectedContact = updated;
          }
        }
      } catch (error) {
        console.error('Error loading threads:', error);
      }
    },

    async fetchMessages(contact, options = {}) {
      const { token } = auth.getState();
      if (!token) return;
      const { markRead = true } = options;
      try {
        const res = await fetch(`/api/messages/${contact.id}`, {
          headers: { 'Authorization': 'Bearer ' + token }
        });
        if (!res.ok) {
          throw new Error(await res.text() || 'Failed to load messages');
        }
        const data = await res.json();
        this.messages = (data.messages || []).map(msg => ({
          id: msg.id,
          text: msg.content,
          time: this.formatTime(msg.created_at),
          sent: msg.sender_id === this.userId,
          read: !!msg.is_read,
          listing_id: msg.listing_id
        }));
        
        // If we have messages with listing_id, fetch the product info
        const messageWithListing = this.messages.find(m => m.listing_id);
        if (messageWithListing && !this.selectedProduct) {
          await this.fetchProductInfo(messageWithListing.listing_id);
        }
        if (markRead) {
          this.markConversationAsRead(contact.id);
          contact.unreadCount = 0;
          // Update navbar badge
          if (typeof window.updateUnreadBadge === 'function') {
            window.updateUnreadBadge();
          }
        }
        this.scrollMessagesToBottom();
      } catch (error) {
        console.error('Failed to load conversation:', error);
        toast.error('Unable to load messages right now.');
      }
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
      this.selectedContact = contact;
      await this.fetchMessages(contact, { markRead: true });
      
      // Check URL for product_id when selecting a contact (in case it wasn't loaded in init)
      const urlParams = new URLSearchParams(window.location.search);
      const productId = urlParams.get('product_id');
      if (productId && !this.selectedProduct) {
        await this.fetchProductInfo(productId);
      }
      
      const panel = document.querySelector(".contacts-panel");
      if (panel) {
        panel.classList.remove("open");
      }
      this.scrollMessagesToBottom();
    },

    // Send a new message
    async sendMessage() {
      if (!this.newMessage.trim() || !this.selectedContact) {
        return;
      }

      const { token } = auth.getState();
      if (!token) return;
      
      // Include listing_id if we have a selected product (first message about a product)
      // Check if this is the first message in the conversation
      const isFirstMessage = this.messages.length === 0;
      const listingId = (this.selectedProduct && isFirstMessage) ? this.selectedProduct.id : null;
      
      try {
        const res = await fetch(`/api/messages/${this.selectedContact.id}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
          },
          body: JSON.stringify({ 
            content: this.newMessage,
            listing_id: listingId
          })
        });
        if (!res.ok) {
          const errorText = await res.text();
          throw new Error(errorText || 'Failed to send message');
        }
        const data = await res.json();
        const sentMessage = data.message;
        this.newMessage = "";
        if (sentMessage) {
          this.upsertMessage({
            id: sentMessage.id,
            text: sentMessage.content,
            time: this.formatTime(sentMessage.created_at),
            sent: true,
            read: !!sentMessage.is_read
          });
          this.updateThreadPreview(this.selectedContact.id, {
            id: sentMessage.id,
            text: sentMessage.content,
            time: this.formatTime(sentMessage.created_at),
            sent: true,
            read: !!sentMessage.is_read
          });
        }
      } catch (error) {
        console.error('Failed to send message:', error);
        toast.error('Failed to send message. Try again.');
      }
    },

    startPolling() {
      this.stopPolling();
      this.pollTimer = setInterval(async () => {
        await this.fetchThreads();
        if (this.selectedContact) {
          await this.fetchMessages(this.selectedContact, { markRead: false });
        }
      }, 7000);
    },

    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer);
        this.pollTimer = null;
      }
    },

    // Format time for messages
    formatTime(dateStr) {
      const date = new Date(dateStr);
      return date.toLocaleString();
    },

    scrollMessagesToBottom() {
      setTimeout(() => {
        const chatMessages = document.getElementById("chat-messages")
        if (chatMessages) {
          chatMessages.scrollTop = chatMessages.scrollHeight
        }
      }, 50)
    },

    markConversationAsRead(contactId) {
      const { token } = auth.getState();
      if (!token || !contactId || !this.socket) return;
      this.socket.emit('mark_read', { token, other_user_id: contactId });
    },

    handleReadReceipt(payload) {
      // Update navbar badge when messages are read
      if (typeof window.updateUnreadBadge === 'function') {
        window.updateUnreadBadge();
      }
      const readerId = payload?.reader_id;
      if (!readerId) return;
      const contact = this.contacts.find(c => c.id === readerId);
      if (contact) {
        contact.unreadCount = 0;
        contact.lastReadAt = Date.now();
      }
      if (this.selectedContact && this.selectedContact.id === readerId) {
        this.messages = this.messages.map(msg => msg.sent ? { ...msg, read: true } : msg);
      }
    },

    upsertMessage(message) {
      const existingIndex = this.messages.findIndex((msg) => msg.id === message.id);
      if (existingIndex >= 0) {
        this.messages.splice(existingIndex, 1, { ...this.messages[existingIndex], ...message });
      } else {
        this.messages.push(message);
      }
      this.scrollMessagesToBottom();
    },

    updateThreadPreview(contactId, message) {
      const contact = this.contacts.find(c => c.id === contactId);
      if (contact) {
        contact.lastMessage = message.text;
        contact.lastMessageTime = message.time;
        const isActiveConversation = this.selectedContact && this.selectedContact.id === contactId;
        if (!message.sent && !isActiveConversation) {
          contact.unreadCount = (contact.unreadCount || 0) + 1;
        } else if (isActiveConversation && !message.sent) {
          contact.unreadCount = 0;
        }
      }
    }
  }
}
