// =============================================
// AI 知识导航 - app.js（重构版）
// =============================================

// ---------- 数据 ----------
const MODELS = [
  { name: 'GPT-4o',       color: '#378ADD', mmlu: 88.7, gpqa: 53.6, math: 76.6, humaneval: 90.2, gsm8k: 92.9, swe: 33.2 },
  { name: 'Claude 3.7',   color: '#D85A30', mmlu: 90.0, gpqa: 70.0, math: 96.2, humaneval: 93.7, gsm8k: 96.9, swe: 62.3 },
  { name: 'Gemini 2.0 Pro', color: '#1D9E75', mmlu: 89.5, gpqa: 65.2, math: 91.8, humaneval: 90.0, gsm8k: 97.0, swe: 35.0 },
  { name: 'DeepSeek-R1',  color: '#7F77DD', mmlu: 90.8, gpqa: 71.5, math: 97.3, humaneval: 92.3, gsm8k: 97.3, swe: 49.2 },
  { name: 'DeepSeek-V3',  color: '#BA7517', mmlu: 88.5, gpqa: 59.1, math: 90.2, humaneval: 91.6, gsm8k: 96.8, swe: 42.0 },
  { name: 'Qwen2.5-Max',  color: '#D4537E', mmlu: 89.5, gpqa: 60.0, math: 93.0, humaneval: 92.0, gsm8k: 97.0, swe: 40.0 },
  { name: 'Kimi k1.5',    color: '#888780', mmlu: 87.5, gpqa: 55.0, math: 96.2, humaneval: 88.0, gsm8k: 96.2, swe: 30.0 },
];

const METRICS = {
  overall:   { label:'综合评分',  fields:['mmlu','gpqa','math','humaneval'],                labels:['MMLU','GPQA Diamond','MATH-500','HumanEval'] },
  reasoning: { label:'推理能力',  fields:['mmlu','gpqa','math','gsm8k'],                     labels:['MMLU','GPQA Diamond','MATH-500','GSM8K'] },
  coding:    { label:'代码能力',  fields:['humaneval','swe','gpqa'],                           labels:['HumanEval','SWE-bench','GPQA Diamond'] },
  math:      { label:'数学能力',  fields:['math','gsm8k','gpqa'],                             labels:['MATH-500','GSM8K','GPQA Diamond'] },
};

// ---------- 状态 ----------
let activeMetric  = 'overall';
let activeModels = [true,true,true,true,true,true,true];
let barChartInst  = null;
let radarChartInst = null;
let videoOpen     = false;
let videoPiP      = false;

// =============================================
// 视频交互 - 向上滚动展开 / 离开视口->PiP / 双击展开
// =============================================
function initVideoScroll() {
  const videoSection = document.getElementById('videoSection');
  const videoContainer = document.getElementById('videoContainer');
  const pipVideo = document.getElementById('pipVideo');
  if (!videoSection || !videoContainer || !pipVideo) return;

  let upScrollAccum = 0;
  const UP_SCROLL_THRESHOLD = 80;
  window.addEventListener('wheel', (e) => {
    if (window.scrollY === 0 && e.deltaY < 0) {
      upScrollAccum += Math.abs(e.deltaY);
      if (upScrollAccum > UP_SCROLL_THRESHOLD && !videoOpen) {
        openVideo();
        upScrollAccum = 0;
      }
    } else {
      upScrollAccum = Math.max(0, upScrollAccum - 2);
    }
  }, { passive: true });

  const pipObserver = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (!videoOpen) return;
      if (!e.isIntersecting) { enterPiP(); }
      else { exitPiP(); }
    });
  }, { threshold: 0.15 });
  pipObserver.observe(videoSection);

  const toggleBtn = document.getElementById('videoToggleBtn');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      if (videoOpen) closeVideo();
      else openVideo();
    });
  }

  const pipClose  = document.getElementById('pipClose');
  const pipExpand = document.getElementById('pipExpand');
  if (pipClose)  pipClose.addEventListener('click', () => closeVideo());
  if (pipExpand) pipExpand.addEventListener('click', () => {
    exitPiP();
    videoSection.scrollIntoView({ behavior:'smooth', block:'center' });
    openVideo();
  });

  videoSection.addEventListener('dblclick', () => {
    if (!videoOpen) openVideo();
  });
}

