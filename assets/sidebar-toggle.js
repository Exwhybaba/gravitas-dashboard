// assets/sidebar-toggle.js - Simplified and more robust version

console.log('Sidebar toggle script loaded at:', new Date().toISOString());

// Test if elements exist
function checkElements() {
  const header = document.querySelector('.header');
  const sidebar = document.querySelector('.sidebar');
  const appGrid = document.querySelector('.app-grid');

  console.log('Elements check:', {
    header: !!header,
    sidebar: !!sidebar,
    appGrid: !!appGrid,
    windowWidth: window.innerWidth,
    isMobile: window.innerWidth <= 768
  });

  return { header, sidebar, appGrid };
}

function initSidebarToggle() {
  console.log('Initializing sidebar toggle...');

  const header = document.querySelector('.header');
  const sidebar = document.querySelector('.sidebar');
  const appGrid = document.querySelector('.app-grid');

  if (!header) {
    console.warn('Sidebar toggle: .header element not found.');
    return;
  }

  if (!sidebar) {
    console.warn('Sidebar toggle: .sidebar element not found.');
    return;
  }

  // Check if button already exists
  if (document.getElementById('sidebar-toggle-js')) {
    return;
  }

  // Create hamburger button
  const btn = document.createElement('button');
  btn.id = 'sidebar-toggle-js';
  btn.className = 'sidebar-toggle-js';
  btn.setAttribute('aria-label', 'Toggle sidebar');
  btn.innerHTML = '&#9776;'; // Hamburger icon
  btn.style.cssText = `
    font-size: 20px !important;
    background: #F4E4C1 !important;
    border: 1px solid #C7A64F !important;
    padding: 8px 12px !important;
    border-radius: 6px !important;
    cursor: pointer !important;
    color: #2C3E50 !important;
    margin-right: 15px !important;
    position: absolute !important;
    left: 15px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    z-index: 3000 !important;
    display: none !important;
  `;

  header.insertBefore(btn, header.firstChild);

  // Function to check if mobile
  function isMobile() {
    return window.innerWidth <= 768;
  }

  // Function to update sidebar visibility
  function updateSidebarVisibility() {
    const mobile = isMobile();

    if (mobile) {
      // Mobile: Show toggle button, hide sidebar by default
      btn.style.display = 'block';
      sidebar.classList.remove('collapsed');

      if (!sidebar.classList.contains('expanded')) {
        sidebar.style.display = 'none';
      } else {
        sidebar.style.display = 'block';
      }
    } else {
      // Desktop: Show toggle button, allow sidebar collapse
      btn.style.display = 'block';
      sidebar.style.display = '';

      // Default to collapsed on desktop
      if (!sidebar.classList.contains('expanded')) {
        sidebar.classList.add('collapsed');
      }
    }
  }

  // Initial setup
  updateSidebarVisibility();

  // Toggle button click handler
  btn.addEventListener('click', function(e) {
    e.preventDefault();
    e.stopPropagation();

    if (isMobile()) {
      // Mobile: Toggle expanded class
      sidebar.classList.toggle('expanded');
      if (sidebar.classList.contains('expanded')) {
        sidebar.style.display = 'block';
      } else {
        sidebar.style.display = 'none';
      }
    } else {
      // Desktop: Toggle collapsed class
      sidebar.classList.toggle('collapsed');
    }
  });

  // Handle window resize
  window.addEventListener('resize', function() {
    updateSidebarVisibility();
  });

  console.log('Sidebar toggle initialized successfully');
}

// Initialize immediately and also after a delay for Dash
initSidebarToggle();

// Also initialize after DOM content loaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', function() {
    setTimeout(initSidebarToggle, 500);
  });
} else {
  setTimeout(initSidebarToggle, 500);
}

// Watch for Dash updates
const observer = new MutationObserver(function(mutations) {
  let shouldReinit = false;
  mutations.forEach(function(mutation) {
    if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
      // Check if header or sidebar was added
      for (let node of mutation.addedNodes) {
        if (node.classList && (node.classList.contains('header') || node.classList.contains('sidebar'))) {
          shouldReinit = true;
          break;
        }
      }
    }
  });

  if (shouldReinit && !document.getElementById('sidebar-toggle-js')) {
    setTimeout(initSidebarToggle, 100);
  }
});

observer.observe(document.body, {
  childList: true,
  subtree: true
});

// Touch support
document.addEventListener('touchstart', function() {}, {passive: true});

// Prevent double-tap zoom on iOS
let lastTouchEnd = 0;
document.addEventListener('touchend', function(event) {
  const now = (new Date()).getTime();
  if (now - lastTouchEnd <= 300) {
    event.preventDefault();
  }
  lastTouchEnd = now;
}, false);