// Journal form: counts words as you type (GAME-034) and shows the points pill only for a
// session that hasn't paid yet (DEC-072). The server checks both again (AI-040).
(function () {
  "use strict";

  function wordCount(text) {
    // GAME-034: split on spaces and line breaks. Punctuation alone is not a word.
    return text.split(/\s+/).filter(function (t) {
      return /[\p{L}\p{N}]/u.test(t);
    }).length;
  }

  function wire(form) {
    if (!form || form.dataset.wired) return;
    form.dataset.wired = "1";
    var box = form.querySelector("textarea");
    var count = form.querySelector(".word-count");
    var pill = form.querySelector("[data-submit-pill]");
    var min = count.dataset.minWords;

    function update() {
      count.textContent = wordCount(box.value) + " / " + min + " words";
    }

    box.addEventListener("input", update);
    form.addEventListener("change", function (e) {
      if (e.target.name === "session") pill.hidden = e.target.dataset.paid === "1";
    });
    update();
  }

  wire(document.querySelector("[data-journal-form]"));
  // An HTMX error swap puts in a fresh form, so wire that one too.
  document.body.addEventListener("htmx:afterSwap", function () {
    wire(document.querySelector("[data-journal-form]"));
  });
})();
