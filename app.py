import streamlit as st
import json
import re
from datetime import date
import anthropic
import gspread

from google.oauth2.service_account import Credentials
import requests

st.set_page_config(page_title="Propiedades", page_icon="🏠", layout="centered")

st.markdown("""
<style>
    .stButton > button { width: 100%; border-radius: 10px; height: 3em; font-size: 16px; }
</style>
""", unsafe_allow_html=True)

st.title("🏠 Cargador de Propiedades")
st.caption("Pegá el link del aviso y la IA extrae los datos solos.")

SCRAPER_API_KEY = "2b6731ac933daea5856ba53385bd1007"
ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
SPREADSHEET_ID = st.secrets.get("SPREADSHEET_ID", "")

def conectar_sheets():
    scopes = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SPREADSHEET_ID)
    try:
        ws = sh.worksheet("Hoja1")
    except:
        ws = sh.get_worksheet(0)
    return ws

def encontrar_ultima_fila_propiedad(ws):
    todos = ws.get_all_values()
    ultima = 6
    for i, fila in enumerate(todos):
        if fila and fila[0].strip().isdigit():
            ultima = i + 1
    return ultima

def obtener_html(url: str) -> str:
    resp = requests.get(
        "http://api.scraperapi.com",
        params={"api_key": SCRAPER_API_KEY, "url": url, "country_code": "ar"},
        timeout=60
    )
    resp.raise_for_status()
    return resp.text

