(function () {
  var drawer = document.getElementById("detail-drawer");
  var title = document.getElementById("drawer-title");
  var body = document.getElementById("drawer-body");

  if (!drawer || !title || !body) {
    return;
  }

  function closeDrawer() {
    drawer.classList.remove("is-open");
    drawer.setAttribute("aria-hidden", "true");
    document.body.classList.remove("drawer-open");
    body.replaceChildren();
  }

  document.addEventListener("click", function (event) {
    var trigger = event.target.closest("[data-drawer-target]");
    if (!trigger) {
      return;
    }

    var template = document.getElementById(trigger.getAttribute("data-drawer-target"));
    if (!template) {
      return;
    }

    title.textContent = trigger.getAttribute("data-drawer-title") || "Details";
    body.replaceChildren(template.content.cloneNode(true));
    drawer.classList.add("is-open");
    drawer.setAttribute("aria-hidden", "false");
    document.body.classList.add("drawer-open");
  });

  document.querySelectorAll("[data-drawer-close]").forEach(function (trigger) {
    trigger.addEventListener("click", closeDrawer);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && drawer.classList.contains("is-open")) {
      closeDrawer();
    }
  });
})();
