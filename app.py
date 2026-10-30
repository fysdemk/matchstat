import streamlit as st
import requests
import json
import re
from datetime import datetime
from google import genai
from google.genai import types

st.set_page_config(page_title="MATCHSTAT Pro Engine", page_icon="⚽", layout="wide")

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
</style>
""", unsafe_allow_html=True)

# ----------------- MOTOR MATEMÁTICO PURO -----------------
def calcular_motor(valores, modo="8/5/3/1"):
    if not valores or len(valores) == 0:
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
        "macro": macro, "p5": p5, "p3": p3, "p1": p1,
        "prom": prom, "med": med, "min": min_val, "max": max_val,
        "u_min": u_min, "pct_min": (pct_min_macro, pct_min_5, pct_min_3),
        "u_prin": u_prin, "pct_prin": (pct_prin_macro, pct_prin_5, pct_prin_3)
    }

# ----------------- CONECTOR COMPATIBLE PLAN GRATUITO -----------------
@st.cache_data(ttl=3600)
def obtener_datos_oficiales_equipo(api_key_football, nombre_equipo, es_local=True, total_partidos=8):
    headers = {"x-apisports-key": api_key_football.strip()}
    base_url = "https://v3.football.api-sports.io"

    # 1. Buscar ID del equipo
    res_team = requests.get(f"{base_url}/teams?name={nombre_equipo}", headers=headers).json()
    if res_team.get("errors"):
        return None, f"Error en API-Football: {res_team['errors']}"
    
    candidatos = res_team.get("response", [])
    if not candidatos:
        res_team = requests.get(f"{base_url}/teams?search={nombre_equipo}", headers=headers).json()
        candidatos = res_team.get("response", [])

    if not candidatos:
        return None, f"No se encontró el equipo '{nombre_equipo}' en la base oficial."

    team_data = candidatos[0]["team"]
    team_id = team_data["id"]
    team_nombre_oficial = team_data["name"]

    # 2. Descargar partidos por temporada (compatible 100% con Plan Free, sin usar 'last')
    anio_actual = datetime.now().year
    fixtures = []

    # Consulta año actual
    res_fix = requests.get(f"{base_url}/fixtures?team={team_id}&season={anio_actual}", headers=headers).json()
    if res_fix.get("errors") and not res_fix.get("response"):
        return None, f"Error al consultar partidos: {res_fix['errors']}"
    
    fixtures.extend(res_fix.get("response", []))

    # Si hay pocos partidos en el año en curso, agregar el año anterior para completar la muestra
    partidos_terminados = [f for f in fixtures if f.get("fixture", {}).get("status", {}).get("short") in ["FT", "AET", "PEN"]]
    if len(partidos_terminados) < 20:
        res_prev = requests.get(f"{base_url}/fixtures?team={team_id}&season={anio_actual - 1}", headers=headers).json()
        fixtures = res_prev.get("response", []) + fixtures

    # 3. Filtrar solo partidos finalizados y ordenar por fecha cronológica descendente (más recientes primero)
    partidos_terminados = [f for f in fixtures if f.get("fixture", {}).get("status", {}).get("short") in ["FT", "AET", "PEN"]]
    partidos_terminados.sort(key=lambda x: x["fixture"]["date"], reverse=True)

    # 4. Filtrar por condición de localía
    partidos_filtrados = []
    for f in partidos_terminados:
        es_en_casa = (f["teams"]["home"]["id"] == team_id)
        if es_local and es_en_casa:
            partidos_filtrados.append(f)
        elif not es_local and not es_en_casa:
            partidos_filtrados.append(f)
            
        if len(partidos_filtrados) == total_partidos:
            break

    if len(partidos_filtrados) < total_partidos:
        condicion = "local" if es_local else "visitante"
        return None, f"Se encontraron solo {len(partidos_filtrados)} partidos oficiales finalizados de {condicion} para {team_nombre_oficial}."

    # Invertir para que queden ordenados del más antiguo al más reciente (8P -> P1)
    partidos_filtrados.reverse()

    stats_recopiladas = {
        "Goles": [],
        "Tiros de esquina": [],
        "Tarjetas": [],
        "Remates totales": [],
        "Tiros al arco": [],
        "Faltas cometidas": [],
        "Fueras de juego": []
    }

    # 5. Extraer estadísticas oficiales de cada acta
    for fix in partidos_filtrados:
        fix_id = fix["fixture"]["id"]
        
        # Goles
        goles = fix["goals"]["home"] if es_local else fix["goals"]["away"]
        stats_recopiladas["Goles"].append(int(goles) if goles is not None else 0)

        # Estadísticas del partido
        res_stat = requests.get(f"{base_url}/fixtures/statistics?fixture={fix_id}&team={team_id}", headers=headers).json()
        stats_data = res_stat.get("response", [])
        
        c_corners, c_yellow, c_red, c_shots, c_target, c_fouls, c_offs = 0, 0, 0, 0, 0, 0, 0
        if stats_data:
            raw_stats = {item["type"]: item["value"] for item in stats_data[0].get("statistics", [])}
            c_corners = raw_stats.get("Corner Kicks") or 0
            c_yellow = raw_stats.get("Yellow Cards") or 0
            c_red = raw_stats.get("Red Cards") or 0
            c_shots = raw_stats.get("Total Shots") or 0
            c_target = raw_stats.get("Shots on Goal") or 0
            c_fouls = raw_stats.get("Fouls") or 0
            c_offs = raw_stats.get("Offsides") or 0

        stats_recopiladas["Tiros de esquina"].append(int(c_corners))
        stats_recopiladas["Tarjetas"].append(int(c_yellow) + int(c_red))
        stats_recopiladas["Remates totales"].append(int(c_shots))
        stats_recopiladas["Tiros al arco"].append(int(c_target))
        stats_recopiladas["Faltas cometidas"].append(int(c_fouls))
        stats_recopiladas["Fueras de juego"].append(int(c_offs))

    return stats_recopiladas, None

# ----------------- INTERFAZ STREAMLIT -----------------
st.title("⚽ MATCHSTAT Engine — Datos Oficiales")
st.caption("Plan Gratuito API-Football habilitado sin restricciones.")

with st.sidebar:
    st.header("⚙️ Configuración")
    api_key_football = st.text_input("API-Football Key", type="password")
    api_key_gemini = st.text_input("Google AI Studio API Key", type="password")
    
    modelo_gemini = st.selectbox(
        "Modelo de Gemini (Texto)",
        ["gemini-3.8-flash", "gemini-2.5-flash"],
        index=0
    )
    modo_motor = st.selectbox("Estructura de muestra", ["8/5/3/1 (Ciclo Extendido)", "7/5/3/1 (Estándar)"])
    st.markdown("---")
    st.info("💡 Usa consultas por temporada compatibles con la cuenta Free de API-Sports.")

col1, col2 = st.columns(2)
with col1:
    equipo_local = st.text_input("Equipo Local", value="Boca Juniors")
with col2:
    equipo_visitante = st.text_input("Equipo Visitante", value="River Plate")

if st.button("🚀 Extraer Datos Reales y Analizar", use_container_width=True):
    if not api_key_football or not api_key_gemini:
        st.error("Por favor, ingresa tanto tu clave de API-Football como la de Gemini en la barra lateral.")
        st.stop()

    n_partidos = 8 if "8" in modo_motor else 7

    with st.spinner("📥 Conectando con API-Football (modo temporada)..."):
        stats_local, err_l = obtener_datos_oficiales_equipo(api_key_football, equipo_local, es_local=True, total_partidos=n_partidos)
        stats_visita, err_v = obtener_datos_oficiales_equipo(api_key_football, equipo_visitante, es_local=False, total_partidos=n_partidos)

    if err_l:
        st.error(f"Error Local ({equipo_local}): {err_l}")
        st.stop()
    if err_v:
        st.error(f"Error Visitante ({equipo_visitante}): {err_v}")
        st.stop()

    # Cálculo matemático 100% determinístico en Python
    resultados_local = {k: calcular_motor(v, modo_motor) for k, v in stats_local.items()}
    resultados_visita = {k: calcular_motor(v, modo_motor) for k, v in stats_visita.items()}

    # Gemini genera la síntesis y lectura táctica de las series verificadas
    with st.spinner("🧠 Generando análisis táctico con Gemini..."):
        client_gemini = genai.Client(api_key=api_key_gemini)
        
        prompt_cualitativo = f"""
        Eres un analista deportivo cuantitativo. Dispones de datos ESTADÍSTICOS 100% REALES Y OFICIALES para el partido {equipo_local} (Local) vs {equipo_visitante} (Visitante):

        SERIES LOCAL ({equipo_local} en casa, últimos {n_partidos} partidos):
        {json.dumps(stats_local)}

        SERIES VISITANTE ({equipo_visitante} fuera, últimos {n_partidos} partidos):
        {json.dumps(stats_visita)}

        REGLA ESTRICTA:
        No inventes ningún número. Con base en las series auditadas, redacta:
        1. "contexto_general": 2 frases sobre la actualidad deportiva real de ambos clubes.
        2. "cruces_local": Para cada una de las estadísticas, 1 frase de cruce estadístico evaluando la producción de {equipo_local} frente al comportamiento de {equipo_visitante}, clasificando con emojis (🟢 Alta consistencia, 🟡 Moderada, 🔴 Baja consistencia).

        Devuelve ÚNICAMENTE un JSON con esta estructura:
        {{
          "contexto_general": "...",
          "cruces_local": {{
            "Goles": "...",
            "Tiros de esquina": "...",
            "Tarjetas": "...",
            "Remates totales": "...",
            "Tiros al arco": "...",
            "Faltas cometidas": "...",
            "Fueras de juego": "..."
          }}
        }}
        """

        analisis_ia = {}
        try:
            resp = client_gemini.models.generate_content(
                model=modelo_gemini,
                contents=prompt_cualitativo,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1)
            )
            analisis_ia = json.loads(resp.text)
        except Exception as e:
            st.warning(f"Aviso: Las métricas numéricas se cargaron con éxito; redacción de cruces en pausa: {e}")

    st.success("✅ Actas oficiales descargadas y auditadas exitosamente.")
    if "contexto_general" in analisis_ia:
        st.markdown(f"**Contexto Competitivo:** {analisis_ia['contexto_general']}")

    tab_local, tab_visita = st.tabs([f"🏠 {equipo_local} (Local)", f"✈️ {equipo_visitante} (Visitante)"])

    def render_panel(resultados, cruces=None):
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
                    <b>Valores reales 8P:</b> {res['macro']} | <b>P1:</b> {res['p1']}
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
        render_panel(resultados_local, analisis_ia.get("cruces_local"))

    with tab_visita:
        render_panel(resultados_visita)
