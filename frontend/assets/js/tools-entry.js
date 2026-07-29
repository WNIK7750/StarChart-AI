import { initPageShell } from "./page-shell.js";
import { initToolsPage } from "./tools-page.js";

if ("scrollRestoration" in history) history.scrollRestoration = "manual";
if (!location.hash) window.scrollTo(0, 0);

void initPageShell("tools").catch((error) => console.warn("Page shell initialization unavailable:", error));
initToolsPage();
