// Tool page runtime: render catalog data without owning tool facts.
(function () {
  var toolSource = window.AINavToolData || { categories: [], tools: [], placements: [] };
  var pageLists = window.AINavToolPageLists || { latestTools: [] };
  var toolsById = {};
  var toolMeta = {};
  var state = {
    category: 'chat',
    page: 1,
    query: '',
    freeOnly: false,
    activeSubs: {},
    sectionPages: {}
  };

  function $(id) {
    return document.getElementById(id);
  }

  function escapeAttr(value) {
    return String(value || '').replace(/[&<>"']/g, function (ch) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
    });
  }

  function escapeText(value) {
    var node = document.createElement('div');
    node.textContent = value == null ? '' : String(value);
    return node.innerHTML;
  }

  function normalizeToolName(name) {
    return String(name || '').replace(/\s+V?\d+(\.\d+)?$/i, '').trim();
  }

  function hostFrom(url) {
    try {
      return new URL(url).hostname;
    } catch (e) {
      return '';
    }
  }

  function buildCategories() {
    toolsById = {};
    toolMeta = {};
    (toolSource.tools || []).forEach(function (tool) {
      toolsById[tool.id] = tool;
      var icons = [tool.icon].concat(tool.iconFallbacks || []).filter(Boolean);
      var meta = {
        url: tool.url,
        icon: tool.icon,
        icons: icons,
        aliases: tool.aliases || []
      };
      toolMeta[tool.name] = meta;
      toolMeta[normalizeToolName(tool.name)] = meta;
      (tool.aliases || []).forEach(function (alias) {
        toolMeta[alias] = meta;
        toolMeta[normalizeToolName(alias)] = meta;
      });
    });

    var placements = toolSource.placements || (toolSource.tools || []).map(function (tool) {
      return {
        toolId: tool.id,
        categoryId: tool.categoryId,
        subcategory: tool.subcategory,
        heat: tool.heat,
        tag: tool.tag
      };
    });

    return (toolSource.categories || []).map(function (cat) {
      var tools = placements.filter(function (place) {
        return place.categoryId === cat.id && toolsById[place.toolId];
      }).map(function (place) {
        var tool = toolsById[place.toolId];
        return {
          category: null,
          name: tool.name,
          desc: tool.description,
          sub: place.subcategory,
          heat: Number(place.heat) || 0,
          tag: place.tag || '',
          mark: tool.mark || 'AI'
        };
      });
      var category = {
        id: cat.id,
        name: cat.name,
        icon: cat.icon,
        logo: cat.logoClass,
        desc: cat.description,
        subs: cat.subcategories || ['全部'],
        tools: tools
      };
      tools.forEach(function (tool) {
        tool.category = category;
      });
      return category;
    });
  }

  var categories = buildCategories();

  function latestTools() {
    return (pageLists.latestTools || []).map(function (item) {
      var tool = window.AINavFindTool ? (window.AINavFindTool(item.toolName) || window.AINavFindTool(item.displayName)) : null;
      return {
        displayName: item.displayName,
        provider: item.provider || (tool && tool.categoryName) || '',
        label: item.label || (tool && tool.tag) || '',
        mark: item.mark || (tool && tool.mark) || 'AI',
        logoClass: item.logoClass || (tool && tool.logoClass) || 'logo-chat',
        toolName: item.toolName || item.displayName
      };
    });
  }

  function metaFor(name) {
    return toolMeta[name] || toolMeta[normalizeToolName(name)] || {};
  }

  function toolUrl(name) {
    var meta = metaFor(name);
    return meta.url || ('https://www.baidu.com/s?wd=' + encodeURIComponent(name + ' 官网'));
  }

  function iconCandidates(name) {
    var meta = metaFor(name);
    var url = meta.url || '';
    var host = hostFrom(url);
    var origin = '';
    try {
      origin = new URL(url).origin;
    } catch (e) {}
    return (meta.icons || []).concat(host ? [
      'https://icons.duckduckgo.com/ip3/' + host + '.ico',
      origin + '/favicon.ico'
    ] : []);
  }

  function logoHtml(name, mark, logoClass, className) {
    var icons = iconCandidates(name);
    var base = className || 'tool-logo';
    var classes = base + ' ' + (logoClass || '');
    if (!icons.length) {
      return '<div class="' + escapeAttr(classes) + '" data-mark="' + escapeAttr(mark) + '">' + escapeText(mark) + '</div>';
    }
    return '<div class="' + escapeAttr(classes) + '" data-mark="' + escapeAttr(mark) + '"><img src="' + escapeAttr(icons[0]) + '" alt="' + escapeAttr(name) + ' logo" loading="lazy" decoding="async" data-fallbacks="' + escapeAttr(icons.slice(1).join('|')) + '"></div>';
  }

  function bindBrandIconFallbacks(scope) {
    (scope || document).querySelectorAll('.tool-logo img, .latest-logo img').forEach(function (img) {
      if (img.dataset.boundIconFallback === '1') return;
      img.dataset.boundIconFallback = '1';
      img.addEventListener('error', function () {
        var fallbacks = (img.dataset.fallbacks || '').split('|').filter(Boolean);
        if (fallbacks.length) {
          img.dataset.fallbacks = fallbacks.slice(1).join('|');
          img.src = fallbacks[0];
          return;
        }
        var box = img.parentElement;
        if (box) box.textContent = box.dataset.mark || '';
      });
    });
  }

  function getAllSub(cat) {
    return (cat && cat.subs && cat.subs[0]) || '全部';
  }

  function getActiveSub(cat) {
    return state.activeSubs[cat.id] || getAllSub(cat);
  }

  function setActiveSub(catId, sub) {
    state.activeSubs[catId] = sub;
  }

  function sectionPageKey(catId, sub) {
    return catId + '::' + sub + '::' + (state.query || '') + '::' + (state.freeOnly ? 'free' : 'all');
  }

  function getSectionPage(catId, sub) {
    return state.sectionPages[sectionPageKey(catId, sub)] || 1;
  }

  function setSectionPage(catId, sub, page) {
    state.sectionPages[sectionPageKey(catId, sub)] = page;
  }

  function renderLatest() {
    var track = $('latestTrack');
    if (!track) return;
    track.innerHTML = latestTools().concat(latestTools()).map(function (item) {
      var refName = item.toolName || item.displayName;
      return '<a class="latest-card" href="' + escapeAttr(toolUrl(refName)) + '" target="_blank" rel="noopener noreferrer">' +
        logoHtml(refName, item.mark, item.logoClass, 'latest-logo') +
        '<div><strong>' + escapeText(item.displayName) + '</strong><span>' + escapeText(item.provider) + '</span><em>' + escapeText(item.label) + '</em></div></a>';
    }).join('');
    bindBrandIconFallbacks(track);
  }

  function hydrateWorkflowIcons() {
    document.querySelectorAll('[data-workflow-tool]').forEach(function (item) {
      var name = item.dataset.workflowTool || '';
      var mark = item.dataset.workflowMark || '';
      var icon = item.querySelector('.tool-icon');
      if (!icon || icon.dataset.workflowIconBound === '1') return;
      icon.dataset.workflowIconBound = '1';
      icon.dataset.mark = mark;
      icon.innerHTML = logoHtml(name, mark, '', 'tool-icon').replace(/^<div[^>]*>|<\/div>$/g, '') || escapeText(mark);
    });
    bindBrandIconFallbacks(document);
  }

  function renderNav() {
    var nav = $('categoryNav');
    if (!nav) return;
    nav.innerHTML = '<h3>分区跳转</h3>' + categories.map(function (cat) {
      return '<button class="' + (cat.id === state.category ? 'active' : '') + '" data-cat="' + escapeAttr(cat.id) + '"><span>' + escapeText(cat.icon) + '</span>' + escapeText(cat.name) + '</button>';
    }).join('');
    nav.querySelectorAll('button[data-cat]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        setCategory(btn.dataset.cat);
      });
    });
  }

  function renderRail() {
    var groups = document.querySelectorAll('.rail-group');
    if (!groups.length) return;
    groups[0].innerHTML = '<div class="rail-title">核心工具</div>' + categories.map(function (cat) {
      var active = cat.id === state.category;
      var activeSub = getActiveSub(cat);
      var subs = cat.subs.slice(1).map(function (sub) {
        return '<button class="rail-sub ' + (active && activeSub === sub ? 'active' : '') + '" data-rail-sub="' + escapeAttr(sub) + '" data-rail-cat="' + escapeAttr(cat.id) + '">' + escapeText(sub) + '</button>';
      }).join('');
      return '<div class="rail-category"><button class="rail-link rail-parent ' + (active ? 'active open' : '') + '" data-rail="' + escapeAttr(cat.id) + '"><span class="rail-icon">' + escapeText(cat.icon) + '</span><span>' + escapeText(cat.name) + '</span></button><div class="rail-sublist ' + (active ? 'open' : '') + '">' + subs + '</div></div>';
    }).join('');
    groups[0].querySelectorAll('[data-rail]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        setCategory(btn.dataset.rail);
      });
    });
    groups[0].querySelectorAll('[data-rail-sub]').forEach(function (btn) {
      btn.addEventListener('click', function (event) {
        event.stopPropagation();
        setSubcategory(btn.dataset.railCat, btn.dataset.railSub);
      });
    });
  }

  function toolCard(tool) {
    return '<a href="' + escapeAttr(toolUrl(tool.name)) + '" target="_blank" rel="noopener noreferrer" class="tool-card" data-tool="' + escapeAttr(tool.name) + '">' +
      '<div class="tool-main">' + logoHtml(tool.name, tool.mark, tool.category.logo) +
      '<div class="tool-info"><strong>' + escapeText(tool.name) + '</strong><p>' + escapeText(tool.desc) + '</p></div></div>' +
      '<div class="tool-meta"><span class="tag">' + escapeText(tool.sub) + '</span><span class="tool-arrow">›</span></div></a>';
  }

  function decorateCards(scope) {
    bindBrandIconFallbacks(scope || document);
    (scope || document).querySelectorAll('.tool-card').forEach(function (card) {
      if (card.dataset.boundHover === '1') return;
      card.dataset.boundHover = '1';
      card.addEventListener('mousemove', function (event) {
        var rect = card.getBoundingClientRect();
        card.style.setProperty('--mx', ((event.clientX - rect.left) / rect.width * 100) + '%');
        card.style.setProperty('--my', ((event.clientY - rect.top) / rect.height * 100) + '%');
      });
    });
  }

  function toolMatchesFreeFlag(tool) {
    return /免费|开源|国产|中文|free|open/i.test(tool.tag + tool.desc + tool.sub);
  }

  function filteredSectionTools(cat, activeSub) {
    return cat.tools.filter(function (tool) {
      var text = (tool.name + tool.desc + tool.sub + tool.category.name).toLowerCase();
      var matchSub = activeSub === getAllSub(cat) || tool.sub === activeSub;
      var matchQuery = !state.query || text.includes(state.query.toLowerCase());
      var matchFree = !state.freeOnly || toolMatchesFreeFlag(tool);
      return matchSub && matchQuery && matchFree;
    }).sort(function (a, b) {
      return b.heat - a.heat;
    });
  }

  function sectionPagerControls(catId, activeSub, currentPage, totalPages) {
    return '<button type="button" data-page-cat="' + escapeAttr(catId) + '" data-page-sub="' + escapeAttr(activeSub) + '" data-page-dir="prev" ' + (currentPage === 1 ? 'disabled' : '') + '>&lt;</button>' +
      '<span>' + currentPage + ' / ' + totalPages + '</span>' +
      '<button type="button" data-page-cat="' + escapeAttr(catId) + '" data-page-sub="' + escapeAttr(activeSub) + '" data-page-dir="next" ' + (currentPage === totalPages ? 'disabled' : '') + '>&gt;</button>';
  }

  function bindSectionPager(scope) {
    (scope || document).querySelectorAll('[data-page-dir]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var current = getSectionPage(btn.dataset.pageCat, btn.dataset.pageSub);
        var next = current + (btn.dataset.pageDir === 'next' ? 1 : -1);
        renderSectionPage(btn.dataset.pageCat, btn.dataset.pageSub, next);
      });
    });
  }

  function renderSectionPage(catId, activeSub, requestedPage) {
    var keepY = window.scrollY;
    var cat = categories.find(function (item) { return item.id === catId; });
    var section = document.getElementById('section-' + catId);
    if (!cat || !section) return;

    var tools = filteredSectionTools(cat, activeSub);
    var pageSize = 12;
    var totalPages = Math.max(1, Math.ceil(tools.length / pageSize));
    var currentPage = Math.max(1, Math.min(requestedPage, totalPages));
    var pageTools = tools.slice((currentPage - 1) * pageSize, currentPage * pageSize);
    var grid = section.querySelector('.category-tools');
    var pager = section.querySelector('.section-pager');

    setSectionPage(catId, activeSub, currentPage);
    if (grid) grid.innerHTML = pageTools.map(toolCard).join('');
    if (totalPages > 1) {
      if (!pager) {
        section.insertAdjacentHTML('beforeend', '<div class="section-pager"></div>');
        pager = section.querySelector('.section-pager');
      }
      pager.innerHTML = sectionPagerControls(catId, activeSub, currentPage, totalPages);
      bindSectionPager(pager);
    } else if (pager) {
      pager.remove();
    }
    decorateCards(section);
    if (document.activeElement) document.activeElement.blur();
    window.scrollTo(0, keepY);
    requestAnimationFrame(function () {
      window.scrollTo(0, keepY);
    });
  }

  function renderTools() {
    var container = $('toolsSections');
    if (!container) return;
    renderNav();
    renderRail();

    var html = categories.map(function (cat) {
      var activeSub = state.query || state.freeOnly ? getAllSub(cat) : getActiveSub(cat);
      var tools = filteredSectionTools(cat, activeSub);
      if (!tools.length) return '';

      var pageSize = 12;
      var totalPages = Math.max(1, Math.ceil(tools.length / pageSize));
      var currentPage = Math.min(getSectionPage(cat.id, activeSub), totalPages);
      var pageTools = tools.slice((currentPage - 1) * pageSize, currentPage * pageSize);
      var tabs = cat.subs.map(function (sub) {
        return '<button class="' + (sub === activeSub ? 'active' : '') + '" data-sub-cat="' + escapeAttr(cat.id) + '" data-sub="' + escapeAttr(sub) + '">' + escapeText(sub) + '</button>';
      }).join('');
      var pager = totalPages > 1 ? '<div class="section-pager">' + sectionPagerControls(cat.id, activeSub, currentPage, totalPages) + '</div>' : '';

      setSectionPage(cat.id, activeSub, currentPage);
      return '<section class="category-section" id="section-' + escapeAttr(cat.id) + '">' +
        '<div class="category-top"><div class="category-title"><h2>' + escapeText(cat.name) + '</h2><p>' + escapeText(cat.desc) + '</p></div><div class="category-count">' + tools.length + ' 个工具</div></div>' +
        '<div class="section-subnav">' + tabs + '</div><div class="category-tools">' + pageTools.map(toolCard).join('') + '</div>' + pager + '</section>';
    }).join('');

    container.innerHTML = html || '<div class="empty">没有找到匹配工具，换个关键词试试。</div>';
    container.querySelectorAll('[data-sub-cat]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        setSubcategory(btn.dataset.subCat, btn.dataset.sub);
      });
    });
    bindSectionPager(container);
    decorateCards(container);
  }

  function setCategory(id) {
    state.category = id;
    state.page = 1;
    state.query = '';
    state.freeOnly = false;
    if ($('searchInput')) $('searchInput').value = '';
    renderTools();
    var target = document.getElementById('section-' + id) || $('directory');
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function setSubcategory(catId, sub) {
    state.category = catId;
    state.page = 1;
    state.query = '';
    state.freeOnly = false;
    setActiveSub(catId, sub);
    setSectionPage(catId, sub, 1);
    if ($('searchInput')) $('searchInput').value = '';
    renderTools();
    var target = document.getElementById('section-' + catId) || $('directory');
    if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function bindGlobalInteractions() {
    var progressBar = $('progressBar');
    if (progressBar) {
      window.addEventListener('scroll', function () {
        var root = document.documentElement;
        var denominator = root.scrollHeight - root.clientHeight;
        progressBar.style.width = (denominator ? root.scrollTop / denominator * 100 : 0) + '%';
      }, { passive: true });
    }

    if ('IntersectionObserver' in window) {
      var revealIo = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('in');
            revealIo.unobserve(entry.target);
          }
        });
      }, { threshold: 0.12, rootMargin: '0px 0px -80px 0px' });
      document.querySelectorAll('.reveal').forEach(function (element) {
        revealIo.observe(element);
      });
    } else {
      document.querySelectorAll('.reveal').forEach(function (element) {
        element.classList.add('in');
      });
    }

    document.querySelectorAll('[data-scroll]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var target = $(btn.dataset.scroll);
        if (target) target.scrollIntoView({ behavior: 'smooth' });
      });
    });

    document.querySelectorAll('a[href^="#"]').forEach(function (link) {
      link.addEventListener('click', function (event) {
        var id = link.getAttribute('href').slice(1);
        var target = id ? $(id) : null;
        if (!target) return;
        event.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });

    var freeBtn = document.querySelector('[data-hot="free"]');
    if (freeBtn) {
      freeBtn.addEventListener('click', function () {
        state.freeOnly = !state.freeOnly;
        state.page = 1;
        renderTools();
        if ($('directory')) $('directory').scrollIntoView({ behavior: 'smooth' });
      });
    }

    document.querySelectorAll('[data-query]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        state.query = btn.dataset.query;
        if ($('searchInput')) $('searchInput').value = state.query;
        state.page = 1;
        renderTools();
        if ($('directory')) $('directory').scrollIntoView({ behavior: 'smooth' });
      });
    });

    var searchForm = $('searchForm');
    if (searchForm) {
      searchForm.addEventListener('submit', function (event) {
        event.preventDefault();
        state.query = $('searchInput') ? $('searchInput').value.trim() : '';
        state.page = 1;
        renderTools();
        if ($('directory')) $('directory').scrollIntoView({ behavior: 'smooth' });
      });
    }

    var railToggle = $('railToggle');
    if (railToggle) {
      railToggle.addEventListener('click', function () {
        var shell = document.querySelector('.page-shell');
        if (shell) shell.classList.toggle('rail-collapsed');
      });
    }

    var backTop = $('backTop');
    if (backTop) {
      backTop.addEventListener('click', function () {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    }
  }

  renderLatest();
  renderTools();
  hydrateWorkflowIcons();
  bindGlobalInteractions();
})();
