# AI 知识导航 · 设计令牌 (Design Tokens) v2

> **作用**：本文件是 UI 设计的"宪法"。所有页面、组件、动效都必须从这里取值，禁止临场发挥。
> **基底**：亮色主题为主，深色为对照；参考 Stripe 亮色页面 + Linear 字体层次 + Aceternity UI 动效语法。
> **使用方式**：HTML 内联 CSS 时，全部使用 `:root` 下的 CSS 变量；若未来迁移至 Tailwind，按文末映射表转换。

---

## 0. 设计哲学 (Design Principles)

| 原则 | 含义 | 反例（禁止） |
|---|---|---|
| **克制中的动感** | 静态时干净，交互时有惊喜——动效是奖励，不是装饰 | 一进页面所有元素都在动 |
| **内容至上** | 动效服务于内容理解，不喧宾夺主 | 大型背景光束盖过文字 |
| **等宽节奏** | 任何数据、章节号、技术词汇都用等宽字体形成"代码感" | 全页无衬线，无层次 |
| **玻璃而非纯色** | 卡片用半透 + 模糊 + 1px 高光描边，营造空间深度 | 平面纯白卡片 |
| **彩色克制使用** | 品牌色只用于关键交互（CTA、当前态、强调），其余灰阶 | 满屏彩色，无视觉焦点 |

---

## 1. 色彩系统 (Color Tokens)

### 1.1 亮色主题（默认 · Light）

```css
:root {
  /* —— 背景层（从下到上）—— */
  --bg-canvas:     #FAFAFB;   /* 页面最底层 */
  --bg-elevated:   #FFFFFF;   /* 卡片/浮起表面 */
  --bg-subtle:     #F4F4F7;   /* 次级背景，分区底色 */
  --bg-muted:      #ECECF1;   /* 标签底、禁用态 */

  /* —— 文字层 —— */
  --text-primary:   #0A0A0F;  /* 主标题 */
  --text-secondary: #3F3F4A;  /* 正文 */
  --text-tertiary:  #6E6E7A;  /* 次要说明 */
  --text-quaternary:#A0A0AC;  /* 占位、辅助 */
  --text-on-brand:  #FFFFFF;  /* 品牌色上的文字 */

  /* —— 描边层 —— */
  --border-subtle:  rgba(15, 15, 25, 0.06);
  --border-default: rgba(15, 15, 25, 0.10);
  --border-strong:  rgba(15, 15, 25, 0.16);
  --border-focus:   #7C5CFF;  /* 聚焦态 */

  /* —— 品牌色板（克制使用）—— */
  --brand-primary:  #7C5CFF;  /* 主紫 — CTA、当前态、Logo */
  --brand-secondary:#5EE0FF;  /* 青 — 次级强调 */
  --brand-tertiary: #FF7AC6;  /* 粉 — 装饰渐变 */
  --brand-quaternary:#FFD56B; /* 黄 — 装饰渐变 */

  /* —— 渐变预设 —— */
  --grad-hero:      linear-gradient(120deg, #7C5CFF 0%, #5EE0FF 50%, #FF7AC6 100%);
  --grad-brand:     linear-gradient(135deg, #7C5CFF, #5EE0FF);
  --grad-warm:      linear-gradient(135deg, #FF7AC6, #FFD56B);
  --grad-text:      linear-gradient(180deg, #0A0A0F 0%, #4A4A55 100%);
  --grad-aurora:    radial-gradient(ellipse at 20% 0%, rgba(124,92,255,0.18), transparent 50%),
                    radial-gradient(ellipse at 80% 0%, rgba(94,224,255,0.15), transparent 50%),
                    radial-gradient(ellipse at 50% 10%, rgba(255,122,198,0.10), transparent 60%);

  /* —— 语义色 —— */
  --success:        #16A34A;  /* 通过、免费、可用 */
  --success-bg:     rgba(22, 163, 74, 0.08);
  --warning:        #D97706;
  --warning-bg:     rgba(217, 119, 6, 0.08);
  --danger:         #DC2626;
  --danger-bg:      rgba(220, 38, 38, 0.08);
  --info:           #2563EB;
  --info-bg:        rgba(37, 99, 235, 0.08);

  /* —— 分类色（与现有模型对比一致）—— */
  --cat-chat:       #7C5CFF;  /* 对话助手 */
  --cat-code:       #5EE0FF;  /* 编程开发 */
  --cat-image:      #FF7AC6;  /* 图像生成 */
  --cat-write:      #FFD56B;  /* 写作办公 */
  --cat-video:      #4ADE80;  /* 视频音频 */
  --cat-search:     #FB923C;  /* 智能搜索 */
}
```

