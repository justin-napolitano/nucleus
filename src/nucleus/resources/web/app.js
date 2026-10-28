const results = document.querySelector("#results");
const total = document.querySelector("#total");
const page = document.querySelector("#page");
const previous = document.querySelector("#previous");
const next = document.querySelector("#next");
const search = document.querySelector("#search");
const kind = document.querySelector("#kind");
let offset = 0;
const limit = 20;

function empty(title, message) {
  const box = document.createElement("div");
  box.className = "empty";
  const heading = document.createElement("h3");
  heading.textContent = title;
  const body = document.createElement("p");
  body.textContent = message;
  box.append(heading, body);
  results.replaceChildren(box);
}

async function load() {
  const query = new URLSearchParams({offset: String(offset), limit: String(limit)});
  if (search.value) query.set("query", search.value);
  if (kind.value) query.set("kind", kind.value);
  try {
    const response = await fetch(`/v1/catalog?${query}`, {headers: {Accept: "application/json"}});
    if (!response.ok) throw new Error("unavailable");
    const data = await response.json();
    total.textContent = `${data.total} ${data.total === 1 ? "item" : "items"}`;
    page.textContent = `Page ${Math.floor(offset / limit) + 1}`;
    previous.disabled = offset === 0;
    next.disabled = data.nextOffset === null;
    if (!data.items.length) {
      empty("No matches in this view", "Try another search or category. Imported definitions will appear after an explicit registration.");
      return;
    }
    results.replaceChildren(...data.items.map(item => {
      const card = document.createElement("article");
      card.className = "card";
      const type = document.createElement("span");
      type.className = "kind";
      type.textContent = item.kind;
      const heading = document.createElement("h3");
      heading.textContent = item.displayName;
      const description = document.createElement("p");
      description.textContent = item.description;
      const meta = document.createElement("div");
      meta.className = "meta";
      meta.textContent = `${item.objectId} · ${item.state} · execution disabled`;
      card.append(type, heading, description, meta);
      if (["Source", "SchemaContract", "Mapping", "Run", "Artifact", "Lineage", "Decision"].includes(item.kind)) {
        const details = document.createElement("details");
        const summary = document.createElement("summary");
        summary.textContent = "View catalog evidence";
        const definition = document.createElement("pre");
        definition.textContent = JSON.stringify(item, null, 2);
        details.append(summary, definition);
        card.append(details);
      }
      if (item.kind === "Skill" && item.state === "review") {
        const details = document.createElement("details");
        details.className = "skill-review";
        const summary = document.createElement("summary");
        summary.textContent = "Review skill definition";
        const content = document.createElement("div");
        content.textContent = "Open to load the pinned instructions.";
        details.append(summary, content);
        details.addEventListener("toggle", async () => {
          if (!details.open || details.dataset.loaded) return;
          content.textContent = "Loading reviewed source…";
          try {
            const params = new URLSearchParams({object_id: item.objectId});
            const response = await fetch(`/v1/review/skill?${params}`, {headers: {Accept: "application/json"}});
            if (!response.ok) throw new Error("unavailable");
            const record = await response.json();
            const provenance = document.createElement("p");
            provenance.textContent = `${record.source.repository} · ${record.source.commit} · ${record.source.path} · ${record.license.id} · review pending`;
            const instructions = document.createElement("pre");
            instructions.textContent = record.instructionsText;
            content.replaceChildren(provenance, instructions);
            details.dataset.loaded = "true";
          } catch {
            content.textContent = "The pinned definition is unavailable. Reload or check the package integrity.";
          }
        });
        card.append(details);
      }
      return card;
    }));
  } catch {
    total.textContent = "— items";
    empty("Library unavailable", "Check that the local Nucleus API is running, then reload this page.");
  }
}

let timer;
search.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => { offset = 0; void load(); }, 180); });
kind.addEventListener("change", () => { offset = 0; void load(); });
previous.addEventListener("click", () => { offset = Math.max(0, offset - limit); void load(); });
next.addEventListener("click", () => { offset += limit; void load(); });
void load();
