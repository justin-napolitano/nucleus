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
      empty(data.total ? "No matches on this page" : "Your Library starts empty", data.total ? "Try another search or return to the first page." : "Add reviewed registry packages to make domains, products, skills, workflows, and tools discoverable here.");
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