### 1.2 深色主题（Dark · 切换备用）

```css
[data-theme="dark"] {
  --bg-canvas:     #0A0A0F;
  --bg-elevated:   #16161F;
  --bg-subtle:     #111118;
  --bg-muted:      #1F1F2A;

  --text-primary:   #F4F4F7;
  --text-secondary: #C0C0CC;
  --text-tertiary:  #8E8E9A;
  --text-quaternary:#5A5A68;
  --text-on-brand:  #FFFFFF;

  --border-subtle:  rgba(255, 255, 255, 0.06);
  --border-default: rgba(255, 255, 255, 0.10);
  --border-strong:  rgba(255, 255, 255, 0.16);

  /* 品牌色板不变，但在深色下增加发光 */
  --brand-primary:  #9B7EFF;  /* 提亮 10% */
  --brand-secondary:#7CE8FF;
  --brand-tertiary: #FF9AD4;

  /* 深色下 aurora 透明度提高 */
  --grad-aurora:    radial-gradient(ellipse at 20% 0%, rgba(124,92,255,0.45), transparent 50%),
                    radial-gradient(ellipse at 80% 0%, rgba(94,224,255,0.35), transparent 50%),
                    radial-gradient(ellipse at 50% 10%, rgba(255,122,198,0.25), transparent 60%);
}
```

### 1.3 色彩使用规则

| 用途 | 取值 | 备注 |
|---|---|---|
| 页面背景 | `--bg-canvas` | 不允许在主页大面积使用纯白 |
| 卡片背景 | `--bg-elevated` + `backdrop-filter: blur(12px)` | 玻璃态 |
| 主标题 | `--text-primary` | 不使用渐变文字（除 Hero 主标题） |
| 正文 | `--text-secondary` | 14-16px |
| CTA 按钮 | `--brand-primary` 背景 + `--text-on-brand` 文字 | 全站主按钮唯一来源 |
| 当前选中态 | `--brand-primary` 边框 + `rgba(124,92,255,0.08)` 背景 | 不允许用其他色 |
| 装饰渐变 | `--grad-aurora` / `--grad-hero` | 仅 Hero 和章节分隔 |

---

## 2. 字体系统 (Typography Tokens)

### 2.1 字族（Font Family）

```css
:root {
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
               "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  --font-mono: "SF Mono", "JetBrains Mono", "Cascadia Code", Menlo, Consolas, monospace;
  --font-display: var(--font-sans);  /* 暂不引入额外 display 字体，保持加载速度 */
}
```

> **决策**：不引入 Inter / Geist 等额外字体。系统字体在中文环境下渲染最稳定，且零加载延迟。等宽字体仅用于"代码感"装饰（章节号、数据、标签、技术词汇）。

### 2.2 字号比例（Type Scale）

基于 1.250（Major Third）比例，桌面端：

| Token | 字号 | 行高 | 字重 | 用途 |
|---|---|---|---|---|
| `--text-hero`     | 72px | 1.05 | 600 | Hero 主标题 |
| `--text-display`  | 52px | 1.10 | 600 | 章节大标题 |
| `--text-h1`       | 40px | 1.15 | 600 | 页面 H1 |
| `--text-h2`       | 30px | 1.20 | 600 | 区块标题 |
| `--text-h3`       | 22px | 1.30 | 600 | 卡片标题 |
| `--text-body-lg`  | 18px | 1.55 | 400 | Hero 副标题、引导文 |
| `--text-body`     | 15px | 1.60 | 400 | 正文（默认） |
| `--text-body-sm`  | 13px | 1.55 | 400 | 次要说明 |
| `--text-caption`  | 12px | 1.40 | 400 | 标签、提示 |
| `--text-overline` | 11px | 1.20 | 500 | 章节编号 `§ 01`、UPPERCASE |

