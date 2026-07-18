import assert from "node:assert/strict";
import fs from "node:fs";

const html = fs.readFileSync("frontend/assistant.html", "utf8");
const script = fs.readFileSync("frontend/assets/js/assistant-page.js", "utf8");
const search = fs.readFileSync("frontend/assets/js/site-search.js", "utf8");

assert.match(html, /id="assistantForm"/);
assert.match(html, /data-page="assistant"/);
assert.match(script, /apiPost\("\/agent\/chat"/);
assert.match(script, /saveAgentWorkflow/);
assert.match(script, /confirmed: true/);
assert.match(script, /data-auth-trigger="login"/);
assert.doesNotMatch(script, /tool-data\.js|learning-data\.js/);
assert.match(search, /url: "assistant\.html"/);

console.log("agent frontend contract tests passed");