def extraer_con_ia(html: str, url: str) -> dict:
    texto = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    texto = re.sub(r'<style[^>]*>.*?</style>', '', texto, flags=re.DOTALL)
    texto = re.sub(r'<[^>]+>', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()[:12000]

    prompt = f"""Analizá este texto extraído de un aviso inmobiliario argentino y devolvé SOLO un JSON con los datos de la propiedad.

TEXTO:
{texto}

Devolvé EXACTAMENTE este JSON (sin texto extra, sin markdown):
{{
  "direccion": "dirección completa",
  "metros_raw": 0,
  "piso": "número o null",
  "valor_usd_raw": 0,
  "expensas_ars_raw": 0,
  "broker": "nombre e inmobiliaria o null",
  "telefono": "teléfono completo o null"
}}

Reglas:
- metros_raw: número entero de m² totales (null si no está)
- valor_usd_raw: precio en USD como número entero (null si no está)
- expensas_ars_raw: expensas en ARS como número entero (null si no están)
- Si un dato no existe, usá null
- SOLO JSON, nada más"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    texto_resp = response.content[0].text.strip()
    match = re.search(r'\{[\s\S]*\}', texto_resp)
    if not match:
        raise ValueError("No se pudieron extraer los datos del aviso.")
    datos = json.loads(match.group(0))
    m2 = datos.get("metros_raw")
    usd = datos.get("valor_usd_raw")
    datos["usd_m2_raw"] = round(usd / m2) if m2 and usd else None
    datos["aviso_url"] = url
    return datos

def guardar_en_sheets(ws, datos: dict):
    def fmt_usd(val):
        return f"USD {int(val):,}".replace(",", ".") if val else ""
    def fmt_ars(val):
        return f"$ {int(val):,}".replace(",", ".") if val else ""

    ultima_prop = encontrar_ultima_fila_propiedad(ws)
    nueva_fila = ultima_prop + 1

    # Calcular número de propiedad
    todos = ws.get_all_values()
    nums = [int(f[0]) for f in todos if f and f[0].strip().isdigit()]
    num = max(nums) + 1 if nums else 1

    valores = [
        str(num),
        datos.get("fecha", ""),
        datos.get("hora", ""),
        datos.get("direccion", ""),
        str(int(datos["metros_raw"])) if datos.get("metros_raw") else "",
        datos.get("piso", ""),
        fmt_usd(datos.get("valor_usd_raw")),
        fmt_usd(datos.get("usd_m2_raw")),
        fmt_ars(datos.get("expensas_ars_raw")),
        datos.get("comentarios", ""),
        datos.get("broker", ""),
        datos.get("telefono", ""),
        datos.get("estado", ""),
    ]

    # Insertar fila en la posición correcta
    ws.insert_rows([valores + [""]], nueva_fila)

    # Poner el link como "Ver aviso →"
    url = datos.get("aviso_url", "")
    if url:
        ws.update_acell(f"N{nueva_fila}", f'=HYPERLINK("{url}","Ver aviso →")')

    # Copiar formato de la fila anterior
    sh = ws.spreadsheet
    requests_body = {
        "requests": [{
            "copyPaste": {
                "source": {
                    "sheetId": ws.id,
                    "startRowIndex": ultima_prop - 1,
                    "endRowIndex": ultima_prop,
                    "startColumnIndex": 0,
                    "endColumnIndex": 14
                },
                "destination": {
                    "sheetId": ws.id,
                    "startRowIndex": nueva_fila - 1,
                    "endRowIndex": nueva_fila,
                    "startColumnIndex": 0,
                    "endColumnIndex": 14
                },
                "pasteType": "PASTE_FORMAT",
                "pasteOrientationEnum": "NORMAL"
            }
        }]
    }
    sh.batch_update(requests_body)

if not ANTHROPIC_API_KEY:
    st.error("Falta configurar la API key de Anthropic en los secrets de Streamlit.")
    st.stop()

st.subheader("1️⃣ Pegá el link del aviso")
url = st.text_input("", placeholder="https://www.zonaprop.com.ar/... o cualquier portal inmobiliario", label_visibility="collapsed")

st.subheader("2️⃣ Comentarios (opcional)")
comentarios = st.text_area("", placeholder="Ej: buena luz, necesita reciclaje, 2 cocheras...", label_visibility="collapsed")

col1, col2, col3 = st.columns(3)
with col1:
    fecha = st.date_input("Fecha visita", value=date.today())
with col2:
    hora_input = st.time_input("Hora visita", value=None)
with col3:
    estado = st.selectbox("Estado", ["— sin definir —", "Candidata", "Descartado", "Descartada", "A reciclar", "En evaluación"])

st.markdown("---")

if "datos" not in st.session_state:
    st.session_state.datos = None
if "guardado" not in st.session_state:
    st.session_state.guardado = False

if st.button("🔍 Extraer datos del aviso", type="primary"):
    if not url or not url.startswith("http"):
        st.error("Ingresá un link válido (tiene que empezar con http).")
    else:
        st.session_state.guardado = False
        with st.spinner("Abriendo el aviso y extrayendo datos... (puede tardar 30 segundos)"):
            try:
                html = obtener_html(url)
                datos = extraer_con_ia(html, url)
                datos["fecha"] = fecha.strftime("%d/%m/%Y")
                datos["hora"] = hora_input.strftime("%H:%M") if hora_input else ""
                datos["estado"] = estado if estado != "— sin definir —" else ""
                datos["comentarios"] = comentarios or ""
                st.session_state.datos = datos
            except Exception as e:
                st.error(f"Error al extraer datos: {e}")

if st.session_state.datos and not st.session_state.guardado:
    d = st.session_state.datos
    st.subheader("3️⃣ Revisá los datos extraídos")

    col1, col2 = st.columns(2)
    with col1:
        d["direccion"] = st.text_input("Dirección", value=d.get("direccion") or "")
        d["metros_raw"] = st.number_input("M²", value=float(d["metros_raw"]) if d.get("metros_raw") else 0.0, min_value=0.0)
        d["valor_usd_raw"] = st.number_input("Valor USD", value=float(d["valor_usd_raw"]) if d.get("valor_usd_raw") else 0.0, min_value=0.0)
        d["broker"] = st.text_input("Broker / Inmobiliaria", value=d.get("broker") or "")
    with col2:
        d["piso"] = st.text_input("Piso", value=d.get("piso") or "")
        d["expensas_ars_raw"] = st.number_input("Expensas ARS", value=float(d["expensas_ars_raw"]) if d.get("expensas_ars_raw") else 0.0, min_value=0.0)
        m2 = d.get("metros_raw") or 0
        usd = d.get("valor_usd_raw") or 0
        usd_m2 = round(usd / m2) if m2 > 0 and usd > 0 else 0
        d["usd_m2_raw"] = usd_m2
        st.metric("USD / m² (calculado)", f"USD {usd_m2:,.0f}".replace(",", ".") if usd_m2 else "—")
        d["telefono"] = st.text_input("Teléfono", value=d.get("telefono") or "")

    st.markdown("---")

    if st.button("✅ Guardar en Google Sheets", type="primary"):
        with st.spinner("Guardando en la planilla..."):
            try:
                ws = conectar_sheets()
                guardar_en_sheets(ws, d)
                st.session_state.guardado = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

if st.session_state.guardado:
    st.success("🎉 ¡Propiedad guardada en la planilla!")
    st.markdown(f"[📊 Ver planilla](https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/edit)")
    if st.button("➕ Cargar otra propiedad"):
        st.session_state.datos = None
        st.session_state.guardado = False
        st.rerun()
