// api/info.js
// Fetches YouTube video/playlist metadata using oEmbed + YouTube's no-auth APIs

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(204).end();

  const { url } = req.query;
  if (!url) return res.status(400).json({ error: 'missing url' });

  // Extract video ID from various YouTube URL formats
  const videoIdMatch = url.match(
    /(?:youtube\.com\/(?:watch\?v=|shorts\/|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/
  );
  const playlistIdMatch = url.match(/[?&]list=([a-zA-Z0-9_-]+)/);

  if (!videoIdMatch && !playlistIdMatch) {
    return res.status(400).json({ error: 'could not parse YouTube URL' });
  }

  try {
    if (videoIdMatch) {
      const videoId = videoIdMatch[1];

      // oEmbed gives us title + thumbnail for free, no API key needed
      const oEmbed = await fetch(
        `https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`
      );
      if (!oEmbed.ok) return res.status(404).json({ error: 'video not found or unavailable' });
      const oe = await oEmbed.json();

      return res.status(200).json({
        type:      'video',
        videoId,
        title:     oe.title,
        author:    oe.author_name,
        thumbnail: `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`,
        url:       `https://www.youtube.com/watch?v=${videoId}`,
      });
    }

    if (playlistIdMatch) {
      const listId = playlistIdMatch[1];
      // For playlists we just return basic info — full playlist would need API key
      return res.status(200).json({
        type:     'playlist',
        listId,
        title:    'YouTube Playlist',
        url:      `https://www.youtube.com/playlist?list=${listId}`,
        note:     'Playlist detected — videos will be downloaded one at a time.',
      });
    }
  } catch (e) {
    return res.status(502).json({ error: e.message });
  }
}