```css
:root {
  --text-hero:     72px;
  --text-display:  52px;
  --text-h1:       40px;
  --text-h2:       30px;
  --text-h3:       22px;
  --text-body-lg:  18px;
  --text-body:     15px;
  --text-body-sm:  13px;
  --text-caption:  12px;
  --text-overline: 11px;
}
```

### 2.3 字重（Font Weight）

| Token | 值 | 用途 |
|---|---|---|
| `--weight-regular` | 400 | 正文 |
| `--weight-medium`  | 500 | 强调正文、按钮、章节编号 |
| `--weight-semibold`| 600 | 标题 |
| `--weight-bold`    | 700 | 仅用于数据数字、Logo |

### 2.4 字间距（Letter Spacing）

| Token | 值 | 用途 |
|---|---|---|
| `--tracking-tight` | -0.025em | 大标题（≥30px） |
| `--tracking-normal`| 0 | 正文 |
| `--tracking-wide`  | 0.05em | 等宽字体（章节号、标签） |
| `--tracking-wider` | 0.10em | UPPERCASE 文字 |

### 2.5 字体使用规则

- **大标题用 tracking-tight + weight-semibold**（不是 bold），营造 Linear 那种克制感
- **章节编号统一 `§ 01 / Section Name` 格式**，等宽字体 + uppercase + tracking-wide
- **数据数字一律等宽字体**（评分、得分、统计数）
- **Hero 主标题可用渐变文字**（`background-clip: text`），但全页只允许 1 处

---

## 3. 间距系统 (Spacing Tokens)

### 3.1 基础栅格（4px 基准）

```css
:root {
  --space-0:   0;
  --space-1:   4px;
  --space-2:   8px;
  --space-3:   12px;
  --space-4:   16px;
  --space-5:   20px;
  --space-6:   24px;
  --space-8:   32px;
  --space-10:  40px;
  --space-12:  48px;
  --space-16:  64px;
  --space-20:  80px;
  --space-24:  96px;
  --space-32:  128px;
}
```

### 3.2 语义间距

| Token | 值 | 用途 |
|---|---|---|
| `--gap-card`      | 12px | 卡片网格内间距 |
| `--gap-section`   | 16px | 同一区块内元素间距 |
| `--pad-card`      | 24px | 卡片内边距 |
| `--pad-card-lg`   | 32px | 大卡片内边距 |
| `--pad-page`      | 32px | 容器左右内边距 |
| `--pad-page-mobile`| 20px | 移动端容器左右内边距 |
| `--section-y`     | 120px | 区块上下间距（桌面） |
| `--section-y-mobile`| 80px | 区块上下间距（移动） |
| `--container-max` | 1200px | 内容最大宽度 |

### 3.3 间距使用规则

- **任何间距值必须来自上表**，不允许 `15px`、`7px` 这种非栅格值
- **区块间距统一 `--section-y`**，区块内统一 `--gap-section`
- **卡片内边距**：小卡片 24px，大卡片（hero card / section feature）32px

---

## 4. 圆角系统 (Radius Tokens)

```css
:root {
  --radius-xs:   4px;   /* 标签、kbd */
  --radius-sm:   6px;   /* 小按钮、tag */
  --radius-md:   10px;  /* 按钮、输入框 */
  --radius-lg:   14px;  /* 标准卡片 */
  --radius-xl:   22px;  /* 大卡片、Hero 容器 */
  --radius-2xl:  32px;  /* 装饰性大圆角（极少用） */
  --radius-full: 9999px; /* 胶囊、徽章 */
}
```

