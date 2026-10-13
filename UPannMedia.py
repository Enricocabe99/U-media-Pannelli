import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm as mm_rl
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
)

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title="Calcolo U media pannelli",
                   page_icon="🏗️", layout="wide")
st.title("🏗️ Calcolo U media dei pannelli")
st.caption(
    "Dimensioni in **cm**. Premi **Invio** per passare alla cella a destra; "
    "dall'ultima cella dell'ultima riga, **Invio** aggiunge una nuova riga."
)

# ============================================================
# SESSION STATE
# ============================================================
def _default_row(rid=1):
    return {"id": rid, "B": 0.0, "H": 0.0, "U": 0.0, "N": 1}

if "rows" not in st.session_state:
    st.session_state.rows = [_default_row()]
    st.session_state.next_id = 2
if "gen" not in st.session_state:
    st.session_state.gen = 0  # "generazione" widget: invalida le chiavi vecchie

# Applica un caricamento pendente PRIMA di creare qualsiasi widget
if "_pending_rows" in st.session_state:
    new_rows = st.session_state.pop("_pending_rows")
    for k in list(st.session_state.keys()):
        if k.startswith(("b_", "h_", "u_", "n_")):
            try:
                del st.session_state[k]
            except Exception:
                pass
    st.session_state.rows = new_rows
    st.session_state.next_id = len(new_rows) + 1
    st.session_state.gen += 1
    st.session_state["_flash_ok"] = "Dati caricati correttamente."

if "_flash_ok" in st.session_state:
    st.success(st.session_state.pop("_flash_ok"))
if "_flash_err" in st.session_state:
    st.error(st.session_state.pop("_flash_err"))

# ============================================================
# HELPER
# ============================================================
def add_row():
    st.session_state.rows.append(
        {"id": st.session_state.next_id, "B": 0.0, "H": 0.0, "U": 0.0, "N": 1}
    )
    st.session_state.next_id += 1

def delete_row(rid):
    st.session_state.rows = [r for r in st.session_state.rows if r["id"] != rid]
    g = st.session_state.gen
    for p in ("b_", "h_", "u_", "n_"):
        k = f"{p}{g}_{rid}"
        if k in st.session_state:
            try:
                del st.session_state[k]
            except KeyError:
                pass

def reset_all():
    st.session_state["_pending_rows"] = [{"id": 1, "B": 0.0, "H": 0.0,
                                           "U": 0.0, "N": 1}]

def do_import(file_bytes):
    """Callback eseguita PRIMA del rerun: prepara i dati per il prossimo run."""
    try:
        rows = parse_excel(BytesIO(file_bytes))
        st.session_state["_pending_rows"] = rows
    except Exception as e:
        st.session_state["_flash_err"] = f"Errore nel caricamento: {e}"

def parse_excel(file_obj):
    """Legge un file Excel con colonne:
       Pannello | B (cm) | H (cm) | U (W/m²K) | N°
    """
    df = pd.read_excel(file_obj)
    col_map = {}
    for c in df.columns:
        cl = str(c).strip().lower()
        if "pannell" in cl:
            col_map[c] = "Pannello"
        elif cl.startswith("b"):
            col_map[c] = "B"
        elif cl.startswith("h"):
            col_map[c] = "H"
        elif cl.startswith("u"):
            col_map[c] = "U"
        elif cl.startswith("n"):
            col_map[c] = "N"
    df2 = df.rename(columns=col_map)

    missing = {"B", "H", "U", "N"} - set(df2.columns)
    if missing:
        raise ValueError(
            f"Colonne mancanti: {missing}. Trovate: {list(df.columns)}"
        )

    df2 = df2.reset_index(drop=True)

    rows = []
    new_id = 1
    for _, r in df2.iterrows():
        try:
            B = float(r["B"]) if pd.notna(r["B"]) else 0.0
            H = float(r["H"]) if pd.notna(r["H"]) else 0.0
            U = float(r["U"]) if pd.notna(r["U"]) else 0.0
            N = int(r["N"]) if pd.notna(r["N"]) else 1
        except (ValueError, TypeError):
            continue
        rows.append({"id": new_id, "B": B, "H": H, "U": U, "N": N})
        new_id += 1

    if not rows:
        rows = [{"id": 1, "B": 0.0, "H": 0.0, "U": 0.0, "N": 1}]
    return rows

