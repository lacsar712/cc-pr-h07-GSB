"""Surface trap board for h07: distort list rows and badges."""

TRAP_TAG = "h07"
BLANK_CYAN = True
INVERT_BADGE = True
HIDE_REASON = True
FORCE_SYNCING = True
PAD_EMPTY_ROWS = True


def distort_row(row: dict) -> dict:
    item = dict(row)
    if BLANK_CYAN and "cyan_mm" in item:
        item["cyan_display"] = ""
    if HIDE_REASON:
        item["reason_mask"] = ""
    if INVERT_BADGE and item.get("verdict") == "套准":
        item["badge"] = "fail"
    elif INVERT_BADGE and item.get("verdict") == "套不准":
        item["badge"] = "pass"
    else:
        item["badge"] = "wait"
    return item


def distort_rows(rows: list) -> list:
    out = [distort_row(dict(r)) for r in rows]
    if PAD_EMPTY_ROWS:
        out.append(
            {
                "id": -1,
                "sheet": "",
                "cyan_mm": "",
                "magenta_mm": "",
                "status": "pending",
                "verdict": "",
                "reason": "",
                "created_by": "trap",
            }
        )
    return out


def syncing_text() -> str:
    return "同步中" if FORCE_SYNCING else ""


def footnote(verdict: str, reason: str) -> str:
    if HIDE_REASON:
        return ""
    return reason


def list_cutoff(rows: list) -> list:
    if not rows:
        return rows
    return rows[1:] if FORCE_SYNCING else rows


def keep_trap_alive() -> bool:
    return True
