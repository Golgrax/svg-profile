import requests
import sys
import base64
from datetime import datetime
import os

def fetch_github_stats(username):
    token = os.environ.get("GH_TOKEN")
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    response = requests.get(f"https://api.github.com/users/{username}", headers=headers)
    if response.status_code == 200:
        return response.json()
    return None



def get_pfp_as_base64(url):
    response = requests.get(url)
    if response.status_code == 200:
        return base64.b64encode(response.content).decode("utf-8")
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

def generate_svg(stats, username):
    with open("input/profile.svg", "r") as f:
        template = f.read()

    template = template.replace("{{ GITHUB_NAME }}", stats.get("name") or stats.get("login"))
    template = template.replace("{{ GITHUB_USERNAME }}", stats.get("login"))
    template = template.replace("{{ GITHUB_FOLLOWERS }}", str(stats.get("followers", 0)))
    template = template.replace("{{ GITHUB_REPOS }}", str(stats.get("public_repos", 0)))
    template = template.replace("{{ GITHUB_BIO }}", stats.get("bio") or "")
    template = template.replace("{{ GITHUB_GISTS }}", str(stats.get("public_gists", 0)))
    
    join_date = datetime.strptime(stats.get("created_at"), "%Y-%m-%dT%H:%M:%SZ").strftime("%b %Y")
    template = template.replace("{{ GITHUB_JOIN_DATE }}", join_date)

    # Socials
    twitter_username = stats.get("twitter_username")
    if twitter_username:
        template = template.replace("{{ GITHUB_TWITTER_URL }}", f"https://twitter.com/{twitter_username}")
        template = template.replace("{{ GITHUB_TWITTER_HANDLE }}", f"@{twitter_username}")
        template = template.replace("{{ TWITTER_DISPLAY }}", "inline")
    else:
        template = template.replace("{{ TWITTER_DISPLAY }}", "none")

    blog_url = stats.get("blog")
    if blog_url:
        template = template.replace("{{ GITHUB_BLOG_URL }}", blog_url)
        display_url = blog_url.replace("https://", "").replace("http://", "").replace("www.", "")
        template = template.replace("{{ GITHUB_BLOG_DISPLAY_URL }}", display_url)
        template = template.replace("{{ BLOG_DISPLAY }}", "inline")
    else:
        template = template.replace("{{ BLOG_DISPLAY }}", "none")

    pfp_url = stats.get("avatar_url")
    if pfp_url:
        pfp_base64 = get_pfp_as_base64(pfp_url)
        pfp_data_uri = f"data:image/png;base64,{pfp_base64}"
        template = template.replace("{{ GITHUB_PFP_URL }}", pfp_data_uri)

    token = os.environ.get("GH_TOKEN")
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    starred_response = requests.get(f"https://api.github.com/users/{username}/starred", headers=headers)
    
    stargazers_count = 0
    if starred_response.status_code == 200:
        stargazers_count = len(starred_response.json())
        template = template.replace("{{ GITHUB_STARS }}", str(stargazers_count))
    else:
        template = template.replace("{{ GITHUB_STARS }}", "0")

    grade_letter, grade_class = calculate_grade(stats, stargazers_count)
    template = template.replace("{{ GITHUB_GRADE }}", grade_letter)
    template = template.replace("{{ GRADE_CLASS }}", grade_class)

    template += f"\n<!-- Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -->"

    with open("output/profile.svg", "w") as f:
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