# ============================================================
# JS: navigazione con INVIO tra le celle numeriche
# ============================================================
components.html(
    """
    <script>
    (function() {
        const pWin = window.parent;
        const pDoc = pWin.document;
        if (pWin.__enterNavInstalled) return;
        pWin.__enterNavInstalled = true;

        function visibleNumberInputs() {
            return Array.from(pDoc.querySelectorAll('input[type="number"]'))
                .filter(el => el.clientWidth > 0 && !el.disabled);
        }

        pDoc.addEventListener('keydown', function(e) {
            if (e.key !== 'Enter') return;
            const t = e.target;
            if (!t || t.tagName !== 'INPUT' || t.type !== 'number') return;
            const inputs = visibleNumberInputs();
            const idx = inputs.indexOf(t);
            if (idx < 0) return;
            e.preventDefault();
            e.stopPropagation();
            if (idx < inputs.length - 1) {
                const next = inputs[idx + 1];
                next.focus();
                if (next.select) next.select();
            } else {
                const addBtn = Array.from(pDoc.querySelectorAll('button'))
                    .find(b => b.textContent.includes('Aggiungi riga'));
                if (addBtn) addBtn.click();
            }
        }, true);
    })();
    </script>
    """,
    height=1,
)

# ============================================================
# LAYOUT 2/3 + 1/3
# ============================================================
col_data, col_res = st.columns([2, 1], gap="large")

# ------------------------------------------------------------
# COLONNA SINISTRA – DATI
# ------------------------------------------------------------
with col_data:
    st.subheader("📋 Dati pannelli")

    with st.form("add_row_form", clear_on_submit=True):
        c_add = st.columns([5, 1])
        c_add[0].text_input(
            "Aggiungi riga", label_visibility="collapsed",
            placeholder="Premi Invio per aggiungere una riga...",
        )
        submitted = c_add[1].form_submit_button("➕ Aggiungi riga")
        if submitted:
            add_row()
            st.session_state.focus_rid = st.session_state.rows[-1]["id"]
            st.rerun()

    # Intestazione
    hc = st.columns([1, 1.4, 1.4, 1.4, 0.8, 0.5])
    hc[0].markdown("**Pannello**")
    hc[1].markdown("**B (cm)**")
    hc[2].markdown("**H (cm)**")
    hc[3].markdown("**U (W/m²K)**")
    hc[4].markdown("**N°**")
    hc[5].markdown("**🗑️**")

    g = st.session_state.gen
    rows_data = []
    for i, row in enumerate(st.session_state.rows):
        rid = row["id"]
        c = st.columns([1, 1.4, 1.4, 1.4, 0.8, 0.5])

        c[0].markdown(
            f"<div style='padding-top:8px; font-weight:600;'>P{i+1}</div>",
            unsafe_allow_html=True,
        )
        b = c[1].number_input(
            "B", value=float(row["B"]), min_value=0.0, step=1.0,
            key=f"b_{g}_{rid}", label_visibility="collapsed",
        )
        hh = c[2].number_input(
            "H", value=float(row["H"]), min_value=0.0, step=1.0,
            key=f"h_{g}_{rid}", label_visibility="collapsed",
        )
        u = c[3].number_input(
            "U", value=float(row["U"]), min_value=0.0, step=0.01,
            format="%.3f", key=f"u_{g}_{rid}", label_visibility="collapsed",
        )
        n = c[4].number_input(
            "N", value=int(row["N"]), min_value=0, step=1,
            key=f"n_{g}_{rid}", label_visibility="collapsed",
        )
        c[5].button("❌", key=f"del_{g}_{rid}",
                    on_click=delete_row, args=(rid,))

        rows_data.append({
            "Pannello": f"P{i+1}",
            "B_cm": b, "H_cm": hh, "U": u, "N": int(n),
        })

    st.button("🗑️ Reset tutto", on_click=reset_all)

# Focus dopo aggiunta riga
if st.session_state.get("focus_rid"):
    st.session_state.pop("focus_rid", None)
    components.html("""
        <script>
        setTimeout(function() {
            const pDoc = window.parent.document;
            const inputs = Array.from(pDoc.querySelectorAll('input[type="number"]'))
                .filter(el => el.clientWidth > 0);
            if (inputs.length >= 4) {
                const t = inputs[inputs.length - 4];
                t.focus(); if (t.select) t.select();
            }
        }, 250);
        </script>
    """, height=0)

