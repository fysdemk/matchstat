import streamlit as st
import json
import re
from google import genai
from google.genai import types

st.set_page_config(page_title="MATCHSTAT Global Engine — IA Web Search", page_icon="⚽", layout="wide")

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
        # Aseguramos conversión numérica
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

# ----------------- INTERFAZ STREAMLIT -----------------
st.title("⚽ MATCHSTAT Global Engine — IA Web Search")
st.caption("Búsqueda en tiempo real mediante Gemini 3.8 Flash con Google Search Grounding oficial.")

with st.sidebar:
    st.header("⚙️ Configuración")
    api_key_gemini = st.text_input("Google AI Studio API Key", type="password")
    st.markdown("[👉 Obtén tu API Key gratis aquí](https://aistudio.google.com/app/apikey) *(No pide tarjeta)*")
    
    st.markdown("---")
    modo_motor = st.selectbox("Estructura de la muestra", ["8/5/3/1 (Ciclo Extendido)", "7/5/3/1 (Estándar)"])
    st.info("💡 **Sin APIs pagas:** La IA consulta Google en vivo, audita actas de partidos y extrae estadísticas.")

col1, col2 = st.columns(2)
with col1:
    equipo_local = st.text_input("Equipo Local", value="Boca Juniors")
with col2:
    equipo_visita = st.text_input("Equipo Visitante", value="River Plate")

if st.button("🚀 Buscar Datos en la Web y Analizar", use_container_width=True):
    if not api_key_gemini:
        st.error("Por favor, ingresa tu API Key gratuita de Google AI Studio en la barra lateral.")
        st.stop()

    n_partidos = 8 if "8" in modo_motor else 7

    client = genai.Client(api_key=api_key_gemini)

    prompt = f"""
    Actúa como un recolector de estadísticas deportivas y auditor cuantitativo.
    Realiza una búsqueda exhaustiva en la web (en fuentes oficiales como Promiedos, Flashscore, Sofascore, Transfermarkt) para obtener los datos de los ÚLTIMOS {n_partidos} PARTIDOS OFICIALES YA FINALIZADOS de:
    1. {equipo_local} jugando en condición de LOCAL.
    2. {equipo_visita} jugando en condición de VISITANTE.

    Para cada uno de esos {n_partidos} partidos por equipo, extrae exactamente las series numéricas cronológicas (del más antiguo al más reciente) de:
    - Goles
    - Tiros de esquina
    - Tarjetas (amarillas + rojas)
    - Remates totales
    - Tiros al arco
    - Faltas cometidas
    - Fueras de juego

    REGLAS ESTRICTAS:
    1. Debes buscar partidos reales ya terminados de las temporadas recientes oficiales.
    2. Cada lista dentro de 'stats' debe tener EXACTAMENTE {n_partidos} números enteros.
    3. 'partidos' debe ser una lista de {n_partidos} textos con la fecha y rival (ej: "2024-03-10 vs Racing").
    4. Devuelve ÚNICAMENTE un bloque JSON válido con esta estructura exacta:

    {{
      "partidos_local": ["fecha - rival", ...],
      "stats_local": {{
        "Goles": [0, 1, 2, ...],
        "Tiros de esquina": [4, 6, ...],
        "Tarjetas": [2, 3, ...],
        "Remates totales": [12, 10, ...],
        "Tiros al arco": [4, 5, ...],
        "Faltas cometidas": [11, 14, ...],
        "Fueras de juego": [1, 2, ...]
      }},
      "partidos_visita": ["fecha - rival", ...],
      "stats_visita": {{
        "Goles": [0, 1, ...],
        "Tiros de esquina": [3, 5, ...],
        "Tarjetas": [1, 4, ...],
        "Remates totales": [8, 11, ...],
        "Tiros al arco": [2, 3, ...],
        "Faltas cometidas": [13, 10, ...],
        "Fueras de juego": [0, 1, ...]
      }},
      "contexto_general": "2 frases sobre la actualidad deportiva real de ambos clubes.",
      "cruces_local": {{
        "Goles": "🟢/🟡/🔴 breve cruce",
        "Tiros de esquina": "🟢/🟡/🔴 breve cruce",
        "Tarjetas": "🟢/🟡/🔴 breve cruce",
        "Remates totales": "🟢/🟡/🔴 breve cruce",
        "Tiros al arco": "🟢/🟡/🔴 breve cruce",
        "Faltas cometidas": "🟢/🟡/🔴 breve cruce",
        "Fueras de juego": "🟢/🟡/🔴 breve cruce"
      }}
    }}
    """

    with st.spinner("🌐 Gemini 3.8 Flash está auditando las actas en Google Search en vivo..."):
        try:
            # LLAMADA CON GOOGLE SEARCH ACTIVADO
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.1
                )
            )

            texto_respuesta = response.text.strip()
            
            # Extracción segura del objeto JSON evitando explicaciones o formatos markdown
            match = re.search(r"\{.*\}", texto_respuesta, re.DOTALL)
            if match:
                texto_respuesta = match.group(0)

            datos = json.loads(texto_respuesta)

        except Exception as e:
            st.error(f"Error durante la búsqueda de la IA: {e}")
            st.stop()

    # Procesar métricas en el motor matemático puro
    stats_local = datos.get("stats_local", {})
    stats_visita = datos.get("stats_visita", {})
    partidos_local = datos.get("partidos_local", [])
    partidos_visita = datos.get("partidos_visita", [])
    cruces_local = datos.get("cruces_local", {})

    res_local = {k: calcular_motor(v, modo_motor) for k, v in stats_local.items()}
    res_visita = {k: calcular_motor(v, modo_motor) for k, v in stats_visita.items()}

    st.success("✅ Datos recopilados de la web y auditados correctamente.")
    if "contexto_general" in datos:
        st.markdown(f"**Contexto Competitivo:** {datos['contexto_general']}")

    tab_local, tab_visita = st.tabs([f"🏠 {equipo_local} (Local)", f"✈️ {equipo_visita} (Visitante)"])

    def render_panel(resultados, partidos, cruces=None):
        if partidos:
            st.markdown("<div class='match-list'><b>📋 Actas encontradas en la web:</b><br>" + "<br>".join(partidos) + "</div>", unsafe_allow_html=True)

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