function openVideo() {
  const videoContainer = document.getElementById('videoContainer');
  const toggleBtn = document.getElementById('videoToggleBtn');
  if (!videoContainer) return;
  videoContainer.classList.remove('collapsed');
  videoOpen = true;
  if (toggleBtn) {
    const icon = toggleBtn.querySelector('.toggle-icon');
    if (icon) icon.style.transform = 'rotate(180deg)';
    toggleBtn.title = i18nT('videoCollapseTip') || '收起视频';
  }
}

function closeVideo() {
  const videoContainer = document.getElementById('videoContainer');
  const toggleBtn = document.getElementById('videoToggleBtn');
  if (!videoContainer) return;
  videoContainer.classList.add('collapsed');
  videoOpen = false;
  exitPiP();
  if (toggleBtn) {
    const icon = toggleBtn.querySelector('.toggle-icon');
    if (icon) icon.style.transform = 'rotate(0deg)';
    toggleBtn.title = i18nT('videoExpandTip') || '展开视频';
  }
}

function enterPiP() {
  const pipVideo = document.getElementById('pipVideo');
  if (!pipVideo || videoPiP) return;
  pipVideo.classList.add('show');
  videoPiP = true;
}

function exitPiP() {
  const pipVideo = document.getElementById('pipVideo');
  if (!pipVideo) return;
  pipVideo.classList.remove('show');
  videoPiP = false;
}

function i18nT(key) {
  const lang = window.i18nLang || 'zh';
  const dict = (window.I18N && window.I18N[lang]) ? window.I18N[lang] : null;
  return dict && dict[key] !== undefined ? dict[key] : null;
}

// =============================================
// 热门搜索词 - 点击填入搜索框
// =============================================
function initHotSearches() {
  const track = document.getElementById('hotScrollTrack');
  if (!track) return;

  track.addEventListener('click', (e) => {
    const term = e.target.closest('.hot-term');
    if (!term) return;
    const q = term.textContent.trim();
    const input = document.getElementById('searchInput');
    if (input) { input.value = q; input.focus(); input.dispatchEvent(new Event('input')); }
    const heroInput = document.getElementById('heroSearchInput');
    if (heroInput) { heroInput.value = q; heroInput.focus(); heroInput.dispatchEvent(new Event('input')); }
  });

  const terms = track.querySelectorAll('.hot-term');
  terms.forEach(term => { track.appendChild(term.cloneNode(true)); });
}

