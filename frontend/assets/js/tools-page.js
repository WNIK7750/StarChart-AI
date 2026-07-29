import { apiGet } from "./api.js";
import { safeHttpHref } from "./url-safety.js";
import { feedbackKindForError, feedbackMarkup, renderFeedback } from "./ui-feedback.js";

// Tool page runtime: render catalog data without owning tool facts.
export function initToolsPage() {
  var toolSource = { categories: [], tools: [], placements: [] };
  var pageLists = { latestTools: [] };
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
        aliases: tool.aliases || [],
        linkStatus: tool.linkStatus || 'unchecked'
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
          mark: tool.mark || 'AI',
          isFree: Boolean(tool.isFree),
          linkStatus: tool.linkStatus || 'unchecked'
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

  var categories = [];

  function latestTools() {
    return (pageLists.latestTools || []).map(function (item) {
      var tool = (toolSource.tools || []).find(function (candidate) {
        return candidate.name === item.toolName || candidate.name === item.displayName;
      });
      return {
        displayName: item.displayName,
        provider: item.provider || (tool && tool.categoryName) || '',
        label: item.label || (tool && tool.tag) || '',
        mark: item.mark || (tool && tool.mark) || 'AI',
        logoClass: item.logoClass || (tool && tool.logoClass) || 'logo-chat',
        toolName: item.toolName || item.displayName,
        linkStatus: (tool && tool.linkStatus) || 'unchecked'
      };
    });
  }

  function metaFor(name) {
    return toolMeta[name] || toolMeta[normalizeToolName(name)] || {};
  }

  function toolUrl(name) {
    var meta = metaFor(name);
    if (meta.linkStatus === 'unavailable') return '';
    return safeHttpHref(meta.url, '');
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
      var href = item.linkStatus === 'unavailable' ? '' : toolUrl(refName);
      return '<a class="latest-card' + (!href ? ' is-unavailable' : '') + '" href="' + escapeAttr(href || '#') + '" ' + (!href ? 'aria-disabled="true"' : 'target="_blank" rel="noopener noreferrer"') + '>' +
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
    var href = toolUrl(tool.name);
    var unavailable = !href;
    return '<a href="' + escapeAttr(href || '#') + '" ' + (unavailable ? 'aria-disabled="true"' : 'target="_blank" rel="noopener noreferrer"') + ' class="tool-card' + (unavailable ? ' is-unavailable' : '') + '" data-tool="' + escapeAttr(tool.name) + '">' +
      '<div class="tool-main">' + logoHtml(tool.name, tool.mark, tool.category.logo) +
      '<div class="tool-info"><strong>' + escapeText(tool.name) + '</strong><p>' + escapeText(tool.desc) + '</p>' + (unavailable ? '<span class="link-maintenance">链接维护中</span>' : '') + '</div></div>' +
      '<div class="tool-meta"><span class="tag">' + escapeText(tool.sub) + '</span><span class="tool-arrow">›</span></div></a>';
  }

  function scheduleCardPointerFrame(card, event) {
    card._pendingPointerX = event.clientX;
    card._pendingPointerY = event.clientY;
    if (card._pointerFrame) return;
    card._pointerFrame = requestAnimationFrame(function () {
      card._pointerFrame = 0;
      var rect = card.getBoundingClientRect();
      card.style.setProperty('--mx', ((card._pendingPointerX - rect.left) / rect.width * 100) + '%');
      card.style.setProperty('--my', ((card._pendingPointerY - rect.top) / rect.height * 100) + '%');
    });
  }

  function decorateCards(scope) {
    bindBrandIconFallbacks(scope || document);
    (scope || document).querySelectorAll('.tool-card').forEach(function (card) {
      if (card.dataset.boundHover === '1') return;
      card.dataset.boundHover = '1';
      card.addEventListener('mousemove', function (event) {
        scheduleCardPointerFrame(card, event);
      }, { passive: true });
    });
  }

  function toolMatchesFreeFlag(tool) {
    return tool.isFree || /免费|开源|\bfree\b|\bopen(?:\s*source)?\b/i.test(tool.tag);
  }

  function syncFreeControls() {
    document.querySelectorAll('[data-hot="free"]').forEach(function (btn) {
      btn.classList.toggle('active', state.freeOnly);
      btn.setAttribute('aria-pressed', state.freeOnly ? 'true' : 'false');
    });
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
    if (grid) {
      grid.classList.toggle('is-paged', totalPages > 1);
      grid.innerHTML = pageTools.map(toolCard).join('');
    }
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
        '<div class="section-subnav">' + tabs + '</div><div class="category-tools' + (totalPages > 1 ? ' is-paged' : '') + '">' + pageTools.map(toolCard).join('') + '</div>' + pager + '</section>';
    }).join('');

    container.innerHTML = html || feedbackMarkup({
      title: '没有找到匹配工具',
      message: '可以换一个关键词，或清除免费和分类筛选。',
    });
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

  var toolsScrollFrame = 0;

  function scheduleToolsScrollFrame(progressBar, floatingTools) {
    if (toolsScrollFrame) return;
    toolsScrollFrame = requestAnimationFrame(function () {
      toolsScrollFrame = 0;
      var root = document.documentElement;
      var denominator = root.scrollHeight - root.clientHeight;
      progressBar.style.width = (denominator ? root.scrollTop / denominator * 100 : 0) + '%';
      if (floatingTools) floatingTools.classList.toggle('is-visible', root.scrollTop > 400);
    });
  }

  function bindGlobalInteractions() {
    var progressBar = $('progressBar');
    var floatingTools = document.querySelector('.float-tools');
    if (progressBar) {
      window.addEventListener('scroll', function () {
        scheduleToolsScrollFrame(progressBar, floatingTools);
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

    document.querySelectorAll('[data-hot="free"]').forEach(function (freeBtn) {
      if (freeBtn.dataset.boundFreeFilter === '1') return;
      freeBtn.dataset.boundFreeFilter = '1';
      freeBtn.addEventListener('click', function () {
        state.freeOnly = !state.freeOnly;
        state.page = 1;
        syncFreeControls();
        renderTools();
        if ($('directory')) $('directory').scrollIntoView({ behavior: 'smooth' });
      });
    });
    syncFreeControls();

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

  function start(source) {
    toolSource = source;
    pageLists = { latestTools: source.latestTools || [] };
    categories = buildCategories();
    var initialQuery = new URLSearchParams(window.location.search).get('q');
    if (initialQuery) {
      state.query = initialQuery.trim();
      if ($('searchInput')) $('searchInput').value = state.query;
    }
    renderLatest();
    renderTools();
    hydrateWorkflowIcons();
    bindGlobalInteractions();
    if (state.query && $('directory')) {
      requestAnimationFrame(function () {
        $('directory').scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    }
  }

  function showCatalogError(error) {
    var grid = $('toolsSections');
    var latest = $('latestTrack');
    if (latest) latest.innerHTML = '';
    if (grid) {
      renderFeedback(grid, {
        kind: feedbackKindForError(error),
        title: error && error.code === 'API_OFFLINE' ? '当前处于离线状态' : '工具目录暂时无法加载',
        message: '请检查网络后重试。',
        actionLabel: '重新加载',
        actionKey: 'retry-catalog',
        onAction: function () { location.reload(); }
      });
      var directorySection = grid.closest('.reveal');
      if (directorySection) directorySection.classList.add('in');
    }
    bindGlobalInteractions();
  }

  apiGet('/tools/catalog')
    .then(start)
    .catch(showCatalogError);
}
