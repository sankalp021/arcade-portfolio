import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';

const escapeXml = (s: string) =>
  s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');

// Hand-rolled RSS feed — keeps the site dependency-free.
export const GET: APIRoute = async ({ site }) => {
  const base = (site ?? new URL('https://snklp.dev')).href.replace(/\/$/, '');
  const posts = (await getCollection('blog', ({ data }) => !data.draft)).sort(
    (a, b) => b.data.date.valueOf() - a.data.date.valueOf()
  );

  const items = posts
    .map(
      (p) => `    <item>
      <title>${escapeXml(p.data.title)}</title>
      <link>${base}/blog/${p.id}</link>
      <guid isPermaLink="true">${base}/blog/${p.id}</guid>
      <pubDate>${p.data.date.toUTCString()}</pubDate>
      <description>${escapeXml(p.data.description)}</description>
    </item>`
    )
    .join('\n');

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Sankalp Chaturvedi — Dev Log</title>
    <link>${base}/blog</link>
    <atom:link href="${base}/rss.xml" rel="self" type="application/rss+xml" />
    <description>Research notes and write-ups on backend engineering, data pipelines, agentic AI, and whatever else is currently under investigation.</description>
    <language>en</language>
${items}
  </channel>
</rss>
`;

  return new Response(body, {
    headers: { 'Content-Type': 'application/rss+xml; charset=utf-8' },
  });
};
