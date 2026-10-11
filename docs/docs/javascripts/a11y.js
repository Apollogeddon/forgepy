// Fills accessibility gaps in Zensical's theme that its configuration can't reach: the search
// dialog (built in a shadow root) has unnamed buttons and stays focusable while closed, the
// header's icon labels carry aria-label (not allowed on <label>), the one-scheme palette's
// hidden radio is focusable, and code blocks scroll without being reachable by keyboard.
// Elements are found by role and icon rather than Zensical's minified class names.
(() => {
  // A closed panel leaves the tab order and the accessibility tree; Zensical only fades it out.
  // The dialog turns off pointer events as it closes; the filter panel only fades, so it is
  // checked again when its transition ends.
  const syncHidden = (el, hidden) => {
    el.inert = hidden;
    if (hidden) el.setAttribute("aria-hidden", "true");
    else el.removeAttribute("aria-hidden");
  };

  const fixSearch = (root) => {
    const input = root.querySelector('input[role="combobox"]');
    if (!input) return false;
    // the dialog is the input's ancestor that sits beside the backdrop
    let dialog = input;
    while (dialog.parentElement && dialog.parentElement.parentNode !== root) dialog = dialog.parentElement;
    const results = dialog.querySelector("ol");
    const filters = root.querySelector("h3")?.parentElement?.parentElement ?? null;

    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.setAttribute("aria-label", "Search");
    input.setAttribute("aria-label", "Search");
    if (results) {
      results.id = "fp-search-results";
      results.setAttribute("aria-label", "Search results");
      input.setAttribute("aria-controls", results.id);
    }
    for (const button of root.querySelectorAll("button")) {
      if (button.querySelector(".lucide-search")) button.setAttribute("aria-label", "Search");
      else if (button.querySelector(".lucide-list-filter")) button.setAttribute("aria-label", "Filters");
      button.querySelector("svg")?.setAttribute("aria-hidden", "true");
    }
    // the filter panel's headings follow on from the page's, so they'd skip levels
    for (const heading of root.querySelectorAll("h3, h4")) {
      heading.setAttribute("aria-level", heading.tagName === "H3" ? "2" : "3");
    }

    const sync = () => {
      syncHidden(dialog, getComputedStyle(dialog).pointerEvents === "none");
      if (filters) syncHidden(filters, getComputedStyle(filters).opacity === "0");
      input.setAttribute("aria-expanded", String(Boolean(results?.childElementCount)));
    };
    sync();
    new MutationObserver(sync).observe(root, { subtree: true, childList: true, attributes: true, attributeFilter: ["class"] });
    root.addEventListener("transitionend", sync);
    return true;
  };

  // each code block wraps its copy button in a <nav>, which makes a landmark per block
  const fixCodeNavs = (scope) => {
    for (const nav of scope.querySelectorAll("nav.md-code__nav:not([role])")) nav.setAttribute("role", "none");
  };

  // a code block that scrolls sideways needs focus to scroll by keyboard, as on forgego's site
  const fixCodeBlocks = (scope) => {
    for (const code of scope.querySelectorAll(".md-typeset pre > code:not([tabindex])")) code.tabIndex = 0;
  };

  // the label's name moves into its text, which also names the checkbox it toggles
  const fixHeaderLabels = () => {
    for (const label of document.querySelectorAll("label.md-header__button[aria-label]")) {
      const name = document.createElement("span");
      name.className = "fp-sr-only";
      name.textContent = label.getAttribute("aria-label");
      label.append(name);
      label.removeAttribute("aria-label");
    }
    // the palette has one scheme, so its radio is never shown, but it can still take focus
    for (const radio of document.querySelectorAll('[data-md-component="palette"] input[aria-hidden="true"]')) {
      radio.tabIndex = -1;
    }
  };

  const watched = new WeakSet();
  let searchFixed = false;
  const scan = () => {
    fixCodeNavs(document);
    fixCodeBlocks(document);
    if (searchFixed) return;
    for (const host of document.body.children) {
      const root = host.shadowRoot;
      if (!root) continue;
      if (fixSearch(root)) {
        searchFixed = true;
        break;
      }
      // the host can be attached before its contents are rendered
      if (!watched.has(root)) {
        watched.add(root);
        new MutationObserver(scan).observe(root, { childList: true, subtree: true });
      }
    }
  };

  fixHeaderLabels();

  new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });
  scan();
})();
