// Main JavaScript file for shared functionality

// Function to toggle mobile menu
document.addEventListener("DOMContentLoaded", () => {
  // Any global initialization can go here
  console.log("FASTTrade initialized")
})

// Fetch featured listings from the backend
function featuredListings() {
  return {
    listings: [],
    async fetchListings() {
      try {
        const response = await fetch('/api/listings/featured');
        const data = await response.json();
        if (data.listings) {
          this.listings = data.listings;
        } else {
          this.listings = [];
        }
      } catch (e) {
        console.error('Failed to fetch featured listings:', e);
        this.listings = [];
      }
    },
    // Get 6 random listings for homepage
    get randomListings() {
      const shuffled = [...this.listings].sort(() => 0.5 - Math.random())
      return shuffled.slice(0, 6)
    },
  }
}
