# 📌 ACTIVITY

## Enrich Zoning and POI Data with an LLM (R + Ollama Cloud)

🕒 *Estimated Time: 10–15 minutes*

---

## 📋 Overview

You will run **[`fixer/fixer_parcels.R`](fixer/fixer_parcels.R)** and **[`fixer/fixer_pois.R`](fixer/fixer_pois.R)**. Each script calls **Ollama** with **batched tool calls** (one **`/api/chat` per chunk** of rows): parcels get **`record_parcel_zoning`** from **polygon** rows (**`wkt`** in WGS84); POIs get **`record_poi_category`** from **point** rows (**`x`**, **`y`**). Outputs are enriched CSVs, **audit JSONL** files, and **before/after** maps (**`sf`** + **`ggplot2`**) under **`fixer/output/`**.

More detail: **[`fixer/README.md`](fixer/README.md)**.

---

## ✅ Your Task

### 🧱 Stage 1: Environment

- [ ] Install R packages **`dplyr`**, **`readr`**, **`jsonlite`**, **`purrr`**, **`sf`**, **`ggplot2`**, **`httr2`**, **`future`**, and **`furrr`** (same **`fixer/.env`** as the CSV activity: **`OLLAMA_API_KEY`**, **`OLLAMA_HOST`**, **`OLLAMA_MODEL`**).
- [ ] Confirm **`fixer/data/parcels_zoning_raw.csv`** (polygons in **`wkt`**) and **`fixer/data/pois_messy_raw.csv`** exist.

### 🧱 Stage 2: Run and verify

- [ ] Run: **`Rscript 10_data_management/fixer/fixer_parcels.R`** and **`Rscript 10_data_management/fixer/fixer_pois.R`** from the **`dsai`** repo root (or use **`FIXER_ROOT`** as in **[`fixer/README.md`](fixer/README.md)**).
- [ ] Open **`fixer/output/parcels_enriched.csv`** or **`fixer/output/pois_enriched.csv`** and note at least one LLM-derived column (for example **`primary_land_use`** or **`normalized_category`**). If **`error_flag`** is **`TRUE`** anywhere, note one row and what you might try next (model, **`ROWS_PER_BATCH`**, or connectivity).
- [ ] Open **`fixer/output/map_parcels_before.png`** and **`map_parcels_after.png`** (or the POI pair) and compare how the map encoding changed.

### 🧱 Stage 3 (optional) — Contextual spatial routing

- [ ] After enriched CSVs exist, run **`Rscript 10_data_management/fixer/fixer_spatial_context.R`**. The LLM chooses **`nearest_poi`** / **`count_pois_within`** / **`record_context_note`** from **zone_code** and **primary_land_use**; R computes distances and counts. Inspect **`fixer/output/parcels_context_enriched.csv`** and **`fixer/output/context_routing_audit.jsonl`**.

---

# 📤 To Submit

- Screenshot of **one** enriched map (**`map_parcels_after.png`** or **`map_pois_after.png`**) from **`fixer/output/`**.
- One sentence: what does **`primary_land_use`** add that raw **`zone_code`** alone does not express?

---

![](../docs/images/icons.png)

---

← 🏠 [Back to Top](#ACTIVITY)