// =============================================
// 主题切换
// =============================================
function initThemeToggle() {
  var switcher = document.getElementById('themeSwitcher');
  if (!switcher) return;

  var themes = ['light', 'geek', 'dark'];

  // 读取已迁移的主题（v2 迁移已在 DOMContentLoaded 中完成）
  var saved = localStorage.getItem('preferred-theme');
  if (!saved || themes.indexOf(saved) === -1) saved = 'geek';
  setTheme(saved);

  // 点击分段切换
  switcher.querySelectorAll('.theme-switcher__segment').forEach(function(seg) {
    seg.addEventListener('click', function(e) {
      e.stopPropagation();
      var theme = this.getAttribute('data-theme-value');
      setTheme(theme);
    });
  });

  // 拖动切换（pointer events）
  var isDragging = false;
  var startX = 0;
  var switcherRect = null;

  switcher.addEventListener('pointerdown', function(e) {
    if (e.target.closest('.theme-switcher__segment')) return; // 分段点击已处理
    isDragging = true;
    startX = e.clientX;
    switcherRect = switcher.getBoundingClientRect();
    switcher.setPointerCapture(e.pointerId);
  });

  switcher.addEventListener('pointermove', function(e) {
    if (!isDragging || !switcherRect) return;
    var relX = e.clientX - switcherRect.left;
    var segW = switcherRect.width / 3;
    var segIdx = Math.min(2, Math.max(0, Math.floor(relX / segW)));
    var theme = themes[segIdx];
    setTheme(theme);
  });

  switcher.addEventListener('pointerup', function() { isDragging = false; switcherRect = null; });
  switcher.addEventListener('pointercancel', function() { isDragging = false; switcherRect = null; });

  // 键盘切换支持
  switcher.setAttribute('tabindex', '0');
  switcher.setAttribute('role', 'radiogroup');
  switcher.setAttribute('aria-label', '主题切换');
  switcher.querySelectorAll('.theme-switcher__segment').forEach(function(seg, i) {
    seg.setAttribute('role', 'radio');
    seg.setAttribute('aria-checked', String(i === themes.indexOf(saved)));
    seg.setAttribute('tabindex', '-1');
  });

  switcher.addEventListener('keydown', function(e) {
    var idx = themes.indexOf(switcher.dataset.active);
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault();
      idx = (idx + 1) % 3;
      setTheme(themes[idx]);
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      idx = (idx + 2) % 3;
      setTheme(themes[idx]);
    }
  });

  function setTheme(theme) {
    var idx = themes.indexOf(theme);
    if (idx === -1) idx = 1;
    switcher.dataset.active = String(idx);
    document.documentElement.setAttribute('data-theme', theme);
    document.body.setAttribute('data-theme', theme);
    localStorage.setItem('preferred-theme', theme);
    // 同步 CSS 变量（applyCustomTokens 会从 localStorage 读取首选主题）
    if (typeof applyCustomTokens === 'function') applyCustomTokens();
    // 同步分段 aria-checked
    switcher.querySelectorAll('.theme-switcher__segment').forEach(function(seg, i) {
      seg.setAttribute('aria-checked', String(i === idx));
    });
    // 同步设计面板中的主题按钮高亮（如果存在）
    document.querySelectorAll('.theme-btn').forEach(function(b) {
      b.classList.toggle('active', b.dataset.theme === theme);
    });
  }
}

// =============================================
// Hero 搜索框
// =============================================
function initHeroSearch() {
  const input    = document.getElementById('heroSearchInput');
  const dropdown = document.getElementById('heroSearchDropdown');
  const clearBtn = document.getElementById('heroSearchClear');
  if (!input || !dropdown) return;
  let debounceTimer = null;

  input.addEventListener('input', function() {
    clearTimeout(debounceTimer);
    const q = this.value.trim();
    if (clearBtn) clearBtn.style.display = q ? '' : 'none';
    if (q.length < 1) { closeHeroDropdown(); return; }
    debounceTimer = setTimeout(() => {
      const results = searchAll(q);
      renderSearchResults(results, q, dropdown);
      openHeroDropdown();
    }, 200);
  });

  input.addEventListener('focus', function() {
    const q = this.value.trim();
    if (q.length >= 1) {
      const results = searchAll(q);
      renderSearchResults(results, q, dropdown);
      openHeroDropdown();
    }
  });

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      input.value = ''; clearBtn.style.display = 'none';
      closeHeroDropdown(); input.focus();
    });
  }

  document.addEventListener('click', (e) => {
    const wrap = input.closest('.hero-search-wrap');
    if (wrap && !wrap.contains(e.target)) closeHeroDropdown();
  });

  input.addEventListener('keydown', (e) => {
    const items = dropdown.querySelectorAll('.sri');
    const active = dropdown.querySelector('.sri.active');
    let idx = Array.from(items).indexOf(active);
    if (e.key === 'ArrowDown') {
      e.preventDefault(); idx = (idx + 1) % items.length;
      items.forEach(el => el.classList.remove('active'));
      if (items[idx]) items[idx].classList.add('active');
    } else if (e.key === 'ArrowUp') {
      e.preventDefault(); idx = idx <= 0 ? items.length - 1 : idx - 1;
      items.forEach(el => el.classList.remove('active'));
      if (items[idx]) items[idx].classList.add('active');
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (active) active.click(); else if (items.length > 0) items[0].click();
    } else if (e.key === 'Escape') { closeHeroDropdown(); }
  });

  function openHeroDropdown() { dropdown.style.display = 'block'; }
  function closeHeroDropdown() {
    dropdown.style.display = 'none';
    dropdown.querySelectorAll('.sri').forEach(el => el.classList.remove('active'));
  }
}

