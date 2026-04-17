/* DriveEasy — Public JS (static/js/public.js) */

document.addEventListener('DOMContentLoaded', function () {

  // ── Navbar scroll shadow
  const navbar = document.getElementById('navbar');
  if (navbar) {
    window.addEventListener('scroll', () => {
      navbar.style.boxShadow = window.scrollY > 8
        ? '0 4px 24px rgba(0,0,0,.12)'
        : '0 2px 8px rgba(0,0,0,.06)';
    }, { passive: true });
  }

  // ── Mobile navbar toggle
  const hamburger = document.getElementById('navHamburger');
  const navLinks  = document.getElementById('navLinks');
  if (hamburger && navLinks) {
    hamburger.addEventListener('click', () => {
      navLinks.classList.toggle('open');
    });
    document.addEventListener('click', e => {
      if (!hamburger.contains(e.target) && !navLinks.contains(e.target)) {
        navLinks.classList.remove('open');
      }
    });
  }

  // ── Scroll reveal for car cards
  const revealEls = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window && revealEls.length) {
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((entry, i) => {
        if (entry.isIntersecting) {
          setTimeout(() => entry.target.classList.add('visible'), i * 55);
          obs.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08 });
    revealEls.forEach(el => obs.observe(el));
  } else {
    revealEls.forEach(el => el.classList.add('visible'));
  }

  // ── Flash auto-dismiss
  document.querySelectorAll('.flash').forEach(flash => {
    setTimeout(() => {
      flash.style.transition = 'opacity .4s, transform .4s';
      flash.style.opacity = '0';
      flash.style.transform = 'translateX(110%)';
      setTimeout(() => flash.remove(), 400);
    }, 5000);
  });

  // ── Filter form auto-submit on radio change (cars page)
  const filterForm = document.getElementById('filterForm');
  if (filterForm) {
    filterForm.querySelectorAll('input[type="radio"]').forEach(r => {
      r.addEventListener('change', () => setTimeout(() => filterForm.submit(), 180));
    });
  }

  // ── Smooth anchor scroll
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const id = a.getAttribute('href');
      if (id === '#') return;
      const el = document.querySelector(id);
      if (el) {
        e.preventDefault();
        window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 80, behavior: 'smooth' });
      }
    });
  });

});
