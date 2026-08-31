// Project-wide custom JavaScript for the admin dashboard.

document.addEventListener("DOMContentLoaded", function () {
  var sidebar = document.getElementById("app-sidebar");
  var backdrop = document.getElementById("sidebar-backdrop");
  var toggle = document.getElementById("sidebar-toggle");

  function openSidebar() {
    if (!sidebar) return;
    sidebar.classList.remove("-translate-x-full");
    if (backdrop) backdrop.classList.remove("hidden");
  }

  function closeSidebar() {
    if (!sidebar) return;
    sidebar.classList.add("-translate-x-full");
    if (backdrop) backdrop.classList.add("hidden");
  }

  if (toggle) {
    toggle.addEventListener("click", function () {
      if (sidebar.classList.contains("-translate-x-full")) {
        openSidebar();
      } else {
        closeSidebar();
      }
    });
  }

  if (backdrop) {
    backdrop.addEventListener("click", closeSidebar);
  }

  // Close the mobile sidebar whenever a nav link is tapped.
  if (sidebar) {
    sidebar.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        if (window.innerWidth < 1024) closeSidebar();
      });
    });
  }
});
