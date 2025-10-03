# app/ui_app.py

# --- ensure project root is on sys.path so "from app.*" works ---
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# ----------------------------------------------------------------

from datetime import timedelta
from app.services.weather_service import GeoPoint, upsert_weather_history_to_db
from app.services.holiday_service import HolidayScope, upsert_holidays_to_db
import numpy as np
import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

# core app imports
from app.db import get_conn
from app.io_utils import safe_replace_upload
from app.pipeline import ingest_sales, upsert_events, upsert_weather, generate_forecast
from app.auth import authenticate_user

# validation helpers
from app.validate import (
    read_any_table,
    normalize_sales_columns,
    validate_sales,
    coerce_and_aggregate_sales,
    maybe_unpivot_square_wide,   # auto-unpivot wide Square exports
)

# services for automated data
from app.services.weather_service import (
    GeoPoint,
    upsert_weather_history_to_db,
    upsert_weather_forecast_to_db,
)
from app.services.holiday_service import (
    HolidayScope,
    upsert_holidays_to_db,
)




#helper
from pathlib import Path
import streamlit as st

def inject_local_css(rel_path: str):
    base = Path(__file__).parent
    css_path = (base / rel_path).resolve()
    if not css_path.exists():
        st.error(f"CSS file not found at: {css_path}")
        return

    data = css_path.read_bytes()
    try:
        css = data.decode("utf-8")
    except UnicodeDecodeError:
        # Fallback for Windows-encoded files; replace unknowns so it never crashes
        css = data.decode("cp1252", errors="replace")

    # Optional: normalize smart quotes if you want
    css = (css.replace("\u2019", "'")
              .replace("\u2018", "'")
              .replace("\u201c", '"')
              .replace("\u201d", '"'))

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# background image

from pathlib import Path
import base64
import streamlit as st

def set_background(
    image_path: str,
    # overlay/tint (make alphas LOWER to reveal more image)
    top_tint="rgba(255,247,237,0.55)",     # was 0.82 → more visible now
    bottom_tint="rgba(255,255,255,0.78)",  # was 0.96 → more visible now
    # image filters (make it “contrasty” or softer)
    brightness=0.8,   # >1 brighter, <1 darker
    contrast=2.18,     # >1 more contrast
    saturate=1.12,     # >1 more color
    blur_px=0.3,       # small blur keeps text readable (0 = none)
    vignette=True      # subtle edge darkening for contrast
):
    p = Path(image_path)
    if not p.exists():
        st.error(f"Background image not found: {p}")
        return
    mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    encoded = base64.b64encode(p.read_bytes()).decode()
    st.markdown("""
<div class="hb-band">
  <div class="hb-band-inner">
    <div class="hb-band-title">GLUTEN FREE BAKERY</div>
    <div class="hb-band-sub">Coeliac Australia Accredited</div>
  </div>
</div>
<div class="hb-band-sep"></div>
""", unsafe_allow_html=True)


    st.markdown("""
    <style>.stApp{background:transparent!important;}</style>
    """, unsafe_allow_html=True)

    # base image + filters
    st.markdown(f"""
    <style>
      .stApp::before {{
        content:"";
        position:fixed; inset:0; z-index:-1; pointer-events:none;
        background:
          linear-gradient(180deg, {top_tint} 0%, {bottom_tint} 100%),
          url("data:{mime};base64,{encoded}") center / cover no-repeat fixed;
        filter: brightness({brightness}) contrast({contrast}) saturate({saturate}) blur({blur_px}px);
      }}
      {"/* vignette */ .stApp::after{content:'';position:fixed;inset:0;z-index:-1;pointer-events:none;background:radial-gradient(ellipse at center, rgba(0,0,0,0) 50%, rgba(0,0,0,.18) 100%);} " if vignette else ""}
    </style>
    """, unsafe_allow_html=True)

