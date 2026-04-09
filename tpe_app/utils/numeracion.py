import re
from datetime import date


_NUM_YY_RE = re.compile(r"^\s*(\d+)\s*/\s*(\d{2})\s*$")


def _year_suffix(target_date: date) -> str:
    return f"{target_date.year % 100:02d}"


def next_num_yy(values: list[str | None], *, today: date | None = None, min_width: int = 2) -> str:
    """
    Genera el siguiente correlativo con formato `NN/YY` basado en valores existentes.

    - Ignora valores vacíos o con formato distinto.
    - Solo considera el año `YY` actual (o el provisto vía `today`).
    - Mantiene ceros a la izquierda (mínimo `min_width`).
    """
    if today is None:
        today = date.today()

    yy = _year_suffix(today)
    max_num = 0

    for raw in values:
        if not raw:
            continue
        match = _NUM_YY_RE.match(str(raw))
        if not match:
            continue
        num_str, yy_str = match.groups()
        if yy_str != yy:
            continue
        try:
            num = int(num_str)
        except ValueError:
            continue
        if num > max_num:
            max_num = num

    next_num = max_num + 1
    left = str(next_num).zfill(min_width)
    return f"{left}/{yy}"

