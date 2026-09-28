import requests
import sys
import base64
from datetime import datetime
import os
import html
import textwrap

def fetch_github_stats(username):
    token = os.environ.get("GH_TOKEN")
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    response = requests.get(f"https://api.github.com/users/{username}", headers=headers)
    if response.status_code == 200:
        stats = response.json()
        try:
            web_resp = requests.get(f"https://github.com/{username}", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
            if web_resp.status_code == 200:
                import re
                m = re.search(r'<span[^>]*class="[^"]*text-bold[^"]*"[^>]*>([0-9,]+)</span>\s*followers', web_resp.text)
                if m:
                    web_followers = int(m.group(1).replace(",", ""))
                    stats["followers"] = max(stats.get("followers", 0), web_followers)
        except Exception as e:
            print(f"Warning: Failed to verify real-time followers ({e})")
        return stats
    return None

def get_pfp_as_base64(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return base64.b64encode(response.content).decode("utf-8")
    except Exception as e:
        print(f"Warning: Failed to fetch PFP ({e})")
    return ""

def calculate_grade(stats, starred_count):
    score = (starred_count * 10) + (stats.get("followers", 0) * 20) + (stats.get("public_repos", 0))
    if score > 2000: return ("S", "grade-s")
    if score > 1000: return ("A", "grade-a")
    if score > 500: return ("B+", "grade-b")
    if score > 400: return ("B", "grade-b")
    if score > 350: return ("B-", "grade-b")
    if score > 200: return ("C", "grade-c")
    if score > 100: return ("D", "grade-c")
    if score > 50: return ("E", "grade-c")
    return ("F", "grade-c")

def format_bio_tspans(bio, max_chars=42, max_lines=3, x=185, line_height=18):
    if not bio:
        return ""
    clean_bio = bio.replace("\r", " ").replace("\n", " ").strip()
    lines = textwrap.wrap(clean_bio, width=max_chars)[:max_lines]
    if len(lines) == 1:
        return f'<tspan x="{x}" dy="0">{html.escape(lines[0])}</tspan>'
    tspans = []
    for i, line in enumerate(lines):
        line_escaped = html.escape(line)
        if i == 0:
            tspans.append(f'<tspan x="{x}" dy="0">{line_escaped}</tspan>')
        else:
            tspans.append(f'<tspan x="{x}" dy="{line_height}">{line_escaped}</tspan>')
    return "".join(tspans)

def generate_svg(stats, username):
    with open("input/profile.svg", "r") as f:
        template = f.read()

    name = stats.get("name") or stats.get("login") or username
    login = stats.get("login") or username
    bio = stats.get("bio") or ""
    followers = stats.get("followers", 0)
    public_repos = stats.get("public_repos", 0)
    public_gists = stats.get("public_gists", 0)

    template = template.replace("{{ GITHUB_NAME }}", html.escape(name))
    template = template.replace("{{ GITHUB_USERNAME }}", html.escape(login))
    template = template.replace("{{ GITHUB_FOLLOWERS }}", str(followers))
    template = template.replace("{{ GITHUB_REPOS }}", str(public_repos))
    template = template.replace("{{ GITHUB_BIO }}", html.escape(bio))
    template = template.replace("{{ GITHUB_BIO_TSPAN }}", format_bio_tspans(bio, max_chars=42, max_lines=3, x=185, line_height=18))
    template = template.replace("{{ GITHUB_GISTS }}", str(public_gists))

    # Socials
    twitter_username = stats.get("twitter_username")
    if twitter_username:
        template = template.replace("{{ GITHUB_TWITTER_URL }}", f"https://twitter.com/{html.escape(twitter_username)}")
        template = template.replace("{{ GITHUB_TWITTER_HANDLE }}", f"@{html.escape(twitter_username)}")
        template = template.replace("{{ TWITTER_DISPLAY }}", "inline")
    else:
        template = template.replace("{{ GITHUB_TWITTER_URL }}", "#")
        template = template.replace("{{ GITHUB_TWITTER_HANDLE }}", "")
        template = template.replace("{{ TWITTER_DISPLAY }}", "none")

    blog_url = stats.get("blog")
    if blog_url:
        if not blog_url.startswith("http://") and not blog_url.startswith("https://"):
            blog_href = f"https://{blog_url}"
        else:
            blog_href = blog_url
        template = template.replace("{{ GITHUB_BLOG_URL }}", html.escape(blog_href))
        display_url = blog_url.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
        template = template.replace("{{ GITHUB_BLOG_DISPLAY_URL }}", html.escape(display_url))
        template = template.replace("{{ BLOG_DISPLAY }}", "inline")
    else:
        template = template.replace("{{ GITHUB_BLOG_URL }}", "#")
        template = template.replace("{{ GITHUB_BLOG_DISPLAY_URL }}", "")
        template = template.replace("{{ BLOG_DISPLAY }}", "none")

    # Avatar base64
    pfp_url = stats.get("avatar_url")
    pfp_data_uri = ""
    if pfp_url:
        pfp_base64 = get_pfp_as_base64(pfp_url)
        if pfp_base64:
            pfp_data_uri = f"data:image/png;base64,{pfp_base64}"
    
    if not pfp_data_uri and pfp_url:
        pfp_data_uri = pfp_url
    template = template.replace("{{ GITHUB_PFP_URL }}", pfp_data_uri)

    # Stars (original query, no per_page)
    token = os.environ.get("GH_TOKEN")
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    starred_count = 0
    try:
        starred_response = requests.get(f"https://api.github.com/users/{username}/starred", headers=headers, timeout=10)
        if starred_response.status_code == 200:
            starred_count = len(starred_response.json())
    except Exception as e:
        print(f"Warning: Failed to fetch starred ({e})")
    
    template = template.replace("{{ GITHUB_STARS }}", str(starred_count))

    # Grade calculation
    grade_letter, grade_class = calculate_grade(stats, starred_count)

    template = template.replace("{{ GITHUB_GRADE }}", grade_letter)
    template = template.replace("{{ GRADE_CLASS }}", grade_class)

    os.makedirs("output", exist_ok=True)
    with open("output/profile.svg", "w", encoding="utf-8") as f:
        f.write(template)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_svg.py <github_username>")
        sys.exit(1)

    username = sys.argv[1]
    github_stats = fetch_github_stats(username)

    if github_stats:
        generate_svg(github_stats, username)
        print(f"Successfully generated output/profile.svg for {username}")
    else:
        print(f"Could not fetch stats for {username}")
        sys.exit(1)
