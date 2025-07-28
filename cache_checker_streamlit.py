
import streamlit as st
import requests
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
        st.warning(f"[{base_url}] Error fetching posts: {e}")
        return []


def check_cache_and_rocket(url, rocket_check=True):
    """
    Faz uma requisição ao URL e retorna:
    - status_code
    - cf-cache-status
    - age (em minutos)
    - presença do Rocket
    - tempo de resposta (em segundos)
    - presença de noindex
    """
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
        if '<link rel="canonical"' in html:
            start = html.find('<link rel="canonical"')
            href_start = html.find('href="', start) + 6
            href_end = html.find('"', href_start)
            canonical = html[href_start:href_end].strip()

        noindex = "noindex" if '<meta name="robots"' in html and "noindex" in html else "-"
        return status_code, cf_status, age, rocket, elapsed, noindex, canonical
    except Exception as e:
        return "ERR", "ERR", "ERR", "-", "-", f"Error: {e}"
    
    try:
        resp = requests.get(url, timeout=15)
        html = resp.text
        status_code = resp.status_code
        cf_status = resp.headers.get("cf-cache-status", "N/A")
        age_raw = resp.headers.get("age", "N/A")
        age = f"{int(age_raw) // 60} min" if age_raw.isdigit() else age_raw
        rocket = "Rocket" if rocket_check and "Performance optimized by WP Rocket" in html else "-"
        canonical = "-"
        if '<link rel="canonical"' in html:
            start = html.find('<link rel="canonical"')
            href_start = html.find('href="', start) + 6
            href_end = html.find('"', href_start)
            canonical = html[href_start:href_end].strip()

        return status_code, cf_status, age, rocket
    except Exception as e:
        return "ERR", "ERR", "ERR", f"Error: {e}"

# Execute
if st.button("🔎 Executar Verificação"):
    today = datetime.now().date().isoformat()
    domains = [d.strip() for d in domains_input.strip().splitlines() if d.strip()]

    results = []

    for domain in domains:
        st.subheader(f"🌐 {domain}")
        base_url = f"https://{domain}"
        posts = get_today_posts(base_url, today, max_posts)
        if not posts:
            st.write("Nenhum post encontrado hoje.")
            continue

        if check_single:
            st.markdown("**📝 Verificando posts individuais:**")
            for post in posts:
                status, cf_status, age, rocket, elapsed, noindex, canonical = check_cache_and_rocket(post['link'], rocket_check=check_rocket)
                st.write(f"- {post['link']} → HTTP: {status}, Cache: {cf_status}, Age: {age}, Rocket: {rocket}, Tempo: {elapsed}s, Noindex: {noindex}")

        if check_archives:
            st.markdown("**📂 Verificando arquivos:**")
            seen = set()
            for post in posts:
                for link in post.get("categories", []) + post.get("tags", []):
                    archive_url = f"{base_url}/?cat={link}"
                    if archive_url in seen:
                        continue
                    seen.add(archive_url)
                    status, cf_status, age, _, elapsed, noindex = check_cache_and_rocket(archive_url, rocket_check=False)
                    st.write(f"- {archive_url} → HTTP: {status}, Cache: {cf_status}, Age: {age}, Tempo: {elapsed}s, Noindex: {noindex}")

            # Authors via link sniffing (optional)
            
            st.markdown("**👤 Verificando autores via HTML:**")
            author_urls = set()
            for post in posts:
                try:
                    post_html = requests.get(post['link'], timeout=15).text
                    for a in post_html.split('<a '):
                        if '/autor/' in a or '/author/' in a:
                            start = a.find('href="') + 6
                            end = a.find('"', start)
                            href = a[start:end]
                            if href.startswith("http"):
                                full_url = href
                            elif href.startswith("/"):
                                full_url = base_url.rstrip("/") + href
                            else:
                                full_url = base_url.rstrip("/") + "/" + href
                            full_url = full_url.split("?")[0].rstrip("/") + "/"
                            author_urls.add(full_url)
                except Exception as e:
                    st.warning(f"Erro ao buscar autor em {post['link']}: {e}")

            for author_url in sorted(author_urls):
                status, cf_status, age, _, elapsed, noindex = check_cache_and_rocket(author_url, rocket_check=False)
                st.write(f"- {author_url} → HTTP: {status}, Cache: {cf_status}, Age: {age}, Tempo: {elapsed}s, Noindex: {noindex}")
    
