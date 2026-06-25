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

  const paperBrowser = document.querySelector("[data-paper-browser]");
  if (!paperBrowser) return;

  const source = paperBrowser.dataset.source;
  const paperQuery = paperBrowser.querySelector("[data-paper-query]");
  const groupSelect = paperBrowser.querySelector("[data-paper-group]");
  const typeSelect = paperBrowser.querySelector("[data-paper-type]");
  const paperList = paperBrowser.querySelector("[data-paper-list]");
  const paperStatus = paperBrowser.querySelector("[data-paper-status]");
  const paperCount = paperBrowser.querySelector("[data-paper-count]");
  const loadMore = paperBrowser.querySelector("[data-paper-more]");
  const batchSize = 48;
  let papers = [];
  let filteredPapers = [];
  let rendered = 0;
  let searchTimer;

  function createElement(tag, className, text) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== undefined) element.textContent = text;
    return element;
  }

  function paperSearchText(paper) {
    return normalize(
      [paper.t, paper.a, paper.g, paper.c, paper.d, paper.e, ...(paper.k || [])].join(" ")
    );
  }

  function createPaperCard(paper) {
    const card = createElement("article", "catalog-paper-card");
    const badges = createElement("div", "catalog-badges");
    badges.append(createElement("span", "catalog-badge group", paper.g));
    if (paper.d) badges.append(createElement("span", "catalog-badge", paper.d));
    if (paper.e && paper.e !== paper.d) {
      badges.append(createElement("span", "catalog-badge accent", paper.e));
    }

    const title = createElement("h3");
    const titleLink = createElement("a", "", paper.t);
    titleLink.href = paper.u || paper.v;
    titleLink.target = "_blank";
    titleLink.rel = "noreferrer";
    title.append(titleLink);

    const authors = createElement("p", "catalog-authors", paper.a);
    const area = createElement("p", "catalog-area", paper.c || paper.g);
    const actions = createElement("div", "catalog-actions");
    if (paper.u) {
      const official = createElement("a", "", "论文与评审 ↗");
      official.href = paper.u;
      official.target = "_blank";
      official.rel = "noreferrer";
      actions.append(official);
    }
    if (paper.v && paper.v !== paper.u) {
      const virtual = createElement("a", "", "会议展示 ↗");
      virtual.href = paper.v;
      virtual.target = "_blank";
      virtual.rel = "noreferrer";
      actions.append(virtual);
    }

    card.append(badges, title, authors, area);
    if (paper.k?.length) {
      const keywords = createElement("p", "catalog-keywords", paper.k.join(" · "));
      card.append(keywords);
    }
    card.append(actions);
    return card;
  }

  function renderMorePapers() {
    const next = filteredPapers.slice(rendered, rendered + batchSize);
    const fragment = document.createDocumentFragment();
    next.forEach((paper) => fragment.append(createPaperCard(paper)));
    paperList.append(fragment);
    rendered += next.length;
    loadMore.hidden = rendered >= filteredPapers.length;
    loadMore.textContent = `继续加载（已显示 ${rendered.toLocaleString()} / ${filteredPapers.length.toLocaleString()}）`;
  }

  function filterPapers() {
    const query = normalize(paperQuery.value);
    const group = groupSelect.value;
    const type = typeSelect.value;
    filteredPapers = papers.filter(
      (paper) =>
        (!query || paper._search.includes(query)) &&
        (!group || paper.g === group) &&
        (!type || paper.d === type || paper.e === type)
    );
    paperList.replaceChildren();
    rendered = 0;
    paperCount.textContent = filteredPapers.length.toLocaleString();
    paperStatus.textContent = filteredPapers.length
      ? `找到 ${filteredPapers.length.toLocaleString()} 篇，按官方研究方向整理。`
      : "没有匹配论文，请调整关键词或筛选条件。";
    renderMorePapers();
  }

  function fillSelect(select, values, defaultLabel) {
    const first = createElement("option", "", defaultLabel);
    first.value = "";
    select.append(first);
    values.forEach(([value, count]) => {
      const option = createElement("option", "", `${value}（${count.toLocaleString()}）`);
      option.value = value;
      select.append(option);
    });
  }

  fetch(source)
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then((payload) => {
      papers = payload.papers.map((paper) => ({
        ...paper,
        _search: paperSearchText(paper),
      }));
      const groupCounts = new Map();
      const typeCounts = new Map();
      papers.forEach((paper) => {
        groupCounts.set(paper.g, (groupCounts.get(paper.g) || 0) + 1);
        new Set([paper.d, paper.e].filter(Boolean)).forEach((type) => {
          typeCounts.set(type, (typeCounts.get(type) || 0) + 1);
        });
      });
      fillSelect(
        groupSelect,
        [...groupCounts.entries()].sort((a, b) => b[1] - a[1]),
        "全部研究方向"
      );
      fillSelect(
        typeSelect,
        [...typeCounts.entries()].sort((a, b) => b[1] - a[1]),
        "全部展示类型"
      );
      filteredPapers = papers;
      paperStatus.textContent = `已加载 ${papers.length.toLocaleString()} 篇官方论文记录。`;
      paperCount.textContent = papers.length.toLocaleString();
      renderMorePapers();
    })
    .catch(() => {
      paperStatus.textContent = "论文数据加载失败，请刷新页面或使用上方官方论文入口。";
      paperBrowser.classList.add("has-error");
    });

  paperQuery.addEventListener("input", () => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(filterPapers, 120);
  });
  groupSelect.addEventListener("change", filterPapers);
  typeSelect.addEventListener("change", filterPapers);
  loadMore.addEventListener("click", renderMorePapers);
})();
