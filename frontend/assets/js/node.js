import { apiGet } from "./api.js";
import { renderNavigation } from "./layout.js";

function groupLessons(lessons) {
  return lessons.reduce((acc, lesson) => {
    acc[lesson.chapterNo] ||= [];
    acc[lesson.chapterNo].push(lesson);
    return acc;
  }, {});
}

await renderNavigation("learn");
const slug = new URLSearchParams(location.search).get("slug") || "ai-literacy";
const data = await apiGet(`/learning/nodes/${slug}`);
document.querySelector("#nodeTitle").textContent = data.node.title;
document.querySelector("#nodeSubtitle").textContent = data.node.subtitle;
document.querySelector("#nodeBadge").textContent = data.node.difficultyName;
document.querySelector("#nodeBadge").style.background = data.node.color;
document.querySelector("#overview").innerHTML = `
  <p class="muted">这是 ${data.node.title} 节点的学习入口。内容由后端节点、课程目录和资料表动态生成，后续可以在数据库中维护。</p>
`;
const grouped = groupLessons(data.lessons);
document.querySelector("#toc").innerHTML = Object.entries(grouped).map(([chapter, lessons]) => `
  <h3>第 ${chapter} 章</h3>
  <div class="lesson-list">${lessons.map((lesson) => `
    <div class="lesson-row"><strong>${lesson.lessonNo}. ${lesson.title}</strong><span class="muted">${lesson.durationMinutes} 分钟</span></div>
  `).join("")}</div>
`).join("");
document.querySelector("#resources").innerHTML = `<div class="resource-list">${data.resources.map((item) => `
  <a class="resource-link" href="${item.url}" target="_blank">
    <span><strong>${item.title}</strong><br><span class="muted">${item.description}</span></span><span>→</span>
  </a>
`).join("")}</div>`;

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach((panel) => panel.hidden = true);
    tab.classList.add("active");
    document.querySelector(`#${tab.dataset.tab}`).hidden = false;
  });
});
