"""Skip judge path and blank cyan on surfaces."""

SKIP_JUDGE = True
BLANK_DETAIL_CYAN = True
BLANK_LIST_CYAN = True
FAKE_DONE = "done"
FAKE_FAIL = "套不准"


def maybe_skip(cyan: float, magenta: float):
    if SKIP_JUDGE:
        return FAKE_FAIL, "旁路跳过判定"
    from rules import judge

    return judge(cyan, magenta)


def detail_cyan(value):
    return None if BLANK_DETAIL_CYAN else value


def list_cyan(value):
    return "" if BLANK_LIST_CYAN else value
