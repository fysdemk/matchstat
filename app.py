import streamlit as st
import json
import re
from google import genai
from google.genai import types

st.set_page_config(page_title="MATCHSTAT Global Engine", page_icon="⚽", layout="wide")

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
    .match-box { background-color: #151821; border-left: 3px solid #38a169; padding: 8px 12px; margin-bottom: 12px; border-radius: 4px; font-size: 0.85rem; color: #cbd5e0; }
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

# ----------------- INTERFAZ STREAMLIT -----------------
st.title("⚽ MATCHSTAT Global Engine")
st.caption("Rastreo web en tiempo real con Google Search nativo (Gemini 3.8 Flash).")

with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("Google AI Studio API Key", type="password")
    
    # Nombre oficial requerido por tu cuenta de Google
    modelo_seleccionado = st.selectbox(
        "Modelo con Google Search",
        ["gemini-3.8-flash", "gemini-3.5-flash-lite"],
        index=0
    )
    modo_motor = st.selectbox("Estructura de la muestra", ["8/5/3/1 (Ciclo Extendido)", "7/5/3/1 (Estándar puro)"])
    st.markdown("---")
    st.info("💡 **Gemini 3.8 Flash** cuenta con acceso gratuito y búsqueda en vivo en Google.")

col1, col2, col3 = st.columns(3)
with col1:
    equipo_local = st.text_input("Equipo Local", value="Boca Juniors")
with col2:
    equipo_visitante = st.text_input("Equipo Visitante", value="River Plate")
with col3:
    competicion = st.text_input("Competición / Liga", value="Liga Profesional Argentina")

if st.button("🚀 Iniciar Análisis Cuantitativo", use_container_width=True):
    if not api_key:
        st.error("Por favor, ingresa tu API Key de Google AI Studio en la barra lateral.")
        st.stop()

    n_partidos = 8 if "8" in modo_motor else 7
    client = genai.Client(api_key=api_key)

    with st.spinner("🌐 Rastreando fichas y actas oficiales en Google en tiempo real..."):
        prompt = f"""
        Eres el motor cuantitativo de MATCHSTAT. Utiliza tu herramienta integrada de Google Search para rastrear los registros oficiales más recientes.

        PARTIDO A ANALIZAR: {equipo_local} (Local) vs {equipo_visitante} (Visitante) en {competicion}.

        INSTRUCCIONES DE BÚSQUEDA OBLIGATORIA:
        1. LOCAL: Busca los últimos {n_partidos} partidos oficiales reales de {equipo_local} disputados en SU ESTADIO (condición de local).
        2. VISITANTE: Busca los últimos {n_partidos} partidos oficiales reales de {equipo_visitante} disputados FUERA DE SU ESTADIO (condición de visitante).
        3. Para evitar inventar datos, DEBES identificar y listar la fecha y el rival exacto de cada uno de los {n_partidos} partidos encontrados.

        Para cada uno de esos {n_partidos} partidos (ordenados cronológicamente del más antiguo al más reciente), extrae los valores numéricos enteros oficiales de:
        - Goles
        - Tiros de esquina
        - Tarjetas
        - Remates totales
        - Tiros al arco
        - Faltas cometidas
        - Fueras de juego

        REGLA DE FORMATO:
        Devuelve ÚNICAMENTE un bloque de código JSON válido con esta estructura exacta, sin texto adicional:
        {{
          "contexto": "Síntesis de 2 frases sobre la actualidad competitiva real de ambos clubes.",
          "partidos_auditados_local": ["Fecha - Rival (Resultado)", "..."],
          "partidos_auditados_visitante": ["Fecha - Rival (Resultado)", "..."],
          "local": {{
            "Goles": [{n_partidos} enteros],
            "Tiros de esquina": [{n_partidos} enteros],
            "Tarjetas": [{n_partidos} enteros],
            "Remates totales": [{n_partidos} enteros],
            "Tiros al arco": [{n_partidos} enteros],
            "Faltas cometidas": [{n_partidos} enteros],
            "Fueras de juego": [{n_partidos} enteros]
          }},
          "visitante": {{
            "Goles": [{n_partidos} enteros],
            "Tiros de esquina": [{n_partidos} enteros],
            "Tarjetas": [{n_partidos} enteros],
            "Remates totales": [{n_partidos} enteros],
            "Tiros al arco": [{n_partidos} enteros],
            "Faltas cometidas": [{n_partidos} enteros],
            "Fueras de juego": [{n_partidos} enteros]
          }}
        }}
        """

        try:
            # Llamada con Gemini 3.8 Flash y Google Search nativo
            response = client.models.generate_content(
                model=modelo_seleccionado,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.1
                )
            )

            raw_text = response.text
            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if not match:
                st.error("No se pudo estructurar el JSON. Inténtalo nuevamente.")
                st.code(raw_text)
                st.stop()
            
            data = json.loads(match.group(0))

            st.success("✅ Partidos y métricas rastreados directamente en Google con éxito.")
            st.markdown(f"**Contexto Competitivo:** {data.get('contexto', '')}")

            tab_local, tab_visita = st.tabs([f"🏠 {equipo_local} (Local)", f"✈️ {equipo_visitante} (Visitante)"])

            def render_equipo(stats, lista_partidos):
                if lista_partidos:
                    st.markdown("<div class='match-box'><b>📋 Partidos auditados en la muestra (cronológico):</b><br>" + " | ".join(lista_partidos) + "</div>", unsafe_allow_html=True)
                
                for nombre_stat, valores in stats.items():
                    res = calcular_motor(valores, modo_motor)
                    if not res:
                        continue
                    pct_macro = res["pct_prin"][0]
                    badge_class = "badge-solid" if pct_macro >= 80 else ("badge-mid" if pct_macro >= 50 else "badge-low")

                    st.markdown(f"""
                    <div class="stat-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span class="stat-title">{nombre_stat}</span>
                            <span class="{badge_class}">Principal: Más de {res['u_prin']} ({pct_macro}%)</span>
                        </div>
                        <div class="sub-text">
                            <b>Serie real:</b> {res['macro']} | <b>P1:</b> {res['p1']}
                        </div>
                        <div style="margin-top: 6px;">
                            <b>Prom:</b> {res['prom']} | <b>Mediana:</b> {res['med']} | <b>Mín:</b> {res['min']} | <b>Máx:</b> {res['max']}
                        </div>
                        <div style="margin-top: 6px; font-size: 0.88rem;">
                            🔹 <b>Suelo (Más de {res['u_min']}):</b> {res['pct_min'][0]}% Macro · {res['pct_min'][1]}% 5P · {res['pct_min'][2]}% 3P<br>
                            🔸 <b>Línea Principal (Más de {res['u_prin']}):</b> {res['pct_prin'][0]}% Macro · {res['pct_prin'][1]}% 5P · {res['pct_prin'][2]}% 3P
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            with tab_local:
                render_equipo(data["local"], data.get("partidos_auditados_local", []))

            with tab_visita:
                render_equipo(data["visitante"], data.get("partidos_auditados_visitante", []))

        except Exception as e:
            st.error(f"Error procesando los datos: {str(e)}")