**规则**：
- 卡片统一 `--radius-lg`，"特写卡片"用 `--radius-xl`
- 按钮统一 `--radius-md`，胶囊型按钮用 `--radius-full`
- 不允许出现 `8px`、`12px`、`16px` 这种非栅格圆角

---

## 5. 阴影系统 (Shadow Tokens)

```css
:root {
  /* 静态阴影 */
  --shadow-xs:   0 1px 2px rgba(15, 15, 25, 0.04);
  --shadow-sm:   0 2px 8px rgba(15, 15, 25, 0.06);
  --shadow-md:   0 8px 24px rgba(15, 15, 25, 0.08);
  --shadow-lg:   0 24px 48px rgba(15, 15, 25, 0.10);

  /* 玻璃态阴影（带顶部高光）*/
  --shadow-glass: 0 1px 0 rgba(255, 255, 255, 0.8) inset,
                  0 8px 24px rgba(15, 15, 25, 0.06);

  /* 品牌色发光（聚焦态、当前卡片）*/
  --shadow-brand: 0 0 0 4px rgba(124, 92, 255, 0.12),
                  0 8px 24px rgba(124, 92, 255, 0.18);

  /* 悬浮态（hover 提升）*/
  --shadow-hover: 0 1px 0 rgba(255, 255, 255, 0.9) inset,
                  0 16px 40px rgba(15, 15, 25, 0.12);
}
```

**规则**：
- 默认态用 `--shadow-glass`（带顶部高光的玻璃态）
- hover 用 `--shadow-hover`（提升 4-8px）
- 聚焦态用 `--shadow-brand`（紫色发光环）
- 模态框/弹层用 `--shadow-lg`

---

## 6. 边框系统 (Border Tokens)

```css
:root {
  --border-width-hairline: 1px;
  --border-width-default:  1px;
  --border-width-strong:   2px;
  --border-width-focus:    2px;

  /* 玻璃态边框（亮色）*/
  --border-glass: 1px solid var(--border-default);
  /* 玻璃态顶部高光线（伪元素）*/
  --border-glass-highlight: linear-gradient(90deg, transparent, rgba(255,255,255,0.9), transparent);
}
```

---

## 7. 动效系统 (Motion Tokens)

> **核心原则**：动效是"奖励"，不是"装饰"。静态时页面应当干净克制，用户交互时才"亮起来"。

### 7.1 时长（Duration）

```css
:root {
  --duration-instant: 100ms;   /* 状态切换（active/disabled）*/
  --duration-fast:    150ms;   /* hover、color */
  --duration-base:    250ms;   /* transform、shadow */
  --duration-slow:    400ms;   /* 大幅位移、模态 */
  --duration-slower:  600ms;   /* 入场动画 */
  --duration-slowest: 800ms;   /* reveal 动画 */
}
```

### 7.2 缓动曲线（Easing）

```css
:root {
  --ease-standard:    cubic-bezier(0.4, 0, 0.2, 1);    /* 通用 */
  --ease-emphasized:  cubic-bezier(0.16, 1, 0.3, 1);   /* 入场、揭示 */
  --ease-decelerated: cubic-bezier(0, 0, 0.2, 1);      /* 进入 */
  --ease-accelerated: cubic-bezier(0.4, 0, 1, 1);      /* 离开 */
  --ease-spring:      cubic-bezier(0.34, 1.56, 0.64, 1);/* 弹簧（hover 提升等）*/
}
```

### 7.3 动效模式库

| 模式 | 触发 | 时长 | 曲线 | CSS 实现 |
|---|---|---|---|---|
| `fade-in`        | 进入视口 | 800ms | emphasized | `opacity: 0→1` |
| `fade-up`        | 进入视口 | 800ms | emphasized | `opacity + translateY(20px→0)` |
| `hover-lift`     | hover | 200ms | spring | `transform: translateY(-2px)` + shadow 变化 |
| `hover-glow`     | hover | 250ms | standard | `box-shadow` 加 brand 光晕 |
| `spotlight-follow`| mousemove | instant | — | CSS 变量驱动 radial-gradient |
| `border-beam`    | 持续 | 3000ms | linear infinite | conic-gradient 旋转 |
| `text-generate`  | 进入视口 | 50ms/字 | — | 逐字 opacity |
| `shimmer`        | 持续 | 2000ms | linear infinite | background-position 滚动 |
| `aurora-drift`   | 持续 | 18-30s | ease-in-out alternate | transform translate + scale |

