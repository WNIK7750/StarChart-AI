import { initLearnPage } from "./learning-pages.js";
import { bindNavbarScroll, bindReveal, bindSpotlight, initPageShell } from "./page-shell.js";

const shellReady = initPageShell("learn");
void shellReady.catch((error) => console.warn("Page shell initialization unavailable:", error));
bindNavbarScroll();
await initLearnPage({ authReady: shellReady.then(([, user]) => user) });
bindReveal();
bindSpotlight();
