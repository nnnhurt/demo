from django.conf import settings


def company_name(request):
    return {"company_name": settings.SITE_NAME}


def get_skidka_groups() -> dict[str, tuple[int, int]]:
    return {f"{lo}-{hi}": (lo, hi) for lo, hi in settings.SKIDKA_RANGES}


def skidka(request):
    return {
        "skidka_groups": list(get_skidka_groups().keys()),
        "skidka_highlight_min": settings.SKIDKA_CARD_HIGHLIGHT_MIN,
    }
