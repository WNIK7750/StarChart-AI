export function bindRoadmapTabs(scope, onSelect) {
  const tabs = [...scope.querySelectorAll(".roadmap-tab[data-domain]")];
  if (!tabs.length) return;

  const select = (selectedTab) => {
    tabs.forEach((tab) => {
      const selected = tab === selectedTab;
      tab.classList.toggle("active", selected);
      tab.setAttribute("aria-selected", selected ? "true" : "false");
      tab.tabIndex = selected ? 0 : -1;
    });
    onSelect({
      domain: selectedTab.dataset.domain,
      color: selectedTab.style.getPropertyValue("--domain-color"),
      glow: selectedTab.style.getPropertyValue("--domain-glow"),
    });
  };

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => select(tab));
  });

  select(tabs.find((tab) => tab.classList.contains("active")) || tabs[0]);
}
