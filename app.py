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

SPREADSHEET_ID = st.secrets.get("SPREADSHEET_ID", "1avShRW4RWj_XHQGdrgQKmvEKXq8WktQpcNO4JQU_Wx4")

GOOGLE_CREDS = {
    "type": "service_account",
    "project_id": "scenic-block-501300-n9",
    "private_key_id": "a451d7fa60bcc4b45fde7d109c92cff1d1b82cdd",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDE8Pmw99Avf485\njsL8UyUXiBke4nfsHltJO0nF05O7eRihF2pfRgnTD+TKr/8h/CH6PTYZ/VjTcpsO\nnNIlD5bkJB9EV26iRBLFwwk+MlxgQ3bOD6Yib340ujyNwUm44oXnLrevQgz6rsgu\niuswv6v6gW6wuPMC+OLJWopmn99MVfFrfJDdYmIDFzj0rLr8jUJEEpLmYzOLCyL1\njhDt4ZW0znC9aA5d/1S38My5tixCc2dMoo9HvaD3/WWneeHajUHROp+p4Sm8/c2J\nurKXnNKacQO4iJYTcQhwfXcQnJRIrfuCRCgEsMMdfPfGdDoJ/YmWRGBisqOxZ46W\nDkqMsmTzAgMBAAECggEAETKl61FIqc0u2azg1B4CoDJvVyYZqNHh0NxPjeny/a0O\nfIrJ7DX2h6rcpOKHmhUldm+/+LcJ+bUJW1ZQd5IL8DJDVLl53MurBAALH5ZQQMvD\nZS0yqdEoqTwWK57UbEPDw7NtsO1Iqt92dbIF5cTnJMIGw4HzHrBTRZgVe+68FjNH\nnKH+3/5523nGk6YRkGwa9IhspaW5ue2ao4QxjFub1R6aUa8lkblQ+uWI6YL6o9Zz\npIJnvU5RsdIpkvGIh6aJafPBSSUm+ZbeZ/OdM6PG9f5AZ6KUsQUo9ivi0HUGhgW0\njZLY2AexIH56425dWQyF+b8x9Qcd5niRlPmDto7ImQKBgQD8bG8JSNpnZ7mmWr4r\nZPE4tjTFb5jgIciPgxUvtSGq2CAmi+udGO/kcIO3aeu+9i2d81RkxWKXuwRkqP5t\np16zwn/ai9NZ8dbeowT+kkqcuMfQHUEuWL83ouaklRZcm4mqi5+WKQIt+HW9jwhf\nQ+BDbAqw/YLTDkXdiq4kTvyBrwKBgQDHu00/65u2WS3L+SMRBigTXdor2En5P1Tk\nAPNOyjXd23QebsrkAzhhpGaEJ6vS2Oe9I4kchWUOVNI0KZlQRacxkzex+gZ4ZjMO\nRCdQqP7knTY5HRdZQQfhYj1b+QENRLpGtRfHuH+yWJ8ek4NCWqyjaysSMqL1M5gj\nlAbg8sM1/QKBgQDX6/lfO853Pab0whKCFCqzlEi3yqo+rydce4iX8p0GAzIdRvsY\nusgZ5JUHQ7fA9dw3jHnYaW/Y0sUDRfu92LmNkwbC73CvM8vVTiVrjb/9J6LkRuIG\nvytycApTJqSmOvYbyKuOSy3uHOa6a6uBshIYGkda9r/9wevJgmNL87TTSQKBgFST\n1BqFQuLs0J/XWCoVWVMaIxD9/hU15FTIsj9jEXxpObrJX9E+K9ntLBw6UGBwyXEm\nYyFYu3peIMVF+E4tsKclmCgdoC/L10LrSVq2tXlJuXRmBUUebJ/cYe9YekGMIPVg\nKjnAvxJexMLF5Idsrj5lW0/RcYAz4PDv9hm7sz5hAoGBAO0J8aVifzO0wdWBmXC2\ng+1yDFYuF7DUmEH+XPYj68UFvRUL2pvB8As3emybK13JSaNjcOUV4J2iqchsPkFd\nJQYn7+MopqiWJkq3ik2V+VuvqJ5Pp8m88xuqxFjusaKa9hJL2x5oi2MMUbIOrgqJ\nq/kqtdWKYyJjMGUNnaolFTS8\n-----END PRIVATE KEY-----\n",
    "client_email": "agente-propiedades@scenic-block-501300-n9.iam.gserviceaccount.com",
    "client_id": "113276906618406088175",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/agente-propiedades%40scenic-block-501300-n9.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
SCRAPER_API_KEY = "2b6731ac933daea5856ba53385bd1007"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
}

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
- valor_usd_raw: precio en USD como número entero (null si no está). Si el precio está en ARS convertilo a USD usando tipo de cambio oficial aproximado
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

def guardar_en_sheets(ws, datos: dict, num_fila: int):
    def fmt_usd(val):
        return f"USD {int(val):,}".replace(",", ".") if val else ""
    def fmt_ars(val):
        return f"$ {int(val):,}".replace(",", ".") if val else ""

    fila = [
        num_fila,
        datos.get("fecha", ""),
        datos.get("hora", ""),
        datos.get("direccion", ""),
        int(datos["metros_raw"]) if datos.get("metros_raw") else "",
        datos.get("piso", ""),
        fmt_usd(datos.get("valor_usd_raw")),
        fmt_usd(datos.get("usd_m2_raw")),
        fmt_ars(datos.get("expensas_ars_raw")),
        datos.get("comentarios", ""),
        datos.get("broker", ""),
        datos.get("telefono", ""),
        datos.get("estado", ""),
        datos.get("aviso_url", ""),
    ]
    ws.append_row(fila, value_input_option="USER_ENTERED")

if not ANTHROPIC_API_KEY:
    st.error("Falta configurar la API key de Anthropic en los secrets de Streamlit.")
    st.stop()

st.subheader("1️⃣ Pegá el link del aviso")
url = st.text_input("", placeholder="https://www.zonaprop.com.ar/... o argenprop.com/... o cualquier portal", label_visibility="collapsed")

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
        with st.spinner("Abriendo el aviso y extrayendo datos... (puede tardar 20 segundos)"):
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
                todos = ws.get_all_values()
                num_fila = len(todos)
                guardar_en_sheets(ws, d, num_fila)
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
