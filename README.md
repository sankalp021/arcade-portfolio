# SANKALP ARCADE

Retro-arcade portfolio + dev log for Sankalp Chaturvedi. Built with
[Astro](https://astro.build) — zero extra dependencies, blog posts are plain
markdown files.

## Run it locally

Requires **Node.js 22+** (Astro 7 minimum).

```bash
npm install
npm run dev      # → http://localhost:4321
```

`npm run build` outputs a static site to `dist/`.

> Stuck on an older Node? `npm i astro@^5` runs this exact codebase too
> (same content-collections API), on Node 18.17+.

## Deploy (once)

1. Create a GitHub repo and push this folder:
   ```bash
   git init && git add -A && git commit -m "insert coin"
   git branch -M main
   git remote add origin git@github.com:YOUR-USERNAME/sankalp-arcade.git
   https://github.com/sankalp021/arcade-portfolio.git
   git push -u origin main
   ```
2. Go to [vercel.com/new](https://vercel.com/new), import the repo. Vercel
   auto-detects Astro — just hit Deploy.
3. Every push to `main` now deploys automatically.

## Publishing blog posts

Posts live in `src/content/blog/`. One markdown file = one post. The filename
is the URL slug. See `_template.md` for the frontmatter fields.

**The pipeline:** write the post in markdown → commit to `main` → Vercel
rebuilds → live in ~a minute. No CMS, no admin panel.

## SEO / discoverability

All of this is dependency-free (hand-rolled endpoints, no integrations):

- `src/pages/sitemap.xml.ts` — sitemap, auto-includes every published post
- `src/pages/rss.xml.ts` — RSS feed for the dev log
- `public/robots.txt` — crawlers welcome, points at the sitemap
- `public/llms.txt` — site summary for AI search engines
- `public/og.png` — social-share card (regenerate with a pixel-font script if
  the tagline ever changes)
- `src/layouts/Base.astro` — canonical URLs, Open Graph / Twitter meta, and
  JSON-LD structured data (Person + WebSite on home, BlogPosting on posts)

## Notes

- Your phone number is deliberately **not** on the site (public internet +
  phone numbers = spam). Add it only if you want it.

## Design notes

- Tokens (colors, fonts, pixel size) live at the top of
  `src/styles/global.css`. Change `--gold` / `--red` / `--green` / `--cyan`
  to re-skin the whole site.
- Display font: Press Start 2P. Body: VT323 at 21px. If you ever want calmer
  reading on blog posts, swap the font inside `.prose` only.
- All pixel art is original inline SVG — era-inspired, no Nintendo/Namco
  assets, keep it that way.
- `prefers-reduced-motion` disables the walker, blink, and coin spin.
