# CODEX MASTER EXECUTION PROMPT — HOODOOMART

> Paste this prompt into Codex from the repository root. Copy the provided course slides into `docs/reference/PTTKHT-Slides.pdf` (and optionally the revised Markdown specification to `docs/reference/Multimodal-Search-Spec.md`) first. If these files are not present, report that fact and use the requirement baseline below without pretending to have read missing files.

## 0. Your role, goals, and operating rules

You are the technical lead, senior full-stack engineer, search/ML engineer, data engineer, UX designer, test engineer, and technical writer for **HoodooMart**. Build a real, runnable, well-tested, Vietnamese-first e-commerce web application whose central deliverable is **multimodal product discovery: Vietnamese text, Vietnamese voice, and product-image search**, with browse, product detail, cart and authenticated order lookup. Build correct foundations for seller/admin and simulated commerce workflows, but do not divert effort away from the assignment's working search demo.

**Non-negotiable working method:**
1. Inspect the existing repository, installed AGENTS.md, skills and existing app before deciding anything. Follow project-local instructions and reuse functioning code. Do not overwrite work. Apply installed skills when relevant (`frontend-design`, `storefront-best-practices`, `vercel-react-best-practices`, `shadcn`, `fastapi`, `supabase-postgres-best-practices`, `internationalization-i18n`, `webapp-testing`). Use skills critically; do not change our FastAPI architecture to Medusa just because a skill mentions Medusa.
2. Read `docs/reference/PTTKHT-Slides.pdf` as the main course specification. Distinguish **requirements directly supported by the slides** from **new engineering decisions** in documentation. The slides call the old demo "Lumina"; the new project brand is **HoodooMart**, not a silent change to its business rules. The course presentation demonstrates 1,148 products in 34 leaf categories (4 top-level and 11 intermediate), but that source dataset is not automatically available to this repository. Never invent or claim to have obtained the Tiki records.
3. Start by producing `docs/IMPLEMENTATION_PLAN.md`, `docs/REQUIREMENTS_TRACEABILITY.md`, `docs/ARCHITECTURE.md`, `docs/DATA_SOURCES.md`, `docs/DECISIONS.md` and a prioritized issue checklist. Inspect first; THEN implement the first working vertical slice, rather than delivering only a plan. Make small, independently testable changes. Run actual checks after each stage. Keep reporting what is genuinely working versus incomplete.
4. All customer-facing UI, messages, product names, filters and price formats must be natural **Vietnamese (vi-VN)**; use VND integer values and show `499.000 ₫`. Support Vietnamese with diacritics, without diacritics, and mixed English product terms. Code identifiers/documentation may be English.
5. **Zero required paid APIs.** Default `LOCAL_ONLY=true`, no paid LLM, ASR, embeddings, images, voice, email, shipping or payment services; no automatic charges, billing signup or silent external inference. Open-source weights can be downloaded once with user approval, subject to license. Local inference still consumes CPU/RAM/electricity, and deployment/storage may cost money; document this truthfully.
6. If hardware is unknown, design a baseline running on **Windows + PowerShell + Docker Desktop + CPU** (without assuming NVIDIA/AMD GPU). Keep optional GPU providers behind interfaces. Heavy models must not start in every API worker. Provide safe quality/performance degradation and graceful user-visible fallback.
7. Never fake functionality or label a deterministic rule as "AI". A simulated adapter must be clearly marked `demo/mock`, separately testable, and never promoted as genuine voice/image understanding. Core search must have a fully working no-paid-API mode.
8. Dataset data, product images and reviews require explicit provenance, license verification, rights assessment and suitability for the target use. "Public on the internet" is not permission to republish. Preserve original source IDs. No scraping blocked endpoints or evasion. Do not publish restricted/unknown-rights content; provide manually authored or explicitly approved demo fixtures while license checks are unresolved.
9. Use secure defaults: protect customer orders by ownership check; keep uploaded media temporary; validate actual file content; no plaintext passwords, committed tokens, hard-coded demo admin credentials in public deployments, or real card handling.
10. If a genuine blocker requires one decision, ask the user precisely, offer a safe default, and continue unblocked parts. Do not ask broad open-ended questions before writing code.

## 1. Source-of-truth scope and traceability

The slides describe a marketplace with seven actors: **Customer, Seller, Admin, Customer Service Staff, Finance Staff, Payment Gateway, Shipping Provider**. They analyze ordering, stock reservation, simulated payment/escrow, shipping, disputes and reporting as context, but their **implemented prototype concentrates on searching and looking up orders**. Reflect this distinction in an explicit implementation scope:

