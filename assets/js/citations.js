(function () {
  function getReferenceId(citation) {
    var text = citation.textContent || "";
    var match = text.match(/\[(\d+)\]/);
    return match ? "ref-" + match[1] : null;
  }

  function activateReference(reference) {
    reference.scrollIntoView({ behavior: "smooth", block: "center" });
    reference.classList.remove("aphr-reference-highlight");
    window.setTimeout(function () {
      reference.classList.add("aphr-reference-highlight");
    }, 20);
  }

  document.addEventListener("click", function (event) {
    var citation = event.target.closest(".citation");
    if (!citation) {
      return;
    }

    var referenceId = getReferenceId(citation);
    if (!referenceId) {
      return;
    }

    var reference = document.getElementById(referenceId);
    if (reference) {
      activateReference(reference);
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" && event.key !== " ") {
      return;
    }

    var citation = event.target.closest(".citation");
    if (!citation) {
      return;
    }

    event.preventDefault();
    citation.click();
  });

  document.querySelectorAll(".citation").forEach(function (citation) {
    citation.setAttribute("tabindex", "0");
    citation.setAttribute("role", "button");
    citation.setAttribute("aria-label", "Show reference " + citation.textContent);
  });
})();
