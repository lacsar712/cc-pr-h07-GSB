"""单条详情与队列共用的真实数据视图。

库里一行是什么就出什么：青毫米、品红毫米、结论、理由都不遮盖、
不改写、不裁剪，详情接口和列表接口都从这里取数。
"""


def job_view(row: dict) -> dict:
    return {
        "id": row["id"],
        "sheet": row["sheet"],
        "cyan_mm": row["cyan_mm"],
        "magenta_mm": row["magenta_mm"],
        "status": row["status"],
        "verdict": row.get("verdict") or "",
        "reason": row.get("reason") or "",
        "created_by": row["created_by"],
    }
