# Worldwide Equipment Guide (WEG) data

Source: ODIN Worldwide Equipment Guide (https://odin.t2com.army.mil/), full CSV export. The raw export file (`data/WorldwideEquipmentGuide.csv`) is git-ignored. As of 2026-10-13 it is 119.7 MB, 13,708 columns, and 99.7% of values are empty (`-`).

`split_weg.py` converts it losslessly into two files:

| File             | Rows    | Columns                                                                                                               |
| ---------------- | ------- | --------------------------------------------------------------------------------------------------------------------- |
| `systems.csv`    | 4,142   | `identifier` (key), `name`, `dateOfIntroduction`, `disname`, `disstring`, `origin`, `proliferation`, `domain`, `type` |
| `attributes.csv` | 131,302 | `identifier`, `attribute` (original column name), `value`                                                             |

## Formatting Rules

- UTF-8, LF line endings, RFC 4180 quoting, header row; both files sorted by `identifier` (then `attribute`).
- The placeholder `-` means "no value" and is dropped from `attributes.csv`. Other literals (`INA`, `Unknown`) are kept.
- The original column order is not preserved; values are.

## Usage

Regenerate the split files with `uv run python data/weg/split_weg.py data/WorldwideEquipmentGuide.csv data/weg/`

## Rejoining

The SQL examples assume the files are loaded as tables `weg_systems` and `weg_attributes`. A system's missing attributes come back as NULL (`NaN` in pandas), not `-`. Pivoting into all 13k+ attributes as columns is impractical, so either keep the attributes in a map or pivot only the ones you need.

Keep all attributes in a map column, with one row per system:

```sql
CREATE OR REPLACE TABLE weg_equipment AS
WITH attrs AS (
  SELECT identifier, map_from_entries(collect_list(struct(attribute, value))) AS attributes
  FROM weg_attributes
  GROUP BY identifier
)
SELECT s.*, coalesce(a.attributes, map()) AS attributes
FROM weg_systems s LEFT JOIN attrs a USING (identifier);

-- e.g. SELECT name, attributes['maximum speed'] FROM weg_equipment;
```

Pivot selected attributes into columns, in SQL:

```sql
CREATE OR REPLACE TABLE weg_equipment_wide AS
SELECT s.*, p.* EXCEPT (identifier)
FROM weg_systems s
LEFT JOIN (
  SELECT * FROM weg_attributes
  PIVOT (first(value) FOR attribute IN ('maximum speed' AS maximum_speed, 'crew' AS crew, 'weight' AS weight))
) p USING (identifier);
```

The same pivot in pandas (not a project dependency: `uv run --with pandas python ...`):

```python
import pandas as pd

# dtype=str and keep_default_na=False keep literals such as "INA" and "None" as text
systems = pd.read_csv("data/weg/systems.csv", dtype=str, keep_default_na=False)
attributes = pd.read_csv("data/weg/attributes.csv", dtype=str, keep_default_na=False)

wanted = ["maximum speed", "crew", "weight"]
wide = systems.merge(
    attributes[attributes["attribute"].isin(wanted)]
    .pivot(index="identifier", columns="attribute", values="value")
    .reset_index(),
    on="identifier",
    how="left",
)
```
