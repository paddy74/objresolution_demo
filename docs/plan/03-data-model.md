# 03: Data model

Purpose: the canonical tables, CCO classes and seeded cases the live build must produce, so the demo shows recovered data, a real review queue and a sourced dossier. This file is the source of truth for table names, thresholds and hero objects; files 01, 02 and 04–07 must match it.

All data is synthetic. Every number in this file marked `~` is an expected value from the notebook's generator parameters, **not** a measured result. Replace with measured values after a notebook run.

## 1. Type taxonomy decision

Object types are **CCO-native labels**, verified against `data/ontology/CommonCoreOntologiesMerged.ttl` (version IRI `https://www.commoncoreontologies.org/2026-08-13/CommonCoreOntologiesMerged`). Type compatibility is computed from `cco_classes.ancestor_iris` (the rdflib flatten), not from a hand-built taxonomy, so "ontology-conformant" is a true claim.

Where CCO's label differs from the everyday name:

| Everyday name                                         | CCO label used             | Note                                                                                                                            |
| ----------------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Airfield                                              | `Airport`                  |                                                                                                                                 |
| Radar site                                            | `Military Facility`        | CCO has only radar *imaging artifact functions*, no radar-site class                                                            |
| Fixed-wing aircraft                                   | `Aircraft`                 | No fixed-wing subclass                                                                                                          |
| Armored vehicle                                       | `Armored Fighting Vehicle` |                                                                                                                                 |
| Artifact (generic root)                               | `Material Artifact`        |                                                                                                                                 |
| Facility / Ground Vehicle / Vehicle (generic parents) | same labels                | In CCO, `Aircraft` is a child of `Vehicle`, not a sibling-parent, so ancestors are derived from `cco_classes`, never hand-built |

A small hand-built `type_ancestors` table is the fallback only if the flatten breaks.

Test: the pipeline notebook asserts that all 5 leaves and 3 generics resolve to exactly one IRI each.

## 2. Chosen CCO / BFO classes

IRIs verified by grep against the local `.ttl`. CCO IRIs have the form `https://www.commoncoreontologies.org/<id>`; BFO IRIs have the form `http://purl.obolibrary.org/obo/BFO_<id>`.

### Object types (the core entity)
| Role in demo                              | CCO label                | IRI                                                | Parent chain (verified)                                                                                                              |
| ----------------------------------------- | ------------------------ | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Leaf: facility                            | Airport                  | `https://www.commoncoreontologies.org/ont00001078` | Transportation Facility `ont00000226` → Facility `ont00000192` → Material Artifact `ont00000995` → BFO material entity `BFO_0000040` |
| Leaf: facility                            | Military Facility        | `https://www.commoncoreontologies.org/ont00001052` | Facility `ont00000192` → Material Artifact                                                                                           |
| Leaf: equipment                           | Truck                    | `https://www.commoncoreontologies.org/ont00000606` | Ground Motor Vehicle `ont00000053` → Ground Vehicle `ont00000618` → Vehicle `ont00000713` → Material Artifact                        |
| Leaf: equipment                           | Armored Fighting Vehicle | `https://www.commoncoreontologies.org/ont00000427` | Ground Motor Vehicle `ont00000053` → Ground Vehicle → Vehicle                                                                        |
| Leaf: equipment                           | Aircraft                 | `https://www.commoncoreontologies.org/ont00001043` | Vehicle `ont00000713` → Material Artifact                                                                                            |
| Generic (what a weak observation reports) | Facility                 | `https://www.commoncoreontologies.org/ont00000192` |                                                                                                                                      |
| Generic                                   | Ground Vehicle           | `https://www.commoncoreontologies.org/ont00000618` |                                                                                                                                      |
| Generic                                   | Vehicle                  | `https://www.commoncoreontologies.org/ont00000713` |                                                                                                                                      |

