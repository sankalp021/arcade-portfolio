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

**The pipeline:** draft a post with Claude in chat → give the green flag →
Claude commits the `.md` file to this repo via the GitHub connector → Vercel
rebuilds → live in ~a minute.

## TODO before going live

Search the codebase for `TODO`:

- [ ] `astro.config.mjs` — set `site` to your deployed URL
- [ ] `src/pages/index.astro` — real GitHub / LinkedIn profile URLs (contact
      section) and DEMO / CODE links on both project cabinets
- [ ] Optional: your phone number is deliberately **not** on the site
      (public internet + phone numbers = spam). Add it only if you want it.

## Design notes

- Tokens (colors, fonts, pixel size) live at the top of
  `src/styles/global.css`. Change `--gold` / `--red` / `--green` / `--cyan`
  to re-skin the whole site.
- Display font: Press Start 2P. Body: VT323 at 21px. If you ever want calmer
  reading on blog posts, swap the font inside `.prose` only.
- All pixel art is original inline SVG — era-inspired, no Nintendo/Namco
  assets, keep it that way.
- `prefers-reduced-motion` disables the walker, blink, and coin spin.