// =============================================
// 全局搜索系统（Header 搜索框）
// =============================================
function initSearch() {
  const input    = document.getElementById('searchInput');
  const dropdown = document.getElementById('searchDropdown');
  const overlay  = document.getElementById('searchOverlay');
  const clearBtn = document.getElementById('searchClear');
  const searchWrap = document.getElementById('searchWrap');
  if (!input || !dropdown) return;
  let debounceTimer = null;

  input.addEventListener('input', function() {
    clearTimeout(debounceTimer);
    const q = this.value.trim();
    if (clearBtn) clearBtn.style.display = q ? '' : 'none';
    if (q.length < 1) { closeDropdown(); return; }
    debounceTimer = setTimeout(() => {
      const results = searchAll(q);
      renderSearchResults(results, q, dropdown);
      openDropdown();
    }, 200);
  });

  input.addEventListener('focus', function() {
    const q = this.value.trim();
    if (q.length >= 1) {
      const results = searchAll(q);
      renderSearchResults(results, q, dropdown);
      openDropdown();
    }
  });

  if (clearBtn) {
    clearBtn.addEventListener('click', function() {
      input.value = ''; this.style.display = 'none';
      closeDropdown(); input.focus();
    });
  }

  if (overlay) overlay.addEventListener('click', closeDropdown);

  input.addEventListener('keydown', function(e) {
    const items = dropdown.querySelectorAll('.sri');
    const active = dropdown.querySelector('.sri.active');
    let idx = Array.from(items).indexOf(active);
    if (e.key === 'ArrowDown') {
      e.preventDefault(); idx = (idx + 1) % items.length;
      items.forEach(el => el.classList.remove('active'));
      if (items[idx]) items[idx].classList.add('active');
    } else if (e.key === 'ArrowUp') {
      e.preventDefault(); idx = idx <= 0 ? items.length - 1 : idx - 1;
      items.forEach(el => el.classList.remove('active'));
      if (items[idx]) items[idx].classList.add('active');
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (active) active.click(); else if (items.length > 0) items[0].click();
    } else if (e.key === 'Escape') { closeDropdown(); }
  });

  document.addEventListener('click', (e) => {
    if (searchWrap && !searchWrap.contains(e.target)) closeDropdown();
  });

  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault(); input.focus(); input.select();
    }
  });

  function openDropdown() {
    dropdown.style.display = 'block';
    if (overlay) overlay.classList.add('show');
  }
  function closeDropdown() {
    dropdown.style.display = 'none';
    if (overlay) overlay.classList.remove('show');
    dropdown.querySelectorAll('.sri').forEach(el => el.classList.remove('active'));
  }
}

