---
title: "I wrote HNSW from scratch and found out I didn't need it"
description: "Benchmarking a from-scratch Python HNSW against FAISS and exact brute-force vector search on BEIR: below ~5,000 documents brute force wins by 10–18×, the query encoder dwarfs the index either way, and BM25+dense fusion (RRF) is the only statistically significant quality gain."
date: 2026-08-25
tags: ["search", "hnsw", "bm25", "vector-search", "benchmarks"]
---

On a corpus of 3,633 documents, exact brute-force search over numpy is
**10.9× faster** than the HNSW graph I spent a weekend implementing — HNSW
being the graph index inside most vector databases. On 5,183 documents it's
**18.3× faster**. Retrieval quality differences are under 0.0003 nDCG —
statistically indistinguishable.

That's partly a story about pure-Python graph traversal being slow, which it
is. The more interesting part is what FAISS does on the same two corpora:

| system (median/query) | NFCorpus (3,633 docs) | SciFact (5,183 docs) |
|---|---|---|
| `faiss-flat` (exact) | 0.153 ms | 0.237 ms |
| `faiss-hnsw` M=16, ef=256 | 0.135 ms | 0.323 ms |
| `mini-brute` (exact, mine) | 0.295 ms | 0.410 ms |
| `mini-hnsw` M=16, ef=256 | 3.227 ms | 7.517 ms |

On NFCorpus, optimized C++ HNSW came out ahead of optimized C++ exact search
in all three repeats (per-repeat means 0.136/0.138/0.159 ms against
0.167/0.161/0.164 ms) — but HNSW's own run-to-run spread is 0.023 ms, larger
than the 0.019 ms gap between the two systems' means, and p95 is 0.207
against 0.209. The variation within one system exceeds the difference
between them. On SciFact the flat index simply wins, by 1.36×.

So the graph costs over 500× more to build than the flat index it's meant to
accelerate (0.93 s against 0.0017 s), carries a stack of tuning parameters,
and at these corpus sizes buys nothing measurable in C++ and an order of
magnitude of loss in Python.

All four systems above retrieve at the same quality: nDCG@10 — ranking
quality, higher is better — between 0.3159 and 0.3162 on NFCorpus, and
0.6451 for every one of them on SciFact.

## What it is

