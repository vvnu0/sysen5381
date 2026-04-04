# Fixer — LLM-assisted data repair and enrichment (R)

Example scripts for **Module 10** showing how an LLM can **directly fix tabular data** (batched **set_cell** tool calls) and **derive structured fields from short zoning prose and messy place names** (batched tool calls), with **sf** + **ggplot2** maps before and after enrichment.

Hands-on write-ups: **[`ACTIVITY_fixer_csv.md`](../ACTIVITY_fixer_csv.md)** and **[`ACTIVITY_fixer_spatial.md`](../ACTIVITY_fixer_spatial.md)** (in **`10_data_management/`**).

**Smoke test** (minimal chat, no tools — good for debugging HTTP 400): from repo root, **`Rscript 10_data_management/fixer/testme.R`** (requires **`fixer/.env`** with **`OLLAMA_API_KEY`**; uses **`OLLAMA_MODEL`** or defaults to **`gpt-oss:120b`**).

## Prerequisites

- R packages: `dplyr`, `readr`, `httr2`, `jsonlite`, `purrr`, `sf`, `ggplot2`
- For [`fixer_csv.R`](fixer_csv.R), [`fixer_parcels.R`](fixer_parcels.R), [`fixer_pois.R`](fixer_pois.R), and [`fixer_spatial_context.R`](fixer_spatial_context.R) also: `future`, `furrr`
- **Ollama Cloud** API key and a **tool-capable** model for the batched scripts (same pattern as [`../agentr/`](../agentr/))
- Copy `.env.example` to `.env` in this folder (or set env vars in your shell) with `OLLAMA_API_KEY`, `OLLAMA_HOST`, `OLLAMA_MODEL`

## Run order

1. From repo root or this folder, ensure working directory contains `10_data_management/fixer` paths as in the scripts (they `setwd` to **`fixer/`** via **`REPO`** / **`stringr::str_extract(getwd(), ".*dsai")`**).
2. `Rscript 10_data_management/fixer/fixer_csv.R` — copies **`data/messy_inventory_raw.csv`** to **`output/messy_inventory_working.csv`**, splits into chunks of **ROWS_PER_BATCH** rows (default **10**), runs one **`/api/chat` per chunk** (parallel across chunks when **FIXER_CHUNK_WORKERS** is greater than 1), applies **set_cell** patches on the main process, writes **`output/fix_audit.jsonl`**.
3. `Rscript 10_data_management/fixer/fixer_parcels.R` — reads **polygon** parcels (**`wkt`** in WGS84), batched **`record_parcel_zoning`** tool calls, writes **`output/parcels_enriched.csv`**, **`output/parcels_enrich_audit.jsonl`**, and parcel map PNGs.
4. `Rscript 10_data_management/fixer/fixer_pois.R` — reads **point** POIs (**`x`** / **`y`**), batched **`record_poi_category`** tool calls, writes **`output/pois_enriched.csv`**, **`output/pois_enrich_audit.jsonl`**, and POI map PNGs.
5. `Rscript 10_data_management/fixer/fixer_spatial_context.R` — **after** steps 3–4: reads **`output/parcels_enriched.csv`** + **`output/pois_enriched.csv`**, uses the LLM to **route** **`nearest_poi`**, **`count_pois_within`**, and **`record_context_note`** tool calls from **zone_code** / **primary_land_use**; **sf** computes all distances/counts (EPSG **32617** for meters). Writes **`output/parcels_context_enriched.csv`**, **`output/context_routing_audit.jsonl`**, **`output/map_parcels_context_transport.png`**. Optional env: **`FIXER_CONTEXT_PARCELS`**, **`FIXER_CONTEXT_POIS`** (override input paths).

**Offline tests** (chunking + patch logic + parcel WKT parse, no API): `Rscript 10_data_management/fixer/tests/test_fixer_csv_helpers.R`

## Artifacts

| Path | Description |
|------|-------------|
| `data/messy_inventory_raw.csv` | Immutable messy inventory (30 rows; no `notes` column — rules live in **`DATA_QUALITY_BLURB`** inside [`fixer_csv.R`](fixer_csv.R)) |
| `data/parcels_zoning_raw.csv` | Synthetic **non-overlapping parcel polygons** (**`wkt`**) + **`parcel_id`**, **`zone_code`**, **`zoning_excerpt`** |
| `data/pois_messy_raw.csv` | Synthetic messy POI names + point coordinates (**`poi_id`**, **`x`**, **`y`**) |
| `output/messy_inventory_working.csv` | Working copy after [`fixer_csv.R`](fixer_csv.R) |
| `output/fix_audit.jsonl` | One JSON object per successful **`set_cell`** |
| `output/parcels_enriched.csv` | Parcels + LLM-derived tags |
| `output/parcels_enrich_audit.jsonl` | One JSON object per **`record_parcel_zoning`** |
| `output/pois_enriched.csv` | POIs + normalized categories |
| `output/pois_enrich_audit.jsonl` | One JSON object per **`record_poi_category`** |
| `output/map_*.png` | Before/after maps |
| [`functions.R`](functions.R) | Shared **`ollama_chat_once`**, **`parse_function_arguments`**, **`truncate_tool_output`**, **`split_df_into_row_chunks`** (sourced by the fixer scripts and **`testme.R`**) |

## Extending with real OSM data (optional)

- **POIs:** replace synthetic **`x`** / **`y`** with coordinates from **`osmdata`**: build a bbox with `osmdata::getbb("Your City")`, then `opq(bbox) |> add_osm_feature(...)` and keep columns **`poi_id`**, **`x`**, **`y`**, **`name_messy`** for [`fixer_pois.R`](fixer_pois.R).
- **Parcels:** supply your own **`POLYGON` WKT** (or build polygons in **sf** and `sf::st_as_text`) in **`wkt`**, with **`parcel_id`**, **`zone_code`**, and **`zoning_excerpt`**, for [`fixer_parcels.R`](fixer_parcels.R).

## Troubleshooting

- If **tool calls** never fire, try another cloud model or a smaller **ROWS_PER_BATCH** so each request sees fewer rows.
- **HTTP 500** / **429** on batched scripts: try **FIXER_CHUNK_WORKERS=1** (sequential chunk requests) to reduce load on Ollama Cloud.
- **HTTP 400** on **`fixer_csv.R`** (and related): Ollama Cloud may reject `options.num_predict`; scripts omit it unless you set **`FIXER_MAX_OUTPUT_TOKENS`** (digits only) in **`.env`**. If the error mentions JSON/`}` , ensure tool schemas use **`{}`** for empty `properties` (not `[]` — an R empty `list()` encodes as an array).
- If a spatial chunk returns **no tool calls** or **`error_flag`** is **`TRUE`** on rows, inspect **`parcels_enrich_audit.jsonl`** / **`pois_enrich_audit.jsonl`**, reduce **ROWS_PER_BATCH**, or try a stronger model.
- **Context synthesis** ([`fixer_spatial_context.R`](fixer_spatial_context.R)): if counts/distances are all **NA**, confirm POIs include the **`normalized_category`** values the router requests (e.g. **`transport`**). Inspect **`context_routing_audit.jsonl`** for `no_pois_of_category` or `beyond_max_search_m`.
