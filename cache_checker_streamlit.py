
import streamlit as st
import requests
from datetime import datetime

st.set_page_config(page_title="Cache Checker", layout="wide")
st.title("🔍 WordPress Cache & WP Rocket Checker")

# Input
domains_input = st.text_area("Enter one or more domains (one per line):", value="nossopalestra.com.br\nric.com.br\nfolhavitoria.com.br")
check_single = st.checkbox("Check single posts", value=True)
check_archives = st.checkbox("Check archives (categories, tags, authors)")
check_rocket = st.checkbox("Check WP Rocket footer signature", value=True)
max_posts = st.slider("Max posts per domain", 1, 20, 5)

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
    try:
        resp = requests.get(url, timeout=15)
        html = resp.text
        status_code = resp.status_code
        cf_status = resp.headers.get("cf-cache-status", "N/A")
        age_raw = resp.headers.get("age", "N/A")
        age = f"{int(age_raw) // 60} min" if age_raw.isdigit() else age_raw
        rocket = "Rocket" if rocket_check and "Performance optimized by WP Rocket" in html else "-"
        return status_code, cf_status, age, rocket
    except Exception as e:
        return "ERR", "ERR", "ERR", f"Error: {e}"

# Execute
if st.button("🔎 Run Check"):
    today = datetime.now().date().isoformat()
    domains = [d.strip() for d in domains_input.strip().splitlines() if d.strip()]

    results = []

    for domain in domains:
        st.subheader(f"🌐 {domain}")
        base_url = f"https://{domain}"
        posts = get_today_posts(base_url, today, max_posts)
        if not posts:
            st.write("No posts found today.")
            continue

        if check_single:
            st.markdown("**📝 Checking single posts:**")
            for post in posts:
                status, cf_status, age, rocket = check_cache_and_rocket(post['link'], rocket_check=check_rocket)
                st.write(f"- {post['link']} → HTTP: {status}, Cache: {cf_status}, Age: {age}, Rocket: {rocket}")

        if check_archives:
            st.markdown("**📂 Checking archives:**")
            seen = set()
            for post in posts:
                for link in post.get("categories", []) + post.get("tags", []):
                    archive_url = f"{base_url}/?cat={link}"
                    if archive_url in seen:
                        continue
                    seen.add(archive_url)
                    status, cf_status, age, _ = check_cache_and_rocket(archive_url, rocket_check=False)
                    st.write(f"- {archive_url} → HTTP: {status}, Cache: {cf_status}, Age: {age}")

            # Authors via link sniffing (optional)
            st.markdown("**👤 Author archive checks skipped for simplicity.**")
