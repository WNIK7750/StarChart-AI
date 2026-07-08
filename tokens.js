/* =============================================
   Design Tokens — 设计令牌引擎
   ============================================= */

// ============ 默认令牌（与 :root 中的值保持一致）============
const TOKENS = {
  // —— 颜色 ——
  '--color-primary':       '#185FA5',
  '--color-primary-light': '#E6F1FB',
  '--color-primary-dark':  '#0C447C',
  '--color-bg':            '#ffffff',
  '--color-bg-page':       '#f5f5f0',
  '--color-bg-secondary':  '#f8f8f6',
  '--color-text':          '#1a1a1a',
  '--color-text-secondary':'#555555',
  '--color-text-hint':     '#999999',
  '--color-border':        'rgba(0,0,0,0.08)',
  '--color-border-md':     'rgba(0,0,0,0.13)',
  '--color-success':       '#3B6D11',
  '--color-warning':       '#993C1D',
  '--color-purple':        '#534AB7',
  '--color-purple-light':  '#EEEDFE',

  // —— 字体 ——
  '--font-family':   '-apple-system,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif',
  '--font-size-xs':  '10px',
  '--font-size-sm':  '12px',
  '--font-size-base': '14px',
  '--font-size-md':  '15px',
  '--font-size-lg':  '22px',
  '--font-size-xl':  '36px',
  '--font-weight-normal':  '400',
  '--font-weight-md':    '500',
  '--font-weight-bold':   '600',
  '--line-height':   '1.65',

  // —— 间距 ——
  '--spacing-xs':  '4px',
  '--spacing-sm':  '8px',
  '--spacing-md':  '12px',
  '--spacing-lg':  '16px',
  '--spacing-xl':  '20px',
  '--spacing-2xl': '24px',
  '--gap':         '24px',

  // —— 圆角 ——
  '--radius-sm': '6px',
  '--radius-md': '10px',
  '--radius-lg': '99px',

  // —— 布局 ——
  '--top-h':          '56px',
  '--sidebar-left-w': '160px',
  '--sidebar-right-w':'160px',

  // —— 阴影 & 动效 ——
  '--shadow-sm':  '0 1px 4px rgba(0,0,0,0.06)',
  '--shadow-md':  '0 2px 12px rgba(0,0,0,0.08)',
  '--transition-fast':   '0.15s ease',
  '--transition-normal':'0.22s ease',
};

