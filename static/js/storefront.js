// Lolaire's Kitchen — storefront interactions

document.addEventListener("DOMContentLoaded", () => {
  // Mobile nav toggle
  const navToggle = document.getElementById("mobile-nav-toggle");
  const mobileNav = document.getElementById("mobile-nav");
  if (navToggle && mobileNav) {
    navToggle.addEventListener("click", () => {
      mobileNav.classList.toggle("is-open");
      navToggle.setAttribute(
        "aria-expanded",
        mobileNav.classList.contains("is-open") ? "true" : "false"
      );
    });
  }

  // Scroll reveal
  const revealEls = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && revealEls.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15 }
    );
    revealEls.forEach((el) => observer.observe(el));
  } else {
    revealEls.forEach((el) => el.classList.add("is-visible"));
  }

  // Smooth scroll for on-page anchor links
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", (e) => {
      const targetId = link.getAttribute("href");
      if (targetId.length > 1) {
        const target = document.querySelector(targetId);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      }
    });
  });

  // Navbar background on scroll
  const nav = document.getElementById("site-nav");
  if (nav) {
    const onScroll = () => {
      if (window.scrollY > 24) {
        nav.classList.add("nav-scrolled");
      } else {
        nav.classList.remove("nav-scrolled");
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  // Menu category filter pills (client-side toggle of already-loaded page,
  // real filtering happens server-side via query params on click)
  const filterForm = document.getElementById("menu-filter-form");
  if (filterForm) {
    filterForm.querySelectorAll("[data-category-pill]").forEach((pill) => {
      pill.addEventListener("click", () => {
        filterForm.querySelector('input[name="category"]').value = pill.dataset.categoryPill;
        filterForm.submit();
      });
    });
  }

  // Quantity steppers (checkout/cart quantity forms auto-submit on change)
  document.querySelectorAll("[data-qty-form]").forEach((form) => {
    const input = form.querySelector("input[name='quantity']");
    form.querySelectorAll("[data-qty-step]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const step = parseInt(btn.dataset.qtyStep, 10);
        const next = Math.max(0, parseInt(input.value || "1", 10) + step);
        input.value = next;
        form.submit();
      });
    });
  });

  // Quantity steppers that only adjust the number, without submitting
  // (e.g. the product detail page, where "Add to Cart" is a separate,
  // deliberate action rather than an immediate update).
  document.querySelectorAll("[data-qty-adjust]").forEach((wrapper) => {
    const input = wrapper.querySelector("input[name='quantity']");
    wrapper.querySelectorAll("[data-qty-step]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const step = parseInt(btn.dataset.qtyStep, 10);
        const next = Math.max(1, parseInt(input.value || "1", 10) + step);
        input.value = next;
      });
    });
  });
});