# ============================================================
# CALCOLI
# ============================================================
df = pd.DataFrame(rows_data)
df_val = df[(df["B_cm"] > 0) & (df["H_cm"] > 0)
            & (df["U"] > 0) & (df["N"] > 0)].reset_index(drop=True)

if not df_val.empty:
    df_val["Area singola (m²)"] = (df_val["B_cm"] / 100.0) * (df_val["H_cm"] / 100.0)
    df_val["Area tot (m²)"] = df_val["Area singola (m²)"] * df_val["N"]
    area_tot = float(df_val["Area tot (m²)"].sum())
    n_tot = int(df_val["N"].sum())
    u_media_area = float((df_val["U"] * df_val["Area tot (m²)"]).sum() / area_tot)
    u_media_count = float((df_val["U"] * df_val["N"]).sum() / n_tot)
else:
    area_tot = 0.0
    n_tot = 0
    u_media_area = 0.0
    u_media_count = 0.0

# ============================================================
# GENERATORI OUTPUT
# ============================================================
def make_pdf(df_in, u_area, u_count, area, n_tot_):
    """
    PDF con:
    - U dei pannelli a 2 decimali, U medie a 4 decimali
    - Aree a 1 decimale
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm_rl, rightMargin=15 * mm_rl,
        topMargin=15 * mm_rl, bottomMargin=15 * mm_rl,
        title="Calcolo U media pannelli",
    )
    styles = getSampleStyleSheet()
    el = []
    el.append(Paragraph("Riepilogo calcolo U media pannelli", styles["Title"]))
    el.append(Paragraph(
        datetime.now().strftime("Data elaborazione: %d/%m/%Y %H:%M"),
        styles["Normal"]))
    el.append(Spacer(1, 14))

    headers = ["Pannello", "B (cm)", "H (cm)", "Area sing. (m²)",
               "U (W/m²K)", "N", "Area tot. (m²)"]
    data = [headers]
    for _, r in df_in.iterrows():
        data.append([
            r["Pannello"],
            f"{r['B_cm']:.1f}",
            f"{r['H_cm']:.1f}",
            f"{r['Area singola (m²)']:.1f}",   # area → 1 decimale
            f"{r['U']:.2f}",                    # U singolo pannello → 2 decimali
            str(int(r["N"])),
            f"{r['Area tot (m²)']:.1f}",       # area → 1 decimale
        ])
    data.append(["TOTALE", "", "", "", "", str(n_tot_), f"{area:.1f}"])

    t = Table(data, hAlign="CENTER",
              colWidths=[25*mm_rl, 22*mm_rl, 22*mm_rl, 28*mm_rl,
                         28*mm_rl, 15*mm_rl, 30*mm_rl])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ecf0f1")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    el.append(t)
    el.append(Spacer(1, 20))

    el.append(Paragraph("Risultati", styles["Heading2"]))
    el.append(Paragraph(
        f"<b>U media pesata sull'area:</b> {u_area:.4f} W/(m²·K)",
        styles["Normal"]))
    el.append(Paragraph(
        f"<b>U media pesata sul numero di pannelli:</b> {u_count:.4f} W/(m²·K)",
        styles["Normal"]))
    el.append(Paragraph(f"<b>Area totale:</b> {area:.1f} m²", styles["Normal"]))
    el.append(Paragraph(f"<b>Numero totale pannelli:</b> {n_tot_}", styles["Normal"]))
    el.append(Spacer(1, 12))
    el.append(Paragraph(
        "<i>Nota: la U media pesata sull'area è quella fisicamente corretta per la trasmittanza "
        "media dell'involucro.</i>",
        styles["Italic"]))
    doc.build(el)
    buf.seek(0)
    return buf.getvalue()


def make_text(df_in, u_area, u_count, area, n_tot_):
    L = []
    L.append("=" * 70)
    L.append("CALCOLO U MEDIA PANNELLI")
    L.append("=" * 70)
    L.append(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    L.append("")
    L.append("PANNELLI")
    L.append("-" * 70)
    L.append(f"{'Nome':<8}{'B(cm)':>10}{'H(cm)':>10}"
             f"{'Area(m²)':>12}{'U':>8}{'N':>5}{'AreaTot':>12}")
    for _, r in df_in.iterrows():
        L.append(
            f"{r['Pannello']:<8}{r['B_cm']:>10.1f}{r['H_cm']:>10.1f}"
            f"{r['Area singola (m²)']:>12.1f}{r['U']:>8.2f}"
            f"{int(r['N']):>5}{r['Area tot (m²)']:>12.1f}"
        )
    L.append("-" * 70)
    L.append(f"{'TOTALE':<8}{'':>10}{'':>10}{'':>12}{'':>8}{n_tot_:>5}{area:>12.1f}")
    L.append("")
    L.append("RISULTATI")
    L.append("-" * 70)
    L.append(f"U media (pesata area):   {u_area:.4f} W/(m²·K)")
    L.append(f"U media (pesata numero): {u_count:.4f} W/(m²·K)")
    L.append(f"Area totale:             {area:.1f} m²")
    L.append(f"Numero totale pannelli:  {n_tot_}")
    return "\n".join(L)


def make_excel_reimport(df_in):
    """
    Esporta un Excel con lo STESSO formato dell'input:
    Pannello | B (cm) | H (cm) | U (W/m²K) | N°
    Re-importabile direttamente nell'app.
    """
    buf = BytesIO()
    out = df_in.rename(columns={
        "B_cm": "B (cm)",
        "H_cm": "H (cm)",
        "U": "U (W/m²K)",
        "N": "N°",
    })
    cols = ["Pannello", "B (cm)", "H (cm)", "U (W/m²K)", "N°"]
    out[cols].to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    return buf.getvalue()

# ============================================================
# COLONNA DESTRA – RISULTATI + IMPORT/EXPORT
# ============================================================
with col_res:
    st.subheader("📊 Risultati")

    if df_val.empty:
        st.warning("Inserisci almeno un pannello valido (B, H, U > 0 e N > 0).")
    else:
        st.metric("U media (pesata area)", f"{u_media_area:.4f} W/(m²·K)")
        st.metric("U media (pesata n°)",   f"{u_media_count:.4f} W/(m²·K)")
        st.metric("Area totale",           f"{area_tot:.1f} m²")
        st.metric("N° pannelli",           n_tot)

        with st.expander("🔎 Dettaglio calcoli", expanded=False):
            dettaglio = df_val.rename(columns={
                "B_cm": "B (cm)", "H_cm": "H (cm)",
                "U": "U (W/m²K)", "N": "N°",
            })
            st.dataframe(
                dettaglio[["Pannello", "B (cm)", "H (cm)",
                           "Area singola (m²)", "U (W/m²K)",
                           "N°", "Area tot (m²)"]]
                .round({"Area singola (m²)": 1, "Area tot (m²)": 1, "U (W/m²K)": 2}),
                use_container_width=True, hide_index=True,
            )

    st.divider()

    # ---------------- IMPORT ----------------
    st.markdown("**📤 Importa dati (Excel)**")
    uploaded = st.file_uploader(
        "Formato atteso: Pannello | B (cm) | H (cm) | U (W/m²K) | N°",
        type=["xlsx"], key="uploader",
    )
    if uploaded is not None:
        file_bytes = uploaded.getvalue()
        st.button("📥 Carica e sostituisci",
                  on_click=do_import, args=(file_bytes,))

    st.divider()

    # ---------------- EXPORT ----------------
    st.markdown("**📥 Esporta risultati**")

    if df_val.empty:
        st.info("Compila almeno un pannello per abilitare l'export.")
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M")

        st.download_button(
            "📄 PDF (risultati + dettaglio)",
            data=make_pdf(df_val, u_media_area, u_media_count, area_tot, n_tot),
            file_name=f"U_media_{ts}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

        st.download_button(
            "📊 Excel (pannelli, re-importabile)",
            data=make_excel_reimport(df_val),
            file_name=f"pannelli_{ts}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        st.download_button(
            "📝 Testo (.txt)",
            data=make_text(df_val, u_media_area, u_media_count, area_tot, n_tot),
            file_name=f"U_media_{ts}.txt",
            mime="text/plain",
            use_container_width=True,
        )