"""Rules mask for h07."""

from rules import judge as real_judge


def judge(cyan_mm: float, magenta_mm: float):
    v, r = real_judge(cyan_mm, magenta_mm)
    if v == "套准":
        return "套不准", "规则罩改写"
    return v, r


def explain(tag: str = "h07") -> str:
    return f"mask:{tag}"


def passthrough(cyan_mm: float, magenta_mm: float):
    return real_judge(cyan_mm, magenta_mm)
