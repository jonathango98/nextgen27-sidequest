// Favorite verse pickers: the chapter and verse lists show only numbers that exist in the
// chosen book (WRAP-012). The server checks the pick again (AI-040).
// Then it asks for the picked verse's words (DEC-083).
(function () {
  "use strict";

  var verses = JSON.parse(document.getElementById("bible-verses").textContent);

  function fill(select, count) {
    var keep = Math.min(Number(select.value) || 1, count);
    select.replaceChildren();
    for (var n = 1; n <= count; n++) select.add(new Option(n, n, false, n === keep));
  }

  // Delegated, so it still works after HTMX swaps the answer card back in.
  document.addEventListener("change", function (e) {
    var form = e.target.form;
    if (!form || !form.chapter || !form.verse) return;
    var chapters = verses[form.book.value];
    if (chapters) {
      if (e.target.name === "book") fill(form.chapter, chapters.length);
      if (e.target.name === "book" || e.target.name === "chapter") {
        fill(form.verse, chapters[Number(form.chapter.value) - 1]);
      }
    }
    // Only after narrowing, or the request carries the last book's numbers.
    form.querySelector(".verse-text").dispatchEvent(new Event("verse-picked"));
  });

  // The words load above the pickers, so scroll by however far that pushed them (DEC-083).
  var pickersTop;
  document.addEventListener("htmx:beforeSwap", function (e) {
    if (!e.detail.target.matches(".verse-text")) return;
    pickersTop = e.detail.target.nextElementSibling.getBoundingClientRect().top;
  });
  document.addEventListener("htmx:afterSwap", function (e) {
    if (!e.detail.target.matches(".verse-text")) return;
    scrollBy(0, e.detail.target.nextElementSibling.getBoundingClientRect().top - pickersTop);
  });
})();
