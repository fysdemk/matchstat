import streamlit as st
import json
import re
from google import genai
from google.genai import types
from duckduckgo_search import DDGS

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
</style>
""", unsafe_allow_html=True)

def buscar_en_la_web(query, max_res=5):
    try:
        results = DDGS().text(query, max_results=max_res)
        textos = []
        for r in results:
            textos.append(f"Fuente: {r.get('title')}\nDetalle: {r.get('body')}")
        return "\n---\n".join(textos)
    except Exception as e:
        return f"Sin resultados directos: {str(e)}"

def calcular_motor(valores, modo="8/5/3/1"):
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

st.title("⚽ MATCHSTAT Global Engine")
st.caption("Motor cuantitativo con Gemini 1.5 Pro y rastreo web en tiempo real.")

with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("Google AI Studio API Key", type="password")
    modelo_seleccionado = st.selectbox("Modelo de Gemini", ["gemini-1.5-pro", "gemini-1.5-flash"], index=0)
    modo_motor = st.selectbox("Estructura de la muestra", ["8/5/3/1 (Ciclo Extendido)", "7/5/3/1 (Estándar puro)"])
    st.markdown("---")
    st.info("💡 **Gemini 1.5 Pro** garantiza máxima precisión cuantitativa y seguimiento de JSON.")

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

    with st.spinner("🌐 Rastreando fichas oficiales en la web libre..."):
        q_local = f"{equipo_local} ultimos partidos local estadisticas goles corners tarjetas remates {competicion}"
        q_visita = f"{equipo_visitante} ultimos partidos visitante estadisticas goles corners tarjetas remates {competicion}"
        
        datos_web_local = buscar_en_la_web(q_local, max_res=5)
        datos_web_visita = buscar_en_la_web(q_visita, max_res=5)

    with st.spinner(f"⚡ Procesando métricas con {modelo_seleccionado}..."):
        prompt = f"""
        Eres un analista cuantitativo de fútbol de élite. Tu tarea es extraer con rigor matemático absoluto las estadísticas oficiales de partidos oficiales recientes.

        DATOS LOCAL ({equipo_local} en casa):
        {datos_web_local}

        DATOS VISITANTE ({equipo_visitante} fuera):
        {datos_web_visita}

        Con base en los datos web anteriores y tus registros estadísticos oficiales verificados para {equipo_local} vs {equipo_visitante} en {competicion}, extrae las series de los últimos {n_partidos} partidos oficiales:
        1. LOCAL ({equipo_local}) jugando realmente en CASA (estadio local).
        2. VISITANTE ({equipo_visitante}) jugando realmente FUERA (a domicilio).

        Entrega listas de exactamente {n_partidos} enteros reales ordenados cronológicamente de más antiguo a más reciente para:
        1. Goles
        2. Tiros de esquina
        3. Tarjetas
        4. Remates totales
        5. Tiros al arco
        6. Faltas cometidas
        7. Fueras de juego
        8. Saques de meta
        9. Tackles

        Devuelve ÚNICAMENTE un JSON con esta estructura exacta, sin texto adicional:
        {{
          "contexto": "Breve síntesis de 2 frases sobre la dinámica real de ambos equipos.",
          "local": {{
            "nombre": "{equipo_local}",
            "stats": {{
              "Goles": [{n_partidos} enteros],
              "Tiros de esquina": [{n_partidos} enteros],
              "Tarjetas": [{n_partidos} enteros],
              "Remates totales": [{n_partidos} enteros],
              "Tiros al arco": [{n_partidos} enteros],
              "Faltas cometidas": [{n_partidos} enteros],
              "Fueras de juego": [{n_partidos} enteros],
              "Saques de meta": [{n_partidos} enteros],
              "Tackles": [{n_partidos} enteros]
            }}
          }},
          "visitante": {{
            "nombre": "{equipo_visitante}",
            "stats": {{
              "Goles": [{n_partidos} enteros],
              "Tiros de esquina": [{n_partidos} enteros],
              "Tarjetas": [{n_partidos} enteros],
              "Remates totales": [{n_partidos} enteros],
              "Tiros al arco": [{n_partidos} enteros],
              "Faltas cometidas": [{n_partidos} enteros],
              "Fueras de juego": [{n_partidos} enteros],
              "Saques de meta": [{n_partidos} enteros],
              "Tackles": [{n_partidos} enteros]
            }}
          }}
        }}
        """

        try:
            response = client.models.generate_content(
                model=modelo_seleccionado,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1  # Baja temperatura para evitar alucinaciones y asegurar exactitud
                )
            )

            raw_text = response.text
            match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            if not match:
                st.error("No se pudo estructurar el JSON. Inténtalo nuevamente.")
                st.stop()
            
            data = json.loads(match.group(0))

            st.success(f"✅ Métricas verificadas exitosamente con {modelo_seleccionado}.")
            st.markdown(f"**Contexto Competitivo:** {data.get('contexto', '')}")

            tab_local, tab_visita = st.tabs([f"🏠 {equipo_local} (Local)", f"✈️ {equipo_visitante} (Visitante)"])

            def render_equipo(datos_equipo, es_local=True):
                stats = datos_equipo["stats"]
                for nombre_stat, valores in stats.items():
                    res = calcular_motor(valores, modo_motor)
                    pct_macro = res["pct_prin"][0]
                    badge_class = "badge-solid" if pct_macro >= 80 else ("badge-mid" if pct_macro >= 50 else "badge-low")

                    st.markdown(f"""
                    <div class="stat-card">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span class="stat-title">{nombre_stat}</span>
                            <span class="{badge_class}">Principal: Más de {res['u_prin']} ({pct_macro}%)</span>
                        </div>
                        <div class="sub-text">
                            <b>Serie:</b> {res['macro']} | <b>P1:</b> {res['p1']}
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
                render_equipo(data["local"], es_local=True)

            with tab_visita:
                render_equipo(data["visitante"], es_local=False)

        except Exception as e:
            st.error(f"Error procesando los datos: {str(e)}")