// =============================================
// 渲染搜索结果
// =============================================
function renderSearchResults(results, query, dropdown) {
  if (!dropdown) return;
  if (results.length === 0) {
    dropdown.innerHTML = '<div class="sr-empty">未找到与<strong>' + escapeHtml(query) + '</strong>相关的结果</div>';
    return;
  }

  let html = '';
  results.forEach((result, index) => {
    if (result.type === 'tool') {
      const tool = result.data;
      html += '<div class="sri" data-action="navigate" data-url="' + escapeHtml(tool.url) + '" data-index="' + index + '">';
      html +=   '<img class="sri-logo" src="' + getFaviconUrl(tool.domain, 48) + '" alt="' + escapeHtml(tool.name) + '" loading="lazy">';
      html +=   '<div class="sri-content">';
      html +=     '<div class="sri-title">' + escapeHtml(tool.name) + '<span class="sri-badge sri-badge-tool">工具</span></div>';
      html +=     '<div class="sri-sub">' + escapeHtml(tool.catName) + ' - ' + escapeHtml(tool.maker) + '</div>';
      html +=   '</div>';
      html +=   '<span class="sri-arrow">></span>';
      html += '</div>';
    } else if (result.type === 'learn') {
      const entry = result.data;
      html += '<div class="sri" data-action="navigate" data-url="' + escapeHtml(entry.url) + '" data-index="' + index + '">';
      html +=   '<div class="sri-icon sri-icon-learn">📖</div>';
      html +=   '<div class="sri-content">';
      html +=     '<div class="sri-title">' + escapeHtml(entry.name) + '<span class="sri-badge sri-badge-learn">学习</span></div>';
      html +=     '<div class="sri-sub">' + escapeHtml(entry.block) + ' - ' + escapeHtml(entry.desc.substring(0,30)) + '</div>';
      html +=   '</div>';
      html +=   '<span class="sri-arrow">></span>';
      html += '</div>';
    } else if (result.type === 'model') {
      const entry = result.data;
      html += '<div class="sri" data-action="scroll" data-target="section-compare" data-index="' + index + '">';
      html +=   '<img class="sri-logo" src="' + getFaviconUrl(entry.domain, 48) + '" alt="' + escapeHtml(entry.name) + '" loading="lazy">';
      html +=   '<div class="sri-content">';
      html +=     '<div class="sri-title">' + escapeHtml(entry.name) + '<span class="sri-badge sri-badge-model">模型</span></div>';
      html +=     '<div class="sri-sub">' + escapeHtml(entry.maker) + ' - 点击跳转到模型对比区</div>';
      html +=   '</div>';
      html +=   '<span class="sri-arrow">></span>';
      html += '</div>';
    }
  });

  dropdown.innerHTML = html;

  dropdown.querySelectorAll('.sri').forEach(item => {
    item.addEventListener('click', function() {
      const action = this.dataset.action;
      if (action === 'navigate') {
        const url = this.dataset.url;
        if (url && url.startsWith('http')) {
          window.open(url, '_blank', 'noopener,noreferrer');
        } else if (url) {
          window.location.href = url;
        }
      } else if (action === 'scroll') {
        const target = document.getElementById(this.dataset.target);
        if (target) target.scrollIntoView({ behavior:'smooth', block:'start' });
      }
      const dd1 = document.getElementById('searchDropdown');
      const dd2 = document.getElementById('heroSearchDropdown');
      if (dd1) dd1.style.display = 'none';
      if (dd2) dd2.style.display = 'none';
      const ov = document.getElementById('searchOverlay');
      if (ov) ov.classList.remove('show');
    });
  });
}

// =============================================
// 图表相关
// =============================================
function getActiveModels() { return MODELS.filter((_, i) => activeModels[i]); }

function buildBarData() {
  const m = METRICS[activeMetric];
  const models = getActiveModels();
  const datasets = m.fields.map((field, fi) => ({
    label: m.labels[fi],
    data: models.map(mod => mod[field]),
    backgroundColor: models.map(mod => mod.color + 'b0'),
    borderColor: models.map(mod => mod.color),
    borderWidth: 1,
    borderRadius: 4,
  }));
  return { labels: models.map(m => m.name), datasets };
}

function buildRadarData() {
  const m = METRICS[activeMetric];
  const models = getActiveModels();
  return {
    labels: m.labels,
    datasets: models.map(mod => ({
      label: mod.name,
      data: m.fields.map(f => mod[f]),
      borderColor: mod.color,
      backgroundColor: mod.color + '22',
      borderWidth: 1.5,
      pointBackgroundColor: mod.color,
      pointRadius: 3,
    })),
  };
}

const chartDefaults = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
};

