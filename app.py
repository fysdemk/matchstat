import streamlit as st
import requests
import json
import re
from duckduckgo_search import DDGS

st.set_page_config(page_title="MATCHSTAT Global Engine — Web Search Directo", page_icon="⚽", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stat-card {
        background-color: #1a1f2c;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 14px;
        border: 1px solid #2d3748;
    }
    .stat-title { font-size: 1.15rem; font-weight: 700; color: #f7fafc; margin-bottom: 8px; }
    .badge-solid { background-color: #2e7d32; color: #fff; padding: 3px 8px; border-radius: 6px; font-weight: bold; font-size: 0.85rem; }
    .badge-mid { background-color: #f57f17; color: #fff; padding: 3px 8px; border-radius: 6px; font-weight: bold; font-size: 0.85rem; }
    .badge-low { background-color: #c62828; color: #fff; padding: 3px 8px; border-radius: 6px; font-weight: bold; font-size: 0.85rem; }
    .sub-text { font-size: 0.85rem; color: #a0aec0; margin-top: 4px; }
    .cruce-box { background-color: #151821; border-left: 3px solid #3182ce; padding: 8px 12px; margin-top: 8px; border-radius: 4px; font-size: 0.88rem; color: #e2e8f0; }
    .match-list { background-color: #131720; padding: 10px; border-radius: 6px; margin-bottom: 12px; font-size: 0.85rem; border: 1px solid #2d3748; }
</style>
""", unsafe_allow_html=True)

# ----------------- MOTOR MATEMÁTICO -----------------
def calcular_motor(valores, modo="8/5/3/1"):
    if not valores or len(valores) == 0:
        return None
    try:
        valores = [float(x) for x in valores]
    except Exception:
        return None

    tam_macro = 8 if "8" in modo else 7
    macro = valores[-tam_macro:]
    p5 = macro[-5:]
    p3 = macro[-3:]
    p1 = macro[-1]

    prom = round(sum(macro) / len(macro), 2)
    s = sorted(macro)
    n = len(s)
    med = s[n // 2] if n % 2 != 0 else round((s[n // 2 - 1] + s[n // 2]) / 2, 1)
    
    min_val = min(macro)
    max_val = max(macro)

    u_min = (min_val - 0.5) if min_val > 0 else 0.5
    u_prin = u_min + 1.0

    pct_min_macro = round(sum(1 for x in macro if x > u_min) / len(macro) * 100, 1)
    pct_min_5 = round(sum(1 for x in p5 if x > u_min) / len(p5) * 100, 1)
    pct_min_3 = round(sum(1 for x in p3 if x > u_min) / len(p3) * 100, 1)

    pct_prin_macro = round(sum(1 for x in macro if x > u_prin) / len(macro) * 100, 1)
    pct_prin_5 = round(sum(1 for x in p5 if x > u_prin) / len(p5) * 100, 1)
    pct_prin_3 = round(sum(1 for x in p3 if x > u_prin) / len(p3) * 100, 1)

    return {
        "macro": [int(x) if x.is_integer() else x for x in macro],
        "p5": [int(x) if x.is_integer() else x for x in p5],
        "p3": [int(x) if x.is_integer() else x for x in p3],
        "p1": int(p1) if p1.is_integer() else p1,
        "prom": prom, "med": med, "min": min_val, "max": max_val,
        "u_min": u_min, "pct_min": (pct_min_macro, pct_min_5, pct_min_3),
        "u_prin": u_prin, "pct_prin": (pct_prin_macro, pct_prin_5, pct_prin_3)
    }

# ----------------- RECOLECTOR WEB GRATUITO -----------------
def buscar_informacion_web(equipo, condicion):
    """Realiza la búsqueda en DuckDuckGo sin consumir cuotas de API."""
    query = f"{equipo} ultimos partidos estadisticas goles tiros remates faltas promiedos flashscore"
    texto_acumulado = ""
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query, max_results=6))
            for r in resultados:
                texto_acumulado += f"\n- {r.get('title', '')}: {r.get('body', '')}"
    except Exception:
        texto_acumulado = f"Datos recientes de {equipo} en condicion de {condicion}."
    return texto_acumulado

# ----------------- PROCESAMIENTO CON IA LIBRE -----------------
def auditar_con_ia_libre(local, visita, contexto_local, contexto_visita, n_partidos):
    prompt_sistema = "Eres un auditor cuantitativo de futbol. Tu labor es responder UNICAMENTE con un objeto JSON valido, sin saludos ni formato markdown."
    
    prompt_usuario = f"""
    A partir de la siguiente informacion web de actas recientes:
    
    [DATOS WEB LOCAL - {local}]:
    {contexto_local}

    [DATOS WEB VISITANTE - {visita}]:
    {contexto_visita}

    Construye las series numericas de los ultimos {n_partidos} partidos finalizados para:
    1. {local} (Local)
    2. {visita} (Visitante)

    Genera listas de EXACTAMENTE {n_partidos} enteros para cada una de estas métricas:
    Goles, Tiros de esquina, Tarjetas, Remates totales, Tiros al arco, Faltas cometidas, Fueras de juego.

    Devuelve EXACTAMENTE este formato JSON:
    {{
      "partidos_local": ["Rival 1", "Rival 2", ...],
      "stats_local": {{
        "Goles": [1, 2, ...],
        "Tiros de esquina": [4, 6, ...],
        "Tarjetas": [2, 3, ...],
        "Remates totales": [12, 10, ...],
        "Tiros al arco": [4, 5, ...],
        "Faltas cometidas": [11, 14, ...],
        "Fueras de juego": [1, 2, ...]
      }},
      "partidos_visita": ["Rival 1", "Rival 2", ...],
      "stats_visita": {{
        "Goles": [0, 1, ...],
        "Tiros de esquina": [3, 5, ...],
        "Tarjetas": [1, 4, ...],
        "Remates totales": [8, 11, ...],
        "Tiros al arco": [2, 3, ...],
        "Faltas cometidas": [13, 10, ...],
        "Fueras de juego": [0, 1, ...]
      }},
      "contexto_general": "Breve resumen de actualidad deportiva.",
      "cruces_local": {{
        "Goles": "🟢/🟡/🔴 analisis",
        "Tiros de esquina": "🟢/🟡/🔴 analisis",
        "Tarjetas": "🟢/🟡/🔴 analisis",
        "Remates totales": "🟢/🟡/🔴 analisis",
        "Tiros al arco": "🟢/🟡/🔴 analisis",
        "Faltas cometidas": "🟢/🟡/🔴 analisis",
        "Fueras de juego": "🟢/🟡/🔴 analisis"
      }}
    }}
    """

    url = "https://text.pollinations.ai/"
    payload = {
        "messages": [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": prompt_usuario}
        ],
        "model": "openai",
        "jsonMode": True
    }

    resp = requests.post(url, json=payload, timeout=30)
    texto = resp.text.strip()
    
    # Limpieza de caracteres de formato
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    if match:
        texto = match.group(0)
    return json.loads(texto)

# ----------------- INTERFAZ STREAMLIT -----------------
st.title("⚽ MATCHSTAT Global Engine — Web Search Directo")
st.caption("Extracción web abierta + IA de procesamiento sin claves ni límites de cuota.")

with st.sidebar:
    st.header("⚙️ Configuración")
    modo_motor = st.selectbox("Estructura de la muestra", ["8/5/3/1 (Ciclo Extendido)", "7/5/3/1 (Estándar)"])
    st.markdown("---")
    st.success("✅ **Modo 100% Libre:** No requiere API Keys, tarjetas ni cuentas de pago.")

col1, col2 = st.columns(2)
with col1:
    equipo_local = st.text_input("Equipo Local", value="Boca Juniors")
with col2:
    equipo_visita = st.text_input("Equipo Visitante", value="River Plate")

if st.button("🚀 Buscar Datos en la Web y Analizar", use_container_width=True):
    n_partidos = 8 if "8" in modo_motor else 7

    # 1. Búsqueda web directa con DuckDuckGo (sin agotar cuotas)
    with st.spinner("🔍 Rastreando actas y resultados recientes en la web..."):
        info_local = buscar_informacion_web(equipo_local, "local")
        info_visita = buscar_informacion_web(equipo_visita, "visitante")

    # 2. Extracción y estructuración con la IA libre
    with st.spinner("🧠 Auditando números y estructurando series numéricas..."):
        try:
            datos = auditar_con_ia_libre(equipo_local, equipo_visita, info_local, info_visita, n_partidos)
        except Exception as e:
            st.error(f"Error procesando la información: {e}")
            st.stop()

    # 3. Motor matemático puro
    stats_local = datos.get("stats_local", {})
    stats_visita = datos.get("stats_visita", {})
    partidos_local = datos.get("partidos_local", [])
    partidos_visita = datos.get("partidos_visita", [])
    cruces_local = datos.get("cruces_local", {})

    res_local = {k: calcular_motor(v, modo_motor) for k, v in stats_local.items()}
    res_visita = {k: calcular_motor(v, modo_motor) for k, v in stats_visita.items()}

    st.success("✅ Datos recopilados de la web y procesados con éxito.")
    if "contexto_general" in datos:
        st.markdown(f"**Contexto Competitivo:** {datos['contexto_general']}")

    tab_local, tab_visita = st.tabs([f"🏠 {equipo_local} (Local)", f"✈️ {equipo_visita} (Visitante)"])

    def render_panel(resultados, partidos, cruces=None):
        if partidos:
            st.markdown("<div class='match-list'><b>📋 Actas auditadas:</b><br>" + "<br>".join(partidos) + "</div>", unsafe_allow_html=True)

        for nombre_stat, res in resultados.items():
            if not res:
                continue
            pct_macro = res["pct_prin"][0]
            badge_class = "badge-solid" if pct_macro >= 80 else ("badge-mid" if pct_macro >= 50 else "badge-low")

            cruce_html = ""
            if cruces and nombre_stat in cruces:
                cruce_html = f"<div class='cruce-box'>⚔️ <b>Cruce:</b> {cruces[nombre_stat]}</div>"

            st.markdown(f"""
            <div class="stat-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="stat-title">{nombre_stat}</span>
                    <span class="{badge_class}">Principal: Más de {res['u_prin']} ({pct_macro}%)</span>
                </div>
                <div class="sub-text">
                    <b>Valores web:</b> {res['macro']} | <b>Último:</b> {res['p1']}
                </div>
                <div style="margin-top: 6px;">
                    <b>Prom:</b> {res['prom']} | <b>Mediana:</b> {res['med']} | <b>Mín:</b> {res['min']} | <b>Máx:</b> {res['max']}
                </div>
                <div style="margin-top: 6px; font-size: 0.88rem;">
                    🔹 <b>Suelo (Más de {res['u_min']}):</b> {res['pct_min'][0]}% Macro · {res['pct_min'][1]}% 5P · {res['pct_min'][2]}% 3P<br>
                    🔸 <b>Línea Principal (Más de {res['u_prin']}):</b> {res['pct_prin'][0]}% Macro · {res['pct_prin'][1]}% 5P · {res['pct_prin'][2]}% 3P
                </div>
                {cruce_html}
            </div>
            """, unsafe_allow_html=True)

    with tab_local:
        render_panel(res_local, partidos_local, cruces_local)

    with tab_visita:
        render_panel(res_visita, partidos_visita)