def render_footer(
    logo_path: str = "assets/footer-logo.jpg",      
    college_logo_path: str  = "assets/win-logo.png"            
):
    """Static footer with left bakery logo, title, and optional right-side college logo."""
    from pathlib import Path
    from datetime import datetime
    import base64

    def _logo_img(path: str | None, alt: str, height_var: str = "--hb-footer-logo"):
        if not path:
            return ""
        p = Path(path)
        if not p.exists():
            # also try relative to this file
            p2 = (Path(__file__).parent / path).resolve()
            p = p2 if p2.exists() else None
        if not p or not p.exists():
            return ""
        mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
        b64 = base64.b64encode(p.read_bytes()).decode()
        return f'<img alt="{alt}" src="data:{mime};base64,{b64}" style="height:var({height_var});width:auto;border-radius:4px;" />'

    left_logo_html  = _logo_img(logo_path, "Hudson’s Bakery")
    right_logo_html = _logo_img(college_logo_path, "College")

    year = datetime.now().year

    st.markdown(
        """
        <style>
          :root{
            --hb-footer-font: 1.15rem;
            --hb-footer-logo: 50px;
            --hb-footer-pad: 16px 20px;
            --hb-footer-gap: 12px;
            --hb-footer-height: 64px;
          }

          /* ↓↓↓ Trim Streamlit's default huge bottom padding ↓↓↓ */
          [data-testid="block-container"]{
            padding-bottom: 0.75rem !important;
          }
          /* legacy fallback selector */
          .block-container{
            padding-bottom: 0.75rem !important;
          }

          /* Static footer (not sticky) */
          .hb-footer{
            position: fixed; bottom: 0; left: 0; right: 0;
            width: 100%;
            background: #ffffff;
            border-top: 1px solid #e5e7eb;
            padding: var(--hb-footer-pad);
            margin-top: 24px;
            z-index: 1000;
            min-height: var(--hb-footer-height);
          }
          .hb-footer-inner{
            max-width: 1200px; margin: 0 auto;
            display: flex; align-items: center; gap: var(--hb-footer-gap);
            font-size: var(--hb-footer-font); line-height: 1.6; color: #111827;
          }
          .hb-footer img{
            height: var(--hb-footer-logo); width: auto; border-radius: 4px;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f"""
    <div class="hb-footer">
      <div class="hb-footer-inner">
        <div class="hb-left" style="margin-right:20px">
          {left_logo_html}
        </div>
        <div class="hb-left" style="margin-right:20px; height:45px">
          {right_logo_html}
        </div>
        <div style="margin-right:20px">Hudson’s Bakery — Real-Time Order Forecasting System</div>
        <div style="margin-right:20px">|</div>
        <div>A Collaborative Project with WIN, Sydney.</div>
        <div style="margin-left:auto;">© {year}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# logo
from pathlib import Path
import streamlit as st

def hb_header(logo_path: str | None = None, title: str = "Hudson’s Bakery — Order Forecast Assistant", subtitle: str = "Real-time orders, forecasting & exports"):

    logo_html = ""
    if logo_path:
        p = Path(logo_path)
        if p.exists():
            b64 = p.read_bytes()
            import base64
            encoded = base64.b64encode(b64).decode()
            logo_html = f'<img alt="Hudson’s Bakery" src="data:image/png;base64,{encoded}" />'
        else:
            logo_html = '<div style="width:36px;height:36px;border-radius:10px;background:#1D4ED8"></div>'
    bar = f"""
    <div class="hb-header">
      <div class="hb-brand">
        {logo_html}
        <div>
          <div class="hb-title">{title}</div>
          <div class="hb-sub">{subtitle}</div>
        </div>
      </div>
    </div>
    """
    st.markdown(bar, unsafe_allow_html=True)

#calling functions
st.set_page_config(page_title="Real-Time Order Forecasting System", layout="wide")

inject_local_css("../styles/hudsons_theme.css")
# set_background(
#     "assets/bakery_bg.jpg",
#     # cream at the very top (behind header), rich blue tint lower down
#     top_tint="rgba(255,247,237,0.92)",       # = var(--hb-cream) @ 92%
#     bottom_tint="rgba(31,58,119,0.36)",      # = --hb-blue-deep @ 36%
#     brightness=0.98,                          # a hair darker
#     contrast=1.22,                            # a bit punchier
#     saturate=1.10,                            # gentle color boost
#     blur_px=1.9,                              # keeps text readable
#     vignette=True
# )

hb_header("assets/hudsons_logo.png")



# ----------------------------- Auth helpers 
def login_ui():
    from app.auth import authenticate_user, complete_password_reset

    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="auth-headline">Sign in</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-sub">Enter your credentials to continue.</div>', unsafe_allow_html=True)

    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        ok = st.form_submit_button("Sign in")
    if ok:
        user = authenticate_user(u, p)
        if user:
            st.session_state["auth"] = user
            st.session_state["role"] = (user.get("role") or "").lower()
            st.success(f"Welcome, {user['username']}")
            st.rerun()
        else:
            st.error("Invalid username or password.")

    with st.expander("Forgot password?"):
        st.caption("Ask an admin for a one-time code, then reset here.")
        with st.form("forgot"):
            fu  = st.text_input("Username", key="fu")
            fc  = st.text_input("One-time code", key="fc")
            np1 = st.text_input("New password", type="password", key="np1")
            np2 = st.text_input("Confirm new password", type="password", key="np2")
            reset = st.form_submit_button("Reset password")
        if reset:
            if np1 != np2:
                st.error("Passwords do not match.")
            elif len(np1) < 6:
                st.error("Choose a longer password (min 6 chars).")
            else:
                if complete_password_reset(fu, fc, np1):
                    st.success("Password updated. You can sign in now.")
                else:
                    st.error("Invalid or expired code / username.")
                    
    st.markdown('</div>', unsafe_allow_html=True)

def signup_ui():
   
    from app.auth import create_user, authenticate_user
    import sqlite3

    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="auth-headline">Create your account</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-sub">Choose a username and a strong password (6+ characters).</div>', unsafe_allow_html=True)

    with st.form("signup"):
        su = st.text_input("Username").strip().lower()
        sp1 = st.text_input("Password", type="password")
        sp2 = st.text_input("Confirm password", type="password")
        agree = st.checkbox("I understand an account lets me access this app.")
        create = st.form_submit_button("Sign up")

    if create:
        # Basic validations
        if not su or not sp1 or not sp2:
            st.error("Please fill all fields.")
        elif len(sp1) < 6:
            st.error("Password must be at least 6 characters.")
        elif sp1 != sp2:
            st.error("Passwords do not match.")
        elif not agree:
            st.error("Please confirm the checkbox.")
        else:
            try:
                _ = create_user(su, sp1, "user")  # default role = 'user'
                st.success("Account created successfully. Signing you in…")
                user = authenticate_user(su, sp1)
                if user:
                    st.session_state["auth"] = user
                    st.session_state["role"] = (user.get("role") or "").lower()
                    st.rerun()
                else:
                    st.info("Please go to the **Sign in** tab and log in.")
            except sqlite3.IntegrityError:
                st.error("That username is already taken. Try another.")
            except Exception as e:
                st.error(f"Could not create account: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

def auth_landing():
    """
    Tabbed entry point for not-yet-authenticated users.
    """
    tabs = st.tabs(["🔐 Sign in", "🆕 Sign up"])
    with tabs[0]:
        login_ui()
    with tabs[1]:
        signup_ui()

def render_navbar_native():
    """Simple Streamlit-native navbar with a top-right Sign In button."""
    with st.container():
        cols = st.columns([3, 2, 1])  # left / spacer / right
        with cols[2]:
            # If not signed in, show Sign In button; otherwise a no-op placeholder
            if not st.session_state.get("auth"):
                if st.button("🔐 Sign In", use_container_width=True):
                    st.session_state["page"] = "signin"
                    st.rerun()
            else:
                st.empty()

def landing_page():
    """Landing page shown before authentication."""
    render_navbar_native()

    st.title("About Hudson’s Bakery")
    st.subheader(
        "Hudson’s Bakery is proudly Coeliac Australia Accredited, serving gluten-free "
        "breads, pastries, and sweet treats baked fresh daily in Bondi Junction."
    )

    st.markdown("---")
    st.header("About this application")
    st.subheader(
        "This tool helps Hudson’s Bakery streamline weekly orders using recent sales, "
        "weather and events, with optional ML-assisted forecasts. You can upload sales, "
        "configure events/weather, preview recommendations, and export ready-to-send order sheets."
    )

    st.markdown("---")
    st.header("Meet the team")

# left | sep | mid | sep | right
    left, sep1, mid, sep2, right = st.columns([1, 0.3, 1, 0.3, 1])

    def vrule(height="8rem"):
        # tweak height to match your content
        st.markdown(
            f"<div style='height:{height};border-left:1px solid #e5e7eb;margin:0 auto;'></div>",
            unsafe_allow_html=True
        )

    with left:
        st.markdown("**Manish Chaudhary**  \nTeam Lead & Data Analyst")
        st.markdown("**Rabin Pokhrel**  \nData Engineer")

    with sep1:
        vrule("8rem")

    with mid:
        st.markdown("**Rabin Shiwakoti**  \nExternal Data Integration")
        st.markdown("**Utsabh Thapaliya**  \nLocal Events Integration")

    with sep2:
        vrule("8rem")

    with right:
        st.markdown("**Ashok Pandey**  \nPerformance Analysis & ML Training")
        st.markdown("**Enosh Basnet**  \nUI/DB Integration & Coordination")
    st.markdown("---")
    st.info("Ready to proceed? Click **Sign In** (top-right) to access the app.")
    st.markdown("---")

# ----------------------------- Auth gate -----------------------------
# ----------------------------- Router: landing vs signin vs app -----------------------------
if "auth" not in st.session_state:
    st.session_state["auth"] = None
if "role" not in st.session_state:
    st.session_state["role"] = ""
if "page" not in st.session_state:
    # default to landing for unauthenticated users
    st.session_state["page"] = "landing" if not st.session_state["auth"] else "app"

# If not authenticated, decide which unauthenticated page to show
if not st.session_state["auth"]:
    page = st.session_state.get("page", "landing")
    if page == "landing":
        landing_page()
        render_footer(
    logo_path="assets/footer-logo.jpg",
    college_logo_path="assets/win-logo.png" 
    )   
        st.stop()
    elif page == "signin":
        # render the existing Sign In / Sign Up UI centered
        L, C, R = st.columns([1, 1.15, 1])
        with C:
            st.markdown('<div class="tabs-wrap">', unsafe_allow_html=True)
            tab1, tab2 = st.tabs(["🔐 Sign in", "🆕 Sign up"])
            with tab1:
                st.markdown('<div class="auth-shell">', unsafe_allow_html=True)
                login_ui()
                st.markdown('</div>', unsafe_allow_html=True)
            with tab2:
                st.markdown('<div class="auth-shell">', unsafe_allow_html=True)
                signup_ui()
                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
         
        st.stop()
# else: continue into the authenticated app (unchanged below)


def logout_ui():
    if st.sidebar.button("Log out"):
        # clear all session state to avoid stale role/menu issues
        st.session_state.clear()
        st.rerun()

logout_ui()

# (Moved below auth so it doesn't show on the auth screen)
st.title("Real-Time Order Forecasting System")

# ----------------------------- Tabs -----------------------------
# Helper to read the current role from the session (set by login)
def current_role() -> str:
    auth = st.session_state.get("auth") or {}
    return str(auth.get("role", "viewer")).lower()

role = current_role()

# Build the sidebar menu once
base_menu = ["Upload", "Configure", "Preview", "Download", "History"]
menu = base_menu + (["Admin"] if role == "admin" else [])
TAB = st.sidebar.radio("Navigate", menu)

# ----------------------------- Upload -----------------------------
if TAB == "Upload":
    st.subheader("Upload Weekly Sales Excel/CSV")
    up = st.file_uploader("Choose a file (.xlsx or .csv)", type=["xlsx", "csv"])

    st.caption(
        "Required columns (auto-detected & renamed from Square exports): "
        "`date`, `item_name`, `quantity_sold`"
    )

    if up:
        tmp = Path("data") / f"_tmp_{up.name}"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp, "wb") as f:
            f.write(up.getbuffer())

        # 1) Read the raw file
        df_raw = read_any_table(tmp, sheet=0)

        # Auto-handle Square "wide" exports (dates as columns)
        df_raw = maybe_unpivot_square_wide(df_raw)

        # Optional: detect refunds in the raw Square columns
        refund_mask = None
        if "Event Type" in df_raw.columns:
            refund_mask = df_raw["Event Type"].astype(str).str.contains("refund", case=False, na=False)
        elif "Itemisation Type" in df_raw.columns:
            refund_mask = df_raw["Itemisation Type"].astype(str).str.contains("refund", case=False, na=False)

        # 2) Auto-normalize headers to: date / item_name / quantity_sold
        df_norm, missing = normalize_sales_columns(df_raw)
        if missing:
            st.error("Missing required columns after auto-detect.")
            with st.expander("See detected columns & tips"):
                st.write({
                    "Missing": missing,
                    "Detected headers in your file": list(df_raw.columns),
                })
                st.caption("We need these columns (any order): date, item_name, quantity_sold.")
            tmp.unlink(missing_ok=True)
            st.stop()  # stop the Upload flow cleanly

        # 3) Apply refund negativity BEFORE aggregation (row-wise)
        if refund_mask is not None and "quantity_sold" in df_norm.columns:
            q = pd.to_numeric(df_norm["quantity_sold"], errors="coerce")
            mask = refund_mask.reindex(df_norm.index).fillna(False).astype(bool)
            q = np.where(mask, -np.abs(q), q)  # flip sign for refunds
            df_norm["quantity_sold"] = q

        # 4) Aggregate to unique (date, item_name)
        df_final = coerce_and_aggregate_sales(df_norm)
        errs = validate_sales(df_final)
        if errs:
            st.error(" • ".join(errs))
            tmp.unlink(missing_ok=True)
            st.stop()

        # 5) Save normalized+aggregated XLSX and ingest
        dest = safe_replace_upload(tmp, "sales.xlsx")
        with pd.ExcelWriter(dest) as xw:
            df_final.to_excel(xw, index=False, sheet_name="sales")

        st.success(f"Stored normalized file to {dest}. Ingesting to database…")

        # Ingest into DB (pipeline resolves item variants -> item_id)
        ingest_errs = ingest_sales(dest)
        if ingest_errs:
            st.error(" ; ".join(ingest_errs))
        else:
            st.success("Sales data ingested successfully.")

            # --- Auto-load matching history (weather + holidays) ---
            upload_start = pd.to_datetime(df_final["date"]).min().date()
            upload_end   = pd.to_datetime(df_final["date"]).max().date()

            BAKERY_LOC = GeoPoint(-33.8688, 151.2093)  # TODO: set your bakery lat/lon

            try:
                n_w = upsert_weather_history_to_db(BAKERY_LOC, start=upload_start, end=upload_end)
            except Exception as e:
                n_w = 0
                st.warning(f"Weather history not updated: {e}")

            years = list(range(upload_start.year, upload_end.year + 1))
            try:
                n_h = upsert_holidays_to_db(HolidayScope(country="AU", subdiv="NSW", years=years))
            except Exception as e:
                n_h = 0
                st.warning(f"Holidays not updated: {e}")

            st.info(
                f"Auto-loaded {n_w} weather days ({upload_start} → {upload_end}) "
                f"and ensured holidays for {years[0]}–{years[-1]}."
            )

            # flag for Preview guard (if you use it)
            st.session_state["uploaded_this_session"] = True

            # --- Quietly improve accuracy: train/update models after upload ---
            from app.model_train import train_models_for_all_items
            with st.spinner("Improving accuracy…"):
                results = train_models_for_all_items(min_samples=10)
            trained = sum(1 for r in results if r.saved)
            st.info(f"Accuracy improved for {trained} items based on your latest upload.")

        # Always clean up the temp file at the end
        tmp.unlink(missing_ok=True)

# ----------------------------- Configure -----------------------------
elif TAB == "Configure":
    st.subheader("Real-Time Order Updating System")

    # ---------- Manual Events (optional) ----------
    st.markdown("### Events (optional)")
    ev_file = st.file_uploader("Upload events (CSV/XLSX)", type=["csv", "xlsx"], key="events_file")
    if ev_file:
        tmp = Path("data") / f"_tmp_events_{ev_file.name}"
        with open(tmp, "wb") as f:
            f.write(ev_file.getbuffer())
        try:
            ev_df = read_any_table(tmp)
            # Expecting columns: date, event_name, event_type, uplift_pct
            st.dataframe(ev_df.head(), use_container_width=True)
            if st.button("Save events"):
                upsert_events(ev_df)
                st.success("Events saved and will be considered in upcoming forecasts.")
                st.rerun()
        except Exception as e:
            st.error(f"Could not read events file: {e}")
        finally:
            tmp.unlink(missing_ok=True)

    # ---------- Manual Weather for next week (optional) ----------
    st.markdown("### Manual Weather for next week (optional)")
    w_file = st.file_uploader("Upload weather (CSV/XLSX) for the coming week", type=["csv", "xlsx"], key="weather_file")
    if w_file:
        tmp = Path("data") / f"_tmp_weather_{w_file.name}"
        with open(tmp, "wb") as f:
            f.write(w_file.getbuffer())
        try:
            w_df = read_any_table(tmp)
            # Expecting columns: date, max_temp, rain_mm
            st.dataframe(w_df.head(), use_container_width=True)
            if st.button("Save weather"):
                upsert_weather(w_df, source="manual")
                st.success("Weather saved. It will be used for the next week’s forecast.")
                st.rerun()
        except Exception as e:
            st.error(f"Could not read weather file: {e}")
        finally:
            tmp.unlink(missing_ok=True)

    st.markdown("---")
    st.markdown("### Auto-fetch data")

    # ---------- Friendly status peek ----------
    from datetime import date, timedelta
    with get_conn() as conn:
        w_min, w_max, w_rows = conn.execute(
            "SELECT MIN(date), MAX(date), COUNT(*) FROM weather"
        ).fetchone()
        # events table may include general events + holidays
        e_min, e_max, e_rows = conn.execute(
            "SELECT MIN(date), MAX(date), COUNT(*) FROM events"
        ).fetchone()
        next_evt = conn.execute(
            "SELECT date, event_name, event_type FROM events WHERE date >= date('now') ORDER BY date ASC LIMIT 1"
        ).fetchone()

    # ---------- Action buttons ----------
    col1, col2 = st.columns(2)
    with col1:
        from app.services.weather_service import GeoPoint, upsert_weather_forecast_to_db
        BAKERY_LOC = GeoPoint(-33.8688, 151.2093)  # TODO: set your bakery lat/lon once

        if st.button("Weather: refresh next 7 days"):
            try:
                n = upsert_weather_forecast_to_db(BAKERY_LOC)
                st.success(f"7-day weather updated ({n} rows).")
                st.rerun()
            except Exception as e:
                st.error(f"Weather update failed: {e}")

    with col2:
        from app.services.holiday_service import HolidayScope, upsert_holidays_to_db
        if st.button("Holidays: refresh upcoming (next 90 days)"):
            try:
                start = date.today()
                end   = start + timedelta(days=90)
                years = list(range(start.year, end.year + 1))
                n = upsert_holidays_to_db(HolidayScope(country='AU', subdiv='NSW', years=years))
                st.success(f"Holidays ensured for {years[0]}–{years[-1]} (covers the next 90 days).")
                st.rerun()
            except Exception as e:
                st.error(f"Holiday update failed: {e}")

# ----------------------------- Preview -----------------------------
elif TAB == "Preview":
    st.subheader("Generate Recommendations (Next Week)")

    use_ml = st.checkbox("Smart Forecasting (improves accuracy)", value=True)
    ml_blend = st.slider("AI emphasis", 0.0, 1.0, 0.5, 0.05,
                         help="0 = rely on historical pattern only, 1 = rely fully on AI")

    # Show DB status
    with get_conn() as c:
        min_d, max_d, rows = c.execute(
            "SELECT MIN(date), MAX(date), COUNT(*) FROM sales_data"
        ).fetchone()

    # Require a fresh upload this session
    need_upload_now = not st.session_state.get("uploaded_this_session", False)

    if need_upload_now:
        st.info("Please upload a sales file on the **Upload** tab to generate a new forecast.")
    with get_conn() as conn:
        wmin, wmax, wcnt = conn.execute(
        "SELECT MIN(date), MAX(date), COUNT(*) FROM weather"
        ).fetchone()
        emin, emax, ecnt = conn.execute(
        "SELECT MIN(date), MAX(date), COUNT(*) FROM events"
        ).fetchone()

    if st.button("Generate forecast", disabled=need_upload_now):
        df = generate_forecast(use_ml=use_ml, ml_blend=float(ml_blend))
        if df is None or df.empty:
            st.warning("Not enough data to forecast. Please upload more sales history.")
        else:
            st.success("Forecast ready.")
            st.dataframe(df, use_container_width=True)
            st.session_state["latest_forecast"] = df
            # optional: once used, clear the flag so they must upload again
            st.session_state["uploaded_this_session"] = False

# ----------------------------- Download -----------------------------
elif TAB == "Download":
    st.subheader("Export Order Sheet")
    df = st.session_state.get("latest_forecast")

    if df is None or df.empty:
        st.info("Go to Preview and generate a forecast first.")
    else:
        from email.message import EmailMessage
        import smtplib
        import mimetypes

        # 1) Write the file
        ts = datetime.now().strftime("%Y-%m-%d_%H%M")
        out_path = Path("outputs") / f"order_sheet_{ts}.xlsx"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with pd.ExcelWriter(out_path) as xw:
            df.to_excel(xw, index=False, sheet_name="OrderSheet")

        # 2) Let user choose what to do
        action = st.selectbox(
            "Choose an action",
            ["Download the file", "Email the file"]
        )

        if action == "Download the file":
            st.success(f"Saved: {out_path}")
            st.download_button(
                "Download file",
                data=out_path.read_bytes(),
                file_name=out_path.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        else:
            st.caption("Send the generated order sheet to one or more recipients.")
            to_addr = st.text_input("To (comma-separated)", placeholder="owner@example.com, manager@example.com")
            subject = st.text_input("Subject", value=f"Order Sheet — {ts}")
            body = st.text_area("Message", value="Hi,\n\nPlease find this week's order sheet attached.\n\nThanks.")

            # Optional CC/BCC
            col_cc, col_bcc = st.columns(2)
            with col_cc:
                cc_addr = st.text_input("CC (optional)", placeholder="ops@example.com")
            with col_bcc:
                bcc_addr = st.text_input("BCC (optional)", placeholder="")

            # A small helper to send email with attachment via SMTP
            def _send_email_with_attachment(to_list, cc_list, bcc_list):
                # Load SMTP creds from Streamlit secrets
                try:
                    smtp_conf = st.secrets["smtp"]
                    host = smtp_conf.get("host")
                    port = int(smtp_conf.get("port", 587))
                    user = smtp_conf.get("user")
                    password = smtp_conf.get("password")
                    use_tls = bool(smtp_conf.get("use_tls", True))
                except Exception:
                    st.error(
                        "SMTP settings are missing. Please add them to `.streamlit/secrets.toml` "
                        "(see example below)."
                    )
                    return False

                # Build the message
                msg = EmailMessage()
                msg["From"] = user
                msg["To"] = ", ".join(to_list)
                if cc_list:
                    msg["Cc"] = ", ".join(cc_list)
                msg["Subject"] = subject.strip()
                msg.set_content(body or "")

                # Attach the Excel file
                file_bytes = out_path.read_bytes()
                mime, _ = mimetypes.guess_type(out_path.name)
                maintype, subtype = (mime or "application/octet-stream").split("/", 1)
                msg.add_attachment(file_bytes, maintype=maintype, subtype=subtype, filename=out_path.name)

                # Send
                all_rcpts = to_list + cc_list + bcc_list
                try:
                    if use_tls:
                        server = smtplib.SMTP(host, port, timeout=30)
                        server.starttls()
                    else:
                        server = smtplib.SMTP_SSL(host, port, timeout=30)

                    server.login(user, password)
                    server.send_message(msg, to_addrs=all_rcpts)
                    server.quit()
                    return True
                except Exception as e:
                    st.error(f"Email send failed: {e}")
                    return False

            if st.button("Send email"):
                to_list  = [x.strip() for x in to_addr.split(",") if x.strip()]
                cc_list  = [x.strip() for x in cc_addr.split(",") if x.strip()]
                bcc_list = [x.strip() for x in bcc_addr.split(",") if x.strip()]

                if not to_list:
                    st.warning("Please enter at least one recipient.")
                else:
                    with st.spinner("Sending…"):
                        ok = _send_email_with_attachment(to_list, cc_list, bcc_list)
                    if ok:
                        st.success("Email sent ✅")

# ----------------------------- History -----------------------------
elif TAB == "History":
    st.subheader("Recent Forecasts")

    with get_conn() as conn:
        hist = pd.read_sql_query(
            """
            SELECT week_start_date, item_name, mon, tue, wed, thu, fri, sat, alerts, created_at
            FROM forecasts
            ORDER BY created_at DESC, item_name ASC
            """,
            conn,
        )

    if hist.empty:
        st.info("No forecasts saved yet.")
    else:
        hist["created_at"] = pd.to_datetime(hist["created_at"])
        hist["week_start_date"] = pd.to_datetime(hist["week_start_date"]).dt.date

        runs = (
            hist.groupby(["week_start_date", "created_at"])
                .size().reset_index(name="items")
                .sort_values(["created_at", "week_start_date"], ascending=[False, False])
                .reset_index(drop=True)
        )

        def run_label(row):
            count = int(row["items"])
            created = row["created_at"].strftime("%Y-%m-%d %H:%M")
            return f"Week {row['week_start_date']} • created {created} • {count} items"

        choices = runs.index.tolist()
        selected_idx = st.selectbox(
            "Select a forecast run",
            options=choices,
            format_func=lambda i: run_label(runs.loc[i]),
        )

        sel = runs.loc[selected_idx]
        df_run = hist[
            (hist["week_start_date"] == sel.week_start_date)
            & (hist["created_at"] == sel.created_at)
        ].copy()

        df_view = df_run.rename(
            columns={
                "item_name": "Item Name",
                "mon": "MON", "tue": "TUE", "wed": "WED",
                "thu": "THURS", "fri": "FRI", "sat": "SAT",
                "alerts": "Notes",
            }
        )[["Item Name", "MON", "TUE", "WED", "THURS", "FRI", "SAT", "Notes"]]

        st.markdown(
            f"**Week:** {sel.week_start_date}  |  "
            f"**Created:** {sel.created_at:%Y-%m-%d %H:%M}  |  "
            f"**Items:** {len(df_view)}"
        )
        st.dataframe(df_view, use_container_width=True)

        ts = f"{sel.week_start_date}_{sel.created_at:%Y-%m-%d_%H%M%S}"
        out_path = Path("outputs") / f"order_sheet_{ts}.xlsx"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with pd.ExcelWriter(out_path) as xw:
            df_view.to_excel(xw, index=False, sheet_name="OrderSheet")

        st.download_button(
            "Download this run",
            data=out_path.read_bytes(),
            file_name=out_path.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        with st.expander("Previous runs (headlines)"):
            for _, r in runs.iloc[1:].head(15).iterrows():
                st.write(
                    f"- Week {r['week_start_date']} • created {r['created_at']:%Y-%m-%d %H:%M} • {int(r['items'])} items"
                )

# ----------------------------- Admin -----------------------------
elif TAB == "Admin":
    # Only render for admins
    auth = st.session_state.get("auth") or {}
    if auth.get("role", "viewer").lower() != "admin":
        st.stop()

    st.header("Admin")

    # ---------- User management ----------
    st.subheader("User management")

    col1, col2 = st.columns(2, gap="large")

    # Create user
    with col1:
        st.markdown("**Create user**")
        nu = st.text_input("Username (new)", key="nu")
        npw = st.text_input("Password", type="password", key="npw")
        nrole = st.selectbox("Role", ["user", "admin"], index=0, key="nrole")
        if st.button("Create user", key="btn_create_user"):
            from app.auth import create_user
            try:
                if not nu or not npw:
                    st.error("Username and password are required.")
                else:
                    uid = create_user(nu, npw, nrole)
                    st.success(f"User created: {nu} ({nrole})")
            except Exception as e:
                st.error(str(e))

    # Forgot password (One-time code)
    with col2:
        st.markdown("**Forgot password (one-time code)**")
        from app.auth import start_password_reset, complete_password_reset
        r_user = st.text_input("Username", key="r_user")
        gen, setpw = st.columns([1, 1])

        with gen:
            if st.button("Generate code", key="btn_gen_otp"):
                code = start_password_reset(r_user)
                if code:
                    st.success("One-time code generated (valid 15 minutes).")
                    # In production: email/SMS this code to the user
                    st.code(code, language="text")
                else:
                    st.error("User not found.")

        r_code = st.text_input("One-time code", key="r_code")
        r_new = st.text_input("New password", type="password", key="r_new")
        with setpw:
            if st.button("Set new password", key="btn_set_new"):
                if not (r_user and r_code and r_new):
                    st.error("All fields are required.")
                else:
                    ok = complete_password_reset(r_user, r_code, r_new)
                    st.success("Password updated.") if ok else st.error("Invalid/expired code.")
    st.divider()

    # ---------- Improve accuracy (train models) ----------
    st.subheader("Improve accuracy")
    st.caption("Rebuild recommendations by training/retraining per-item models.")

    if st.button("Train models now"):
        from app.model_train import train_models_for_all_items
        with st.spinner("Training models…"):
            results = train_models_for_all_items(min_samples=10)
        trained = sum(1 for r in results if getattr(r, "saved", False))
        st.success(f"Trained/updated models for {trained} items.")


render_footer(logo_path="assets/footer-logo.jpg", college_logo_path="assets/win-logo.png")