- **P0 (must work end-to-end):** Vietnamese storefront, 3 input modes, product catalogue/detail, category browsing and price filter, customer registration/login, demo cart, demo order lookup, search history with privacy controls, admin-controlled catalogue import/verification, reproducible test fixtures.
- **P1 (functional safe demo):** reserve stock transactionally on order placement, COD/mock payment only, cancel and release stock, customer-owned order tracking, seller/admin catalogue CRUD with RBAC, demo order status progression. Do not call this a real escrow or actual payment gateway.
- **P2 (design and extension points, not fabricated as working):** seller finance reconciliation, escrow disputes, integration with real payment providers/carriers, personalization based on real feedback, large-scale deployment. Write interfaces/contracts, but prioritize P0 acceptance.

Honor the slide's **five canonical black-box cases**:
- **TC1 text:** query `áo len nam màu đen dưới 500k` extracts category = `áo len nam`, color = `đen`, upper price = 500000 VND. Slide's original seeded dataset yields **10** results and top three: áo len nam cổ tròn dệt kim 264000, áo len nam cổ lọ 324000, áo len gilê nam 456000. Implement a deterministic **test fixture** that reproduces the course scenario exactly (without pretending those items came from a fetched real dataset). In the real changing catalogue assert invariants/quality rather than hardcoding 10.
- **TC2 voice:** spoken `tôi muốn mua áo mùa đông` becomes an editable Vietnamese transcript, identifies the relevant clothing categories, treats `mùa đông` as a **soft preference**, prioritizes suitable insulated/winter products, preserves `modality=voice`.
- **TC3 image:** uploaded photo of a navy sweater retrieves visually similar **published** catalogue items; a suitable men's sweater should be competitive at the top for a curated judged fixture. No claim of "understanding" if only histogram fallback is active.
- **TC4 low-result relaxation:** `túi đeo chéo màu đỏ dưới 150k` with curated fixture can expand to three bags by relaxing the **inferred** color constraint; category and price stay fixed; explain the relaxation and keep red bag (95000 VND in the fixture) ranked higher based on its soft preference.
- **TC5 order search:** `kiểm tra đơn hàng 20261005` routes to **order lookup, NOT product search**, showing a seeded customer-owned `CONFIRMED` order with áo sơ mi tay dài (115500) + quần tây nam (595000), total 710500 VND. This exact order and prices are **fixture-only**, not claims about any real order. Another user or anonymous visitor must NOT obtain this order's details. Nonexistent/unauthorized requests must not reveal whether another person's order exists.

**Additional test TC6:** text/voice/image searches and order lookup are read-only, do not mutate product, stock, cart, order or payment state. Preserve search-history storage as a separate, privacy-aware, bounded analytics side effect, with history writes asynchronous/best-effort, and never on critical search latency path.

**Non-negotiable search business rules (from slides):**
- Published catalogue is authoritative for name, category, price, availability; never infer price or stock from semantic similarity.
- **Hard filters:** category incl. descendant categories; brand, price range, color, material, gender when explicitly requested or inferred with high confidence. UI-selected category and price take priority over natural-language extraction.
- **Soft preferences:** season, occasion, style, warmth. These influence ranking but never exclude products.
- If fewer than **3 candidates**, relax eligible **inferred** hard filters *one by one* in this sequence: `material → color → brand → gender → price`; **never relax category**; never relax explicit UI-selected conditions. Treat each relaxed criterion as a soft preference and communicate the exact changed filter in results. Make this deterministic and testable. Explicit textual constraints need provenance (`explicit_text`, `inferred`, `ui_selected`) and explicit user-selected constraints must not be loosened. Clarify where a course rule could otherwise weaken user intent; document the chosen safety-preserving interpretation.
- Ranking priority: primary query/image relevance, then preference matching; only when relevance is close use credible sales and rating signals. Out-of-stock products stay visible but rank lower and cannot be added to cart. Stable deterministic tie-breakers and normalized, meaningful scores; do not fabricate sold counts/ratings.
- Three input modalities converge to a common `QueryRepresentation` / retrieval/filter/ranking/result pipeline, with swappable `QueryParser`, `SpeechToText`, `ImageEncoder`, `KeywordIndex`, `VectorIndex` adapters.

## 2. Architecture and project organization

Prefer a **modular monolith** with one frontend, one API, one offline indexing/ASR inference worker if needed, and one PostgreSQL instance; no Kubernetes, microservices, Redis, Celery, Kafka, Elasticsearch or extra cloud services by default. Only add them when benchmarks demonstrate a bottleneck.

