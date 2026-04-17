/**
 * DriveEasy — Main JavaScript (main.js)
 * =====================================
 * Handles:
 *  - Navbar mobile toggle
 *  - Scroll-based navbar shadow
 *  - Car card scroll reveal animation
 *  - Flash message auto-dismiss
 *  - Filter form auto-submit on radio change
 */

document.addEventListener('DOMContentLoaded', function () {

    // ──────────────────────────────────────────
    // 1. NAVBAR MOBILE TOGGLE
    // ──────────────────────────────────────────
    const navToggle  = document.getElementById('navToggle');
    const mobileMenu = document.getElementById('mobileMenu');

    if (navToggle && mobileMenu) {
        navToggle.addEventListener('click', function () {
            const isOpen = mobileMenu.classList.toggle('is-open');
            navToggle.setAttribute('aria-expanded', isOpen);
        });

        // Tutup menu saat klik di luar
        document.addEventListener('click', function (e) {
            if (!navToggle.contains(e.target) && !mobileMenu.contains(e.target)) {
                mobileMenu.classList.remove('is-open');
            }
        });
    }

    // ──────────────────────────────────────────
    // 2. NAVBAR SHADOW ON SCROLL
    // ──────────────────────────────────────────
    const navbar = document.querySelector('.navbar');
    if (navbar) {
        window.addEventListener('scroll', function () {
            if (window.scrollY > 10) {
                navbar.style.boxShadow = '0 4px 24px rgba(0,0,0,0.12)';
            } else {
                navbar.style.boxShadow = '0 2px 8px rgba(0,0,0,0.06)';
            }
        }, { passive: true });
    }

    // ──────────────────────────────────────────
    // 3. INTERSECTION OBSERVER — Card Reveal
    //    (Car cards fade & slide up when they
    //     enter the viewport)
    // ──────────────────────────────────────────
    const revealTargets = document.querySelectorAll('.car-card, .entry-card, .step, .trust-item');

    if ('IntersectionObserver' in window && revealTargets.length > 0) {
        // Set initial invisible state via inline style
        revealTargets.forEach(function (el, i) {
            el.style.opacity    = '0';
            el.style.transform  = 'translateY(28px)';
            el.style.transition = `opacity 0.55s ease ${i * 60}ms, transform 0.55s ease ${i * 60}ms`;
        });

        const observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.style.opacity   = '1';
                    entry.target.style.transform = 'translateY(0)';
                    observer.unobserve(entry.target); // Animasi hanya sekali
                }
            });
        }, { threshold: 0.1 });

        revealTargets.forEach(function (el) { observer.observe(el); });
    } else {
        // Fallback: langsung tampilkan jika browser tidak support
        revealTargets.forEach(function (el) {
            el.style.opacity   = '1';
            el.style.transform = 'none';
        });
    }

    // ──────────────────────────────────────────
    // 4. FLASH MESSAGE AUTO-DISMISS (5 detik)
    // ──────────────────────────────────────────
    const flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(function (flash) {
        setTimeout(function () {
            flash.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            flash.style.opacity    = '0';
            flash.style.transform  = 'translateX(110%)';
            setTimeout(function () { flash.remove(); }, 400);
        }, 5000);
    });

    // ──────────────────────────────────────────
    // 5. FILTER SIDEBAR — Auto Submit on Change
    //    (di halaman cars.html, radio filter
    //     langsung submit form saat diklik)
    // ──────────────────────────────────────────
    const filterForm   = document.getElementById('filterForm');
    const filterInputs = filterForm
        ? filterForm.querySelectorAll('input[type="radio"]')
        : [];

    filterInputs.forEach(function (radio) {
        radio.addEventListener('change', function () {
            // Debounce kecil supaya UI terasa responsif
            setTimeout(function () { filterForm.submit(); }, 200);
        });
    });

    // ──────────────────────────────────────────
    // 6. SMOOTH SCROLL untuk anchor link (#...)
    // ──────────────────────────────────────────
    document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            const targetEl = document.querySelector(targetId);
            if (targetEl) {
                e.preventDefault();
                const offset = 80; // kompensasi sticky navbar
                const top = targetEl.getBoundingClientRect().top + window.scrollY - offset;
                window.scrollTo({ top: top, behavior: 'smooth' });
            }
        });
    });

}); // END DOMContentLoaded