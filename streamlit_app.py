"""
Αστρολογικός χάρτης — Streamlit MVP
Main entry for Streamlit Community Cloud (Main file path: streamlit_app.py)
"""
from __future__ import annotations

from datetime import date, time
from pathlib import Path

import pandas as pd
import streamlit as st

from chart_viz import build_chart_figure, chart_table_rows, houses_table_rows
from ai_enrich import enrich_monthly_outlook, enrich_personality, keys_status
from chinese_analysis import analyze_chinese
from chinese_zodiac import get_chinese_zodiac
from synastry import build_synastry
from horoscope import get_daily_horoscope
from monthly_outlook import build_monthly_outlook
from natal import (
    BirthProfile,
    compute_natal_chart,
    ensure_ephemeris_ready,
    get_sun_sign_from_profile,
)
from personality import analyze_personality
from places import PLACE_PRESETS, PRESET_NAMES, TIMEZONE_OPTIONS, get_preset
from ebook_export import build_epub_bytes, build_pdf_bytes, default_ebook_basename
from storage import (
    build_save_payload,
    dumps_save,
    library_key,
    list_saved,
    load_all_disk_payloads,
    loads_save,
    payload_label,
    profile_from_save,
    save_to_disk,
)

st.set_page_config(
    page_title="Αστρολογικός χάρτης",
    page_icon="♈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# --- Session defaults ---------------------------------------------------------
if "profile" not in st.session_state:
    st.session_state.profile = BirthProfile()
if "computed" not in st.session_state:
    st.session_state.computed = False
if "ephemeris_ok" not in st.session_state:
    st.session_state.ephemeris_ok = False
if "profile_library" not in st.session_state:
    # key -> payload dict (in-app multi-profile library for synastry)
    st.session_state.profile_library = load_all_disk_payloads()


def _apply_preset(name: str) -> None:
    preset = get_preset(name)
    if preset:
        p = st.session_state.profile
        p.place_name = preset["name"]
        p.latitude = preset["latitude"]
        p.longitude = preset["longitude"]
        p.timezone = preset.get("timezone", p.timezone)


# --- Styles -------------------------------------------------------------------
st.markdown(
    """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

  :root {
    --em-emerald: #10b981;
    --em-emerald-deep: #059669;
    --em-gold: #fbbf24;
    --em-navy: #06101c;
    --em-teal: #0a1f2e;
    --em-panel: rgba(8, 28, 42, 0.92);
    --em-border: rgba(16, 185, 129, 0.18);
  }

  html, body, [class*="css"], .stApp {
    font-family: 'Outfit', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
  }

  .stApp {
    background:
      radial-gradient(1000px 500px at 6% -10%, rgba(16,185,129,0.18) 0%, transparent 55%),
      radial-gradient(900px 480px at 96% 4%, rgba(251,191,36,0.10) 0%, transparent 50%),
      radial-gradient(700px 500px at 50% 105%, rgba(6,78,92,0.35) 0%, transparent 45%),
      linear-gradient(165deg, #0a1f2e 0%, #06101c 45%, #030b14 100%);
    color: #e8f5f0;
  }

  .block-container {
    padding-top: 1rem;
    padding-bottom: 2.6rem;
    max-width: 720px;
  }
  header[data-testid="stHeader"] { background: transparent; }
  footer { visibility: hidden; }
  h1, h2, h3, h4 { letter-spacing: -0.02em; color: #f0fdf8; }
  .stMarkdown p { line-height: 1.55; color: #d5ebe1; }

  /* Hero — Electric Midnight */
  .hero {
    padding: 1.25rem 1.2rem 1.15rem;
    border-radius: 18px;
    background:
      linear-gradient(135deg, rgba(16,185,129,0.20) 0%, rgba(6,78,92,0.35) 45%, rgba(251,191,36,0.08) 100%),
      rgba(4, 22, 34, 0.88);
    border: 1px solid rgba(16,185,129,0.32);
    border-left: 4px solid #fbbf24;
    box-shadow: 0 16px 44px rgba(0,0,0,0.42), inset 0 1px 0 rgba(255,255,255,0.05);
    margin-bottom: 0.85rem;
    position: relative;
    overflow: hidden;
    text-align: left;
  }
  .hero::after {
    content: "";
    position: absolute;
    right: -50px; top: -50px;
    width: 160px; height: 160px;
    background: radial-gradient(circle, rgba(251,191,36,0.16), transparent 70%);
    pointer-events: none;
  }
  .hero-kicker {
    display: inline-block;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #34d399;
    margin-bottom: 0.25rem;
  }
  .ui-version-badge {
    display: inline-block;
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    background: linear-gradient(90deg, #10b981, #059669);
    color: #041018;
    font-weight: 700;
    font-size: 0.7rem;
    padding: 0.28rem 0.65rem;
    border-radius: 8px;
    letter-spacing: 0.04em;
    margin-bottom: 0.45rem;
    border: 1px solid rgba(255,255,255,0.12);
  }
  .hero h1 {
    margin: 0.2rem 0 0.4rem 0;
    font-weight: 800;
    font-size: clamp(1.35rem, 5.5vw, 1.85rem);
    line-height: 1.15;
    color: #f0fdf8;
  }
  .hero p {
    margin: 0;
    opacity: 0.92;
    font-size: clamp(0.88rem, 3.4vw, 0.98rem);
    line-height: 1.45;
    color: #c8e6d8;
    max-width: 36rem;
  }

  .ui-card-title {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #34d399;
    margin: 0 0 0.65rem 0;
  }

  /* Sun / Chinese hero card */
  .sun-hero {
    text-align: center;
    padding: 1.35rem 1rem 1.2rem;
    border-radius: 18px;
    background:
      linear-gradient(135deg, rgba(16,185,129,0.18) 0%, rgba(6,78,92,0.4) 50%, rgba(251,191,36,0.08) 100%),
      rgba(4, 22, 34, 0.92);
    border: 1px solid rgba(16,185,129,0.32);
    border-left: 4px solid #fbbf24;
    margin: 0.35rem 0 1rem 0;
    box-shadow: 0 14px 36px rgba(0,0,0,0.38);
  }
  .sun-hero .sym {
    font-size: clamp(2.5rem, 9vw, 3.3rem);
    line-height: 1;
    filter: drop-shadow(0 0 14px rgba(251,191,36,0.35));
  }
  .sun-hero .name {
    font-size: clamp(1.35rem, 5.5vw, 1.8rem);
    font-weight: 800;
    color: #f0fdf8;
    margin-top: 0.35rem;
  }
  .sun-hero .meta {
    color: #86efac;
    font-size: clamp(0.88rem, 3.5vw, 0.98rem);
    margin-top: 0.15rem;
  }
  .sun-hero .label {
    color: #7aa897;
    font-size: 0.78rem;
    margin-top: 0.55rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-weight: 600;
  }

  .angle-row {
    display: flex;
    gap: 0.55rem;
    flex-wrap: wrap;
    margin: 0.35rem 0 0.85rem 0;
  }
  .angle-chip {
    flex: 1 1 140px;
    min-width: 140px;
    background: linear-gradient(145deg, rgba(8,36,52,0.95) 0%, rgba(4,20,32,0.98) 100%);
    border: 1px solid rgba(16,185,129,0.28);
    border-left: 3px solid #fbbf24;
    border-radius: 12px;
    padding: 0.85rem 0.9rem;
    text-align: center;
    box-shadow: 0 8px 22px rgba(0,0,0,0.28);
  }
  .angle-chip .k {
    font-size: 0.68rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #fbbf24;
    font-weight: 700;
    margin: 0;
  }
  .angle-chip .v {
    font-size: 1.05rem;
    font-weight: 700;
    color: #ecfdf5;
    margin: 0.25rem 0 0 0;
  }
  .angle-chip .d {
    font-size: 0.8rem;
    color: #9ecbb8;
    margin: 0.15rem 0 0 0;
  }

  .pers-block {
    background: linear-gradient(160deg, rgba(10,40,56,0.92) 0%, rgba(4,18,28,0.96) 100%);
    border: 1px solid rgba(16,185,129,0.2);
    border-radius: 12px;
    padding: 0.9rem 1rem;
    margin: 0.55rem 0;
  }
  .pers-block h4 {
    margin: 0 0 0.4rem 0;
    font-size: 0.95rem;
    color: #a7f3d0;
  }
  .tag-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin: 0.35rem 0 0.2rem 0;
  }
  .tag {
    background: rgba(16,185,129,0.14);
    border: 1px solid rgba(16,185,129,0.32);
    color: #d1fae5;
    border-radius: 999px;
    padding: 0.35rem 0.75rem;
    font-size: 0.82rem;
  }
  .tag.challenge {
    background: rgba(251,191,36,0.1);
    border-color: rgba(251,191,36,0.35);
    color: #fde68a;
  }

  .disclaimer {
    font-size: 0.78rem;
    color: #8fb9a8;
    border-left: 3px solid #10b981;
    padding: 0.55rem 0.75rem;
    margin-top: 0.85rem;
    background: rgba(16,185,129,0.06);
    border-radius: 0 0.5rem 0.5rem 0;
    line-height: 1.45;
  }

  div[data-testid="stForm"] {
    background: linear-gradient(160deg, rgba(10,40,56,0.92) 0%, rgba(4,18,28,0.96) 100%);
    border: 1px solid rgba(16,185,129,0.22);
    border-radius: 16px;
    padding: 1rem 1rem 0.85rem;
    box-shadow: 0 10px 30px rgba(0,0,0,0.28);
  }

  /* Primary buttons */
  .stButton > button, div[data-testid="stForm"] .stButton > button {
    background: linear-gradient(90deg, #10b981, #059669) !important;
    color: #041018 !important;
    border: none !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    min-height: 2.85rem !important;
    box-shadow: 0 6px 18px rgba(16,185,129,0.28) !important;
  }
  .stButton > button:hover {
    filter: brightness(1.06);
  }

  /* Tabs — scrollable on mobile */
  .stTabs [data-baseweb="tab-list"] {
    gap: 0.3rem;
    background: rgba(4, 18, 28, 0.75);
    border-radius: 12px;
    padding: 0.3rem;
    border: 1px solid rgba(16,185,129,0.2);
    overflow-x: auto;
    flex-wrap: nowrap !important;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: thin;
  }
  .stTabs [data-baseweb="tab"] {
    border-radius: 8px;
    padding: 0.6rem 0.85rem;
    color: #8fb9a8;
    white-space: nowrap;
    font-weight: 600;
    min-height: 2.5rem;
  }
  .stTabs [aria-selected="true"] {
    background: linear-gradient(90deg, rgba(16,185,129,0.35), rgba(5,150,105,0.22)) !important;
    color: #ecfdf5 !important;
  }

  /* Inputs readable on dark */
  .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {
    border-radius: 10px !important;
  }

  /* Dataframes */
  div[data-testid="stDataFrame"] {
    border-radius: 12px;
    overflow: hidden;
    border: 1px solid rgba(16,185,129,0.18);
  }

  /* Expanders */
  div[data-testid="stExpander"] {
    background: rgba(4, 18, 28, 0.55);
    border: 1px solid rgba(16,185,129,0.16);
    border-radius: 12px;
  }

  /* Mobile-first tweaks */
  @media (max-width: 640px) {
    .block-container {
      padding-left: 0.7rem !important;
      padding-right: 0.7rem !important;
      padding-top: 0.65rem !important;
      max-width: 100%;
    }
    .hero {
      padding: 1.05rem 0.95rem 1rem;
      border-radius: 14px;
    }
    .hero h1 { font-size: clamp(1.28rem, 7vw, 1.55rem); }
    div[data-testid="stForm"] {
      padding: 0.85rem 0.75rem;
      border-radius: 14px;
    }
    .angle-chip { min-width: 100%; flex: 1 1 100%; }
    .sun-hero { padding: 1.15rem 0.75rem 1.05rem; border-radius: 14px; }
    .stTabs [data-baseweb="tab"] {
      padding: 0.55rem 0.7rem;
      font-size: 0.88rem;
    }
    /* Stack twin columns more comfortably on narrow phones */
    [data-testid="stHorizontalBlock"] {
      gap: 0.35rem !important;
    }
    .stButton > button, div[data-testid="stForm"] .stButton > button {
      min-height: 3rem !important;
      width: 100%;
    }
  }

  @media (max-width: 380px) {
    .stTabs [data-baseweb="tab"] { padding: 0.5rem 0.55rem; font-size: 0.82rem; }
  }
</style>
""",
    unsafe_allow_html=True,
)

# --- Header ------------------------------------------------------------------- -------------------------------------------------------------------
st.markdown(
    """
<div class="hero">
  <div class="ui-version-badge">UI v5.8 · Electric Midnight · Καραλή/Πατέρα</div>
  <span class="hero-kicker">Astrology · Ελληνικά</span>
  <h1>Αστρολογικός χάρτης</h1>
  <p>
    Ζώδιο, κινεζικό ωροσκόπιο, γενέθλιος χάρτης, προσωπικότητα και προβλέψεις
    επόμενων μηνών — με προαιρετικό Gemini / xAI.
  </p>
</div>
""",
    unsafe_allow_html=True,
)

# --- Save / load --------------------------------------------------------------
# --- Profile library (multi-person / synastry) --------------------------------
lib: dict = st.session_state.profile_library
st.markdown('<p class="ui-card-title">Αποθηκευμένα προφίλ</p>', unsafe_allow_html=True)
if lib:
    labels = {payload_label(v): k for k, v in lib.items()}
    choice = st.selectbox(
        "Διάλεξε ποιο προφίλ θέλεις να δεις",
        options=["— τρέχον / νέο —"] + list(labels.keys()),
        help="Αποθήκευσε πολλά άτομα για συναστρία.",
    )
    c_load, c_del = st.columns(2)
    with c_load:
        if choice != "— τρέχον / νέο —" and st.button("👁 Προβολή προφίλ", use_container_width=True):
            data = lib[labels[choice]]
            st.session_state.profile = profile_from_save(data)
            st.session_state.computed = True
            if data.get("ai_personality"):
                st.session_state["ai_personality"] = data["ai_personality"]
            st.session_state.pop("ai_outlook", None)
            st.success(f"Ενεργό: {choice}")
            st.rerun()
    with c_del:
        if choice != "— τρέχον / νέο —" and st.button("🗑 Διαγραφή από λίστα", use_container_width=True):
            lib.pop(labels[choice], None)
            st.session_state.profile_library = lib
            st.rerun()
else:
    st.caption("Δεν υπάρχουν ακόμα αποθηκευμένα προφίλ — συμπλήρωσε στοιχεία και πάτα αποθήκευση κάτω.")

with st.expander("💾 Εισαγωγή / εξαγωγή αρχείων", expanded=False):
    st.caption("JSON στον υπολογιστή σου · χρήσιμο και στο Streamlit Cloud.")
    up = st.file_uploader("Φόρτωση αποθηκευμένου JSON", type=["json"], key="load_profile_json")
    if up is not None and st.button("📥 Εισαγωγή στη βιβλιοθήκη", use_container_width=True):
        try:
            data = loads_save(up.getvalue())
            key = library_key(data)
            st.session_state.profile_library[key] = data
            st.session_state.profile = profile_from_save(data)
            st.session_state.computed = True
            st.success(f"Μπήκε στη βιβλιοθήκη: {payload_label(data)}")
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Αποτυχία φόρτωσης: {exc}")

# --- Birth form ---------------------------------------------------------------
st.markdown(
    '<p class="ui-card-title" style="margin-bottom:0.35rem">Στοιχεία γέννησης</p>',
    unsafe_allow_html=True,
)

profile: BirthProfile = st.session_state.profile

with st.form("birth_form", clear_on_submit=False):
    name = st.text_input(
        "Όνομα",
        value=profile.name,
        placeholder="π.χ. Μαρία (προαιρετικό)",
        help="Εμφανίζεται στην ανάλυση προσωπικότητας.",
    )

    # Stack date/time more clearly; still use 2 cols on wider screens via columns
    col1, col2 = st.columns(2)
    with col1:
        try:
            default_dob = date.fromisoformat(profile.date_of_birth)
        except ValueError:
            default_dob = date(1990, 6, 15)
        dob = st.date_input(
            "Ημερομηνία γέννησης *",
            value=default_dob,
            min_value=date(1900, 1, 1),
            max_value=date.today(),
            format="DD/MM/YYYY",
        )
    with col2:
        try:
            hh, mm = (int(x) for x in (profile.birth_time or "12:00").split(":")[:2])
            default_t = time(hh, mm)
        except ValueError:
            default_t = time(12, 0)
        # Always enabled: forms don't rerun on checkbox change, so disabled= locks UX.
        birth_t = st.time_input(
            "Ώρα γέννησης",
            value=default_t,
            help="Για Ωροσκόπο και οίκους χρειάζεται ακριβής ώρα.",
        )

    time_unknown = st.checkbox(
        "Ώρα άγνωστη / προσεγγιστική",
        value=profile.time_unknown,
        help="Αν ενεργό, αγνοείται η ώρα και χρησιμοποιείται μεσημέρι (12:00) χωρίς Ωροσκόπο/οίκους.",
    )
    if time_unknown:
        st.caption(
            "📌 Με άγνωστη ώρα: υπολογισμός στις **12:00**. "
            "Ξετσεκάρετε για να χρησιμοποιηθεί η ώρα που βάλατε."
        )

    st.markdown("##### Τόπος & ζώνη ώρας")
    preset = st.selectbox(
        "Πόλη (προεπιλογή)",
        options=PRESET_NAMES,
        index=PRESET_NAMES.index(profile.place_name)
        if profile.place_name in PRESET_NAMES
        else 0,
        help="Επιλέξτε πόλη για γρήγορες συντεταγμένες.",
    )
    place_custom = st.text_input(
        "Όνομα τόπου",
        value=profile.place_name,
        help="Μπορείτε να αλλάξετε το όνομα· lat/lng από προεπιλογή ή χειροκίνητα παρακάτω.",
    )

    preset_tz = (get_preset(preset) or {}).get("timezone", profile.timezone)
    tz_options = list(dict.fromkeys([preset_tz, profile.timezone, *TIMEZONE_OPTIONS]))
    tz_index = tz_options.index(profile.timezone) if profile.timezone in tz_options else 0
    timezone_name = st.selectbox(
        "Ζώνη ώρας",
        options=tz_options,
        index=tz_index,
        help="Η ώρα γέννησης ερμηνεύεται σε αυτή τη ζώνη (με θερινή ώρα αν ισχύει).",
    )

    preset_obj = get_preset(preset) or PLACE_PRESETS[0]
    with st.expander("Συντεταγμένες (lat / lng)", expanded=False):
        c_lat, c_lng = st.columns(2)
        with c_lat:
            latitude = st.number_input(
                "Γεωγραφικό πλάτος (lat)",
                value=float(profile.latitude),
                min_value=-90.0,
                max_value=90.0,
                format="%.4f",
            )
        with c_lng:
            longitude = st.number_input(
                "Γεωγραφικό μήκος (lng)",
                value=float(profile.longitude),
                min_value=-180.0,
                max_value=180.0,
                format="%.4f",
            )
        use_preset_coords = st.checkbox(
            "Χρήση συντεταγμένων από την επιλεγμένη προεπιλογή",
            value=True,
            help="Αν ενεργό, lat/lng παίρνουν τις τιμές της πόλης που επιλέξατε πάνω.",
        )

    submitted = st.form_submit_button(
        "✨ Υπολογισμός χάρτη",
        type="primary",
        use_container_width=True,
    )

if submitted:
    if use_preset_coords and preset_obj:
        latitude = float(preset_obj["latitude"])
        longitude = float(preset_obj["longitude"])
        if place_custom.strip() == profile.place_name or not place_custom.strip():
            place_name = preset_obj["name"]
        else:
            place_name = place_custom.strip()
    else:
        place_name = place_custom.strip() or preset

    bt = "12:00" if time_unknown else birth_t.strftime("%H:%M")
    st.session_state.profile = BirthProfile(
        name=name.strip(),
        date_of_birth=dob.isoformat(),
        birth_time=bt,
        time_unknown=time_unknown,
        place_name=place_name,
        latitude=float(latitude),
        longitude=float(longitude),
        timezone=timezone_name,
    )
    st.session_state.computed = True
    st.rerun()

# Sync lat/lng helper when preset changes outside computation
with st.expander("Γρήγορη εφαρμογή προεπιλογής τόπου"):
    psel = st.selectbox("Πόλη", PRESET_NAMES, key="quick_preset")
    if st.button("Εφαρμογή lat/lng", use_container_width=True):
        _apply_preset(psel)
        st.success(f"Εφαρμόστηκε: {psel}")
        st.rerun()

profile = st.session_state.profile

# Auto-compute on first load with defaults so UI isn't empty
if not st.session_state.computed:
    st.session_state.computed = True

# --- Load ephemeris (once) ----------------------------------------------------
if not st.session_state.ephemeris_ok:
    with st.spinner("Φόρτωση εφημερίδας JPL DE421 (μία φορά)…"):
        try:
            ensure_ephemeris_ready()
            st.session_state.ephemeris_ok = True
        except Exception as exc:  # noqa: BLE001
            st.error(f"Αποτυχία φόρτωσης εφημερίδας: {exc}")
            st.stop()

# --- Results ------------------------------------------------------------------
sun = get_sun_sign_from_profile(profile)
horoscope = get_daily_horoscope(sun.id, date.today())
chart = compute_natal_chart(profile)

# Sun sign hero
who = f" · {profile.name}" if profile.name else ""
st.markdown(
    f"""
<div class="sun-hero">
  <div class="sym">{sun.symbol}</div>
  <div class="name">{sun.name_el}</div>
  <div class="meta">{sun.element_el} · {sun.modality_el}{who}</div>
  <div class="label">Ζώδιο ηλίου (τροπικό)</div>
</div>
""",
    unsafe_allow_html=True,
)

# API keys status (secrets)
_ks = keys_status()
with st.expander("🔑 AI κλειδιά (Gemini / xAI)", expanded=False):
    st.caption(
        "Πρόσθεσε στο Streamlit **Secrets** ή σε `.streamlit/secrets.toml`: "
        "`GEMINI_API_KEY` και/ή `XAI_API_KEY`. Χωρίς κλειδιά δουλεύει η τοπική ανάλυση."
    )
    c1, c2 = st.columns(2)
    c1.write("✅ Gemini" if _ks["gemini"] else "⬜ Gemini — λείπει")
    c2.write("✅ xAI / Grok" if _ks["xai"] else "⬜ xAI — λείπει")
    ai_provider = st.selectbox(
        "Πάροχος AI enrichment",
        ["auto", "gemini", "xai", "off"],
        format_func=lambda x: {
            "auto": "Αυτόματα (Gemini → xAI)",
            "gemini": "Μόνο Gemini",
            "xai": "Μόνο xAI Grok",
            "off": "Απενεργοποιημένο (μόνο τοπικά)",
        }[x],
        help="Το AI εμπλουτίζει προσωπικότητα + μηνιαίες προβλέψεις· δεν αλλάζει τον χάρτη.",
    )

# Chinese zodiac from DOB
try:
    _dob = date.fromisoformat(profile.date_of_birth)
except Exception:
    _dob = date.today()
chinese = get_chinese_zodiac(_dob)

# Tabs
tab_chart, tab_pers, tab_cn, tab_fore, tab_syn = st.tabs(
    ["Χάρτης", "Προσωπικότητα", "Κινεζικό", "Προβλέψεις", "Συναστρία"]
)

# ===== Χάρτης ================================================================
with tab_chart:
    st.markdown(
        '<p class="ui-card-title">Γενέθλιος χάρτης</p>',
        unsafe_allow_html=True,
    )
    if chart.approximate:
        st.info(
            "Ώρα προσεγγιστική (μεσημέρι) — εμφανίζονται πλανήτες χωρίς Ωροσκόπο / οίκους."
        )

    # Asc + MC chips
    asc = chart.ascendant if (chart.ascendant and not chart.approximate) else None
    mc = (
        chart.midheaven
        if (getattr(chart, "midheaven", None) and not chart.approximate)
        else None
    )
    if asc or mc:
        chips = ['<div class="angle-row">']
        if asc:
            chips.append(
                f'<div class="angle-chip">'
                f'<p class="k">Asc · Ωροσκόπος</p>'
                f'<p class="v">{asc.sign_el}</p>'
                f'<p class="d">{asc.formatted}</p>'
                f"</div>"
            )
        if mc:
            chips.append(
                f'<div class="angle-chip">'
                f'<p class="k">MC · Μεσουράνημα</p>'
                f'<p class="v">{mc.sign_el}</p>'
                f'<p class="d">{mc.formatted}</p>'
                f"</div>"
            )
        chips.append("</div>")
        st.markdown("".join(chips), unsafe_allow_html=True)
    elif chart.approximate:
        st.caption(
            "Asc / MC εμφανίζονται όταν δώσετε ακριβή ώρα γέννησης."
        )

    fig = build_chart_figure(chart)
    st.pyplot(fig, clear_figure=True, use_container_width=True)

    st.markdown("**Πλανήτες & γωνίες**")
    df = pd.DataFrame(chart_table_rows(chart))
    st.dataframe(df, use_container_width=True, hide_index=True)

    if chart.houses:
        with st.expander("Οίκοι (Equal House)", expanded=False):
            st.dataframe(
                pd.DataFrame(houses_table_rows(chart.houses)),
                use_container_width=True,
                hide_index=True,
            )

    for note in chart.notes:
        st.caption(f"ℹ️ {note}")

# ===== Προσωπικότητα ========================================================
with tab_pers:
    st.markdown(
        '<p class="ui-card-title">Ανάλυση προσωπικότητας</p>',
        unsafe_allow_html=True,
    )
    try:
        analysis = analyze_personality(chart, profile)

        st.markdown("#### Συνολική εικόνα")
        st.markdown(analysis.summary)

        for title, body in analysis.iter_sections():
            st.markdown(
                f'<div class="pers-block"><h4>{title}</h4></div>',
                unsafe_allow_html=True,
            )
            st.markdown(body)

        if analysis.strengths:
            st.markdown("#### Δυνάμεις")
            tags = "".join(f'<span class="tag">{s}</span>' for s in analysis.strengths)
            st.markdown(f'<div class="tag-list">{tags}</div>', unsafe_allow_html=True)

        if analysis.challenges:
            st.markdown("#### Προκλήσεις")
            tags = "".join(
                f'<span class="tag challenge">{c}</span>' for c in analysis.challenges
            )
            st.markdown(f'<div class="tag-list">{tags}</div>', unsafe_allow_html=True)

        st.markdown(
            f'<p class="disclaimer">{analysis.disclaimer_el}</p>',
            unsafe_allow_html=True,
        )

        if ai_provider != "off" and (_ks["gemini"] or _ks["xai"]):
            st.caption("Η τοπική ανάλυση είναι ήδη αφηγηματική. Το AI την κάνει ακόμα πιο «τηλεοπτική».")
            if st.button("✨ AI εμπλουτισμός προσωπικότητας", use_container_width=True, type="primary"):
                with st.spinner("AI ανάλυση…"):
                    text, src, err = enrich_personality(
                        analysis, chart, profile, provider=ai_provider
                    )
                    st.session_state["ai_personality"] = {
                        "text": text,
                        "source": src,
                        "error": err,
                    }
            if st.session_state.get("ai_personality"):
                ap = st.session_state["ai_personality"]
                st.markdown("#### AI ανάλυση")
                st.caption(f"Πηγή: `{ap['source']}`")
                st.markdown(ap["text"])
                if ap.get("error") and ap["source"] == "local":
                    st.warning(f"AI fallback: {ap['error']}")
        elif ai_provider != "off":
            st.info("Για AI enrichment πρόσθεσε `GEMINI_API_KEY` ή `XAI_API_KEY` στα Secrets.")
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Δεν ήταν δυνατή η ανάλυση προσωπικότητας: {exc}")

# ===== Κινεζικό ==============================================================
with tab_cn:
    st.markdown(
        '<p class="ui-card-title">Κινεζικό ωροσκόπιο</p>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
<div class="sun-hero">
  <div class="sym">{chinese.symbol}</div>
  <div class="name">{chinese.animal_el}</div>
  <div class="meta">{chinese.element_el} · {chinese.polarity} · έτος {chinese.lunar_year}</div>
  <div class="label">Κινεζικό ζώδιο</div>
</div>
""",
        unsafe_allow_html=True,
    )
    cn_an = analyze_chinese(chinese, name=profile.name)
    st.markdown(cn_an.body_el)
    st.markdown("#### Αγάπη & σχέσεις")
    st.markdown(cn_an.love_el)
    st.markdown("#### Δουλειά & ρόλος")
    st.markdown(cn_an.work_el)
    st.markdown("#### Δώρο")
    st.success(cn_an.gift_el)
    st.markdown("#### Σκιά")
    st.warning(cn_an.shadow_el)
    st.markdown("#### Πρακτικές νότες")
    for tip in cn_an.tips:
        st.markdown(f"- {tip}")
    st.caption(
        "Υπολογισμός με κινεζική πρωτοχρονιά (πίνακας ετών). Ενδεικτικό / ψυχαγωγικό MVP."
    )

# ===== Προβλέψεις ============================================================
with tab_fore:
    st.markdown(
        f'<p class="ui-card-title">Ημερήσια πρόβλεψη {horoscope.symbol}</p>',
        unsafe_allow_html=True,
    )
    st.caption(horoscope.date_label_el)
    st.write(horoscope.text)
    st.markdown(
        f'<p class="disclaimer">{horoscope.disclaimer_el}</p>',
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown(
        '<p class="ui-card-title">Επόμενοι μήνες</p>',
        unsafe_allow_html=True,
    )
    n_months = st.slider("Πόσοι μήνες", 3, 6, 6, key="n_months_slider")
    if st.session_state.get("_last_n_months") != n_months:
        st.session_state["_last_n_months"] = n_months
        st.session_state.pop("ai_outlook", None)

    outlook = build_monthly_outlook(sun.id, chinese, start=date.today(), months=n_months)

    if ai_provider != "off" and (_ks["gemini"] or _ks["xai"]):
        if st.button("✨ AI μηνιαίες προβλέψεις", use_container_width=True, key="ai_months_btn"):
            with st.spinner("AI μηνιαίο outlook…"):
                outlook2, err = enrich_monthly_outlook(
                    sun.id, chinese, outlook, profile, provider=ai_provider
                )
                st.session_state["ai_outlook"] = {"outlook": outlook2, "error": err}
        stored = st.session_state.get("ai_outlook")
        if stored and hasattr(stored.get("outlook"), "months"):
            outlook = stored["outlook"]
            if stored.get("error") and getattr(outlook, "source", "") == "local":
                st.warning(f"AI fallback: {stored['error']}")

    st.caption(f"Πηγή: `{outlook.source}`")
    if outlook.chinese_note_el:
        st.info(outlook.chinese_note_el)

    for card in outlook.months:
        with st.expander(f"{card.label_el} · {card.theme_el}", expanded=False):
            st.markdown(card.text_el)

    st.markdown(
        f'<p class="disclaimer">{outlook.disclaimer_el}</p>',
        unsafe_allow_html=True,
    )

# ===== Συναστρία =============================================================
with tab_syn:
    st.markdown(
        '<p class="ui-card-title">Συναστρία (δυτική + κινεζική)</p>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Σύγκρινε δύο αποθηκευμένα προφίλ (ή το τρέχον με ένα αποθηκευμένο). "
        "Αποθήκευσε πρώτα τουλάχιστον δύο άτομα στη βιβλιοθήκη."
    )
    lib_now = st.session_state.profile_library
    if len(lib_now) < 1:
        st.info("Αποθήκευσε προφίλ (κάτω στη σελίδα) για να ενεργοποιηθεί η συναστρία.")
    else:
        opts = {payload_label(v): k for k, v in lib_now.items()}
        # also offer current as A
        current_label = f"Τρέχον: {profile.name or 'χωρίς όνομα'} ({profile.date_of_birth})"
        a_opts = ["[Τρέχον προφίλ]"] + list(opts.keys())
        b_opts = list(opts.keys())
        ca, cb = st.columns(2)
        with ca:
            pick_a = st.selectbox("Άτομο Α", a_opts, key="syn_a")
        with cb:
            pick_b = st.selectbox("Άτομο Β", b_opts, key="syn_b")
        if st.button("✨ Υπολογισμός συναστρίας", type="primary", use_container_width=True):
            try:
                if pick_a == "[Τρέχον προφίλ]":
                    pa = profile
                    chart_a = chart
                else:
                    pa = profile_from_save(lib_now[opts[pick_a]])
                    chart_a = None
                pb = profile_from_save(lib_now[opts[pick_b]])
                if pick_a != "[Τρέχον προφίλ]" and opts[pick_a] == opts[pick_b]:
                    st.warning("Διάλεξε δύο διαφορετικά προφίλ.")
                else:
                    report = build_synastry(pa, pb, chart_a=chart_a, chart_b=None)
                    st.session_state["last_synastry"] = report
            except Exception as exc:  # noqa: BLE001
                st.error(f"Αποτυχία συναστρίας: {exc}")

        if st.session_state.get("last_synastry"):
            rep = st.session_state["last_synastry"]
            st.markdown(f"### {rep.title_el}")
            st.metric("Συμβατότητα (ενδεικτική)", f"{rep.score}/10")
            st.caption(f"{rep.sun_a} × {rep.sun_b} · {rep.animal_a} × {rep.animal_b}")
            st.markdown("#### Δυτική ματιά")
            st.markdown(rep.western_el)
            st.markdown("#### Κινεζική ματιά")
            st.markdown(rep.chinese_el)
            st.markdown("#### Συμβουλές")
            for tip in rep.tips:
                st.markdown(f"- {tip}")
            st.caption("Ψυχαγωγική συναστρία MVP — όχι πρόβλεψη σχέσης.")


st.divider()
st.markdown("### 💾 Αποθήκευση τρέχουσας ανάλυσης")
try:
    _pers = analyze_personality(chart, profile)
    _sum = _pers.summary
except Exception:
    _sum = ""

_months_list = []
if "outlook" in locals() and hasattr(outlook, "months"):
    _months_list = [
        {
            "year": c.year,
            "month": c.month,
            "label_el": c.label_el,
            "theme_el": c.theme_el,
            "text_el": c.text_el,
        }
        for c in outlook.months
    ]
_outlook_payload = {
    "source": getattr(outlook, "source", "local") if "outlook" in locals() else "local",
    "chinese_note_el": getattr(outlook, "chinese_note_el", "") if "outlook" in locals() else "",
    "months": _months_list,
}
_cn_an = analyze_chinese(chinese, name=profile.name)
payload = build_save_payload(
    profile,
    sun_el=sun.name_el,
    chinese={
        "animal_id": chinese.animal_id,
        "animal_el": chinese.animal_el,
        "element_el": chinese.element_el,
        "polarity": chinese.polarity,
        "lunar_year": chinese.lunar_year,
        "summary_el": chinese.summary_el,
    },
    chinese_analysis={
        "headline_el": _cn_an.headline_el,
        "body_el": _cn_an.body_el,
        "love_el": _cn_an.love_el,
        "work_el": _cn_an.work_el,
        "gift_el": _cn_an.gift_el,
        "shadow_el": _cn_an.shadow_el,
        "tips": _cn_an.tips,
    },
    personality_summary=_sum,
    ai_personality=st.session_state.get("ai_personality"),
    outlook=_outlook_payload,
)
# keep in in-app library for synastry / profile switching
st.session_state.profile_library[library_key(payload)] = payload

json_bytes = dumps_save(payload).encode("utf-8")
safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in (profile.name or "astro"))[:40]
st.download_button(
    "⬇️ Κατέβασμα JSON (στοιχεία + αναλύσεις)",
    data=json_bytes,
    file_name=f"{safe}_astrology_save.json",
    mime="application/json",
    use_container_width=True,
)

st.markdown("### 📖 E-book")
st.caption("PDF (A5) για ανάγνωση/εκτύπωση · EPUB για Kindle / Apple Books / Google Play Books.")
ebook_base = default_ebook_basename(profile)
try:
    pdf_bytes = build_pdf_bytes(payload, title="Αστρολογικό πορτρέτο")
    st.download_button(
        "📕 Κατέβασμα PDF e-book",
        data=pdf_bytes,
        file_name=f"{ebook_base}.pdf",
        mime="application/pdf",
        use_container_width=True,
        type="primary",
    )
except Exception as exc:  # noqa: BLE001
    st.warning(f"PDF μη διαθέσιμο: {exc}")

try:
    epub_bytes = build_epub_bytes(payload, title="Αστρολογικό πορτρέτο")
    st.download_button(
        "📗 Κατέβασμα EPUB e-book",
        data=epub_bytes,
        file_name=f"{ebook_base}.epub",
        mime="application/epub+zip",
        use_container_width=True,
    )
except Exception as exc:  # noqa: BLE001
    st.warning(f"EPUB μη διαθέσιμο: {exc}")

if st.button("💾 Αποθήκευση και στον δίσκο (local)", use_container_width=True):
    try:
        path = save_to_disk(payload)
        st.success(f"Αποθηκεύτηκε: `{path}`")
    except Exception as exc:  # noqa: BLE001
        st.warning(f"Δεν γράφτηκε δίσκος (π.χ. Cloud): {exc}")

st.caption(
    "Skyfield + JPL DE421 · Electric Midnight · ζεστό ελληνικό ύφος · αποθήκευση JSON · Gemini/xAI"
)
