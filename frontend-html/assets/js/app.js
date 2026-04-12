(function() {
  'use strict';

  const App = {
    initialized: false,
    theme: localStorage.getItem('theme') || 'light',
    sidebarCollapsed: localStorage.getItem('sidebarCollapsed') === 'true',

    init() {
      if (this.initialized) return;
      this.initialized = true;
      this.initTheme();
      this.initSidebar();
      this.initDropdowns();
      this.initModals();
      this.initTabs();
      this.initAnimations();
      this.initCounters();
    },

    initTheme() {
      document.documentElement.setAttribute('data-theme', this.theme);
      const themeToggle = document.querySelector('[data-theme-toggle]');
      if (themeToggle) {
        themeToggle.addEventListener('click', () => {
          this.theme = this.theme === 'light' ? 'dark' : 'light';
          document.documentElement.setAttribute('data-theme', this.theme);
          localStorage.setItem('theme', this.theme);
        });
      }
    },

    initSidebar() {
      const sidebar = document.querySelector('.sidebar');
      const toggle = document.querySelector('.sidebar-toggle');
      const mainContent = document.querySelector('.main-content');
      const topbar = document.querySelector('.topbar');

      if (sidebar && toggle) {
        if (this.sidebarCollapsed) {
          sidebar.classList.add('collapsed');
          if (mainContent) mainContent.classList.add('sidebar-collapsed');
          if (topbar) topbar.classList.add('sidebar-collapsed');
        }

        toggle.addEventListener('click', () => {
          this.sidebarCollapsed = !this.sidebarCollapsed;
          sidebar.classList.toggle('collapsed');
          if (mainContent) mainContent.classList.toggle('sidebar-collapsed');
          if (topbar) topbar.classList.toggle('sidebar-collapsed');
          localStorage.setItem('sidebarCollapsed', this.sidebarCollapsed);
        });
      }

      const mobileToggle = document.querySelector('.topbar-mobile-toggle');
      const sidebarOverlay = document.querySelector('.sidebar-overlay');
      if (mobileToggle && sidebar) {
        mobileToggle.addEventListener('click', () => {
          sidebar.classList.toggle('mobile-open');
          sidebarOverlay.classList.toggle('visible');
        });
        if (sidebarOverlay) {
          sidebarOverlay.addEventListener('click', () => {
            sidebar.classList.remove('mobile-open');
            sidebarOverlay.classList.remove('visible');
          });
        }
      }
    },

    initDropdowns() {
      document.querySelectorAll('.dropdown').forEach(dropdown => {
        const trigger = dropdown.querySelector('.dropdown-trigger');
        if (trigger) {
          trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            document.querySelectorAll('.dropdown.open').forEach(d => {
              if (d !== dropdown) d.classList.remove('open');
            });
            dropdown.classList.toggle('open');
          });
        }
      });

      document.addEventListener('click', () => {
        document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
      });
    },

    initModals() {
      document.querySelectorAll('[data-modal]').forEach(trigger => {
        const modalId = trigger.dataset.modal;
        const modal = document.getElementById(modalId);
        if (modal) {
          trigger.addEventListener('click', () => this.openModal(modalId));
        }
      });

      document.querySelectorAll('.modal-backdrop, .modal-close').forEach(el => {
        el.addEventListener('click', () => this.closeAllModals());
      });

      document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
          if (e.target === modal) this.closeAllModals();
        });
      });

      document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') this.closeAllModals();
      });
    },

    openModal(id) {
      const modal = document.getElementById(id);
      const backdrop = document.querySelector('.modal-backdrop');
      if (modal) {
        modal.classList.add('open');
        if (backdrop) backdrop.classList.add('open');
        document.body.style.overflow = 'hidden';
      }
    },

    closeAllModals() {
      document.querySelectorAll('.modal.open').forEach(m => m.classList.remove('open'));
      document.querySelectorAll('.modal-backdrop.open').forEach(b => b.classList.remove('open'));
      document.body.style.overflow = '';
    },

    initTabs() {
      document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
          const tabGroup = tab.dataset.tabGroup;
          const tabTarget = tab.dataset.tab;

          document.querySelectorAll(`[data-tab-group="${tabGroup}"]`).forEach(t => {
            t.classList.remove('active');
          });

          document.querySelectorAll(`[data-tab="${tabTarget}"]`).forEach(c => {
            c.classList.add('active');
          });

          tab.classList.add('active');
        });
      });
    },

    initAnimations() {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('card-reveal');
            observer.unobserve(entry.target);
          }
        });
      }, { threshold: 0.1 });

      document.querySelectorAll('.animate-on-scroll').forEach(el => observer.observe(el));
    },

    initCounters() {
      const counters = document.querySelectorAll('[data-counter]');
      if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver((entries) => {
          entries.forEach(entry => {
            if (entry.isIntersecting) {
              const el = entry.target;
              const target = parseInt(el.dataset.counter);
              const duration = parseInt(el.dataset.duration) || 2000;
              this.animateCounter(el, target, duration);
              observer.unobserve(el);
            }
          });
        }, { threshold: 0.5 });
        counters.forEach(c => observer.observe(c));
      }
    },

    animateCounter(el, target, duration) {
      const start = 0;
      const startTime = performance.now();
      const update = (currentTime) => {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const value = Math.floor(progress * (target - start) + start);
        el.textContent = value;
        if (progress < 1) requestAnimationFrame(update);
      };
      requestAnimationFrame(update);
    }
  };

  document.addEventListener('DOMContentLoaded', () => App.init());

  window.App = App;
})();