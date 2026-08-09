// Frozen Agent-page compatibility entry. Non-Agent pages use explicit page entries.
import { initPageShell } from "./page-shell.js?v=20260809-auth-store-1";

const page = document.body.dataset.page || "home";
void initPageShell(page === "learn-node" ? "learn" : page).catch((error) => console.warn("Page shell initialization unavailable:", error));