function initCharts() {
  const barCtx = document.getElementById('barChart');
  const radarCtx = document.getElementById('radarChart');
  if (!barCtx || !radarCtx) return;

  barChartInst = new Chart(barCtx, {
    type: 'bar',
    data: buildBarData(),
    options: {
      ...chartDefaults,
      scales: {
        x: { ticks:{ font:{size:11}, color:'#888', autoSkip:false, maxRotation:30 }, grid:{ color:'rgba(0,0,0,0.05)' } },
        y: { min:0, max:100, ticks:{ font:{size:10}, color:'#888', callback:v=>v+'%' }, grid:{ color:'rgba(0,0,0,0.06)' } },
      },
      plugins: { tooltip:{ callbacks:{ label:ctx=>' ' + ctx.dataset.label + ': ' + ctx.parsed.y.toFixed(1) + '%' } } },
    },
  });

  radarChartInst = new Chart(radarCtx, {
    type: 'radar',
    data: buildRadarData(),
    options: {
      ...chartDefaults,
      scales: {
        r: {
          min:40, max:100,
          ticks:{ stepSize:20, font:{size:9}, color:'#aaa', backdropColor:'transparent', callback:v=>v+'%' },
          pointLabels:{ font:{size:10}, color:'#666' },
          grid:{ color:'rgba(0,0,0,0.07)' },
          angleLines:{ color:'rgba(0,0,0,0.08)' },
        },
      },
      plugins: { tooltip:{ callbacks:{ label:ctx=>' ' + ctx.dataset.label + ': ' + ctx.parsed.r.toFixed(1) + '%' } } },
    },
  });
}

function refreshCharts() {
  if (!barChartInst || !radarChartInst) return;
  barChartInst.data = buildBarData(); barChartInst.update();
  radarChartInst.data = buildRadarData(); radarChartInst.update();
}

function initControls() {
  document.querySelectorAll('.metric-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.metric-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeMetric = btn.dataset.metric;
      refreshCharts();
    });
  });
  document.querySelectorAll('#modelToggles input').forEach(cb => {
    cb.addEventListener('change', () => {
      const idx = parseInt(cb.value);
      activeModels[idx] = cb.checked;
      if (activeModels.filter(Boolean).length === 0) { cb.checked = true; activeModels[idx] = true; }
      refreshCharts();
    });
  });
}

// =============================================
// 工具卡片渲染
// =============================================
function renderToolCards() {
  const grid = document.getElementById('toolGrid');
  if (!grid || typeof TOOLS === 'undefined') return;

  function tagClass(t) {
    if (t === '免费') return 'ttag-blue';
    if (t === '付费') return 'ttag-orange';
    if (t === '开源' || t === '免费版') return 'ttag-green';
    return '';
  }

  let html = '';
  TOOLS.forEach(tool => {
    const tagsHtml = tool.tags.map(t =>
      '<span class="ttag' + (tagClass(t) ? ' '+tagClass(t) : '') + '">' + t + '</span>'
    ).join('');
    html += '<div class="tool-card" data-cat="' + tool.cat + '" data-id="' + tool.id + '">'
      +   '<img class="tool-logo" src="' + getFaviconUrl(tool.domain) + '" alt="' + tool.name + '" loading="lazy">'
      +   '<span class="tool-logo-fallback" style="display:none">' + tool.name.charAt(0) + '</span>'
      +   '<div class="tool-info">'
      +     '<div class="tool-name">' + tool.name + '</div>'
      +     '<div class="tool-maker">' + tool.maker + '</div>'
      +     '<div class="tool-desc">' + tool.desc + '</div>'
      +   '</div>'
      +   '<div class="tool-tags">' + tagsHtml + '</div>'
      +   '<a href="' + tool.url + '" target="_self" class="tool-goto">访问 ></a>'
      + '</div>';
  });
  grid.innerHTML = html;

  // 为每个工具卡片图片绑定 onerror 处理
  grid.querySelectorAll('.tool-logo').forEach(img => {
    img.addEventListener('error', function() {
      this.style.display = 'none';
      var fb = this.nextElementSibling;
      if (fb && fb.classList.contains('tool-logo-fallback')) {
        fb.style.display = 'flex';
      }
    });
  });
}

