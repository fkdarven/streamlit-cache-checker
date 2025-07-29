
import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import re

st.set_page_config(page_title="Cache Checker", layout="wide")
st.title("🔍 WordPress Cache & WP Rocket Checker")

# Input
domains_input = st.text_area("Insira um ou mais domínios (um por linha):", value="nossopalestra.com.br\nric.com.br\nfolhavitoria.com.br")
check_single = st.checkbox("Checar posts individuais", value=True)
check_archives = st.checkbox("Checar páginas de arquivos (categorias, tags)")
check_rocket = st.checkbox("Verificar rodapé do WP Rocket", value=True)
max_posts = st.slider("Máximo de posts por domínio", 1, 20, 5)
custom_urls_input = st.text_area("Ou insira URLs específicas para testar (uma por linha):", value="", help="Essas URLs serão verificadas diretamente, além dos posts.")


# Helpers
def get_today_posts(base_url, date_iso, per_page=10):
    url = f"{base_url}/wp-json/wp/v2/posts?after={date_iso}T00:00:00&per_page={per_page}"
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; CacheCheckerBot/1.0)'}
        resp = requests.get(url, headers=headers, timeout=15)
        posts = resp.json()
        return posts if posts else []
    except Exception as e:
        st.warning(f"[{base_url}] Erro ao buscar posts: {e}")
        return []

def check_cache_and_rocket(url, rocket_check=True):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; CacheCheckerBot/1.0)'}
        resp = requests.get(url, headers=headers, timeout=15)
        html = resp.text
        status_code = resp.status_code
        elapsed = round(resp.elapsed.total_seconds(), 2)
        cf_status = resp.headers.get("cf-cache-status", "N/A")
        age_raw = resp.headers.get("age", "N/A")
        age = f"{int(age_raw) // 60} min" if age_raw.isdigit() else age_raw
        rocket = "Rocket" if rocket_check and "Performance optimized by WP Rocket" in html else "-"

        match = re.search(r'<link rel="canonical" href="([^"]+)"', html)
        canonical = match.group(1) if match else "-"

        noindex = "noindex" if re.search(r'<meta name="robots"[^>]*content="[^"]*noindex', html) else "-"

        return status_code, cf_status, age, rocket, elapsed, noindex, canonical
    except Exception as e:
        return "ERR", "ERR", "ERR", "-", "-", f"Erro: {e}", "-"

# Filtro fora do botão
filtro = st.selectbox("Filtrar por status de saúde:", options=["Todos", "✅ Saudável", "⚠️ Atenção", "❌ Sem cache"])

# Execute
if st.button("🔎 Executar Verificação"):
    today = datetime.now().date().isoformat()
    domains = [d.strip() for d in domains_input.strip().splitlines() if d.strip()]
    custom_urls = [u.strip() for u in custom_urls_input.strip().splitlines() if u.strip()]

    all_data = []

    for domain in domains:
        st.subheader(f"🌐 {domain}")
        base_url = f"https://{domain}"
        posts = get_today_posts(base_url, today, max_posts) if check_single else []

        urls_to_check = [post["link"] for post in posts]

        if custom_urls:
            urls_to_check.extend([url for url in custom_urls if domain in url])

        if not urls_to_check:
            st.write("Nenhuma URL para verificar.")
            continue

        data = []

        for url in urls_to_check:
            status, cf_status, age, rocket, elapsed, noindex, canonical = check_cache_and_rocket(url, rocket_check=check_rocket)

            if cf_status == "MISS" or age in ("N/A", "0 min"):
                score = "❌ Sem cache"
            elif rocket == "-" or noindex != "-" or elapsed == "-" or (elapsed != "-" and float(elapsed) > 1.5):
                score = "⚠️ Atenção"
            else:
                score = "✅ Saudável"

            data.append({
                "URL": url,
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