### 7.4 减少动效（Accessibility）

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

---

## 8. 玻璃态规范 (Glassmorphism Spec)

亮色主题下的玻璃态比深色更难，关键是**透明度 + 模糊 + 高光**三层叠加：

```css
.glass {
  background: rgba(255, 255, 255, 0.72);       /* 透明度 72% */
  backdrop-filter: blur(16px) saturate(180%);
  -webkit-backdrop-filter: blur(16px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.6);  /* 内描边亮 */
  box-shadow: var(--shadow-glass);
  border-radius: var(--radius-lg);
}

/* 顶部 1px 高光线（伪元素）*/
.glass::before {
  content: "";
  position: absolute;
  top: 0; left: 12%; right: 12%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.95), transparent);
}
```

**使用场景**：
- 顶部导航栏（Floating Navbar）
- 卡片（普通卡片可选）
- 模态框、Popover

**禁止**：
- 大面积使用（一屏不超过 3 个玻璃态元素）
- 在没有内容背景的位置使用（会变成"灰白泥"）

---

## 9. Aceternity UI 组件适配令牌

> 由于本项目是**纯静态 HTML/CSS/JS**（非 React + Tailwind），Aceternity 组件需用 CSS 还原。下表是核心组件的 CSS 实现映射。

### 9.1 必选组件（v2 必用）

| Aceternity 组件 | CSS 还原方案 | 关键令牌 |
|---|---|---|
| **Floating Navbar** | `position: sticky; backdrop-filter: blur()` + scroll 时切换 class | `--shadow-glass`, `--duration-base` |
| **Grid and Dot Background** | `background-image: linear-gradient` 双层 + `mask-image` 径向遮罩 | `--border-subtle` |
| **Background Lines** | SVG path + `stroke-dashoffset` 动画 | `--brand-secondary` |
| **Spotlight (Card)** | CSS 变量 `--mx --my` + `radial-gradient` 跟随鼠标 | `--brand-primary` |
| **Bento Grid** | CSS Grid + `grid-template-areas` + 不等高 | `--gap-card`, `--radius-lg` |
| **Layout Grid** | CSS Grid + 点击展开（JS 切 class） | `--shadow-hover` |
| **Text Generate Effect** | JS 拆字 + `setTimeout` + opacity | `--duration-instant` |
| **Typewriter Effect** | JS setInterval + CSS blink caret | `--font-mono` |
| **Pointer Highlight** | SVG path + `stroke-dashoffset` 滚动触发 | `--brand-primary` |
| **Moving Border** | `conic-gradient` + `animation: rotate` | `--grad-brand` |
| **Stateful Button** | 三态 class 切换 + spinner SVG | `--duration-base` |
| **Placeholders And Vanish Input** | JS 切换 placeholder + 提交时 `transform: scale(0)` | `--duration-slow` |
| **Animated Tabs** | `transform: translateX` + `::after` 下划线动画 | `--brand-primary` |
| **Lamp Section Header** | 双层 `radial-gradient` + `mask-image` | `--brand-primary`, `--brand-secondary` |
| **Tracing Beam** | SVG path + `scroll` 事件驱动 `stroke-dashoffset` | `--brand-primary` |
| **Infinite Moving Cards** | `animation: marquee linear infinite` + 双倍内容 | `--duration-slowest` |
| **Timeline** | sticky header + scroll-triggered class | `--brand-primary` |
| **Code Block** | `<pre><code>` + 简易 highlight | `--font-mono` |

### 9.2 可选组件（v2 视情况用）

