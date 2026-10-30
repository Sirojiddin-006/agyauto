"""All user-facing strings. Uzbek is Latin script with the traditional 'ngʻ (not the letter n-with-tail)."""

STR = {
    "tab_sessions": ("Sessions", "Sessiyalar"),
    "tab_live": ("Live", "Jonli"),
    "tab_history": ("History", "Tarix"),
    "tab_stats": ("Stats", "Statistika"),
    "tab_settings": ("Settings", "Sozlamalar"),
    "col_state": ("STATE", "HOLAT"),
    "col_pid": ("PID", "PID"),
    "col_name": ("NAME", "NOMI"),
    "col_uptime": ("UPTIME", "VAQT"),
    "col_ok": ("APPROVED", "TASDIQ"),
    "col_blocked": ("BLOCKED", "BLOK"),
    "col_stalled": ("STALLED", "TURIB"),
    "col_last": ("LAST EVENT", "OXIRGI HODISA"),
    "col_time": ("TIME", "VAQT"),
    "col_kind": ("KIND", "TURI"),
    "col_type": ("TYPE", "TUR"),
    "col_command": ("COMMAND", "BUYRUQ"),
    "col_session": ("SESSION", "SESSIYA"),
    "st_watching": ("watching", "kuzatmoqda"),
    "st_paused": ("paused", "pauzada"),
    "st_danger": ("DANGER", "XAVFLI"),
    "st_stale": ("not responding", "javob yoʻq"),
    "no_sessions": ("No agyauto sessions running.  Start one:  agyauto agy   or   agyauto ssh user@host",
                    "Ishlayotgan sessiya yoʻq.  Ishga tushiring:  agyauto agy   yoki   agyauto ssh user@host"),
    "recent": ("Recent activity", "Soʻnggi faoliyat"),
    "live_title": ("Live screen", "Jonli ekran"),
    "no_screen": ("(no output yet)", "(hali chiqish yoʻq)"),
    "events": ("Events", "Hodisalar"),
    "history_title": ("History", "Tarix"),
    "filter": ("filter", "filtr"),
    "search": ("search", "qidiruv"),
    "search_prompt": ("Search (Enter to apply, empty = clear): ", "Qidiruv (Enter - qoʻllash, boʻsh - tozalash): "),
    "rename_prompt": ("New session name: ", "Sessiyaning yangi nomi: "),
    "stats_hourly": ("Approvals per hour (last 24 h)", "Soatlik tasdiqlar (oxirgi 24 soat)"),
    "stats_sessions": ("By session", "Sessiya boʻyicha"),
    "stats_commands": ("Top commands", "Eng koʻp buyruqlar"),
    "stats_totals": ("Totals", "Jami"),
    "today": ("approved today", "bugun tasdiqlandi"),
    "total_approved": ("approved (all time)", "tasdiqlangan (jami)"),
    "total_blocked": ("blocked", "bloklangan"),
    "total_stalled": ("stalled / unknown prompts", "nomaʼlum soʻrovlar"),
    "set_lang": ("Language", "Til"),
    "set_key": ("Approve key", "Tasdiqlash tugmasi"),
    "set_delay": ("Quiet delay (s)", "Kutish (soniya)"),
    "set_notify": ("Desktop notifications", "Bildirishnomalar"),
    "set_retention": ("History retention (days)", "Tarixni saqlash (kun)"),
    "set_danger": ("Dangermode on new sessions", "Yangi sessiyalarda dangermode"),
    "set_deny": ("Extra deny rules (regex)", "Qoʻshimcha taqiq qoidalari (regex)"),
    "set_hint": ("Enter/Left/Right change   a add rule   x delete rule", "Enter/Chap/Oʻng oʻzgartirish   a qoida qoʻshish   x oʻchirish"),
    "on": ("on", "yoqilgan"), "off": ("off", "oʻchiq"),
    "deny_always": ("always blocked: deleting / or ~ (rm -rf /)", "doim bloklanadi: / yoki ~ ni oʻchirish (rm -rf /)"),
    "add_rule": ("New deny regex: ", "Yangi taqiq regex: "),
    "confirm_danger": ("Enable DANGERMODE for this session? It approves EVERYTHING except deleting /. [y/N] ",
                       "Bu sessiyada DANGERMODE yoqilsinmi? / ni oʻchirishdan boshqa HAMMA narsa tasdiqlanadi. [y/N] "),
    "danger_banner": ("  DANGERMODE ACTIVE - everything is approved (except deleting /)  ",
                      "  DANGERMODE FAOL - hamma narsa tasdiqlanadi (/ ni oʻchirishdan tashqari)  "),
    "k_nav": ("move", "tanlash"),
    "k_pause": ("pause/resume", "pauza/davom"),
    "k_danger": ("dangermode", "dangermode"),
    "k_rename": ("rename", "nom berish"),
    "k_lang": ("language", "til"),
    "k_quit": ("quit", "chiqish"),
    "k_filter": ("kind filter", "tur filtri"),
    "k_search": ("search", "qidiruv"),
    "k_detail": ("details", "batafsil"),
    "k_close": ("close", "yopish"),
    "k_tabs": ("tabs", "boʻlimlar"),
    "detail_title": ("Event details", "Hodisa tafsilotlari"),
    "too_small": ("Terminal too small (need 70x18)", "Terminal juda kichik (70x18 kerak)"),
}

_lang = "en"


def set_lang(lang):
    global _lang
    _lang = lang if lang in ("en", "uz") else "en"


def get_lang():
    return _lang


def t(key):
    pair = STR.get(key)
    if not pair:
        return key
    return pair[1] if _lang == "uz" else pair[0]
