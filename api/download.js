// api/download.js
// Uses cobalt's public API directly - no setup needed

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'method not allowed' });

  const { url, downloadMode, audioFormat, videoQuality } = req.body || {};
  if (!url) return res.status(400).json({ error: 'missing url' });

  // Try multiple public cobalt instances in order
  const instances = [
    'https://api.cobalt.tools',
    'https://cobalt.api.timelessnesses.me',
    'https://co.wuk.sh',
  ];

  let lastError = 'all cobalt instances failed';

  for (const base of instances) {
    try {
      const r = await fetch(base, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          url,
          downloadMode: downloadMode || 'auto',
          audioFormat:  audioFormat  || 'mp3',
          videoQuality: videoQuality || '1080',
          filenameStyle: 'pretty',
          tiktokFullAudio: true,
        }),
        signal: AbortSignal.timeout(9000),
      });

      const text = await r.text();
      let data;
      try { data = JSON.parse(text); } catch { lastError = `bad response from ${base}`; continue; }

      // Cobalt returns status: tunnel/redirect/error/picker
      if (data.status === 'error') { lastError = data.error?.code || 'cobalt error'; continue; }
      if (data.status === 'tunnel' || data.status === 'redirect' || data.url) {
        return res.status(200).json(data);
      }
      // picker = multiple streams (e.g. tiktok with separate audio/video)
      if (data.status === 'picker') {
        return res.status(200).json(data);
      }

      lastError = `unexpected status: ${data.status}`;
    } catch (e) {
      lastError = e.message.includes('timeout') ? `${base} timed out` : e.message;
      continue;
    }
  }

  return res.status(502).json({ error: lastError });
}
