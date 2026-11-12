// In dev (vite :5173) talk to the Flask backend; in production it's same-origin.
export const BACKEND =
  import.meta.env.DEV && location.port === '5173' ? 'http://localhost:5000' : '';

export const post = (path, body) =>
  fetch(`${BACKEND}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body ?? {}),
  }).then((r) => r.json());

export const get = (path) => fetch(`${BACKEND}${path}`).then((r) => r.json());

// Backend-proxied cover art comes back as a relative path
export const artSrc = (u) => (u && u.startsWith('/') ? `${BACKEND}${u}` : u || '');
