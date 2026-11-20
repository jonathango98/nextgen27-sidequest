// Favorite verse pickers: the chapter and verse lists show only numbers that exist in the
// chosen book (WRAP-012). The server checks the pick again (AI-040).
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
    if (!chapters) return;
    if (e.target.name === "book") fill(form.chapter, chapters.length);
    if (e.target.name === "book" || e.target.name === "chapter") {
      fill(form.verse, chapters[Number(form.chapter.value) - 1]);
    }
  });
})();