// ============ 预设主题 ============
const THEMES = {
  light: {
    '--color-primary':       '#185FA5',
    '--color-primary-light': '#E6F1FB',
    '--color-primary-dark':  '#0C447C',
    '--color-bg':            '#ffffff',
    '--color-bg-page':       '#f5f5f0',
    '--color-bg-secondary':  '#f8f8f6',
    '--color-text':          '#1a1a1a',
    '--color-text-secondary':'#555555',
    '--color-text-hint':     '#999999',
    '--color-border':        'rgba(0,0,0,0.08)',
    '--color-border-md':     'rgba(0,0,0,0.13)',
    '--color-success':       '#3B6D11',
    '--color-warning':       '#993C1D',
    '--color-purple':        '#534AB7',
    '--color-purple-light':  '#EEEDFE',
    '--shadow-sm':  '0 1px 4px rgba(0,0,0,0.06)',
    '--shadow-md':  '0 2px 12px rgba(0,0,0,0.08)',
  },

  dark: {
    '--color-primary':       '#60A5FA',
    '--color-primary-light': '#1E3A5F',
    '--color-primary-dark':  '#93C5FD',
    '--color-bg':            '#1E1E2E',
    '--color-bg-page':       '#111118',
    '--color-bg-secondary':  '#27273A',
    '--color-text':          '#E0E0E0',
    '--color-text-secondary':'#A0A0A0',
    '--color-text-hint':     '#666666',
    '--color-border':        'rgba(255,255,255,0.08)',
    '--color-border-md':     'rgba(255,255,255,0.13)',
    '--color-success':       '#4ADE80',
    '--color-warning':       '#FCA5A5',
    '--color-purple':        '#A78BFA',
    '--color-purple-light':  '#2D1B69',
    '--shadow-sm':  '0 1px 4px rgba(0,0,0,0.3)',
    '--shadow-md':  '0 2px 12px rgba(0,0,0,0.4)',
  },


  geek: {
    '--color-primary':       '#32f08c',
    '--color-primary-light': '#132a1f',
    '--color-primary-dark':  '#0fdc78',
    '--color-bg':            '#121417',
    '--color-bg-page':       '#0a0b0d',
    '--color-bg-secondary':  '#191c20',
    '--color-text':          '#f5f9fe',
    '--color-text-secondary':'#a6aab5',
    '--color-text-hint':     '#787d87',
    '--color-border':        'rgba(50,240,140,0.08)',
    '--color-border-md':     'rgba(255,255,255,0.12)',
    '--color-success':       '#32f08c',
    '--color-warning':       '#FF6B35',
    '--color-purple':        '#32f08c',
    '--color-purple-light':  '#132a1f',
    '--shadow-sm':  '0 1px 4px rgba(50,240,140,0.08)',
    '--shadow-md':  '0 2px 12px rgba(237,239,242,0.10)',
  },
  blue: {
    '--color-primary':       '#2563EB',
    '--color-primary-light': '#DBEAFE',
    '--color-primary-dark':  '#1E40AF',
    '--color-bg':            '#ffffff',
    '--color-bg-page':       '#EFF6FF',
    '--color-bg-secondary':  '#F0F9FF',
    '--color-text':          '#1E293B',
    '--color-text-secondary':'#475569',
    '--color-text-hint':     '#94A3B8',
    '--color-border':        'rgba(37,99,235,0.08)',
    '--color-border-md':     'rgba(37,99,235,0.15)',
    '--color-success':       '#059669',
    '--color-warning':       '#D97706',
    '--color-purple':        '#7C3AED',
    '--color-purple-light':  '#EDE9FE',
  },

  green: {
    '--color-primary':       '#059669',
    '--color-primary-light': '#D1FAE5',
    '--color-primary-dark':  '#047857',
    '--color-bg':            '#ffffff',
    '--color-bg-page':       '#F0FDF4',
    '--color-bg-secondary':  '#F0FDF4',
    '--color-text':          '#1a1a1a',
    '--color-text-secondary':'#555555',
    '--color-text-hint':     '#999999',
    '--color-border':        'rgba(0,0,0,0.08)',
    '--color-border-md':     'rgba(0,0,0,0.13)',
    '--color-success':       '#16A34A',
    '--color-warning':       '#EA580C',
    '--color-purple':        '#7C3AED',
    '--color-purple-light':  '#EEEDFE',
  },

  purple: {
    '--color-primary':       '#7C3AED',
    '--color-primary-light': '#EDE9FE',
    '--color-primary-dark':  '#5B21B6',
    '--color-bg':            '#ffffff',
    '--color-bg-page':       '#FAF5FF',
    '--color-bg-secondary':  '#F5F3FF',
    '--color-text':          '#1a1a1a',
    '--color-text-secondary':'#555555',
    '--color-text-hint':     '#999999',
    '--color-border':        'rgba(124,58,237,0.08)',
    '--color-border-md':     'rgba(124,58,237,0.15)',
    '--color-success':       '#059669',
    '--color-warning':       '#D97706',
    '--color-purple':        '#7C3AED',
    '--color-purple-light':  '#EDE9FE',
  },
};

// ============ 工具函数 ============

/** 设置单个设计令牌（立即生效 + 存入 localStorage） */
function setToken(name, value) {
  document.documentElement.style.setProperty(name, value);
  // 存入自定义令牌集合
  let custom = JSON.parse(localStorage.getItem('customTokens') || '{}');
  custom[name] = value;
  localStorage.setItem('customTokens', JSON.stringify(custom));
}