[mini-search](https://github.com/sankalp021/mini-search) is a retrieval
engine with no retrieval libraries in the core:

- **BM25** over a hand-rolled inverted index — Lucene-style and BM25+
  variants, k1 and b swept
- **HNSW** — hierarchical navigable small world graph, from the paper
- **Reciprocal Rank Fusion** to combine the two ranked lists

FAISS, `bm25s` and `rank_bm25` appear only on the other side of the
benchmark. The repo enforces three rules on anything written into it: no
retrieval-library imports in core, no silent fallbacks, no benchmark numbers
that didn't come out of a run that actually executed.

It's retrieval, not RAG. There's no generation step and no claim about
answer quality.

## Is it correct, though

A performance finding from an implementation nobody has checked is worth
nothing. So, before any of the above:

**Against published BEIR baselines.** Dense retrieval with MiniLM-L6-v2
gives nDCG@10 of 0.3159 on NFCorpus against a published ~0.314, and 0.6451
on SciFact against ~0.645. My BM25 hits 0.6622 on SciFact against ~0.665.

On NFCorpus my BM25 lands at 0.3062 against a published ~0.325. I attribute
that 0.019 gap to tokenization — my analyzer has no stemming and no stopword
list — and my evidence for the attribution is that all three BM25
implementations I tested agree with each other to within 0.0036 while all
three sit below the published figure. That's evidence about *where* the gap
is, not about its size. I haven't built the stemmed variant to measure what
it recovers.

**Against FAISS directly.** Paired bootstrap over 323 queries, BH-corrected
across 36 pairs:

- `mini-brute` vs `faiss-flat`: d = +0.0000, p = 1.00
- `mini-hnsw` vs `faiss-flat`: d = +0.0002, p = 0.68
- `mini-bm25` vs `rank_bm25`: d = −0.0000030, p = 1.00

Indistinguishable everywhere, which is the correct result for a
reimplementation. Nobody should be pleased when their from-scratch version
wins.

**ANN recall against exact search**, sweeping efSearch — the knob that
trades query speed for recall — on NFCorpus:

| efSearch | mini-hnsw | faiss-hnsw |
|---|---|---|
| 16 | 0.9034 | 0.8755 |
| 32 | 0.9548 | 0.9430 |
| 64 | 0.9811 | 0.9740 |
| 128 | 0.9954 | 0.9904 |
| 256 | 0.9975 | 0.9985 |

Both converge cleanly toward exact, and mine sits marginally above FAISS at
low ef. My layer-0 link budget deviates deliberately from the paper's
Algorithm 1, tuned against clustered distributions, and I'd like to tell you
that's the cause — but the A/B between the two budgets only exists on
synthetic uniform vectors. I haven't run the paper-budget variant on BEIR,
so the deviation and the low-ef margin are two facts I can't yet connect.

The evaluation harness never imports the retriever it grades — boundary
tests parse the source tree to enforce exactly that — and it earned its
independence: it fired a coverage gate at my BM25 and accused it of dropping
25 of 323 queries. The BM25 was fine — those queries were single rare terms
absent from the entire 26,359-term corpus vocabulary, so it correctly
returned nothing. The harness couldn't distinguish *found nothing* from
*crashed*, which is a real gap and one I'd never have found by reading my
own code. Fixing it made my published numbers worse, which is how you know
it was a real fix.

## So why does brute force win

Nothing surprising once you write it down. Exact search over 3,633 documents
at 384 dimensions is a single dense matmul — 1,395,072 multiply-adds, which
BLAS does without noticing. HNSW replaces that with a graph traversal:
pointer chasing, per-node distance computations, a priority queue, none of
it vectorized, all of it paying full interpreter overhead per hop in Python
and per cache miss in C++.

The graph wins when the linear scan is long enough that skipping most of it
beats the cost of navigating. At a few thousand documents the scan isn't
long enough to be worth skipping.

**I don't know where the crossover is.** I tested two corpora, 3,633 and
5,183 documents. In both my implementation and FAISS, the gap moved
*further* in brute force's favour on the larger one — which is obviously not
the asymptotic behaviour, since ANN indexes exist and work. Two corpora also
differ in more than size: different documents, different vector
distributions, different degrees of clustering. So that widening is an
observation about these two datasets and not a trend I'm entitled to extend.

What the data does support: the flip hasn't happened by 5,183 documents. A
lot of production vector stores are smaller than that and are running an
index that isn't earning its keep.

## The number that dwarfs all of this

Query embedding on NFCorpus: **25.8 ms**, against 0.295 ms for the exact
search it feeds.

The encoder is 87× the cost of the retrieval step. Every argument in this
post about index structure is happening two orders of magnitude below the
noise floor of the thing that runs immediately before it. If you're
optimizing a vector search stack at this scale and you haven't profiled the
encoder first, you're optimizing the wrong end.

## The one thing that actually helped

RRF fusion of BM25 and dense retrieval is the only statistically significant
quality gain in the project, and it holds on both datasets against every
other system:

| | NFCorpus nDCG@10 | SciFact nDCG@10 |
|---|---|---|
| `mini-hybrid` (RRF, k=60) | **0.3423** | **0.6969** |
| best single method | 0.3162 (`mini-hnsw`) | 0.6644 (`bm25s`) |

Against `faiss-flat`: d = +0.0264, p = 0.0045 on NFCorpus; d = +0.0518,
p = 0.0009 on SciFact.

Two mediocre rankers disagreeing productively beat either alone, and the
fusion step costs 7.36 microseconds. Everything expensive in this project
turned out indistinguishable from its reference implementation. The cheap
thing was the win.

## What I'd flag if I were reading this critically

- **Two datasets, one machine, one embedding model.** The corpus-size claim
  rests on two points and the shape of an argument.
- **No significance test on latency.** The quality comparisons are
  bootstrapped; the timing comparisons are medians over repeats with the
  spread reported. The NFCorpus "within noise" read compares spreads and
  means, not a test result.
- **The expensive HNSW builds are single samples.** I've measured
  M=16/efc=200 on NFCorpus at 270.0 s, 95.4 s and 216.0 s across three runs
  and can't currently explain the spread. Build-cost ratios here are
  approximate to within roughly a factor of two.
- **All latency figures are single-threaded.** Brute force is a BLAS call
  and scales with cores; graph traversal doesn't. Unpinning threads should
  widen the gap in brute force's favour — I haven't measured it, so I'm not
  claiming it.
- **No stemming, no stopwords.** See the reconciliation section; the
  attribution is defensible, the magnitude is inferred.

## Reproducing it

```
git clone https://github.com/sankalp021/mini-search
cd mini-search
python -m benchmarks.runs --dataset nfcorpus --depth 10
python -m eval_harness score \
  --qrels data/beir/nfcorpus/qrels/test.tsv \
  --runs results/runs/nfcorpus/k10 \
  --exact results/runs/nfcorpus/k10/faiss-flat.run \
  --recall-k 10 --ndcg-k 10 --ann-recall-k 10 \
  --out results/nfcorpus/k10
```

Every run file carries a sidecar, and every report a provenance block, which
between them record the corpus, qrels and query hashes, the embedding model
revision, thread count, bootstrap seed, platform, and the numpy and Python
versions the numbers were produced under. 328 tests. If a figure in the
README doesn't come out of your machine, I'd like to know.

*Next weekend: a write-ahead log, memory-mapped segments and crash
recovery — the serialization boundary and stable internal document IDs have
been in place since day one for exactly this.*