Suggested stack (verify compatibility and pin tested versions):
- FE: **Next.js App Router + React + TypeScript + Tailwind + shadcn/ui**, accessible design, Zod form validation, lightweight fetch client and clear server/client component boundaries.
- BE: **Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic**, async IO for database/API calls and bounded isolated threads/processes for CPU-heavy inference. `pytest`, `httpx`, `ruff`, type checking.
- Database: **PostgreSQL** with `pg_trgm` and `unaccent` (or equivalent controlled normalization), optional **pgvector** for vector columns; SQLAlchemy/Alembic-owned schema. Numeric VND values use `BIGINT` (integers), not binary float. Adopt real monetary types/config only where mathematically correct.
- Media: development filesystem or local MinIO (optional); data stored with approved rights, digest, MIME, dimensions, safe local path. Do not store large raw images/audio in PostgreSQL.
- Integration: OpenAPI-derived, typed frontend API client; JSON structured responses; Docker Compose for postgres/API/FE, optionally inference worker. Work with Windows PowerShell commands.

Layer contracts (adapt the slide's 3 layers and packages, without violating actual dependency inversion):
- Presentation/API routes and frontend UI handle inputs and output but **cannot import database repositories directly**.
- Application services (`SearchOrchestrator`, `QueryService`, `SearchService`, `RankingService`, `ProductService`, `OrderLookupService`) orchestrate use cases and depend on abstract repository/encoder contracts.
- Domain defines `Product`, `Category`, `QueryRepresentation`, `SearchResult`, `FilterConstraint`, `Offer`, and invariants.
- Infrastructure/data layer implements SQL persistence, keyword & vector indexes, local media, datasets, and ML model adapters. Dependencies must not point from domain to UI/infrastructure. Use dependency injection to swap providers.

Suggested layout:
```
hoodoomart/
  AGENTS.md
  docs/
    reference/
    IMPLEMENTATION_PLAN.md
    ARCHITECTURE.md
    REQUIREMENTS_TRACEABILITY.md
    DATA_SOURCES.md
    DATA_DICTIONARY.md
    API_CONTRACTS.md
    BENCHMARKS.md
    DECISIONS.md
    RUNBOOK.md
  apps/
    web/                         # Next.js storefront/admin
    api/
      app/
        api/v1/                 # routers/auth/search/catalog/orders/admin
        domain/                 # entities, datatypes, ports
        application/            # orchestrators, services, policies
        infrastructure/         # sqlalchemy repos, search adapters, media, ML
        core/                   # config, security, observability
      alembic/
      tests/
  data_pipeline/
    adapters/                   # CAMEO, FashionSmall, WomensFashion, VNFashion
    ingest/ normalization/ qc/ indexing/
  benchmarks/
    fixtures/ qrels/ audio/ images/ scripts/
  infra/
    docker-compose.yml
  scripts/
  .env.example
  README.md
```
Adapt naming to existing repository rather than forcibly replacing it. Create root `AGENTS.md` with architecture boundaries, run/test commands, Vietnamese UI and safe-data rules.

## 3. Frontend: implement an actual Vietnamese e-commerce application

**Visual design:** modern, polished, credible, clean and mobile-first; attractive yet restrained editorial e-commerce design, consistent product imagery and spacing, readable Vietnamese typography, accessible color contrast and semantic landmarks. Avoid generic template clutter, fake urgency, fake ratings, arbitrary counts, placeholder CTAs and non-working buttons. Use local icons, optimized images, no required paid stock-image API. LCP image not lazily loaded; below-fold images lazy load.

**Pages and workflows:**
1. `/`: announcement/navigation, persistent unified search control (text field + mic + image upload), category hierarchy, product showcases fed from API (not hardcoded), new/featured sections only if data supports them, footer.
2. `/products`: server-side paginated product grid (12-24/page), deep-linkable URL filters, category tree, price min/max, gender, color, brand, material when known; sort relevance/newest/price; search term and active filters visible, mobile filter drawer, empty and loading states.
3. `/products/[slug]`: image gallery with zoom, verified attributes, brand, offers/price VND, stock, selectable sizes/variants, quantity validation and add-to-cart; missing data displayed as unavailable, not guessed.
4. `/search`: unified results with visibly distinct TEXT/VOICE/IMAGE mode, normalized transcript/image preview, interpreted hard/soft chips, results count, relaxed-filter explanation, facet controls, links to product detail, meaningful no-match and retry states. Every filter must actually change backend results and preserve URL state. Preserve explicit selections.
5. `/cart`: quantities, remove, subtotal, empty state; backend validation at checkout. Optional guest cart persisted client-side then reconciled on login.
6. `/auth/login`, `/auth/register`, `/account/orders`, `/account/orders/[id]`, `/orders/lookup`: accessible auth, user's orders only, no IDOR.
7. `/admin/*` behind RBAC: catalog review and publish controls, upload/import batch status, data quality warnings, seller offer/stock management, demo order view. Implement only what current milestone supports; visible but unimplemented features must be clearly disabled and documented.

**Search control specifics:**
- Keyboard text submit Enter and button; debounce suggestions ~250ms, cancel stale requests with AbortController. Do not fire expensive semantic inference on every keystroke. Search button and explicit submit invoke semantic pathway.
- Mic permission requested only on click. Recording indicator, stop/cancel, duration limit ~10-15 seconds for a product query, error for unsupported/insecure browser; show transcribed text for correction and require user action to search after correction if recognition is uncertain. Never autoplay the mic.
- Image upload drag/drop/file picker, preview, file size/type feedback, validation errors, processing spinner, cancel/retry; optional accompanying text/category controls; never silently store user image long-term.
- Responsive layouts 360px/768px/desktop; keyboard navigation and focus states; toasts for cart; accessible labels; meaningful Vietnamese validation/error messages; `Intl.NumberFormat('vi-VN', {style:'currency', currency:'VND',maximumFractionDigits:0})`.
- Strong UI states: skeletons, loading, empty, success, errors, offline/service-unavailable, slow search; no dead-end pages.

## 4. Backend: API, business behavior, security

Create FastAPI `/api/v1` routes with Pydantic request/response schemas and auto-generated OpenAPI. At minimum:
```
GET  /health/live
GET  /health/ready
GET  /api/v1/categories
GET  /api/v1/products?page=&page_size=&category=&sort=&...
GET  /api/v1/products/{id_or_slug}
POST /api/v1/search/text
POST /api/v1/search/voice          # multipart audio
POST /api/v1/search/image          # multipart image + optional text/filters
GET  /api/v1/search/suggestions?q=
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/me
GET  /api/v1/me/orders
GET  /api/v1/me/orders/{order_id}
POST /api/v1/orders/lookup         # authenticated, recognizes order intent
GET/POST/PATCH /api/v1/cart       # define consistent request shapes
POST /api/v1/orders               # demo checkout with stock reservation
GET  /api/v1/admin/import-batches # RBAC
```
Route order-intent text `kiểm tra đơn hàng <code>` to `OrderLookupService` after authenticated owner check; return a typed discriminated `search_type='order'` response. Do not leak order details through a general product API. Ensure search results display only `published=true` items with valid source/rights status.

Required cross-cutting concerns: request IDs, JSON logs, safe exception handling, input validation, query timeouts, per-user/request size limits, rate limiting for CPU-heavy routes, pagination ceiling, response bounds, safe CORS, session/JWT with secure cookie strategy, password hashing Argon2, RBAC, CSRF consideration where cookies are used, simple bot/rate limits, parameterized queries, schema migrations, env-only secrets, no plaintext password logging. Review OWASP upload guidelines: extension/MIME/magic-byte verification, safe decode and re-encode images, decompression-bomb prevention, pixel limits, max bytes, filename randomization, temporary storage outside public webroot and TTL cleanup. Audio accepted only from a documented whitelist; short clip length limits, no arbitrary URL fetch/SSRF.

Make stock reservation atomic with a database transaction and conditional update/row locks; enforce quantity non-negative and idempotency for order creation; do not equate cart addition with stock reservation; checkout revalidates live price + availability. Real online card/payment/escrow are out of P0/P1; labeled mock statuses only.

## 5. Database design (migration-first)

Define at minimum, with primary/foreign keys, constraints and indexes:
- `data_sources(id, name, version, license, rights_status, allowed_use, last_checked_at)`
- `import_batches(id, source_id, started_at, status, counts, errors)`
- `source_products(source_id, external_id, raw_json, raw_hash, imported_at, batch_id)` unique `(source_id,external_id)` where stable ID is available
- `products(id, slug, name_vi, original_name, description_vi, category_id, brand_id_nullable, gender_nullable, publication_status, verification_status, created_at, updated_at)`
- `product_sources(product_id,source_id,external_id,field_provenance)`
- `categories(id,parent_id,slug,name_vi,level,sort_order)` supports 4 > 11 > 34 demo hierarchy, arbitrary descendants
- `product_attributes(product_id,attribute_key,canonical_value,display_value_vi,confidence,review_status,provenance)` or typed indexed columns + validated JSONB; dynamic attrs cannot silently become verified facts
- `product_images(id,product_id,variant_id_nullable,storage_key,sha256,phash,width,height,license_status,is_primary,model_version_nullable)`
- `product_variants(id,product_id,sku,size,color,option_values,status)` unique SKU as appropriate
- `seller_offers(id,product_id,variant_id,seller_id,price_vnd,original_price_vnd_nullable,price_kind,seller_verified,active,updated_at)` with price_kind in `(demo,merchant_verified,source_historical)`; no checkout with source_historical
- `inventory(offer_id,on_hand,reserved,updated_at,version)` with `on_hand>=0`, `reserved>=0`, `reserved<=on_hand`
- `users`, `seller_profiles`, `roles` / `user_roles`, `carts`, `cart_items`, `orders`, `order_items`, `stock_reservations`, `mock_payments`, `shipments_demo`
- `search_queries(id, user_id_nullable, modality, raw_query_nullable, normalized_query, filters_json, soft_preferences_json, created_at, ttl_or_retention_policy, latency_ms_nullable)`
- `search_results(query_id,product_id,rank,score)` unique `(query_id,rank)` and `(query_id,product_id)`; do not denormalize mutable product name/price here (separate order item purchase snapshots are appropriate)
- `text_embeddings(product_id, model_name, model_revision,content_hash, vector, indexed_at)` and `image_embeddings(image_id,model_name,model_revision,content_hash,vector,indexed_at)` with dimension matching chosen model; never mix vectors of incompatible models.

Create constraints, real foreign keys, appropriate cascade policy, check constraints, category subtree support (recursive CTE), indexes for `published`, category, `(price_vnd)`, brand, color, slug, source IDs, and index retrieval. Add GIN trigram on precomputed `search_text_normalized` if benchmark validates. Store normalized product text and Unicode original separately. Seed products/orders deterministically. All DB schema changes through Alembic; `docker compose up` and migration/seed scripts should work from a clean checkout.

## 6. Dataset strategy & Vietnamese data engineering

Never require a gated dataset for P0. Build **source adapters** and a canonical data contract. Candidate sources (verify their live licenses and access before use):
- `allietran/CAMEO` on Hugging Face: Vietnamese cosmetics catalog with historical price, product name, descriptions and image paths, CC BY-NC-SA 4.0; research/demo scope subject to license and image rights.
- `ceyda/fashion-products-small`: apparel with images/categories, largely English, price often missing; confirm license/image rights before any public use. Translate only verified attributes, retain original and review state.
- `arturayupov/womens-fashion-catalog`: women's fashion products, variants, price in source currency, image URLs; check availability, per-image rights and revision; VND offers must be separately approved/demo and correctly labeled.
- `Nhat-Quang/VN_Fashion_data`: gated/future adapter; **never assume access or fabricate records**.
- Shopify catalogue or other datasets are optional benchmark/taxonomy sources, not automatically merchant offers. Restricted review datasets must not be attached arbitrarily to our products.

Pipeline: `acquire metadata (with provenance and license manifest) -> stage raw -> source schema validation -> map/normalize category/color/gender/size/unit/currency -> Vietnamese localized display fields with review status -> image resolve+QC+rights -> duplicate candidate detection -> deterministic reconciliation -> publish approval -> batch build keyword/text/image indexes -> reports`. Idempotent re-runs with content hash, source revision, dry-run, resumability, per-stage counters, quarantined errors, audit log. Never merge two SKUs by text similarity alone; track one product/multiple offers only when verified. Source price is not an authoritative live selling price. Stock and sales/rating if missing remain nullable rather than randomly populated (except clearly separate reproducible demo fixtures).

Build a dataset audit CLI producing a report: row counts, field completeness, Vietnamese coverage, image open/rights validation, duplicates, category distribution, cost/disk and accepted/rejected counts. Start with metadata and 100-300 rows/source to avoid massive image downloads. Enforce publication constraints, separate `demo_seed` from `approved_public` profiles and prevent restricted images from being promoted.

## 7. Vietnamese text search: high relevance at low cost

Define shared typed `QueryRepresentation` with `modality`, `raw_text`, `normalized_text`, `image_vector_ref`, `hard_filters[]` including `origin/confidence`, `soft_preferences[]`, and `relaxed_filters[]`. The system must distinguish explicit UI selections, explicit natural-language constraints, and weak inferred metadata. Keep query parsing deterministic and no-LLM by default:
- Unicode NFC, lowercase, normalize whitespace and punctuation; generate accent-insensitive search shadow but preserve original; don't destructively conflate `đ` and `d` in canonical display data.
- Vietnamese aliases: `áo phông`~`áo thun`; `xanh than`~`navy`; `đen`~`màu đen`; `giày thể thao`~`sneaker`; conditional category mapping.
- Currency/units: `500k`, `500 nghìn`, `500 ngàn`, `năm trăm nghìn` => 500000; `2tr`, `2 triệu`, `2 củ` (colloquial where context strongly indicates VND) => 2000000. Distinguish `dưới` strict upper bound, `không quá` inclusive bound, `trên` lower bound, `tầm/khoảng` a target/soft preference. Ambiguity must not silently produce a hard filter. Detect `size L`, `XL`, colors, brand, material, gender, style, season; add NER extension interface only if measured better.
- Lexical baseline: normalized name/category/aliases + PostgreSQL `pg_trgm`, prefix match; weighted exact name > category/brand > description, optional BM25 adapter if a benchmark justifies added service.
- Semantic candidate retriever: optional local multilingual embeddings. Benchmark a lightweight multilingual encoder against `BAAI/bge-m3` (more capable but resource-heavy); run offline catalogue encoding and cache model. Record model name/revision/dimension, create a new index on any model change. Choose by observed Vietnamese Recall@K/latency/RAM, not by hype. If no model weights available, lexical mode remains fully operational and transparently labeled.
- Fusion: retrieve bounded top-K per modality, enforce hard filters **inside** candidate generation or exact filtered ranking, fuse lexical+semantic using configurable Reciprocal Rank Fusion, then rerank top ~30-100 candidates with explicit structured constraints and soft preference boosts. Don't blindly compare raw score scales across models. Deterministic tie-break; no generic LLM call per search.
- Filter relaxation implements exactly the specified ordered rule only for permitted inferred filters; retrieve again after each change, max bounded passes, explain each step. If still no results, show meaningful empty and related-category guidance without silently discarding category.
- Correctness check: exact hard filter must hold for every displayed result except any explicitly disclosed eligible relaxed constraint; source of truth is current DB. Pagination/ranking must be stable across pages and index updates.

## 8. Vietnamese voice search: offline and honest about latency

The voice feature must follow `record short audio -> validate -> local speech-to-text -> show/edit transcript -> same QueryParser/SearchService/RankingService`. Voice is not a separate product-search engine.

**Provider strategy:**
- Default true offline server-side candidate: `faster-whisper` with small quantized model on CPU (`tiny`/`base`/`small` and `int8`, test actual Vietnamese quality; don't declare a winner a priori), `language='vi'`, optionally VAD for silence, bounded beam size. The model is downloaded once to a local cache after user consent; no per-request paid fees. Bench carefully because quality suffers with too-small models and latency grows with bigger ones. Isolate in one inference worker/semaphore and warm lazily; process audio length ≤ 15s, reject oversize; never load model on each request or in every FastAPI worker.
- Optional zero-server-cost browser ASR only where a compatible browser supports it, but **do not claim Web Speech API is guaranteed offline/private/free**: vendor behavior and browser support vary; it can use a cloud service. Server offline adapter must remain independently functional.
- Optional `whisper.cpp` with WASM may offer client-side offline privacy but incurs download, memory and longer wall-clock; benchmark before choosing, not the default promise.
- Return transcript, language, duration, recognizer name/version, inference_time_ms, recognition warnings and editable text; graceful fallback to text entry for permission failure, noise, no speech, model missing, unsupported browser, service timeout.
- Evaluate **WER, CER, query-intent/attribute extraction accuracy** with Vietnamese North/Central/South dialects, numbers, `năm trăm k`, mixed `size XL/hoodie/Samsung`, and ambient noise. A perfect transcript isn't required if intent/filters correct; report both.

## 9. Image search: real visual similarity with resource-aware retrieval

Must implement **actual pretrained image embeddings**, not only color histogram. A color histogram/HSV+pHash is allowed as clearly labeled no-model baseline or auxiliary signal, with its documented limitations.

- Start with openly licensed **OpenCLIP ViT-B/32** image encoder weights (`laion/CLIP-ViT-B-32-laion2B-s34B-b79K` is a candidate; verify exact model licensing/version). This is image-to-image search: gallery images and user upload use precisely same compatible preprocessing (resize/crop/color normalization), model revision, embedding dimension and vector normalization. Do **not** feed BGE text vectors to CLIP image vectors.
- Pre-encode catalogue images **offline, batched**; store vectors indexed to `image_id`, `product_id`, version, content hash; never embed all catalogue images per query. An uploaded query image is encoded once, temporary file removed; retrieve top image neighbours and aggregate multiple images per product (e.g. maximum or top-n match) while avoiding duplicates.
- For 1k-5k products, first benchmark **exact cosine kNN** (pgvector supports exact by default); introduce HNSW only if measured necessary. For prefilters, test candidate-scoped exact ranking; with ANN, filter-after-scan can lose matches, so evaluate indexed prefilter/iterative scan and Recall@K against exact ground truth. No promise ANN always improves results.
- Add optional category/price filters and accompanying Vietnamese text (parsed using shared QueryParser); visual similarity is primary image relevance. Do not magically infer verified brand/price/material from pixels.
- Handle HEIC/nonstandard formats explicitly, whitelist JPEG/PNG/WebP for MVP, reject corrupt, huge, decompression bombs; strip EXIF, re-encode, no persistent storage unless opt-in; clean temp in failure paths.
- Evaluate with smartphone shots, different viewpoints/backgrounds, occlusion, lighting, cross-brand visually similar items, and irrelevant images. Hold out exact catalogue query images for realistic benchmarks to avoid inflated scores. Report Recall@1/5/10, NDCG@10 and failure examples.

## 10. Latency, memory, quality and cost engineering

No numbers claimed as facts until measured. Create a reproducible **benchmark harness** with fixed machine CPU/RAM/OS/model/catal. sizes, cold vs warm, concurrency=1/5/10, p50/p90/p95/p99, memory RSS, model load time and overall search quality. Instrument all stages `input_validation`, `transcription`, `parse`, `db_prefilter`, `lexical`, `text_embed`, `image_embed`, `vector_search`, `fusion`, `ranking`, `serialize`.

Initial *targets to validate on actual laptop*, not guarantees:
- Text lexical search warm p95 ≤ **300ms API-side** at ~3k products; hybrid semantic p95 ≤ **900ms** with a warmed CPU model (or record why not feasible).
- Image search after warm model p95 ≤ **2.5s** on measured machine with a <=5MB valid query image.
- Voice: report separately **recording time**, **ASR inference time**, and **retrieval time**; target ≤ **5s server processing** for an ~5s utterance on a measured modern CPU; if unavailable, give real result and recommend smaller model/GPU rather than fake SLO.
- Product grid API p95 ≤ **400ms** warm at 3k; track browser LCP, CLS, INP as actual field/lab metrics without fabricated pass claims.

Optimization order: start low-complexity measured baseline -> database `EXPLAIN ANALYZE` and correct indexes -> cache static taxonomy/suggestions/immutable thumbnails -> batched offline embedding -> model warm/correct thread caps and pre-processing -> shortlist rerank rather than whole corpus -> quantify recall/latency trade-off before ANN -> optional Redis/GPU only if justified. Cache keyed by query + filters + model/index generation and TTL, invalidate on publication/price/stock updates or revalidate latest data. No per-request translation LLM. Set request deadlines and capacity controls, bounded model queue, fail fast or lexical fallback; show appropriate UI status. Prevent excessive model download during local setup; include size and license info. Explicitly assess free inference vs hosting/computation cost.

## 11. Evaluation, security and tests

Implement deterministic, locally generated course-fixture catalog in `benchmarks/fixtures` (contains enough black sweaters and three bags) and seeded order `20261005`, with visible disclaimer `dữ liệu mô phỏng`. Keep these fixtures **physically and logically separate** from scraped/restricted source data and normal production offers.

Testing layers:
- Unit: Vietnamese normalizer/aliases/amount parsing; query intent/attribute provenance; hierarchy descendants; filter relaxation priority; stable ranking; price precision; out-of-stock demotion; vector compatibility/version; mime validation.
- Integration: migration/rollback, seed idempotency, DB constraints, product image associations, source adapter, real SQL filtered vector search (not mocks only), authenticated order lookup, stock reservation concurrency, cart and mock checkout.
- E2E Playwright: desktop/mobile journeys search-text/voice/image, filter chips, low-result notice, product detail, add-to-cart, order lookup, inaccessible other-user order, network/ASR failures and empty states. Real audio/image integration tests should run separately when model files available; simulations explicitly labeled.
- Black-box canonical **TC1–TC5** plus read-only **TC6**. Keep slide-matching fixture tests separate from evaluation on variable real dataset.
- Security negative tests: SQLi, XSS, IDOR, CSRF with cookie auth, oversized/malicious media, missing permissions, missing images, stale prices, stock race and duplicate checkout requests.
- Search benchmark: 100-300 judged Vietnamese queries with ordinary speech, diacritic variants, colloquial prices and 20-50 real-world query photos licensed for test use; document sample construction, label guidelines, qrels, category coverage, Recall@K/Precision@K/NDCG@K; ASR WER/CER; measure under same hardware and catalogue snapshot. No metric without actual evidence.

## 12. Implementation milestones, deliverables and acceptance gates

Operate in the following order. For each milestone provide changed files, commands run, test results, measured timings when available, architecture decisions, blockers, next step; stop to resolve genuine failure, never claim unrun tests passed.

**M0 — Audit + spec (day 1):** inspect repo/files/skills, confirm scope and slide-vs-engineering decisions, choose deps/versions, draft ERD and API contract, create `.env.example`, AGENTS.md, plan. **Gate:** traceable FR/use-case/test matrix and reproducible clean setup documented.

**M1 — Data and backend skeleton:** Docker Compose Postgres pgvector, FastAPI, Alembic, health routes, domain entities and seeded fixture, catalog list/details/category endpoints. **Gate:** clean migrate+seed; product API shows verified/demo status, 34 demo leaf categories if generated fixture covers them, no duplicates on re-run.

**M2 — Frontend storefront vertical slice:** polished responsive home, catalog, product detail, shared SearchBar placeholder only if explicitly not yet active, cart demo, auth scaffolding; API driven. **Gate:** user can browse valid published products, see VND and images, cart behavior tested.

**M3 — Vietnamese text search:** deterministic parsing, filter provenance, exact category subtree, lexical baseline, hybrid embeddings where viable, structured ranking, explainable relaxation. **Gate:** TC1, TC4 plus 50+ Vietnamese parser cases pass, no hard-filter leakage; benchmark generated.

**M4 — Image search:** image QC, licensed image fixture, offline CLIP indexing, uploaded-image retrieval and feedback, evaluation. **Gate:** TC3 with actual model (or explicitly blocked if weights unavailable), accurate mapping, no orphan vectors, realistic held-out tests and latency reported.

**M5 — Voice search:** short browser recording, offline Vietnamese ASR worker, editable transcript and text pipeline. **Gate:** TC2 actual ASR (or clearly documented model/download blocker), fallback and microphone errors tested, WER/CER and latency reported.

**M6 — Authenticated order lookup + demo commerce:** owner-safe order intent routing from universal search, cart/checkout mock, order detail/stock consistency, seller/admin minimum. **Gate:** TC5 and TC6, IDOR and stock-concurrency tests pass; real online payments explicitly not implemented.

**M7 — Integration hardening:** security/performance profiling, responsive Playwright regression, tests and docs, demo script matching slides, Docker CPU deployment recipe. **Gate:** complete runnable README, repeatable seed, all TC1-TC6 proven, benchmark with real measured p95, no false production claims.

Acceptance rubric: **correctness > user safety/data authenticity > relevance > latency > aesthetics > feature count**. Never improve measured latency by silently skipping hard filters or returning unverified/out-of-scope products. If a target cannot be achieved on CPU, deliver transparent metrics and a lower-resource mode.

## 13. Codex output format and immediate next action

For your **first response**, provide: (i) exact files/architecture you found; (ii) discrepancies between slides and repo; (iii) planned tech stack and genuinely free local model options with RAM/trade-offs; (iv) milestone M0-M7 implementation checklist with acceptance gates; (v) immediate minimal working vertical slice. Then **begin executing M0 and M1**, not just discussing. If the slides are absent in the repository, say you cannot inspect them locally and ask the user to copy `PTTKHT-Slides.pdf`, but proceed using the baseline in this prompt without claiming the file was read.

At the end of every implementation segment, use:
```
Completed: ...
Changed files: ...
Tests run and exact results: ...
Benchmarks actually measured: ...
Known limitations: ...
Next implementation task: ...
```

Maintain `docs/PROGRESS.md` and update the architecture/traceability matrix with each milestone. Show concrete runnable PowerShell commands for `docker compose up`, environment setup, `alembic upgrade head`, dataset audit, seed, index build, frontend/backend dev, pytest, Playwright and benchmarks. Do not silently substitute proprietary paid services for offline components. Begin now.

## Reference documentation for technical verification

- PostgreSQL pgvector: https://github.com/pgvector/pgvector
- PostgreSQL trigram search: https://www.postgresql.org/docs/current/pgtrgm.html
- Faster Whisper: https://github.com/SYSTRAN/faster-whisper
- Browser whisper.cpp WASM demo: https://github.com/ggml-org/whisper.cpp/tree/master/examples/whisper.wasm
- BGE-M3 model: https://huggingface.co/BAAI/bge-m3
- CLIP lightweight image model: https://huggingface.co/laion/CLIP-ViT-B-32-laion2B-s34B-b79K
- OWASP file upload guidance: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html
- FastAPI OAuth/JWT tutorial: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- Next.js image optimization: https://nextjs.org/docs/app/api-reference/components/image
- Codex project instructions: https://developers.openai.com/codex/guides/agents-md