### Supporting classes (data-model alignment, not used as match types)
| Use                             | CCO label          | IRI                                                |
| ------------------------------- | ------------------ | -------------------------------------------------- |
| An observation record           | Act of Observation | `https://www.commoncoreontologies.org/ont00000037` |
| Finished report text            | Report             | `https://www.commoncoreontologies.org/ont00002043` |
| Collection sensor               | Sensor             | `https://www.commoncoreontologies.org/ont00000569` |
| Area of interest / tasking area | Geospatial Region  | `https://www.commoncoreontologies.org/ont00000472` |

### Not in scope for the build
- **Events** (the core entity is "facility, equipment, event"): out of scope for the initial build. Say so, and say the same pipeline applies to events with BFO `process` / CCO `Act` classes. I did not verify specific event IRIs, so do not cite any.
- Equipment generic **"Ground Motor Vehicle"** (`ont00000053`) is also a valid generic report type. Include it only if time allows.

### What the type compatibility rule does with these classes
- Observation type = object type → `type_score` 1.0
- Observation type is an ancestor of the object type (for example `Vehicle` vs `Truck`) → 0.8, "compatible but generic"
- Observation type missing → 0.5, and `type_missing = 1` as its own feature
- Otherwise (siblings or unrelated, for example `Military Facility` vs `Airport`) → 0.0, which is blocked from the candidate set
- **Deliberate ambiguity:** a generic `Vehicle` observation is an ancestor of Truck, Armored Fighting Vehicle *and* Aircraft, so it matches all three at 0.8. This is a feature, not a bug. It generates real REVIEW cases.

Illustrative only (not code to commit): `type_score` comes from `array_contains(cco.ancestor_iris, obs_type_iri)` joined on the object's type IRI. All type scores must be cast to DOUBLE (see the Decimal/MLflow note in file 04).

## 3. Tables

Naming follows the pipeline notebook (`<catalog>.<schema>.<table>`; schema `objresolution_demo`). Layers: bronze = landed as-is plus lineage columns, silver = joined and scored, gold = what the analyst and the object system consume.

### Layer 1: sources (mocked) and bronze
| Table / file                                                | Mocks                                                     | Source type       | Key columns                                                                                                                                                                                                                                                              | Ingest                                                                                                                        |
| ----------------------------------------------------------- | --------------------------------------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `oms_objects`                                               | Postgres object management system (authoritative objects) | Relational        | `object_id` PK, `object_type` (CCO label), `object_type_iri`, `designator` (e.g. `Bravo-12`; nominations get `New-001`…), `designator_type` (CCO Arbitrary Identifier IRI), `lat`, `lon`, `marking`, `first_seen`, `last_seen`, `obs_count`, `source`, `status`          | Written directly as Delta; production path is Lakehouse Federation or CDC (**untested on Free Edition; do not claim it ran**) |
| `landing/tasking/*.csv` → `bronze_tasking`                  | MySQL collection/tasking records                          | Relational export | `task_id`, `sensor`, `area_wkt` or bbox, `start_time`, `end_time`, `requested_by`, `priority`, `source_file`, `ingested_at`                                                                                                                                              | `COPY INTO` (CSV)                                                                                                             |
| `landing/observations/batch_*.json` → `bronze_observations` | SaaS/API algorithm and analyst feeds                      | JSON API export   | `obs_id` PK, `obs_time`, `lat`, `lon`, `reported_type`, `confidence` (machine score; NULL for analysts), `likelihood` (ICD 203 term), `producer` (`algorithm`/`analyst`), `sensor` (`EO`/`SAR`/`FMV`), `source_file`, `ingested_at`, **`true_object_id` (scoring only)** | `COPY INTO` (incremental and idempotent)                                                                                      |
| `landing/reports/*.json` → `bronze_reports`                 | Finished report text                                      | Documents         | `report_id`, `object_id` (nullable), `obs_id` (nullable), `report_text`, `report_time`, `source_file`, `ingested_at`                                                                                                                                                     | `COPY INTO`                                                                                                                   |
| `cco_classes`                                               | CCO via rdflib                                            | Ontology          | `iri`, `label`, `parent_iris`, `ancestor_iris`                                                                                                                                                                                                                           | rdflib flatten (runs in the pipeline notebook)                                                                                |

