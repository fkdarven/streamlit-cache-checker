import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Cache Checker", layout="wide")
st.title("🔍 WordPress Cache & WP Rocket Checker")

# Input
domains_input = st.text_area("Insira um ou mais domínios (um por linha):", value="nossopalestra.com.br\nric.com.br\nfolhavitoria.com.br")
check_single = st.checkbox("Checar posts individuais", value=True)
check_archives = st.checkbox("Checar páginas de arquivos (categorias, tags)")
check_rocket = st.checkbox("Verificar rodapé do WP Rocket", value=True)
max_posts = st.slider("Máximo de posts por domínio", 1, 20, 5)

# Helpers
def get_today_posts(base_url, date_iso, per_page=10):
    url = f"{base_url}/wp-json/wp/v2/posts?after={date_iso}T00:00:00&per_page={per_page}"
    try:
        resp = requests.get(url, timeout=15)
        posts = resp.json()
        return posts if posts else []
    except Exception as e:
        st.warning(f"[{base_url}] Erro ao buscar posts: {e}")
        return []

def check_cache_and_rocket(url, rocket_check=True):
    try:
        resp = requests.get(url, timeout=15)
        html = resp.text
        status_code = resp.status_code
        elapsed = round(resp.elapsed.total_seconds(), 2)
        cf_status = resp.headers.get("cf-cache-status", "N/A")
        age_raw = resp.headers.get("age", "N/A")
        age = f"{int(age_raw) // 60} min" if age_raw.isdigit() else age_raw
        rocket = "Rocket" if rocket_check and "Performance optimized by WP Rocket" in html else "-"
        canonical = "-"
        if '<link rel=\"canonical\"' in html:
            start = html.find('<link rel=\"canonical\"')
            href_start = html.find('href=\"', start) + 6
            href_end = html.find('"', href_start)
            canonical = html[href_start:href_end].strip()
        noindex = "noindex" if '<meta name=\"robots\"' in html and "noindex" in html else "-"
        return status_code, cf_status, age, rocket, elapsed, noindex, canonical
    except Exception as e:
        return "ERR", "ERR", "ERR", "-", "-", f"Erro: {e}", "-"

# Execute
if st.button("🔎 Executar Verificação"):
    today = datetime.now().date().isoformat()
    domains = [d.strip() for d in domains_input.strip().splitlines() if d.strip()]

    filtro = st.selectbox("Filtrar por status de saúde:", options=["Todos", "✅ Saudável", "⚠️ Atenção", "❌ Sem cache"])

    for domain in domains:
        st.subheader(f"🌐 {domain}")
        base_url = f"https://{domain}"
        posts = get_today_posts(base_url, today, max_posts)
        if not posts:
            st.write("Nenhum post encontrado hoje.")
            continue

        data = []

        if check_single:
            for post in posts:
                status, cf_status, age, rocket, elapsed, noindex, canonical = check_cache_and_rocket(post['link'], rocket_check=check_rocket)
                score = "✅ Saudável"
                if cf_status == "MISS" or age in ("N/A", "0 min"):
                    score = "❌ Sem cache"
                if rocket == "-" or noindex != "-" or elapsed == "-" or (elapsed != "-" and float(elapsed) > 1.5):
                    score = "⚠️ Atenção"
                data.append({
                    "URL": post['link'],
                    "HTTP": status,
                    "Cache": cf_status,
                    "Age": age,
                    "Tempo (s)": elapsed,
                    "Rocket": rocket,
                    "Noindex": noindex,
                    "Canonical": canonical,
                    "Saúde": score
                })

            df = pd.DataFrame(data)
            if filtro != "Todos":
                df = df[df["Saúde"] == filtro]

            if not df.empty:
                st.markdown("### 📊 Resumo do Domínio")
                total = len(df)
                saudavel = (df["Saúde"] == "✅ Saudável").sum()
                atencao = (df["Saúde"] == "⚠️ Atenção").sum()
                sem_cache = (df["Saúde"] == "❌ Sem cache").sum()
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total de URLs", total)
                col2.metric("✅ Saudáveis", saudavel)
                col3.metric("⚠️ Atenção", atencao)
                col4.metric("❌ Sem cache", sem_cache)

                st.dataframe(df, use_container_width=True)
