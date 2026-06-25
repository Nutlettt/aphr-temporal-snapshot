(function () {
  function openDrawer(drawer) {
    if (!drawer) {
      return;
    }
    drawer.classList.add("is-open");
    drawer.setAttribute("aria-hidden", "false");
    document.body.classList.add("nav-open");
  }

  function closeDrawer(drawer) {
    if (!drawer) {
      return;
    }
    drawer.classList.remove("is-open");
    drawer.setAttribute("aria-hidden", "true");
    document.body.classList.remove("nav-open");
  }

  function resolveTarget(trigger) {
    var id = trigger.getAttribute("data-site-nav-open") || "site-content-drawer";
    return document.getElementById(id);
  }

  document.querySelectorAll("[data-site-nav-open]").forEach(function (trigger) {
    trigger.addEventListener("click", function () {
      openDrawer(resolveTarget(trigger));
    });
  });

  document.querySelectorAll("[data-site-nav-close]").forEach(function (trigger) {
    trigger.addEventListener("click", function () {
      closeDrawer(trigger.closest(".site-nav-shell"));
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") {
      return;
    }

    document.querySelectorAll(".site-nav-shell.is-open").forEach(closeDrawer);
  });
})();
