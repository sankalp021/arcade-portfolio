import type { APIRoute } from 'astro';
import { getCollection } from 'astro:content';

// Hand-rolled sitemap — keeps the site dependency-free.
export const GET: APIRoute = async ({ site }) => {
  const base = (site ?? new URL('https://snklp.dev')).href.replace(/\/$/, '');
  const posts = (await getCollection('blog', ({ data }) => !data.draft)).sort(
    (a, b) => b.data.date.valueOf() - a.data.date.valueOf()
  );

  const day = (d: Date) => d.toISOString().split('T')[0];
  const newest = posts[0]?.data.date;

  const urls: { loc: string; lastmod?: string }[] = [
    { loc: `${base}/`, lastmod: newest && day(newest) },
    { loc: `${base}/blog`, lastmod: newest && day(newest) },
    ...posts.map((p) => ({ loc: `${base}/blog/${p.id}`, lastmod: day(p.data.date) })),
  ];

  const body = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls
  .map(
    (u) =>
      `  <url><loc>${u.loc}</loc>${u.lastmod ? `<lastmod>${u.lastmod}</lastmod>` : ''}</url>`
  )
  .join('\n')}
</urlset>
`;

  return new Response(body, {
    headers: { 'Content-Type': 'application/xml; charset=utf-8' },
  });
};
