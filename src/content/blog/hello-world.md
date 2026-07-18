---
title: "Hello, World — Insert Coin"
description: "Why this site exists, what gets written here, and the no-CMS publishing setup behind it."
date: 2026-07-18
tags: ["meta"]
---

Player one has entered the game.

This site is two things: a portfolio, and a **dev log** — a place to write up
whatever I happen to be digging into. Some of it comes straight from work,
some of it is a side quest, and some of it is just a rabbit hole that looked
too interesting to walk past. Expect entries on:

- Agentic AI workflows — what actually works outside of demos
- Elasticsearch and Kibana at scale, and the reporting pipelines behind them
- RAG, vector databases, and LLM integration patterns
- FastAPI backends and the occasional data-debugging war story
- …and honestly, anything else I end up researching. The log follows
  curiosity, not the résumé.

## The publishing setup

There is no CMS here, and no admin panel. Every post is a markdown file in a
Git repo. Writing an entry means writing markdown; publishing it means
`git push`. Vercel notices the commit, rebuilds the site, and the post is
live about a minute later.

That's the whole pipeline. Fewer moving parts than the coin counter in the
corner of this site.

More entries soon. Grab a coin on your way out.
