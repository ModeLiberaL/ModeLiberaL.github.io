(function () {
  const body = document.body;
  const menuButton = document.querySelector(".mobile-menu");
  const closeButton = document.querySelector(".sidebar-close");
  const backdrop = document.querySelector(".sidebar-backdrop");
  const sidebar = document.querySelector(".sidebar");

  function setNavigation(open) {
    body.classList.toggle("nav-open", open);
    if (menuButton) menuButton.setAttribute("aria-expanded", String(open));
    if (backdrop) backdrop.hidden = !open;
  }

  menuButton?.addEventListener("click", () => setNavigation(true));
  closeButton?.addEventListener("click", () => setNavigation(false));
  backdrop?.addEventListener("click", () => setNavigation(false));
  sidebar?.addEventListener("click", (event) => {
    if (event.target.closest("a") && window.innerWidth <= 920) setNavigation(false);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setNavigation(false);
  });

  const search = document.querySelector("[data-guide-search]");
  const root = document.querySelector("[data-search-root]");
  const cards = root ? [...root.querySelectorAll("[data-search-card]")] : [];
  const empty = root?.querySelector("[data-search-empty]");
  const count = document.querySelector("[data-search-count]");

  function normalize(value) {
    return value.toLocaleLowerCase("zh-CN").replace(/\s+/g, " ").trim();
  }

  function runSearch() {
    const query = normalize(search?.value || "");
    let visible = 0;

    cards.forEach((card) => {
      const haystack = normalize(`${card.dataset.search || ""} ${card.textContent || ""}`);
      const match = !query || haystack.includes(query);
      card.hidden = !match;
      if (match) visible += 1;
    });

    if (empty) empty.hidden = visible !== 0;
    if (count) count.textContent = String(visible);
  }

  search?.addEventListener("input", runSearch);

  const localLinks = [...document.querySelectorAll('.directory a[href^="#"]')];
  const observed = localLinks
    .map((link) => document.querySelector(link.getAttribute("href")))
    .filter(Boolean);

  if ("IntersectionObserver" in window && observed.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        const active = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (!active) return;

        localLinks.forEach((link) => {
          link.classList.toggle("is-current", link.getAttribute("href") === `#${active.target.id}`);
        });
      },
      { rootMargin: "-18% 0px -68% 0px", threshold: [0.05, 0.25, 0.5] }
    );

    observed.forEach((section) => observer.observe(section));
  }
})();
