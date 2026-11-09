import os
import json
import urllib.request
from datetime import datetime

USERNAME = "sayantan-pachal"
TOKEN = os.environ.get("GH_PAT")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

query = """
query($login: String!) {
  user(login: $login) {
    repositories(first: 100, isFork: false, ownerAffiliations: OWNER) {
      totalCount
      nodes {
        stargazers { totalCount }
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      pullRequests(first: 1) { totalCount }
      issues(first: 1) { totalCount }
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
  }
}
"""

def fetch_data():
    req = urllib.request.Request("https://api.github.com/graphql", 
                                 data=json.dumps({"query": query, "variables": {"login": USERNAME}}).encode("utf-8"), 
                                 headers=HEADERS, method="POST")
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())["data"]["user"]

def format_date_range(start_str, end_str):
    if not start_str or not end_str: return "Present"
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    
    if start.year == end.year:
        return f"{start.strftime('%b %d')} - {end.strftime('%b %d, %Y')}"
    return f"{start.strftime('%b %Y')} - {end.strftime('%b %Y')}"

def build_svgs():
    data = fetch_data()
    contribs = data["contributionsCollection"]
    repos = data["repositories"]["nodes"]

    # 1. PROCESS STATS
    total_stars = sum(r["stargazers"]["totalCount"] for r in repos)
    total_commits = contribs["totalCommitContributions"] + contribs["restrictedContributionsCount"]
    total_prs = contribs["pullRequests"]["totalCount"]
    total_issues = contribs["issues"]["totalCount"]
    total_repos = data["repositories"]["totalCount"]

    with open("stats.template.svg", "r", encoding="utf-8") as f:
        stats_svg = f.read()
    
    stats_svg = stats_svg.replace("{{STARS}}", f"{total_stars:,}")
    stats_svg = stats_svg.replace("{{COMMITS}}", f"{total_commits:,}")
    stats_svg = stats_svg.replace("{{PRS}}", f"{total_prs:,}")
    stats_svg = stats_svg.replace("{{ISSUES}}", f"{total_issues:,}")
    stats_svg = stats_svg.replace("{{REPOS}}", f"{total_repos:,}")
    
    with open("stats.svg", "w", encoding="utf-8") as f:
        f.write(stats_svg)

    # 2. PROCESS STREAK
    cal = contribs["contributionCalendar"]["weeks"]
    days = [day for week in cal for day in week["contributionDays"]]
    
    total_contribs = contribs["contributionCalendar"]["totalContributions"]
    first_contrib_date = days[0]["date"] if days else None
    
    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    longest_start = None
    longest_end = None
    temp_start = None
    
    today = str(datetime.utcnow().date())
    
    for day in days:
        if day["contributionCount"] > 0:
            if temp_streak == 0:
                temp_start = day["date"]
            temp_streak += 1
            if temp_streak > longest_streak:
                longest_streak = temp_streak
                longest_start = temp_start
                longest_end = day["date"]
        else:
            temp_streak = 0

    for day in reversed(days):
        if day["contributionCount"] > 0:
            current_streak += 1
        elif day["date"] != today and day["date"] < today:
            break

    with open("streak.template.svg", "r", encoding="utf-8") as f:
        streak_svg = f.read()
        
    streak_svg = streak_svg.replace("{{TOTAL_CONTRIB}}", f"{total_contribs:,}")
    streak_svg = streak_svg.replace("{{CONTRIB_RANGE}}", f"{datetime.strptime(first_contrib_date, '%Y-%m-%d').strftime('%b %Y')} - Present")
    streak_svg = streak_svg.replace("{{CURRENT_STREAK}}", str(current_streak))
    streak_svg = streak_svg.replace("{{LONGEST_STREAK}}", str(longest_streak))
    streak_svg = streak_svg.replace("{{LONGEST_RANGE}}", format_date_range(longest_start, longest_end))
    
    with open("streak.svg", "w", encoding="utf-8") as f:
        f.write(streak_svg)

    # 3. PROCESS LANGUAGES
    langs = {}
    for r in repos:
        for edge in r["languages"]["edges"]:
            name = edge["node"]["name"]
            if name not in langs:
                langs[name] = {"size": 0, "color": edge["node"]["color"]}
            langs[name]["size"] += edge["size"]

    sorted_langs = sorted(langs.items(), key=lambda x: x[1]["size"], reverse=True)[:5]
    total_size = sum(langs[name]["size"] for name in langs)
    
    with open("langs.template.svg", "r", encoding="utf-8") as f:
        lang_svg = f.read()

    current_x = 24.0
    for i, (name, details) in enumerate(sorted_langs):
        pct = (details["size"] / total_size) * 100
        width = (pct / 100) * 492.0
        
        # Make language names fit nicely if they are too long
        display_name = name if len(name) < 11 else name[:8] + ".."
        display_pct = f"{pct:.1f}%" if pct >= 0.1 else "<0.1%"
        
        lang_svg = lang_svg.replace(f"{{{{L{i+1}_NAME}}}}", display_name.ljust(10))
        lang_svg = lang_svg.replace(f"{{{{L{i+1}_PCT}}}}", display_pct)
        lang_svg = lang_svg.replace(f"{{{{C{i+1}}}}}", details["color"] or "#858585")
        lang_svg = lang_svg.replace(f"{{{{W{i+1}}}}}", f"{width:.1f}")
        lang_svg = lang_svg.replace(f"{{{{X{i+1}}}}}", f"{current_x:.1f}")
        
        current_x += width

    # Clear out unused language slots if user has fewer than 5 languages
    for i in range(len(sorted_langs), 5):
        lang_svg = lang_svg.replace(f"{{{{L{i+1}_NAME}}}}", "-")
        lang_svg = lang_svg.replace(f"{{{{L{i+1}_PCT}}}}", "0%")
        lang_svg = lang_svg.replace(f"{{{{C{i+1}}}}}", "transparent")
        lang_svg = lang_svg.replace(f"{{{{W{i+1}}}}}", "0")
        lang_svg = lang_svg.replace(f"{{{{X{i+1}}}}}", "0")

    with open("langs.svg", "w", encoding="utf-8") as f:
        f.write(lang_svg)

if __name__ == "__main__":
    build_svgs()
    print("Metrics successfully generated.")