// =============================================
// 工具分类筛选
// =============================================
function initFilterTools() {
  const btns  = document.querySelectorAll('.filter-btn');
  const cards = () => document.querySelectorAll('.tool-card');
  btns.forEach(btn => {
    btn.addEventListener('click', () => {
      btns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const cat = btn.dataset.cat;
      cards().forEach(card => {
        card.classList.toggle('hidden', cat !== 'all' && card.dataset.cat !== cat);
      });
    });
  });
}

// =============================================
// 学习区折叠
// =============================================
function toggleBlock(header) {
  const block = header.closest('.learn-block');
  block.classList.toggle('collapsed');
}

function initLearnBlocks() {
  document.querySelectorAll('.learn-block').forEach(block => {
    block.classList.remove('collapsed');
  });
  document.querySelectorAll('.topic-card').forEach(card => {
    card.style.cursor = 'pointer';
    card.addEventListener('click', function(e) {
      const link = this.querySelector('.topic-link');
      if (link && !e.target.closest('.topic-link')) {
        window.location.href = link.href;
      }
    });
  });
}

// =============================================
// 外部链接修复
// =============================================
function fixExternalLinks() {
  document.querySelectorAll('a[href^="http"]').forEach(link => {
    link.setAttribute('target', '_blank');
    link.setAttribute('rel', 'noopener noreferrer');
  });
}

// =============================================
// 工具函数
// =============================================
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// 如果 search-data.js 未提供这些函数，给空实现避免报错
if (typeof getFaviconUrl !== 'function') {
  window.getFaviconUrl = function(domain) { return ''; };
}
if (typeof getToolById !== 'function') {
  window.getToolById = function(id) { return TOOLS && TOOLS.find(t=>t.id===id); };
}
if (typeof searchAll !== 'function') {
  window.searchAll = function(q) { return []; };
}