- Two required source *types* are met by relational (OMS + tasking) plus JSON feed. Reports add a document source.
- `true_object_id` is **never** a model feature. It stands in for past analyst adjudications when generating labels, and for scoring the demo. A link to a seeded duplicate record (`dup_of`) counts as a match, because both records are the same object. Say this out loud in the demo. In production the labels come from the review queue (`review_decisions`).
- `marking` values are `OPEN` / `RESTRICTED`, so nobody mistakes them for real classification banners.

### Layer 2: silver
| Table                                             | Built from                                                                 | Key columns                                                                                                                                                   |
| ------------------------------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `silver_candidate_pairs`                          | H3 blocking (res 8, `h3_kring` 1) on `bronze_observations` × `oms_objects` | `obs_id`, `object_id`, `dist_m`, `type_score`, `type_missing`, `likelihood_rank`, `is_analyst`, `n_candidates`, `dist_gap_m`, `days_since_last_seen`, `label` |
| `silver_model_decisions`                          | Model scoring, best candidate per observation                              | `obs_id`, `matched_object_id`, `match_prob`, `decision` (`AUTO` ≥ 0.9, `REVIEW` 0.5–0.9, `NOMINATE` < 0.5 or no candidate), `model_version`                   |
| MLflow run + UC model `objresolution_match_model` | `HistGradientBoostingClassifier` on `silver_candidate_pairs`               | Registration needs DOUBLE-cast features and an explicit signature                                                                                             |

Features (all DOUBLE): `dist_m`, `type_score`, `type_missing`, `likelihood_rank`, `is_analyst`, `n_candidates`, `dist_gap_m`, `days_since_last_seen`. Do not add features without updating this spec.

- `likelihood_rank`: the source's ICD 203 likelihood term as 1 (almost no chance) to 7 (almost certain), so machine scores and analyst terms share one scale.
- `n_candidates`: candidate objects for the same observation (within 500 m, compatible type), including this one.
- `dist_gap_m`: this pair's distance minus the nearest other candidate's; negative means this object is the closest, and -500 means no competitor. It stands in for the runner-up score gap, which cannot be a feature because it needs the model's own scores.
- `days_since_last_seen`: days from the object's `last_seen` to the observation, floored at 0. Synthetic assumption: objects that are still observed were last seen 1 to 14 days ago, others 1 to 30 days ago (separate random seed, so the observations do not change).
- Times: `obs_time` is when the intel behind an observation was collected; `report_time` is when the record was entered by an analyst or machine. Synthetic delay (`REPORT_DELAY_MIN` in `notebooks/pipeline/synthetic.py`): machine reports mostly within minutes (up to 2 h), analyst reports mostly within hours (up to a day), never after the present. An object's `first_seen` / `last_seen` are `obs_time` values (write-back and analyst approval use `greatest(last_seen, obs_time)`), never report or processing times.
- ICD 203 (`notebooks/pipeline/icd203.py`): a machine result always keeps its numeric score and is shown as the likelihood term for its range (almost no chance <5%, very unlikely 5-20%, unlikely 20-45%, roughly even chance 45-55%, likely 55-80%, very likely 80-95%, almost certain >=95%; each band includes its lower bound). An analyst never enters a number: observations carry a likelihood term, and review judgements carry a confidence (High, Moderate, Low) in `review_decisions.confidence`, required by the app and `adjudicate`. Likelihood and confidence are never combined in one statement. CCO: likelihood is a Probability Measurement ICE (ont00000692); confidence has no CCO class (local extension). Synthetic sources are less sure of noise and of generic or missing types (`MACHINE_SCORE`, `ANALYST_TERM` in `synthetic.py`, separate random seed).