/** 应用整套预设主题 */
function applyTheme(themeName) {
  const theme = THEMES[themeName];
  if (!theme) return;
  // 先重置所有令牌为默认值
  Object.entries(TOKENS).forEach(([name, value]) => {
    document.documentElement.style.setProperty(name, value);
  });
  // 再覆盖主题令牌
  Object.entries(theme).forEach(([name, value]) => {
    document.documentElement.style.setProperty(name, value);
  });
  localStorage.setItem('preferred-theme', themeName);
  // 清除自定义令牌（切换主题时以主题为准）
  localStorage.removeItem('customTokens');
  // 同步图表模型颜色（如果 MODELS 已定义）
  syncChartColors();
  // 同步 html 元素 data-theme 属性（用于 CSS 主题覆盖）
  document.documentElement.setAttribute('data-theme', themeName);
}

/** 从 localStorage 恢复自定义令牌 */
function applyCustomTokens() {
  const themeName = localStorage.getItem('preferred-theme') || 'geek';
  // 先应用基础主题
  const baseTheme = THEMES[themeName] || THEMES['light'];
  Object.entries(TOKENS).forEach(([name, value]) => {
    document.documentElement.style.setProperty(name, value);
  });
  Object.entries(baseTheme).forEach(([name, value]) => {
    document.documentElement.style.setProperty(name, value);
  });
  // 再覆盖用户自定义令牌
  const custom = JSON.parse(localStorage.getItem('customTokens') || '{}');
  Object.entries(custom).forEach(([name, value]) => {
    document.documentElement.style.setProperty(name, value);
  });
  syncChartColors();
  // 同步 html 元素 data-theme 属性（用于 CSS 主题覆盖）
  document.documentElement.setAttribute('data-theme', themeName);
}

/** 同步图表模型颜色（需要在 app.js 中调用） */
function syncChartColors() {
  // 由 app.js 覆盖此函数
}

/** 导出当前所有令牌为 CS 字符串 */
function exportTokensCSS() {
  const root = document.documentElement;
  const lines = ['/* 设计令牌导出 — ' + new Date().toLocaleString() + ' */', ':root {'];
  Object.keys(TOKENS).forEach(name => {
    const val = root.style.getPropertyValue(name).trim()
             || getComputedStyle(root).getPropertyValue(name).trim();
    if (val) lines.push(`  ${name}: ${val};`);
  });
  lines.push('}');
  return lines.join('\n');
}

