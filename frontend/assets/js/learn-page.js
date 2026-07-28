import { initLearnPage } from "./learning-pages.js";
import { bindNavbarScroll, bindReveal, bindSpotlight, initPageShell } from "./page-shell.js";

await initPageShell("learn");
bindNavbarScroll();
await initLearnPage();
bindReveal();
bindSpotlight();
