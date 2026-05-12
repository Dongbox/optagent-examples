# MG Preprocess Stage

This directory mirrors the original production layout:

```text
program/scripts/preprocess/
```

The original MG common preprocessing flow should remain in charge of creating
the model-facing SQLite tables, including:

- `t_process`
- `t_order`
- `t_process_output`
- `t_connectables`
- `t_machine`
- required `i_*` configuration tables

The OptAgent migration does not replace that common preprocessing flow. The
adapter in this directory validates that the required tables exist before the
model phase starts.

`transformer.py` keeps the original APS extension shape:

```python
from aps.preprocess import Transformer


class CustomTransformer(Transformer):
    ...


def main(in_addr: str, out_addr: str) -> bool:
    ...
```

When APS preprocessing reports invalid input data or raises an exception, the
pipeline stops before the model phase. The migration example intentionally does
not provide a validation-only fallback path; production behavior should match
the original APS handoff boundary.