// ============ 设计面板初始化 ============
function initDesignPanel() {
  const panel    = document.getElementById('designPanel');
  const overlay  = document.getElementById('overlay');
  const btnOpen  = document.getElementById('btnDesign');
  const btnClose = document.getElementById('designPanelClose');
  const btnReset = document.getElementById('btnResetTokens');
  const btnExport= document.getElementById('btnExportTokens');

  if (!panel) return;

  // —— 开关面板 ——
  function openPanel()  {
    panel.classList.add('open');
    overlay && overlay.classList.add('show');
  }
  function closePanel() {
    panel.classList.remove('open');
    overlay && overlay.classList.remove('show');
  }
  btnOpen && btnOpen.addEventListener('click', openPanel);
  btnClose&& btnClose.addEventListener('click', closePanel);
  overlay && overlay.addEventListener('click', closePanel);

  // —— 预设主题按钮 ——
  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyTheme(btn.dataset.theme);
      // 同步拾色器到当前值
      colorControls.forEach(({ id, token, hexId }) => {
        const el = document.getElementById(id);
        if (el) {
          const val = getComputedStyle(document.documentElement).getPropertyValue(token).trim();
          el.value = val || el.value;
        }
        const hexEl = document.getElementById(hexId);
        if (hexEl) hexEl.textContent = el ? el.value : '';
      });
    });
  });

  // —— 颜色拾色器 ——
  const colorControls = [
    { id: 'tokenColorPrimary',  token: '--color-primary',       hexId: 'hexColorPrimary' },
    { id: 'tokenColorBg',      token: '--color-bg',             hexId: 'hexColorBg' },
    { id: 'tokenColorBgPage',  token: '--color-bg-page',        hexId: 'hexColorBgPage' },
    { id: 'tokenColorText',    token: '--color-text',           hexId: 'hexColorText' },
    { id: 'tokenColorPrimaryLight', token: '--color-primary-light', hexId: 'hexColorPrimaryLight' },
  ];
  colorControls.forEach(({ id, token, hexId }) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('input', () => {
      setToken(token, el.value);
      const hexEl = document.getElementById(hexId);
      if (hexEl) hexEl.textContent = el.value;
      if (token === '--color-primary') syncChartColors();
    });
  });

  // —— 圆角滑块 ——
  const radiusSlider = document.getElementById('tokenRadius');
  const radiusVal   = document.getElementById('tokenRadiusVal');
  if (radiusSlider && radiusVal) {
    radiusSlider.addEventListener('input', () => {
      const v = radiusSlider.value + 'px';
      radiusVal.textContent = v;
      setToken('--radius-sm', v);
      setToken('--radius-md', v);
    });
  }

  // —— 侧边栏宽度滑块 ——
  const sbSlider = document.getElementById('tokenSbWidth');
  const sbVal    = document.getElementById('tokenSbWidthVal');
  if (sbSlider && sbVal) {
    sbSlider.addEventListener('input', () => {
      const v = sbSlider.value + 'px';
      sbVal.textContent = v;
      setToken('--sidebar-left-w', v);
      // 触发 resize 以更新 CSS Grid
      window.dispatchEvent(new Event('resize'));
    });
  }

  // —— 顶部导航高度滑块 ——
  const topSlider = document.getElementById('tokenTopH');
  const topVal    = document.getElementById('tokenTopHVal');
  if (topSlider && topVal) {
    topSlider.addEventListener('input', () => {
      const v = topSlider.value + 'px';
      topVal.textContent = v;
      setToken('--top-h', v);
    });
  }

  // —— 重置按钮 ——
  if (btnReset) {
    btnReset.addEventListener('click', () => {
      localStorage.removeItem('customTokens');
      localStorage.setItem('preferred-theme', 'geek');
      applyTheme('geek');
      // 重置滑块
      if (radiusSlider) { radiusSlider.value = 6;  radiusVal.textContent = '6px'; }
      if (sbSlider)     { sbSlider.value = 160; sbVal.textContent = '160px'; }
      if (topSlider)    { topSlider.value = 56;  topVal.textContent = '56px'; }
      document.querySelectorAll('.theme-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.theme === 'geek');
      });
    });
  }

  // —— 导出按钮 ——
  if (btnExport) {
    btnExport.addEventListener('click', () => {
      const css = exportTokensCSS();
      navigator.clipboard.writeText(css).then(() => {
        btnExport.textContent = '已复制！';
        setTimeout(() => { btnExport.textContent = '复制 CS'; }, 1500);
      });
    });
  }

  // —— 初始化面板控件状态 ———
  // 设置当前主题高亮
  const currentTheme = localStorage.getItem('preferred-theme') || 'geek';
  document.querySelectorAll('.theme-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.theme === currentTheme);
  });
  // 同步拾色器到当前值
  colorControls.forEach(({ id, token, hexId }) => {
    const el = document.getElementById(id);
    if (el) {
      const val = getComputedStyle(document.documentElement).getPropertyValue(token).trim();
      if (val) el.value = val;
    }
    const hexEl = document.getElementById(hexId);
    if (hexEl && el) hexEl.textContent = el.value;
  });
}
