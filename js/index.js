function indexData() {
    return {
        detailsModalOpen: false,
        selectedItem: null,
        showListingDetails(item) {
            this.selectedItem = item;
            this.detailsModalOpen = true;
        }
    }
} 