### Layer 2 → 3: gold
| Table                                                                             | Built from                                                                     | Key columns                                                                |
| --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| `nom_edges`, `cc_0`, `cc_1`, `cc_final`                                           | Label propagation over `NOMINATE` observations (runs in the pipeline notebook) | `src`/`dst`, `id`/`label`                                                  |
| `gold_nominations`                                                                | Clusters with ≥ 2 observations                                                 | `object_id` (`NOM-…`), `object_type`, `lat`, `lon`, `obs_count`            |
| `review_queue` (a view over `silver_model_decisions` where `decision = 'REVIEW'`) |                                                                                | `obs_id`, `candidate object_id`, `match_prob`, `reason`                    |
| `possible_duplicate_objects` (a view over `silver_scored_pairs`)                  | Record pairs that are each other's runner-up, within 0.2, for ≥ 2 observations | `object_id_1`, `object_id_2`, `records_apart_m`, `close_call_observations` |
| `review_decisions`                                                                | Analyst approve/reject (new, written live)                                     | `obs_id`, `object_id`, `decision`, `decided_by`, `decided_at`              |
| `oms_objects` (MERGE target)                                                      | `AUTO` associations plus nominations plus approved reviews                     | adds rows with `source = 'DATABRICKS_NOMINATION'`, `status = 'NOMINATED'`  |
| `silver_reports` / `object_dossiers`                                              | `ai_query` over observations, scores and `bronze_reports` for one object       | `object_id`, `dossier_text`, `cited_ids`, `generated_at`                   |

`review_decisions` is the retraining loop: approved and rejected pairs become new `label` values for `silver_candidate_pairs` on the next training run. In the demo, show the write; describe the retrain as the next step. Do not claim a retrain ran unless it did.

## 4. Generator parameters and seeded cases

### Base volumes (from the notebook; expected, not measured)
| Parameter                              | Value                                                                         | Expected result     |
| -------------------------------------- | ----------------------------------------------------------------------------- | ------------------- |
| OMS objects                            | 2,000 uniform over bbox 39.0–39.5 N, 105.5–105.0 W (arbitrary synthetic area) | ~2,000              |
| Objects with observations              | 1,500, each with 1–4 observations (mean 2.5)                                  | ~3,750 observations |
| Not in OMS (should become nominations) | 150 new objects, 2–3 observations each                                        | ~375 observations   |
| Observation noise                      | position σ 80 m (algorithm), 150 m (analyst)                                  |                     |
| Reported type                          | 70% exact, 20% generic parent, 10% missing                                    |                     |
| Producer mix / sensors                 | 70% algorithm, 30% analyst; EO, SAR, FMV                                      |                     |
| Time window                            | last 72 hours                                                                 |                     |

Expected ≈ 4,100 observations; **generated 4,662** (`synthetic.generate`; 233 of them noise). Confirm the printed `objects=…` line (expected 2,025 = 2,000 plus 25 twins).

### Seeded cases (add deliberately)
The uniform generator makes clean cases easy and REVIEW cases rare, which would leave the review queue nearly empty. Add these, then check the counts.

