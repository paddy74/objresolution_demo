# 08: Build plan: icon map, filters, object attributes, logging, demo companion

The resumable plan for the second build iteration, split into **7 independently deliverable features (F1 to F7)**.

Status: **planned, not started** (2026-10-13). Branch: `objresolution_demo`.

**How to use this plan** (implementation agents start here):

1. Read `AGENTS.md`, then sections 1 to 3 of this file, then the files in §4 that your feature touches.
2. Check `git log --oneline` and the checkboxes in §7 to see what has landed. Run `uv run pytest` to see which new tests fail.
3. Take the first unfinished feature in the recommended order (§3) whose **Needs** have landed. Continue from its first unchecked task. Its header line points to the design (§5), tests (§6) and acceptance criteria (§8) it owns.
4. After each task, tick the box and add a line to the progress log (§11).
5. If a Databricks step stalls for more than 10 minutes, propose a fallback (`AGENTS.md` stall rule) and log it.

## 1. Request (verbatim scope)

1. **UI**
   - (a) Each object on the map is a **square containing a simple icon of its top-level object type** (tank for a tank, plane for an aircraft). Use one free, open-source icon set, or visually consistent sets.
   - (b) Filters: **geographic COCOM** (filters objects and observations) and a **time period** (start date, end date; filters observations only, by observation date).
   - (c) Filter by **top-level object type** (filters objects and observations).
