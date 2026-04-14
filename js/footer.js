const FOOTER_PLACEHOLDER_ID = 'footer';
const FOOTER_TEMPLATE_URL = 'partials/footer.html';

async function initFooter() {
  const placeholder = document.getElementById(FOOTER_PLACEHOLDER_ID);
  if (!placeholder) return;

  try {
    const response = await fetch(FOOTER_TEMPLATE_URL, { cache: 'no-store' });
    if (!response.ok) throw new Error('Failed to fetch footer template');
    placeholder.innerHTML = await response.text();
  } catch (error) {
    console.error('Footer template load failed:', error);
  }
}

document.addEventListener('DOMContentLoaded', initFooter);