1. **Twin objects (about 25 pairs).** Two OMS records 150–400 m apart with compatible types (for example two Trucks, or an Armored Fighting Vehicle and a Truck). Three observations placed between them with the shared generic type (for example `Ground Vehicle`) or missing type. This is the "how many objects really are there?" case, and it produces genuine `REVIEW` rows.
2. **Duplicate-object evidence.** For 5 of the twins (same type, same 150–400 m spacing), give the same underlying `true_object_id` to observations pointing at both records (the original's ID, including observations sampled for the duplicate record). Training counts a link to either record as a match, so the model scores both high and `possible_duplicate_objects` lists the pair. This lets you say "the model surfaced that these two records may be one object"; they are flagged for an analyst, not merged, so the object count does not change.
3. **Partial single-source observations (the "discarded data" story).** For each of about 30 of the `NEW-` objects, generate 4 observations that are individually unusable: one missing type, one generic type, one specific type from an algorithm with a low score (0.40–0.55, shown under ICD 203 as unlikely or roughly even chance), and one 1–3 km away (km-scale position error). No single one passes the `AUTO` threshold or can support an analyst judgment alone. The first three cluster into one nomination; the km-off one stays unclustered, showing the pipeline does not over-merge.
4. **Low-likelihood algorithm noise.** About 5% of observations with no real object behind them (`true_object_id = NULL`), single algorithm detections placed at random, with a low source likelihood. They should stay `NOMINATE` and **not** cluster; random placement means a few may land near an object or each other.
5. **Cross-producer corroboration.** For some existing objects, add one algorithm and one analyst observation within 100 m. These are the clean `AUTO` cases.
6. **Marking mix.** Keep ~20% of OMS objects `RESTRICTED` (demo row filter).

### Hero objects (named, memorised, used in the demo)
Pick IDs after a run, and keep a one-line cheat card.
| Hero                         | Scenario                                                                                                                             | Shows                                                                                                     |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| **A: clean auto-associate**  | Armored Fighting Vehicle, 4+ observations (algorithm + analyst), match_prob > 0.95                                                   | Auto-associate, map, dossier with citations                                                               |
| **B: review**                | Look-alike twin records 150–400 m apart (case 1); a weakly typed observation between them lands in `REVIEW` (last run: 0.63 vs 0.47) | Review queue, "why this probability", approve/reject, MERGE write-back, label for retraining              |
| **C: recovered / nominated** | Nominated cluster whose observations are all weak: generic or missing type, or a weak source likelihood (last run: 6 observations)   | A new object nominated from observations that were individually discarded; "observations recovered" count |

### Checks to run after generation
- Count `AUTO` / `REVIEW` / `NOMINATE`. The measured REVIEW queue is 137 rows (2.9%, section 6); it is presented as a ranked queue, not tuned.
- Precision per decision band against `true_object_id` (the pipeline notebook prints `precision_vs_synthetic_truth`). Record the numbers after each run for the demo and slides, labelled **synthetic**.
- Nominations: `noms` and `recovered` (the notebook prints these). Report the recovered-observation count and its share of all observations.
- Confirm no `true_object_id` appears in the model features or the dossier prompt.

## 5. Open items
- Measured: see section 6 (band counts, precision per band, held-out AUC / average precision, nominations, hero IDs). Working `ai_query` endpoint: `databricks-meta-llama-3-3-70b-instruct`.
- CCO `Event` class choice: not researched; out of scope for the build.
- Whether a tasking feature (was this area tasked at the time?) improves the model: out of scope. The tasking table is used for lineage, governance and the "why no observations here?" question only.

## 6. Measured results

### Pipeline notebook run (`notebooks/generate_data.py`): the numbers to use in the demo
Synthetic data. Band precision is **in-sample**; AUC and average precision are **held-out** (grouped by observation).

| Item                       | Value                                                                                                                                  |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Observations / OMS objects | 4,662 / 2,025 seeded; 2,153 after 128 nominations are merged                                                                           |
| AUTO                       | 3,862 (82.8%), precision 0.995                                                                                                         |
| REVIEW                     | 137 (2.9%), precision 0.891 (a ranked queue; not tuned)                                                                                |
| NOMINATE                   | 663 (14.2%), precision 0.979                                                                                                           |
| Held-out                   | AUC 0.978, average precision 0.992                                                                                                     |
| Nominations / recovered    | 128 nominations, 335 observations recovered (7.2% of observations)                                                                     |
| Seeded duplicates surfaced | 5 of 5, in 6 possible-duplicate pairs (`possible_duplicate_objects`; 1 pair is not a seeded duplicate)                                 |
| Model                      | `workspace.objresolution_demo.objresolution_match_model` v8 (Unity Catalog)                                                            |
| Heroes                     | A `OBJ-01289`; B `OBJ-00443` (obs `OBS-804771865849`, look-alike `OBJ-T011`, 0.627 vs 0.466); C `NOM-57872318ae` (6 weak observations) |
| Compute                    | 3.1 minutes end to end                                                                                                                 |

No rules baseline has been run, so make no claim of an edge over rules. Hero B is a REVIEW case because 0.627 is below 0.9; the runner-up at 0.466 is the look-alike record, 0.161 behind.
