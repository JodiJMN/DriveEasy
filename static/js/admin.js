/* DriveEasy — Admin JS (static/js/admin.js) */

document.addEventListener('DOMContentLoaded', function () {

  // ── Sidebar toggle (mobile)
  const sidebarToggle = document.getElementById('sidebarToggle');
  const sidebar       = document.getElementById('sidebar');
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
    document.addEventListener('click', e => {
      if (sidebar.classList.contains('open') &&
          !sidebar.contains(e.target) &&
          !sidebarToggle.contains(e.target)) {
        sidebar.classList.remove('open');
      }
    });
  }

  // ── Alert auto-dismiss (3s)
  document.querySelectorAll('.alert').forEach(a => {
    setTimeout(() => {
      a.style.transition = 'opacity .3s';
      a.style.opacity = '0';
      setTimeout(() => a.remove(), 300);
    }, 4000);
  });

  // ── Confirm delete buttons
  document.querySelectorAll('[data-confirm]').forEach(btn => {
    btn.addEventListener('click', e => {
      if (!confirm(btn.dataset.confirm)) e.preventDefault();
    });
  });

});