| 组件 | 场景 | 备注 |
|---|---|---|
| **Card Spotlight** | 学习卡片 hover | 跟随鼠标的径向渐变 |
| **Glare Card** | 模型对比卡片 | Linear 风格光晕 |
| **Expandable Cards** | 学习节点详情 | 点击展开内嵌资料 |
| **Focus Cards** | 工具网格 hover | 其他卡片模糊 |
| **Link Preview** | 工具卡片 hover | 显示工具截图缩略图 |
| **Apple Cards Carousel** | 首页"精选推荐" | 横向滑动卡片 |
| **Tooltip Card** | 模型对比表的"基准说明" | 跟随鼠标的提示 |
| **Gooey Input** | 顶部搜索框（展开式） | 备选方案 |

### 9.3 禁用组件（亮色下效果差 / 与内容型冲突）

- ❌ Aurora Background（亮色下减弱）
- ❌ Vortex / Meteors / Shooting Stars（暗色专用）
- ❌ Background Beams / Background Beams With Collision（过于装饰）
- ❌ 3D Globe / GitHub Globe（场景不符）
- ❌ Hero Parallax / Container Scroll Animation（过于花哨）

---

## 10. 响应式断点 (Breakpoints)

```css
:root {
  --bp-sm:  640px;   /* 手机横屏 */
  --bp-md:  768px;   /* 平板竖屏 */
  --bp-lg:  1024px;  /* 平板横屏 / 小笔记本 */
  --bp-xl:  1280px;  /* 桌面 */
  --bp-2xl: 1536px;  /* 大屏 */
}
```

**断点策略**：
- `< 768px`：单列布局，导航折叠为汉堡菜单
- `768-1024px`：双列卡片，导航完整
- `> 1024px`：三列及以上，完整体验
- 容器最大宽度 `--container-max: 1200px`，超大屏左右留白

---

## 11. Z-Index 层级

```css
:root {
  --z-base:        0;
  --z-content:     1;
  --z-decorative:  2;   /* 背景光斑、网格 */
  --z-sticky:      10;  /* sticky section head */
  --z-navbar:      50;  /* 顶部导航 */
  --z-dropdown:    100;
  --z-modal:       1000;
  --z-toast:       1100;
  --z-tooltip:     1200;
}
```

---

## 12. Tailwind 迁移映射（备用）

若未来迁移至 Tailwind + shadcn/ui，按下表映射：

| CSS 变量 | Tailwind 配置 |
|---|---|
| `--brand-primary: #7C5CFF` | `colors.brand.500` |
| `--brand-secondary: #5EE0FF` | `colors.brand.400`（accent） |
| `--text-primary: #0A0A0F` | `colors.gray.950` |
| `--bg-canvas: #FAFAFB` | `colors.gray.50` |
| `--radius-lg: 14px` | `borderRadius.lg` |
| `--shadow-glass` | `boxShadow.glass` |
| `--duration-base: 250ms` | `transitionDuration.DEFAULT` |
| `--ease-emphasized` | `transitionTimingFunctions.emphasized` |

---

## 13. 设计令牌使用检查清单

在交付任何页面前，对照本清单逐项确认：

- [ ] 所有颜色取自 `:root`，未出现"野生"颜色
- [ ] 所有字号、字重、字间距取自 Type Scale
- [ ] 所有间距是 4 的倍数（或来自语义 token）
- [ ] 所有圆角来自 Radius 系统
- [ ] 所有阴影来自 Shadow 系统
- [ ] 动效时长/曲线来自 Motion 系统
- [ ] 玻璃态元素一屏不超过 3 个
- [ ] 品牌紫色仅用于 CTA、当前态、强调
- [ ] 章节标题带 `§ NN / Name` 编号
- [ ] 数据/标签使用等宽字体
- [ ] 大标题 `tracking-tight` + `weight-semibold`
- [ ] 提供 `prefers-reduced-motion` 降级
- [ ] 移动端断点 `--bp-md` 以下布局合理

---

**版本**：v2.0 · 2026-07-07
**下一步**：见 `page-plan.md` 的页面规划