// =============================================
// 开屏动画 (Splash Screen)
// 三重保护：try-catch + 节点校验 + 5秒强制fallback
// =============================================
// =============================================
// 开屏动画 (Splash Screen)
// 三重保护：try-catch + 节点校验 + 5秒强制fallback
// =============================================
function initSplash() {
  var splash = document.getElementById('splash');
  if (!splash) return;

  // 5秒安全fallback：任何异常情况下强制移除遮罩
  var fallbackTimer = setTimeout(function () {
    if (splash.parentNode) {
      splash.style.opacity = '0';
      splash.style.pointerEvents = 'none';
      document.body.style.overflow = '';
      setTimeout(function () { if (splash.parentNode) splash.remove(); }, 300);
    }
  }, 5000);

  // 非首次访问：直接移除遮罩
  try {
    if (sessionStorage.getItem('splash-done') === '1') {
      clearTimeout(fallbackTimer);
      splash.remove();
      return;
    }
  } catch (e) {
    clearTimeout(fallbackTimer);
    splash.remove();
    return;
  }

  var splashText = document.getElementById('splashText');
  var heroTitle  = document.querySelector('.hero-title');

  document.body.style.overflow = 'hidden';

  // 第一阶段：逐字动画（CSS 完成），等待其结束
  var phase1End = 1900;

  setTimeout(function () {
    try {
      if (!heroTitle || !splashText) { fadeOut(); return; }

      var splashRect = splashText.getBoundingClientRect();
      var targetRect = heroTitle.getBoundingClientRect();
      if (splashRect.height === 0 || targetRect.height === 0) { fadeOut(); return; }

      // 用字号比算 scale（比 height 比更精确，不受 line-height 影响）
      var currentFS = parseInt(getComputedStyle(splashText).fontSize, 10);
      var targetFS   = parseInt(getComputedStyle(heroTitle).fontSize, 10);
      var scale = targetFS / currentFS;

      var dx = (targetRect.left + targetRect.width / 2) - (splashRect.left + splashRect.width / 2);
      var dy = (targetRect.top  + targetRect.height / 2) - (splashRect.top  + splashRect.height / 2);

      // 主题强调色（hero 标题渐变终点色）
      var theme = document.documentElement.getAttribute('data-theme') || 'geek';
      var accentMap = {
        'light': '#185FA5',
        'geek':  '#32f08c',
        'dark':  '#60A5FA'
      };
      var targetColor = accentMap[theme] || accentMap['geek'];

      /*
       * 动画方案：
       * ① 先设 transition（必须在 transform 之前，否则不会触发动画）
       * ② 用 requestAnimationFrame 确保 transition 已生效
       * ③ 再设 transform + color → 触发飞行动画
       */
      splashText.style.transition =
        'transform 0.7s cubic-bezier(0.25,0.46,0.45,0.94), ' +
        'color 0.9s cubic-bezier(0.4,0,0.2,1)';

      requestAnimationFrame(function () {
        splashText.style.transform =
          'translate(' + dx + 'px,' + dy + 'px) scale(' + scale.toFixed(3) + ')';
        splashText.style.color = targetColor;
      });

      setTimeout(fadeOut, 950);
    } catch (e) {
      fadeOut();
    }
  }, phase1End);

  function fadeOut() {
    clearTimeout(fallbackTimer);
    splash.style.opacity = '0';
    splash.style.pointerEvents = 'none';
    document.body.style.overflow = '';
    try { sessionStorage.setItem('splash-done', '1'); } catch (e) {}
    setTimeout(function () {
      if (splash.parentNode) splash.remove();
    }, 550);
  }
}
// =============================================
// 初始化入口
// =============================================
document.addEventListener('DOMContentLoaded', () => {
  // 0a. v3 主题迁移：默认浅色（必须在 applyCustomTokens 之前执行）
  try {
    if (localStorage.getItem('theme-chosen-v3') !== '1') {
      localStorage.setItem('preferred-theme', 'light');
      localStorage.setItem('theme-chosen-v3', '1');
    }
  } catch (e) {}

  // 0b. 开屏动画（必须在其他初始化之前）
  initSplash();

  // 1. 应用自定义令牌（如果在 tokens.js 中）——此时已迁移到 geek
  if (typeof applyCustomTokens === 'function') applyCustomTokens();

  // 2. 渲染工具卡片
  renderToolCards();

  // 3. 图表
  initCharts();
  initControls();

  // 4. 学习区
  initLearnBlocks();

  // 5. 工具筛选
  initFilterTools();

  // 6. 搜索
  initSearch();
  initHeroSearch();

  // 7. 视频交互
  initVideoScroll();

  // 8. 热门搜索
  initHotSearches();

  // 9. 主题切换
  initThemeToggle();

  // 10. 外部链接
  fixExternalLinks();

  // 11. 模型勾选框 Logo
  if (typeof MODEL_ENTRIES !== 'undefined') initModelToggleLogos();
});

// =============================================
// 模型勾选框 Logo
// =============================================
function initModelToggleLogos() {
  if (typeof MODEL_ENTRIES === 'undefined') return;
  const toggles = document.querySelectorAll('#modelToggles .model-toggle');
  toggles.forEach(toggle => {
    const span = toggle.querySelector('.dot');
    if (!span) return;
    const modelName = toggle.textContent.trim();
    const entry = MODEL_ENTRIES.find(m => modelName.startsWith(m.name));
    if (entry) {
      const img = document.createElement('img');
      img.src = getFaviconUrl(entry.domain, 32);
      img.alt = entry.name;
      img.style.cssText = 'width:18px;height:18px;border-radius:4px;flex-shrink:0;margin-right:2px;';
      img.loading = 'lazy';
      img.onerror = function() { this.style.display='none'; };
      span.parentNode.insertBefore(img, span);
    }
  });
}
