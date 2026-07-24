// frontend/src/api/client.js
// Every fetch call lives here, one function per endpoint.

async function get(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function fetchSummary() {
  return get("/api/summary");
}

export function fetchBrands() {
  return get("/api/brands");
}

export function fetchBrand(brand) {
  return get(`/api/brands/${encodeURIComponent(brand)}`);
}
