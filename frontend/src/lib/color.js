// Pick two background colours: from the album art when it can be sampled,
// otherwise a stable hue derived from the song title.

function hsl(h, s, l) { return `hsl(${Math.round(h)} ${s}% ${l}%)`; }

export function hashPalette(text = '') {
  let h = 0;
  for (let i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) >>> 0;
  const hue = h % 360;
  return [hsl(hue, 70, 38), hsl((hue + 55) % 360, 65, 30)];
}

export function artworkPalette(url) {
  return new Promise((resolve) => {
    if (!url) return resolve(null);
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      try {
        const c = document.createElement('canvas');
        c.width = c.height = 24;
        const ctx = c.getContext('2d', { willReadFrequently: true });
        ctx.drawImage(img, 0, 0, 24, 24);
        const d = ctx.getImageData(0, 0, 24, 24).data;
        const buckets = [];
        for (let i = 0; i < d.length; i += 4) {
          const r = d[i], g = d[i + 1], b = d[i + 2];
          const max = Math.max(r, g, b), min = Math.min(r, g, b);
          const sat = max === 0 ? 0 : (max - min) / max;
          if (max < 40) continue;                 // too dark
          buckets.push({ r, g, b, score: sat * 2 + max / 255 });
        }
        if (!buckets.length) return resolve(null);
        buckets.sort((a, b) => b.score - a.score);
        const pick = (x) => `rgb(${x.r}, ${x.g}, ${x.b})`;
        const a = buckets[0];
        const b = buckets.find((x) => Math.abs(x.r - a.r) + Math.abs(x.g - a.g) + Math.abs(x.b - a.b) > 120) || buckets[Math.floor(buckets.length / 2)];
        resolve([pick(a), pick(b)]);
      } catch { resolve(null); }
    };
    img.onerror = () => resolve(null);
    img.src = url;
  });
}
