const BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000/api";
let token = "";
let onUnauthorized = () => {};

export const setToken = (value) => {
  token = value || "";
};

export const setUnauthorizedHandler = (fn) => {
  onUnauthorized = fn;
};

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  const text = await response.text();

  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    /* not JSON */
  }

  if (!response.ok) {
    if (response.status === 401 && !path.startsWith("/auth/login")) {
      onUnauthorized();
    }

    throw new Error(
      typeof data?.detail === "string"
        ? data.detail
        : `Request failed (${response.status})`,
    );
  }

  return data;
}

export const api = {
  get: (p) => request(p),

  post: (p, body) =>
    request(p, {
      method: "POST",
      body: JSON.stringify(body ?? {}),
    }),

  put: (p, body) =>
    request(p, {
      method: "PUT",
      body: JSON.stringify(body ?? {}),
    }),

  patch: (p, body) =>
    request(p, {
      method: "PATCH",
      body: JSON.stringify(body ?? {}),
    }),

  delete: (p) =>
    request(p, {
      method: "DELETE",
    }),
};