2. **Additional**
   - **Object attributes.** Give objects the minimum required attributes for their closest shared class (Material Entity / Material Artifact), and have synthetic generation populate them with realistic values and distributions.
   - **Authoritative equipment values.** Take them from the Worldwide Equipment Guide (WEG, <https://odin.t2com.army.mil/>).
   - **Logging.**
     - Add verbose but useful runtime logging, with `print` only where necessary.
     - Account for Databricks stdout and log-file behaviour.
     - Use the language-standard logging format.
   - **Demo companion notebook.** It accompanies `demo/10-minute-script.md` with sample scripts, charts and workflow diagrams.
   - Development is test-driven and spec-driven.

## 2. Decisions made with the user (do not re-ask)

| #   | Decision                                                                                                                                                                                                                                                               |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Spread the data over **6 synthetic AOIs, one per geographic COCOM**: NORTHCOM, SOUTHCOM, EUCOM, AFRICOM, CENTCOM and INDOPACOM. SPACECOM is not geographic.                                                                                                            |
| D2  | Add a **new "Operating picture" map page** to the app. **Sidebar filters** (COCOM, type, date range) apply to that page *and* narrow the review queue. The review screen's per-item map uses the same icons.                                                           |
| D3  | Widen the observation window from **72 hours to 30 days**.                                                                                                                                                                                                             |
| D4  | New object attributes: **`model_name`, `primary_function`, `country_of_origin`, `cocom`**, plus source columns for provenance. No mass or length.                                                                                                                      |
| D5  | **Update `AGENTS.md`**: real attribute values are allowed **only** when sourced from the WEG or the CCO/BFO ontologies. Everything else stays synthetic.                                                                                                               |
| D6  | **"Top-level object type"** means the 5 CCO types in `synthetic.LEAVES`: Airport, Military Facility, Truck, Armored Fighting Vehicle and Aircraft. The WEG model (e.g. T-72B3) is an attribute under the type. (Stated to the user as an assumption; not objected to.) |
| D7  | Icons come from **Tabler Icons** (MIT), one outline set, inlined as SVG.                                                                                                                                                                                               |
| D8  | Logging uses the **Python stdlib `logging`** module. `print` stays only for deliberate user-facing notebook output.                                                                                                                                                    |

Decisions in `AGENTS.md` still hold: no Splink, GraphFrames, Vector Search or CV; `COPY INTO`, not Auto Loader; label propagation in Spark SQL.

## 3. Features

| Feature | Delivers (request item)                               | Needs | Better after | Changes measured numbers | Complexity | Size |
| ------- | ----------------------------------------------------- | ----- | ------------ | ------------------------ | ---------- | ---- |
| F1      | Stdlib logging in pipeline and app (Logging, D8)      | —     | —            | No                       | Low        | M    |
| F2      | Square type icons on the existing review map (1a, D7) | —     | F1           | No                       | Low        | S    |
| F3      | Operating picture page and type filter (1c, D2)       | F2    | —            | No                       | High       | L    |
| F4      | 30-day window and date filter (1b time, D3)           | F3    | —            | Yes                      | Medium     | M    |
| F5      | Six COCOM AOIs and COCOM filter (1b COCOM, D1)        | F3    | F4           | Yes                      | High       | XL   |
| F6      | WEG/CCO object attributes (Attributes, WEG, D4, D5)   | —     | F3           | No                       | Medium     | L    |
| F7      | Demo companion notebook (Demo companion)              | —     | F3 to F6     | No                       | Medium     | M    |

- **Needs** are hard prerequisites. **Better after** is a soft order that only saves rework.
- **Estimates** are rough. Complexity = technical risk and unknowns. Size = relative effort (S < M < L < XL < XXL); all seven together come to roughly XXL. The drivers are:
  - F1: ~40 `print` sites.
  - F3: two new views plus a new page.
  - F5: placement rework that touches every view, plus hero/REVIEW tuning and the number refresh.
  - F6: WEG verification research.
- **Recommended order:** F1 → F2 → F3 → F6 → F4 → F5 → F7.
  - F1 goes first because its `print` line list (§4) is pinned to `a4cb608`.
  - F6 draws from a separate generator, so measured numbers do not change.
  - F4 and F5 both change every measured number. Ship them back to back and do the number refresh (F5.9) once.

**Definition of done (every feature):**

- Spec edits land first.
- Tests are written before the code and fail first.
- The repo is green: `uv run pytest`, `uv run ruff check`, `uv run ruff format --check` and `uv run basedpyright`.
- The Databricks check passes and the demo still runs.
- Checkboxes are ticked and the progress log updated.
- One commit with the message given in the feature.

A feature that lands before a "Better after" feature skips the parts that depend on it. The later feature adds them; its tasks say so ("if F3 has landed").

## 4. Current state (verified 2026-10-13, commit `a4cb608`)

Read the files your feature touches before changing them.

- `notebooks/pipeline/synthetic.py`:
  - `LEAVES`, `GENERIC`, and `BBOX = (39.0, 39.5, -105.5, -105.0)`, a single area.
  - `make_obs` puts `obs_time` in the last **72 h** (`rng.uniform(0, 72)`).
  - `generate()` uses one main `rng` (seed 42) for objects, twins and observations, plus separate generators: `seed+1` (last_seen), `seed+2` (report delay) and `seed+3` (likelihood).
  - `last_seen` is `now − U(1,14)` days for observed objects, else `U(1,30)`; `first_seen = now − 30 d`.
  - Tasking windows span 0 to 72 h.
  - `write_sources` writes `oms_objects`, `seed_twins` and the landing files.
- `notebooks/pipeline/config.py`: `Config` (thresholds, `h3_res=8`, `max_dist_m=500`); `hav_sql`.
- `notebooks/pipeline/ontology.py`: loads the CCO TTL with rdflib and writes `cco_classes`, `type_iri` and `type_ancestors`. It asserts that labels resolve and that `GENERIC` matches CCO. The new facility-subclass assertion goes here.
- `notebooks/pipeline/ingest.py`: `COPY INTO` with explicit column lists for the bronze tables; observations land via JSON. `check_h3` uses a Colorado point, which is fine.
- `notebooks/pipeline/model.py`: candidate pairs use `oms_objects WHERE source = 'OMS'`. Features are fixed by spec (03 §3). **Do not add features.**
- `notebooks/pipeline/nominate.py`: the `write_back` MERGE inserts nominations with an explicit column list (`object_id, object_type, lat, lon, marking, first_seen, last_seen, …`). New columns must be added there.
- `notebooks/pipeline/review.py`: `review_queue` view, `adjudicate`.
- `notebooks/pipeline/present.py`: `demo_row_filter`, `hero_map` (folium), `create_dashboard_views` (`dash_decisions`, `dash_object_summary`, `dash_map_points`).
- `notebooks/pipeline/heroes.py`: picks heroes A, B and C from the data; A is an AFV.
- `notebooks/pipeline/dossier.py`: builds the `ai_query` dossier from object fields.
- `notebooks/pipeline/genie.py`: `sync_space` from `demo/genie-space.md`; `parse_genie_md`.
- `notebooks/generate_data.py`: orchestrator notebook, sections 1 to 15 plus the cheat card. It `print`s the cheat card and the 10b form messages.
- `app/app.py`:
  - a 433-line, single-page Streamlit review screen;
  - `run()` executes SQL through `databricks-sql-connector`;
  - pure helpers are inline (`coords`, `object_label`, `distance_m`, `time_ago`, `source_label`, `type_agreement`), and the module runs Streamlit on import, so it **cannot be imported by tests**;
  - the map uses `folium.CircleMarker` plus `folium.Icon`;
  - it deploys from `app/` only, so it cannot import `notebooks/` or `obj_resolution/`.
- `app/requirements.txt`: `streamlit>=1.35`, folium, streamlit-folium, databricks-sdk, databricks-sql-connector, pandas.
- `app/app.yaml`: env `DATABRICKS_WAREHOUSE_ID` (resource) and `OBJ_RESOLUTION_SCHEMA`.
- `tests/unit/test_pipeline.py` covers:
  - determinism (`len(objects) == 2025`, equal frames);
  - report time within `[obs_time, now]`;
  - `hav_sql`;
  - Genie parse (**exactly 16 examples**, no `workspace.`);
  - ICD 203 bands and likelihood ordering;
  - seeded cases (twin distance `TWIN_M`, partial cases, noise fraction).
- `pyproject.toml`: pytest `pythonpath = ["notebooks"]`; ruff line length 88; basedpyright includes `obj_resolution` and `tests` and excludes `notebooks` and `app`.
- `demo/genie-space.md`: Genie instructions plus 16 examples; some mention the "last 72 hours".
- `demo/10-minute-script.md`: timed script. It quotes the "72 hours" Genie question, hero IDs and measured numbers (4,662 obs, 2,025 objects, bands 3,862 / 137 / 663, 128 nominations, 335 recovered).
- `docs/plan/03-data-model.md`: **the spec** (source of truth for tables, columns, parameters and seeded cases). §6 holds the measured numbers.

**`print` call sites to convert (F1):**

- `synthetic.py:376`
- `ingest.py:62,81,87,130`
- `ontology.py:80`
- `present.py:29`
- `model.py:117,138,192,193,195,228`
- `review.py:51,80,93`
- `nominate.py:65,93,131`
- `dossier.py:86,98,121` (keep 121: it prints dossier text for the user)
- `genie.py:147,157,160,162`
- `generate_data.py:63,201,214,264,268,288,353`

### Facts verified in the CCO TTL (`data/ontology/CommonCoreOntologiesMerged.ttl`)

- **No OWL restrictions on Material Artifact.** `Material Artifact` (`ont00000995`) has only the definition "A Material Entity that was designed by some Agent to realize a certain Function". BFO `material entity` (`BFO_0000040`) defines no required data properties either. So "minimum required attributes" is read from the definition:
  - *designed by an Agent* → model and origin;
  - *to realize a Function* → primary function;
  - BFO location → lat/lon (present) plus COCOM.
- **Facility restriction.** `Facility` (`ont00000192`) is restricted to `BFO_0000171` (located in) some `Portion of Geosphere` (`ont00001341`). This justifies the location attributes.
- **Model and function classes.** CCO has `Artifact Model` (`ont00001045`), `Artifact Model Name`, `Artifact Function` (`ont00000323`) and `Military Artifact Function` (`ont00000066`). There is **no** transportation artifact function class.
- **CCO subclasses of the demo types:**
  - Military Facility → Combat Outpost, Command Post Facility, Fort, Military Base, Military Headquarters Facility, Missile Launch Site.
  - Airport → Heliport.
  - Armored Fighting Vehicle → Armored Personnel Carrier, Infantry Fighting Vehicle, Tank.
  - Truck and Aircraft → none.

### Facts verified for icons

These Tabler outline SVGs return HTTP 200 at `https://cdn.jsdelivr.net/npm/@tabler/icons@3.19.0/icons/outline/<name>.svg`: `tank`, `plane`, `truck`, `building-airport`, `building-fortress`, `radar`. Check `help-square` (the fallback) the same way before using it.

## 5. Target design

Each part is tagged with the feature that delivers it.

### 5.1 Data model (spec: `03-data-model.md`)

**Time window (F4):**

- `OBS_WINDOW_H = 30 * 24`; `obs_time` is uniform in `[now − 30 d, now]`.
- `last_seen` falls **before the window**, so `days_since_last_seen` does not floor at 0. It is `now − 30 d − U(1,14) d` if observed, else `now − 30 d − U(1,30) d`, drawn from the same `seed+1` generator.
- `first_seen = last_seen − U(30,180) d`, drawn from a new separate generator.
- Tasking: `start_time` within the 30 days before now; `end_time = start_time + U(12,72) h`, capped at `now`.

**COCOM areas (F5).** New reference table `cocom_aoi`, written by `synthetic.write_sources`:

| column                                     | type   | notes               |
| ------------------------------------------ | ------ | ------------------- |
| `aoi_name`                                 | STRING | e.g. `AOI-NORTHCOM` |
| `cocom`                                    | STRING | one of the 6 COCOMs |
| `min_lat`, `max_lat`, `min_lon`, `max_lon` | DOUBLE | 0.5° × 0.5° box     |

Proposed boxes, to confirm during implementation. Each must be land, inside the COCOM's AOR, away from cities and known military sites, and arbitrary:

| COCOM     | lat            | lon              | note                     |
| --------- | -------------- | ---------------- | ------------------------ |
| NORTHCOM  | 39.0 to 39.5   | −105.5 to −105.0 | existing `BBOX`, keep    |
| SOUTHCOM  | −15.5 to −15.0 | −56.0 to −55.5   | interior South America   |
| EUCOM     | 47.0 to 47.5   | 2.0 to 2.5       | rural interior Europe    |
| AFRICOM   | −22.0 to −21.5 | 17.0 to 17.5     | interior southern Africa |
| CENTCOM   | 23.5 to 24.0   | 53.5 to 54.0     | inland desert            |
| INDOPACOM | −25.0 to −24.5 | 133.0 to 133.5   | interior Australia       |

- **Placement rule.** Objects, `NEW-` objects and noise are drawn **inside an inner margin of 0.05°** (about 5 km) of their AOI. This keeps every derived point inside the box: twins (+400 m), partial far observations (+3 km), observation jitter and the 0.05° tasking boxes. COCOM is then a pure bbox lookup, in Python (`cocom_of`) and in SQL (join on `cocom_aoi`).
- `oms_objects.cocom` = `cocom_of(lat, lon)`. Nominations get it from a `cocom_aoi` join in the MERGE.
- Observations get **no new landed columns**. Their COCOM is derived in SQL from `cocom_aoi`.

**Object attributes (F6).** New `oms_objects` columns; nominations (`DATABRICKS_NOMINATION`) get NULL in all of them:

| column              | type   | Vehicles (Truck, AFV, Aircraft)              | Facilities (Airport, Military Facility)                                                                    |
| ------------------- | ------ | -------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `model_name`        | STRING | WEG system name (CCO *Artifact Model Name*)  | CCO subclass label: Military Facility → one of its 6 subclasses; Airport → `Airport` or `Heliport`         |
| `primary_function`  | STRING | WEG role text, e.g. "Main battle tank"       | Military Facility → `Military Artifact Function` (`ont00000066`); Airport/Heliport → "Air transportation"¹ |
| `country_of_origin` | STRING | WEG country of origin                        | NULL (inventing an operator country would be fabricated real-world data)                                   |
| `attr_source`       | STRING | `'WEG'`                                      | `'CCO'`                                                                                                    |
| `attr_source_ref`   | STRING | WEG reference (ODIN URL, or volume and page) | CCO IRI of the subclass                                                                                    |

¹ CCO has no transportation function class, so quote or derive "Air transportation" from the Airport definition text in the TTL.

**Random streams.**

- Moving objects into AOIs (F5) changes the main stream, so **every downstream number changes**. That is accepted.
- Attribute draws (F6) use their own `default_rng(seed + 4)`, so attributes never perturb observations.

**Observation `display_type` (F3)**, used by the type filter: *An observation shows under the type of the object it is linked to (AUTO, or approved by an analyst); otherwise under what the source reported, if that is one of the 5 types; otherwise as "Unidentified".*

### 5.2 WEG catalog: `notebooks/pipeline/weg.py` (F6)

- `CATALOG` is a static list of rows with these fields:
  - `object_type`;
  - `cco_subclass` (AFV only: Tank, Infantry Fighting Vehicle or Armored Personnel Carrier; otherwise None);
  - `model_name`, `primary_function` and `country_of_origin`;
  - `weight` (the sampling weight; weights sum to 1 per type);
  - `weg_ref`.
- `FACILITY_MODELS` maps each facility type to a list of `(cco_subclass_label, weight)`. `FACILITY_FUNCTION` holds the facility functions.
- **Verify every candidate's name, role and origin on ODIN WEG** before committing. If ODIN needs a login, use the public WEG PDFs: Vol 1 (Ground Systems) and Vol 2 (Airspace & Air Defense). Record `weg_ref` either way, and drop any candidate that cannot be verified.
- Store **names, roles and origins only**, with no performance figures (D5).
- Weights are realistic but simple: tanks and IFVs dominate the AFVs, utility trucks dominate the trucks, and helicopters are about 40% of aircraft. Document the weights in 03.

| Type                     | Candidates (verify)                                                                     |
| ------------------------ | --------------------------------------------------------------------------------------- |
| Truck                    | KamAZ-5350, Ural-4320, GAZ-66, Shaanxi SX2190                                           |
| Armored Fighting Vehicle | T-72B3 (Tank), T-90A (Tank), Type 99A (Tank), BMP-3 (IFV), ZBD-04A (IFV), BTR-82A (APC) |
| Aircraft                 | Su-35, Su-25, J-10C, Mi-8/Mi-17, Mi-24                                                  |

### 5.3 Views in `present.py` and `review.py`

- `map_objects` (F3):
  - `oms_objects.*` plus the designator label;
  - attribute columns flow through automatically once F6 lands;
  - `cocom` comes from the column, with a `cocom_aoi` join as fallback for nominations (F5).
- `map_observations` (F3; `cocom` in F5):
  - columns `obs_id, obs_time, lat, lon, reported_type, producer, sensor, likelihood, decision, match_prob, matched_object_id, display_type, cocom`;
  - joins `bronze_observations` ⨝ `silver_model_decisions` ⟕ `review_decisions` ⟕ `oms_objects` (linked type) ⟕ `cocom_aoi`.
- `review_queue`: add `display_type` (F3) and `cocom` (F5), so the app can apply the same predicates.
- `dash_map_points` and `dash_object_summary`: add `cocom` (F5). It is cheap and useful for the AI/BI fallback and Genie.

### 5.4 App design (`app/`)

```text
app/
  app.py        entry: config, logging, sidebar filters, st.navigation([Operating picture, Review queue])
  helpers.py    pure functions (no Streamlit, no SQL execution): labels, distance, time_ago, filter_sql, object_icon_html
  icons.py      Tabler SVG strings + MIT license header, ICON_SVG dict, FALLBACK_SVG
```

Keep pages as functions in `app.py` (`operating_picture()`, `review_queue()`). Split them into `app/views/*.py` only if `app.py` grows past ~600 lines.

**Shared type list.** `helpers.py` and `icons.py` define their own `OBJECT_TYPES` tuple rather than importing pipeline code, so the app stays deployable on its own. A test asserts that it equals `synthetic.LEAVES`.

**Icons (F2).**

- Use `folium.DivIcon(html=object_icon_html(object_type, source), icon_size=(28, 28), icon_anchor=(14, 14))`.
- The HTML is a 28 px square with a white background, a 2 px border and a 3 px radius, holding the SVG at 20 px with `stroke="currentColor"`.
- The border colour shows the source: OMS `#1b1b1b`, nomination `#e8710a`. A caption under the map is the legend.

| Type                     | Tabler icon         |
| ------------------------ | ------------------- |
| Armored Fighting Vehicle | `tank`              |
| Aircraft                 | `plane`             |
| Truck                    | `truck`             |
| Airport                  | `building-airport`  |
| Military Facility        | `building-fortress` |
| Unknown / nominated      | `help-square`       |

**Sidebar filters** (both pages; values kept in `st.session_state`; DEBUG-log the values on each rerun):

- **Object type (F3):** a multiselect over `OBJECT_TYPES` + `"Unidentified"`.
  - Objects match on `object_type`; observations on `display_type`.
  - Nominated objects with type `Unknown` or a generic type show under Unidentified.
- **Start and end date (F4):** `st.date_input`.
  - They default to the 30-day span, bounded by min/max `obs_time`.
  - A caption reads "Dates filter observations only."
  - A start after the end shows `st.error` and stops.
- **COCOM (F5):** a multiselect with options from `SELECT cocom FROM cocom_aoi ORDER BY cocom`, cached with `st.cache_data(ttl=300)`. Empty means all.

**`filter_sql(kind, *, types=(), start=None, end=None, cocoms=())` → `(where_sql, params)`.** Each feature adds its keyword argument (types in F3, dates in F4, cocoms in F5) without breaking callers.

- `kind` is `"object"` or `"observation"`.
- Named parameters only, one per selected value (`:cocom_0, :cocom_1…`); never interpolate values.
- Values are validated against the known option lists; anything unknown raises `ValueError`.
- Objects ignore dates. Observations use `obs_time >= :start AND obs_time < :end_excl`, where `end_excl` is the end date + 1 day.
- Returns `("TRUE", {})` when nothing is selected.

**Page "Operating picture" (F3):**

- Metrics: objects shown, observations shown, and the observations broken down by decision.
- Folium map:
  - objects as DivIcon markers inside `folium.plugins.MarkerCluster`;
  - observations as `CircleMarker` (radius 4), coloured AUTO green, REVIEW amber, NOMINATE grey and analyst-rejected red;
  - `fit_bounds` to the filtered points.
- Tooltips (show only the columns that exist):
  - object: label, model, function, origin, COCOM, last seen, linked observations;
  - observation: reported as, source, decision, likelihood, time.
- Caps: **3,000** observations and **2,500** objects. When a cap is hit, show `st.warning("Showing first N of M; narrow the filters")` and log a WARNING.

**Page "Review queue":** the existing screen, moved into a function.

- F3: the queue query adds `AND <filter_sql(kind="observation")>` against the `review_queue` columns. The counters show both the filtered and the total "Awaiting review".
- F2: the per-item map shows DivIcon squares for the candidate and the runner-up; the observation stays a red dot.
- Everything else (decision write-back, ICD 203) is unchanged.

**Dependencies.**

- F3: `app/requirements.txt` needs `streamlit>=1.36` for `st.navigation`. folium already includes `plugins.MarkerCluster`.
- F2: add `"app"` to the pytest `pythonpath` in `pyproject.toml`. `helpers.py` and `icons.py` must not import streamlit or folium, so no new dev dependencies are needed. basedpyright keeps excluding `app`.

### 5.5 Logging (F1)

**Databricks constraints** (repeat these in the `log.py` docstring):

- **No file logs.** Serverless notebooks expose no driver log files to the user, and Databricks Apps capture only stdout and stderr (into the **Logs** tab). Stream to stdout; no file handlers anywhere.
- **Pre-configured root logger.** Notebook Python has Databricks handlers on the root logger. `logging.basicConfig()` is a no-op without `force=True`, and forcing it would clobber the platform handlers. So the pipeline uses a **named logger `obj_resolution`** with `propagate=False` and a single `StreamHandler(sys.stdout)`.
- **Re-runs.** `%autoreload` and re-run cells re-import modules, so setup must be idempotent: look for an existing handler tagged with a marker attribute.
- **Noise.** Set `py4j`, `urllib3` and `databricks.sql` to WARNING.

**`notebooks/pipeline/log.py`:**

- `configure_logging(level: str | int = "INFO") -> logging.Logger`:
  - sets up the `obj_resolution` logger once;
  - format `"%(asctime)s %(levelname)s %(name)s: %(message)s"`, `datefmt="%Y-%m-%dT%H:%M:%SZ"`, `converter = time.gmtime` (ISO-8601 UTC);
  - level from the env var `LOG_LEVEL`, else INFO.
- `get_logger(name) -> logging.Logger` returns `logging.getLogger(f"obj_resolution.{name}")`. Each module calls `log = get_logger(__name__.rsplit(".", 1)[-1])`.
- `stage_timer(log, stage)` is a context manager:
  - logs INFO `"<stage> started"`, then `"<stage> finished in X.Xs"`;
  - on an exception, calls `log.exception("<stage> failed after X.Xs")` and re-raises;
  - goes inside each stage function body, so standalone runs log too.
- `generate_data.py` adds a `log_level` widget (default INFO) and calls `configure_logging(dbutils.widgets.get("log_level"))` in the setup cell.

**App:**

- `app.py` calls `logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format=<same>, stream=sys.stdout, force=True)`; `force` is safe in the app process.
- The logger is named `obj_resolution.app`.
- `app.yaml` gets `LOG_LEVEL: INFO`.

**Levels.** Log only useful events, never per-row:

- **INFO:**
  - stage start, finish and duration;
  - generated counts per COCOM and type;
  - `COPY INTO` results and row counts per batch;
  - CCO triples and classes;
  - candidate-pair counts and label balance;
  - held-out metrics and the registered model version;
  - band counts;
  - nomination count and recovered observations;
  - OMS before/after write-back;
  - review queue size;
  - decisions recorded (obs, object, decision, confidence, who), in both `adjudicate` and the app;
  - Genie create or update;
  - app start (schema, warehouse id).
- **DEBUG:** app `run()` query label, row count and elapsed ms; filter values per rerun; label-propagation iteration counts; generated view SQL (one line).
- **WARNING:** dossier falls back to the template; Genie etag bypass and the "hide columns in UI" note; map caps hit; an already-adjudicated observation submitted again.
- **ERROR:** via `log.exception`, in `stage_timer` and around app SQL calls (before `st.error`).

**Kept as `print`/`display`:** the cheat-card JSON (last cell), the 10b form instructions and results, and the dossier text (`dossier.py:121`). These are the demo's visible output, not diagnostics.

### 5.6 Demo companion notebook: `notebooks/demo_companion.py` (F7)

The notebook is in Databricks source format and read-only, so it is idempotent. The first cell is markdown saying what it is and that it pairs with `demo/10-minute-script.md`. F7 builds only the sections backed by tables that exist when it lands; F5 and F6 add their parts later. Sections follow the script's timings:

0. **Setup:**
   - `%pip install -q folium`, then `%pip install -e <repo>` if needed, mirroring `generate_data.py`;
   - `Config.from_spark`, `configure_logging` and `heroes.load_heroes`;
   - widgets for the app, Genie space and dashboard URLs, rendered as links. Look up the Genie space id via `genie.py` if feasible.
1. **Workflow diagram:** the script's Mermaid flowchart, rendered via `displayHTML` with `mermaid@10.9.1` from jsdelivr, followed by a plain-text fallback in a markdown cell.
2. **0:00 to 2:30, governed picture:**
   - the table list with row counts;
   - a `bronze_observations` sample with `source_file` and `ingested_at`;
   - objects by COCOM × type (F5), as `display` plus a bar chart;
   - example attributes from `map_objects` with `attr_source_ref` (F6).
3. **2:30 to 4:30, routine work:** SQL equivalents of the Genie questions (band counts and percentages; nominations and recovered observations), plus a `display()` chart of `dash_decisions`.
4. **4:30 to 7:30, analyst:**
   - the hero B card: candidate vs runner-up, distances, likelihood terms, attributes;
   - a folium map with the same square icons, using a tiny duplicate of the icon helper in `present.py` so the app stays deployable on its own;
   - the review-decision SQL, to show the write landed.
5. **7:30 to 8:30, leaders:** the "AFVs observed in the last 7 days by COCOM" SQL, and possible duplicates.
6. **Hero cards A, B and C** and the cheat card, read from `demo_heroes`, `dash_decisions` and `gold_nominations`. Nothing is hard-coded.
7. **Recovery:** a pointer to `generate_data.py` 10b and the notes from the script's "If you're running long" table.

## 6. Test plan

Tests live in `tests/unit/` and run with `uv run pytest`. Each feature creates a shared test file if it does not exist yet.

### `test_log.py` (new)

| F   | Test                                 | Asserts                                                                                               |
| --- | ------------------------------------ | ----------------------------------------------------------------------------------------------------- |
| F1  | `test_configure_logging_idempotent`  | Two calls → exactly one handler on `obj_resolution`; `propagate is False`                             |
| F1  | `test_log_format_iso_utc`            | Formatted record matches `^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ (INFO\|DEBUG…) obj_resolution\.x: msg$`    |
| F1  | `test_stage_timer_logs_and_reraises` | `caplog` holds "started" and "finished"; on an exception, ERROR "failed" and the exception propagates |

### `test_app_helpers.py` (new; imports `helpers` and `icons` from `app/`)

| F      | Test                                          | Asserts                                                                                                      |
| ------ | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| F2     | `test_object_types_match_leaves`              | `helpers.OBJECT_TYPES == icons.OBJECT_TYPES == synthetic.LEAVES`                                             |
| F2     | `test_icon_for_every_leaf`                    | `set(ICON_SVG) == set(LEAVES)`; each value parses with `xml.etree` and has root `svg`                        |
| F2     | `test_icon_html_is_square`                    | `object_icon_html(...)` has equal width and height and contains the SVG; an unknown type uses `FALLBACK_SVG` |
| F2     | Ported helpers                                | `coords`, `object_label` (raises without designator), `distance_m`, `time_ago`, `type_agreement`             |
| F3     | `test_filter_sql_empty_is_true`               | No selections → `("TRUE", {})`                                                                               |
| F3, F5 | `test_filter_sql_params_only`                 | Selected types (F3) and COCOMs (F5) appear in `params`, never in the SQL text                                |
| F3, F5 | `test_filter_sql_rejects_unknown`             | An unknown type (F3) or COCOM (F5) raises `ValueError`                                                       |
| F4     | `test_filter_sql_object_ignores_dates`        | With dates set, `kind="object"` has no `obs_time` and no date params                                         |
| F4     | `test_filter_sql_observation_dates_inclusive` | `obs_time >= :start` and `< :end_excl`; `end_excl == end + 1 day`                                            |

### `test_synthetic_attrs.py` (new)

| F   | Test                                      | Asserts                                                                                                                                                            |
| --- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| F4  | `test_obs_window_30_days`                 | `now − 30 d ≤ obs_time ≤ now`; the spread exceeds 7 days                                                                                                           |
| F4  | `test_last_seen_before_window`            | `first_seen < last_seen < now − 30 d`                                                                                                                              |
| F5  | `test_aois_one_per_cocom_no_overlap`      | 6 AOIs; their `cocom` set equals the 6 geographic COCOMs; no two boxes intersect; each is 0.5° × 0.5°                                                              |
| F5  | `test_cocom_of_inside_and_outside`        | Centre of each box → its COCOM; a point outside all boxes → `None`; min inclusive, max exclusive                                                                   |
| F5  | `test_all_points_inside_an_aoi`           | Every object and observation (incl. twins, partial far, noise) has a non-None `cocom_of(lat, lon)`; `objects.cocom == cocom_of(...)`                               |
| F5  | `test_every_cocom_has_every_type`         | `objects.groupby(["cocom", "object_type"])` covers 6 × 5                                                                                                           |
| F6  | `test_vehicle_attributes_from_weg`        | Vehicles have non-null model, function and origin; `(object_type, model_name)` ∈ `weg.CATALOG`; `attr_source == "WEG"`; `attr_source_ref` non-empty                |
| F6  | `test_facility_attributes_from_cco`       | `model_name` ∈ `FACILITY_MODELS[type]`; `country_of_origin` is null; `attr_source == "CCO"`; `attr_source_ref` starts with `https://www.commoncoreontologies.org/` |
| F6  | `test_weg_catalog_weights`                | Weights sum to 1 per type; AFV `cco_subclass` ∈ {Tank, Infantry Fighting Vehicle, Armored Personnel Carrier}                                                       |
| F6  | `test_model_distribution_follows_weights` | Observed model shares within ±0.06 of the weights, per vehicle type                                                                                                |
| F6  | `test_duplicate_twins_share_model`        | For `twins.is_duplicate`, the twin's `model_name` equals the original's                                                                                            |

### `test_ontology_attrs.py` (new; parses the TTL, about 10 s, mark `slow` if needed)

| F   | Test                                      | Asserts                                                                                                |
| --- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| F6  | `test_facility_models_are_cco_subclasses` | Each `FACILITY_MODELS` label (other than the type itself) is an `rdfs:subClassOf` its type's CCO class |
| F6  | `test_attr_source_refs_resolve`           | Every facility `attr_source_ref` IRI exists in the TTL with the matching label                         |
| F6  | `test_afv_subclasses_exist`               | `weg.CATALOG` AFV `cco_subclass` labels exist under Armored Fighting Vehicle                           |

### `test_pipeline.py` (existing)

- Must keep passing after every feature:
  - `test_generate_is_deterministic` (2,025 objects, equal frames, including the new columns);
  - `test_seeded_cases_follow_spec`;
  - `test_reports_entered_after_collection_and_before_now`;
  - `test_parse_genie_examples` (exactly 16 examples, numbered 1 to 16; F3 to F6 edit `genie-space.md`).
- New (F3): `test_present_display_type_rule`, if `display_type` is built in Python (`present.display_type_sql()`). It checks that the fragment references each of `LEAVES` and `'Unidentified'`.

### In-notebook asserts (validated on Databricks)

- F3, `present.create_dashboard_views`: every `map_observations.display_type` ∈ `LEAVES ∪ {'Unidentified'}`. F5 adds: no null `cocom`.
- F5, `synthetic.write_sources`: no object has a null `cocom`.
- F6, `ontology.load_cco`: facility `model_name` labels are CCO subclasses of their type, and the AFV `cco_subclass` labels exist.

## 7. Feature tasks

`[ ]` todo · `[x]` done.

### F1: Stdlib logging (pipeline and app)

**Needs** — · **Estimate** Low / M · **Design** §5.5 · **Tests** `test_log.py` · **Acceptance** 7

- [ ] F1.1 Spec:
  - `AGENTS.md` › Decisions already made: add "Logging: stdlib `logging` to stdout (named `obj_resolution` logger); `print` only for user-facing notebook output".
  - `02-architecture.md`: add one paragraph on logging.
- [ ] F1.2 Write the tests (failing).
- [ ] F1.3 `notebooks/pipeline/log.py`.
- [ ] F1.4 Replace the `print` sites (§4) with logger calls at the levels in §5.5. Wrap each stage function body in `stage_timer`.
- [ ] F1.5 `generate_data.py`:
  - add the `log_level` widget and call `configure_logging` in the setup cell;
  - replace `print("Using", …)` with `log.info`;
  - keep the cheat-card and 10b `print`s.
- [ ] F1.6 `app/app.py`:
  - logging setup;
  - INFO logs for startup and decisions;
  - `run()` gets a `label` argument, DEBUG timing, and `log.exception` before `st.error`;
  - `app/app.yaml`: add `LOG_LEVEL: INFO`.
- [ ] F1.7 Databricks:
  - run `generate_data.py`: ISO-UTC lines with stage durations appear in the cell output;
  - redeploy the app and check the Logs tab: INFO on, DEBUG off.
- [ ] F1.8 Commit `feat: stdlib logging for pipeline and app`.

### F2: Square type icons on the review map

**Needs** — · **Estimate** Low / S · **Design** §5.4 (icons, shared type list) · **Tests** `test_app_helpers.py` F2 rows · **Acceptance** 1 (review map)

- [ ] F2.1 Spec: `AGENTS.md`:
  - Decisions: add "Map icons: Tabler Icons (MIT), inlined SVG";
  - Layout: add `app/helpers.py` and `app/icons.py`.
- [ ] F2.2 `pyproject.toml`: add `"app"` to the pytest `pythonpath`. Write the tests (failing).
- [ ] F2.3 `app/icons.py`:
  - download the 6 SVGs from `@tabler/icons@3.19.0` (verify `help-square` first);
  - inline them as constants;
  - add the MIT license header, `ICON_SVG` and `FALLBACK_SVG`.
- [ ] F2.4 `app/helpers.py`: move the pure helpers out of `app.py` unchanged; add `OBJECT_TYPES` and `object_icon_html`.
- [ ] F2.5 `app/app.py`: DivIcon squares for the candidate and the runner-up on the per-item map, plus the legend caption.
- [ ] F2.6 Redeploy the app and check each type's icon and the fallback on a nominated candidate.
- [ ] F2.7 Commit `feat(app): square type icons on the review map`.

### F3: Operating picture page and type filter

**Needs** F2 · **Estimate** High / L · **Design** §5.1 (`display_type`), §5.3, §5.4 · **Tests** `test_app_helpers.py` F3 rows, `test_present_display_type_rule` · **Acceptance** 1, 4

- [ ] F3.1 Spec:
  - `03-data-model.md` §3: add the views `map_objects` and `map_observations` and the `display_type` rule;
  - `04-build-plan.md`: add a pre-demo check of the app map page.
- [ ] F3.2 Write the tests (failing).
- [ ] F3.3 Views:
  - `present.create_dashboard_views`: add `map_objects` and `map_observations` (without `cocom`) and the `display_type` assert;
  - `review.create_review_views`: add `display_type` to `review_queue`.
- [ ] F3.4 App:
  - `filter_sql(kind, *, types=())`;
  - `st.navigation` with `operating_picture()` and `review_queue()`;
  - the sidebar type filter;
  - the Operating picture page;
  - the filtered queue with filtered and total counters;
  - an updated module docstring;
  - `streamlit>=1.36` in `requirements.txt`.
- [ ] F3.5 Genie:
  - `genie.py`: add `map_objects` and `map_observations` to the space's tables, if the list lives in code;
  - `demo/genie-space.md`: mention both views in the instructions.
- [ ] F3.6 `demo/10-minute-script.md`, 4:30 to 7:30:
  - open the **Operating picture**, filter to AFVs, then switch to the Review queue for case B;
  - add 30 s here and cut 30 s from 2:30.
- [ ] F3.7 Databricks:
  - re-run from the views stage and redeploy the app;
  - check both pages, the type filter on both, and the caps.
- [ ] F3.8 Commit `feat: operating picture map page with object type filter`.

### F4: 30-day window and date filter

**Needs** F3 · **Estimate** Medium / M · **Design** §5.1 (time window), §5.4 (dates) · **Tests** `test_synthetic_attrs.py` and `test_app_helpers.py` F4 rows · **Acceptance** 3

- [ ] F4.1 Spec:
  - `03-data-model.md` §4: the 30-day window, `last_seen` before the window, and the tasking windows;
  - a "stale until re-run" banner on 03 §6 and on the numbers in `demo/10-minute-script.md`;
  - `02-architecture.md`: one paragraph on the window.
- [ ] F4.2 Write the tests (failing).
- [ ] F4.3 `synthetic.py`:
  - add `OBS_WINDOW_H`;
  - change `obs_time`, `last_seen`, `first_seen` and the tasking windows per §5.1;
  - fix the "72 hours" docstrings.
- [ ] F4.4 App:
  - `filter_sql(..., start=None, end=None)`;
  - the sidebar date inputs, applied to the map and the queue.
- [ ] F4.5 Demo docs: "72 hours" → "7 days" in `demo/genie-space.md` (still 16 examples) and in `demo/10-minute-script.md`.
- [ ] F4.6 Databricks:
  - run `generate_data.py` and check the heroes as in F5.8;
  - if F5 is not shipping right after, do the number refresh (F5.9) now.
- [ ] F4.7 Commit `feat: 30-day observation window and date filter`.

### F5: Six COCOM AOIs and COCOM filter

**Needs** F3 · **Estimate** High / XL · **Design** §5.1 (COCOM areas), §5.3, §5.4 (COCOM) · **Tests** `test_synthetic_attrs.py` and `test_app_helpers.py` F5 rows · **Acceptance** 2, 5

- [ ] F5.1 Spec:
  - `03-data-model.md` §3: `cocom_aoi`, `oms_objects.cocom`, and `cocom` in the views;
  - 03 §4: the 6 AOIs and the inner margin;
  - stale banners, as in F4.1, if not already present;
  - `02-architecture.md`: one paragraph on the COCOM spread.
- [ ] F5.2 Write the tests (failing).
- [ ] F5.3 Data:
  - `synthetic.py`: add the `Aoi` dataclass, `AOIS`, `COCOMS`, `cocom_of` and `random_point(rng, aoi, margin=0.05)`;
  - replace all `BBOX` draws; keep `BBOX` as a NORTHCOM alias only if something still imports it (grep first);
  - add the `cocom` column;
  - `write_sources`: write `cocom_aoi` and assert no null `cocom`;
  - `ingest.py`: add `cocom` to the `COPY INTO` column list.
- [ ] F5.4 `nominate.write_back`: the MERGE insert takes `cocom` from a `cocom_aoi` bbox join on the nomination centroid.
- [ ] F5.5 Views and dossier:
  - add `cocom` to every view in §5.3, plus its assert;
  - `dossier.py`: add COCOM to the object facts.
- [ ] F5.6 App:
  - `filter_sql(..., cocoms=())`;
  - the COCOM multiselect;
  - COCOM in the tooltips;
  - apply the filter to the map and the queue.
- [ ] F5.7 Demo docs:
  - `genie.py` and `genie-space.md`: add `cocom_aoi`;
  - replace one weaker example with "How many objects are in each COCOM, by type?" (still 16);
  - script: filter the Operating picture to one COCOM;
  - if F7 has landed: add the COCOM × type chart to the companion.
- [ ] F5.8 Databricks: run `generate_data.py`, then check:
  - Heroes: hero A is an AFV with 4+ observations and p > 0.95; hero B is a look-alike twin review case. Relax the selection order only if needed, and document it in 03.
  - REVIEW size: if REVIEW drops below about 80 rows, raise `N_TWIN` (e.g. 25 → 40) and record it in 03 §4.
- [ ] F5.9 Number refresh:
  - copy the measured numbers, hero IDs and compute time into 03 §6, `02-architecture.md` and `demo/10-minute-script.md` (every number reference and the hero sticky-note line);
  - remove the stale banners.
- [ ] F5.10 Commit:
  - `feat: COCOM AOIs and COCOM filter`;
  - `docs: measured results after 08 F4/F5` for F5.9.

### F6: WEG/CCO object attributes

**Needs** — · **Estimate** Medium / L · **Design** §5.1 (object attributes, random streams), §5.2 · **Tests** `test_synthetic_attrs.py` F6 rows, `test_ontology_attrs.py` · **Acceptance** 6

- [ ] F6.1 Spec: `AGENTS.md` › Project Guidelines › Data, replace the rule with:
  > **Data**: synthetic only. Real attribute values (equipment names, roles, countries of origin, facility classes and functions) are allowed **only** when taken from the public Worldwide Equipment Guide (<https://odin.t2com.army.mil/>) or the CCO/BFO ontologies, with the source recorded per value (`attr_source`, `attr_source_ref`). Never add other real or sensitive data, schemas or statistics, and no equipment performance figures.

  Also `03-data-model.md`: §3 the new `oms_objects` columns; §4 the WEG and facility weights.
- [ ] F6.2 Write the tests (failing).
- [ ] F6.3 `weg.py`:
  - verify the candidates on ODIN (or in the WEG PDFs) and record each `weg_ref`;
  - write `CATALOG`, `FACILITY_MODELS` and `FACILITY_FUNCTION`, with docstrings and a source note;
  - if the WEG is unreachable for more than 10 min, stop and ask the user.
- [ ] F6.4 Pipeline:
  - `synthetic.py`: attribute draws from `default_rng(seed + 4)`, with duplicates copying from their original;
  - `ingest.py`: update the column list;
  - `nominate.write_back`: insert NULLs for the attribute columns.
- [ ] F6.5 `ontology.load_cco`: add the facility and AFV subclass asserts.
- [ ] F6.6 Dossier and app:
  - `dossier.py`: model, function and origin in the object facts and the template fallback;
  - if F3 has landed: attributes in the Operating picture tooltips and the review candidate card.
- [ ] F6.7 Demo docs:
  - `genie-space.md`: add the attribute columns;
  - replace one weaker example with "Which equipment models were observed in the last 7 days?" (add "in EUCOM" if F5 has landed; still 16);
  - if F7 has landed: add the attribute examples to the companion.
- [ ] F6.8 Databricks: run `generate_data.py`; the asserts pass and the measured numbers do not change.
- [ ] F6.9 Commit `feat: WEG/CCO object attributes`.

### F7: Demo companion notebook

**Needs** — · **Estimate** Medium / M · **Design** §5.6 · **Tests** none (read-only notebook) · **Acceptance** 8

- [ ] F7.1 Spec: `AGENTS.md` › Layout: add `notebooks/demo_companion.py`.
- [ ] F7.2 Write `notebooks/demo_companion.py`:
  - only the sections backed by tables that exist;
  - the icon map only if F2 has landed.
- [ ] F7.3 `demo/10-minute-script.md`: add a "Companion: `notebooks/demo_companion.py`" line in *Before you start*.
- [ ] F7.4 Databricks: run the notebook top to bottom.
- [ ] F7.5 Commit `feat: demo companion notebook`.

### Close-out (after all features)

- [ ] Z1 Full run on Free Edition:
  - `generate_data.py`, then `demo_companion.py`, then an app redeploy;
  - walk through every criterion in §8.
- [ ] Z2 Mark this file **done**.

## 8. Acceptance criteria

1. (F2, F3) Every object on both app maps is a square with the Tabler icon for its type; nominated or unknown objects use the fallback icon; the legend explains the border colours.
2. (F5) The COCOM filter narrows objects and observations, on the map and in the review queue.
3. (F4) The date range changes the observation counts only; object counts are unchanged.
4. (F3) The type filter narrows objects (by `object_type`) and observations (by `display_type`); "Unidentified" is selectable.
5. (F5) All 6 COCOMs × 5 types are present in `map_objects`.
6. (F6) Vehicle attributes trace to WEG (`attr_source_ref`) and facility attributes to CCO IRIs. There are no other real values and no performance figures.
7. (F1) A pipeline run shows ISO-UTC stdlib log lines with stage durations in the cell output. The app Logs tab shows INFO lines for startup and decisions. The only `print`s left are the cheat card, the 10b form and the dossier text.
8. (F7) `demo_companion.py` runs top to bottom and renders the workflow diagram, charts, maps and hero cards from tables.
9. (all) The definition of done in §3 holds.
10. (all; numbers in F5.9) Docs (03, 02, 10-minute script, Genie space) match the latest run.

## 9. Risks and mitigations

| Risk                                                                               | Mitigation                                                                                      |
| ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Every measured number and hero ID changes (F4, F5)                                 | Expected. Stale banners until F5.9 refreshes the docs                                           |
| A smaller REVIEW queue, because each AOI is a sixth as dense                       | Raise `N_TWIN` (F5.8); do not tune thresholds                                                   |
| ODIN WEG needs a login or is unreachable                                           | Use the public WEG PDFs; record the ref; drop unverifiable systems                              |
| `st_folium` is slow with thousands of markers                                      | MarkerCluster plus the 3,000 / 2,500 caps with a warning; rehearse with no filters              |
| The Databricks Apps runtime has Streamlit < 1.36                                   | Pin it in `requirements.txt`; on failure, fall back to `st.radio` page switching in the sidebar |
| The Mermaid CDN is blocked in `displayHTML`                                        | Plain-text diagram cell directly below                                                          |
| Logging handlers duplicate on autoreload                                           | Marker-attribute idempotence plus a unit test                                                   |
| Nomination centroids fall just outside an AOI and get a null `cocom`               | Inner margin; the in-notebook assert fails fast                                                 |
| Real-named foreign equipment placed in allied territory reads oddly to an audience | Say "synthetic placement" in the script; the AOIs are arbitrary land boxes, not real sites      |

## 10. Out of scope

Events as objects, mass and length qualities, a retrain run, real AOR polygons (bbox AOIs only), Lakeview dashboard JSON in the repo (the dashboard stays hand-built from the views), and any Splink, GraphFrames, Vector Search or CV.

## 11. Progress log

| Date       | Task | Note                                                                                      |
| ---------- | ---- | ----------------------------------------------------------------------------------------- |
| 2026-10-13 | —    | Plan written; nothing started                                                             |
| 2026-10-13 | —    | Task breakdown regrouped into independently deliverable features F1 to F7                 |
| 2026-10-13 | —    | Plan reorganized for handoff: feature overview first, design and tests tagged per feature |
