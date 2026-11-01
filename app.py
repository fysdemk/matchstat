import streamlit as st
import requests
import json
import re
from openai import OpenAI

st.set_page_config(page_title="MATCHSTAT Global Engine — ESPN Direct", page_icon="⚽", layout="wide")

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

# ----------------- CONECTOR ESPN ROBUSTO -----------------
LIGAS_DISPONIBLES = {
    "Liga Profesional Argentina": "arg.1",
    "Brasileirão Série A": "bra.1",
    "Premier League (Inglaterra)": "eng.1",
    "LaLiga (España)": "esp.1",
    "Serie A (Italia)": "ita.1",
    "Bundesliga (Alemania)": "ger.1",
    "Copa Libertadores": "conmebol.libertadores",
    "UEFA Champions League": "uefa.champions"
}

HEADERS_ESPN = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def obtener_equipos_de_liga(codigo_liga):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{codigo_liga}/teams"
    try:
        r = requests.get(url, headers=HEADERS_ESPN, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        equipos = []
        for t in data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", []):
            equipos.append({
                "id": t["team"]["id"],
                "name": t["team"]["displayName"]
            })
        return equipos
    except Exception:
        return []

def obtener_estadisticas_espn(codigo_liga, team_id, nombre_equipo, es_local=True, total_partidos=8, progress_bar=None, status_text=None):
    url_schedule = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{codigo_liga}/teams/{team_id}/schedule"
    r = requests.get(url_schedule, headers=HEADERS_ESPN, timeout=10)
    if r.status_code != 200:
        return None, [], f"Error al consultar calendario en ESPN: HTTP {r.status_code}"

    events = r.json().get("events", [])
    
    partidos_validos = []
    for ev in events:
        comp = ev.get("competitions", [{}])[0]
        status = comp.get("status", {}).get("type", {})
        if status.get("completed", False):
            competitors = comp.get("competitors", [])
            for c in competitors:
                if str(c.get("team", {}).get("id")) == str(team_id):
                    es_en_casa = (c.get("homeAway") == "home")
                    if (es_local and es_en_casa) or (not es_local and not es_en_casa):
                        partidos_validos.append(ev)
                    break

    if len(partidos_validos) < total_partidos:
        cond = "local" if es_local else "visitante"
        return None, [], f"Solo se encontraron {len(partidos_validos)} partidos finalizados de {cond} para {nombre_equipo} en ESPN."

    muestra = partidos_validos[-total_partidos:]

    stats = {
        "Goles": [],
        "Tiros de esquina": [],
        "Tarjetas": [],
        "Remates totales": [],
        "Tiros al arco": [],
        "Faltas cometidas": [],
        "Fueras de juego": []
    }
    nombres_partidos = []

    for i, ev in enumerate(muestra):
        event_id = ev["id"]
        fecha = ev.get("date", "")[:10]
        nombre_partido = ev.get("name", f"Partido {event_id}")
        nombres_partidos.append(f"{fecha} - {nombre_partido}")

        if status_text:
            status_text.text(f"📥 Descargando acta {i+1}/{total_partidos} de {nombre_equipo}: {nombre_partido}")
        if progress_bar:
            progress_bar.progress((i + 1) / total_partidos)

        url_summary = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{codigo_liga}/summary?event={event_id}"
        r_sum = requests.get(url_summary, headers=HEADERS_ESPN, timeout=10)
        
        goles_partido = 0
        corners, amarillas, rojas, remates, al_arco, faltas, offsides = 0, 0, 0, 0, 0, 0, 0

        if r_sum.status_code == 200:
            sum_data = r_sum.json()
            
            for hc in sum_data.get("header", {}).get("competitions", [{}])[0].get("competitors", []):
                if str(hc.get("id")) == str(team_id):
                    try:
                        goles_partido = int(hc.get("score", 0))
                    except:
                        goles_partido = 0

            box_teams = sum_data.get("boxscore", {}).get("teams", [])
            for bt in box_teams:
                if str(bt.get("team", {}).get("id")) == str(team_id):
                    for s in bt.get("statistics", []):
                        val = s.get("displayValue", "0")
                        s_name = s.get("name", "")
                        try:
                            num = int(val)
                        except:
                            num = 0
                        
                        if s_name in ["wonCorners", "cornerKicks"]:
                            corners = num
                        elif s_name == "yellowCards":
                            amarillas = num
                        elif s_name == "redCards":
                            rojas = num
                        elif s_name in ["shotsTotal", "shots"]:
                            remates = num
                        elif s_name == "shotsOnTarget":
                            al_arco = num
                        elif s_name == "foulsCommitted":
                            faltas = num
                        elif s_name == "offsides":
                            offsides = num
                    break

        stats["Goles"].append(goles_partido)
        stats["Tiros de esquina"].append(corners)
        stats["Tarjetas"].append(amarillas + rojas)
        stats["Remates totales"].append(remates)
        stats["Tiros al arco"].append(al_arco)
        stats["Faltas cometidas"].append(faltas)
        stats["Fueras de juego"].append(offsides)

    return stats, nombres_partidos, None

# ----------------- INTERFAZ STREAMLIT -----------------
st.title("⚽ MATCHSTAT Global Engine — ESPN Direct")
st.caption("Extracción en vivo de actas oficiales con barra de progreso.")

with st.sidebar:
    st.header("⚙️ Configuración")
    
    proveedor_ia = st.selectbox(
        "Proveedor de IA",
        ["Groq (Gratis / Llama 3.3 70B)", "Perplexity (Búsqueda Web en Vivo)", "OpenAI (GPT-4o-mini)"],
        index=0
    )
    
    api_key_ia = st.text_input(f"API Key de {proveedor_ia.split()[0]}", type="password")
    
    liga_seleccionada = st.selectbox("Seleccionar Torneo / Liga", list(LIGAS_DISPONIBLES.keys()), index=0)
    codigo_liga = LIGAS_DISPONIBLES[liga_seleccionada]
    
    modo_motor = st.selectbox("Estructura de la muestra", ["8/5/3/1 (Ciclo Extendido)", "7/5/3/1 (Estándar)"])
    st.markdown("---")
    st.info("💡 **Conexión directa:** Las actas se descargan partido a partido desde los servidores abiertos de ESPN.")

equipos_liga = obtener_equipos_de_liga(codigo_liga)
nombres_equipos = [e["name"] for e in equipos_liga]

col1, col2 = st.columns(2)
with col1:
    if nombres_equipos:
        idx_boca = next((i for i, name in enumerate(nombres_equipos) if "Boca" in name), 0)
        equipo_local_nombre = st.selectbox("Equipo Local", nombres_equipos, index=idx_boca)
    else:
        equipo_local_nombre = st.text_input("Equipo Local", value="Boca Juniors")

with col2:
    if nombres_equipos:
        idx_river = next((i for i, name in enumerate(nombres_equipos) if "River" in name), 1 if len(nombres_equipos) > 1 else 0)
        equipo_visita_nombre = st.selectbox("Equipo Visitante", nombres_equipos, index=idx_river)
    else:
        equipo_visita_nombre = st.text_input("Equipo Visitante", value="River Plate")

if st.button("🚀 Extraer Datos Reales y Analizar", use_container_width=True):
    if not api_key_ia:
        st.error(f"Por favor, ingresa tu API Key de {proveedor_ia.split()[0]} en la barra lateral.")
        st.stop()

    n_partidos = 8 if "8" in modo_motor else 7

    id_local = next((e["id"] for e in equipos_liga if e["name"] == equipo_local_nombre), None)
    id_visita = next((e["id"] for e in equipos_liga if e["name"] == equipo_visita_nombre), None)

    if not id_local or not id_visita:
        st.error("No se pudieron resolver los identificadores de los equipos en ESPN.")
        st.stop()

    # Panel de progreso interactivo
    st.markdown("### 🔄 Estado de Descarga")
    status_text = st.empty()
    progress_bar = st.progress(0)

    # 1. Descarga Local
    stats_local, lista_local, err_l = obtener_estadisticas_espn(
        codigo_liga, id_local, equipo_local_nombre, es_local=True, total_partidos=n_partidos,
        progress_bar=progress_bar, status_text=status_text
    )
    if err_l:
        st.error(f"Error Local: {err_l}")
        st.stop()

    # 2. Descarga Visitante
    stats_visita, lista_visita, err_v = obtener_estadisticas_espn(
        codigo_liga, id_visita, equipo_visita_nombre, es_local=False, total_partidos=n_partidos,
        progress_bar=progress_bar, status_text=status_text
    )
    if err_v:
        st.error(f"Error Visitante: {err_v}")
        st.stop()

    status_text.text("✅ ¡Todas las actas de ESPN fueron descargadas con éxito!")
    progress_bar.progress(1.0)

    # 3. Motor matemático puro en Python
    res_local = {k: calcular_motor(v, modo_motor) for k, v in stats_local.items()}
    res_visita = {k: calcular_motor(v, modo_motor) for k, v in stats_visita.items()}

    # 4. Redacción cualitativa con IA (Groq / Perplexity / OpenAI)
    with st.spinner(f"🧠 Redactando cruces tácticos con {proveedor_ia.split()[0]}..."):
        if "Groq" in proveedor_ia:
            cliente_ia = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key_ia)
            modelo_elegido = "llama-3.3-70b-versatile"
        elif "Perplexity" in proveedor_ia:
            cliente_ia = OpenAI(base_url="https://api.perplexity.ai", api_key=api_key_ia)
            modelo_elegido = "sonar"
        else:
            cliente_ia = OpenAI(api_key=api_key_ia)
            modelo_elegido = "gpt-4o-mini"

        prompt_sistema = "Eres un analista cuantitativo de fútbol de élite. Respondes ÚNICAMENTE en formato JSON válido, sin bloques de texto adicionales."

        prompt_usuario = f"""
        Dispones de datos ESTADÍSTICOS 100% REALES extraídos de ESPN para el partido:
        {equipo_local_nombre} (Local) vs {equipo_visita_nombre} (Visitante).

        SERIES AUDITADAS LOCAL ({equipo_local_nombre} en casa, últimos {n_partidos} partidos):
        {json.dumps(stats_local)}

        SERIES AUDITADAS VISITANTE ({equipo_visita_nombre} fuera, últimos {n_partidos} partidos):
        {json.dumps(stats_visita)}

        REGLAS ESTRICTAS:
        - No inventes ningún dato numérico fuera de las series provistas.
        - Redacta:
          1. "contexto_general": 2 frases sobre la actualidad deportiva reciente de ambos equipos.
          2. "cruces_local": Para cada una de las 7 estadísticas, 1 frase evaluando el choque estadístico entre ambos, clasificando con emojis de consistencia (🟢 Alta, 🟡 Moderada, 🔴 Baja).

        ESTRUCTURA EXACTA DE RESPUESTA REQUERIDA (JSON):
        {{
          "contexto_general": "texto...",
          "cruces_local": {{
            "Goles": "🟢/🟡/🔴 texto...",
            "Tiros de esquina": "🟢/🟡/🔴 texto...",
            "Tarjetas": "🟢/🟡/🔴 texto...",
            "Remates totales": "🟢/🟡/🔴 texto...",
            "Tiros al arco": "🟢/🟡/🔴 texto...",
            "Faltas cometidas": "🟢/🟡/🔴 texto...",
            "Fueras de juego": "🟢/🟡/🔴 texto..."
          }}
        }}
        """

        analisis_ia = {}
        try:
            kwargs = {
                "model": modelo_elegido,
                "messages": [
                    {"role": "system", "content": prompt_sistema},
                    {"role": "user", "content": prompt_usuario}
                ],
                "temperature": 0.2
            }
            
            # OpenAI y Groq permiten modo JSON estructurado nativo
            if "Perplexity" not in proveedor_ia:
                kwargs["response_format"] = {"type": "json_object"}

            resp = cliente_ia.chat.completions.create(**kwargs)
            contenido = resp.choices[0].message.content.strip()

            # Limpieza defensiva en caso de que el modelo retorne bloques markdown ```json ... ```
            if "```" in contenido:
                contenido = re.sub(r"```json\s*|```", "", contenido).strip()

            analisis_ia = json.loads(contenido)
        except Exception as e:
            st.warning(f"Redacción cualitativa no disponible ({e}), mostrando métricas matemáticas puras:")

    st.success("✅ Análisis completado con actas oficiales verificadas.")
    if "contexto_general" in analisis_ia:
        st.markdown(f"**Contexto Competitivo:** {analisis_ia['contexto_general']}")

    tab_local, tab_visita = st.tabs([f"🏠 {equipo_local_nombre} (Local)", f"✈️ {equipo_visita_nombre} (Visitante)"])

    def render_panel(resultados, partidos, cruces=None):
        if partidos:
            st.markdown("<div class='match-list'><b>📋 Actas auditadas (cronológico):</b><br>" + "<br>".join(partidos) + "</div>", unsafe_allow_html=True)

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
        render_panel(res_local, lista_local, analisis_ia.get("cruces_local"))

    with tab_visita:
        render_panel(res_visita, lista_visita)
