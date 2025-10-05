import json
import os
from datetime import datetime
from pathlib import Path

from fontTools.misc.timeTools import epoch_diff
from fontTools.ttLib import TTFont
from github import Github

ISSUES_AND_RELEASES_QUERY = """
query ($owner: String!, $name: String!, $since: DateTime!) {
  repository(owner: $owner, name: $name) {
    issues(first: 100, states: CLOSED, filterBy: {since: $since}) {
      nodes {
        title
        number
        url
        closedAt
      }
    }
    refs(refPrefix: "refs/tags/", last: 100) {
      nodes {
        name
        target {
          ... on Tag {
            message
            target {
              ... on Commit {
                committedDate
              }
            }
          }
        }
      }
    }
  }
}
"""

# # Find highest api level fonts in android_fonts/api_level/
# levels = sorted(
#     [
#         int(x.name)
#         for x in Path("android_fonts/api_level/").iterdir()
#         if x.is_dir() and x.name.isdigit()
#     ],
#     reverse=True,
# )
# THEIR_DIRECTORY = "android_fonts/api_level/" + str(levels[0])
THEIR_DIRECTORY = os.environ.get(
    "ANDROID_MOUNT_POINT", "android/system/system/fonts"
)

assert os.path.exists(THEIR_DIRECTORY+"/Roboto-Regular.ttf"), f"No fonts in '{THEIR_DIRECTORY}'"

g = Github(os.environ["GITHUB_TOKEN"])


def font_datetime(value):
    return datetime.fromtimestamp(
        max(0, value + epoch_diff), tz=datetime.now().astimezone().tzinfo
    )


def format_fonttime(value, format="%Y-%m-%dT%H:%M:%S.%f%z"):
    return datetime.fromtimestamp(
        max(0, value + epoch_diff), tz=datetime.now().astimezone().tzinfo
    ).strftime(format)


def remove_suffixes(fontname):
    for suffix in [".ttf", ".otf", "-Regular", "-Bold", "-Italic", "-VF", "[wght]"]:
        if fontname.endswith(suffix):
            fontname = fontname[: -len(suffix)]
    return fontname


android_equivalent = {}
noto_state = json.load(open("notofonts.github.io/docs/noto.json"))

for repo_name, repo in noto_state.items():
    for family_name, family in repo.get("families", {}).items():
        unhinted = family["files"]["unhinted"]
        # If there is both slim-variable-ttf and variable-ttf, use the slim version
        if len(unhinted) > 1 and any("slim-variable-ttf" in x for x in unhinted):
            unhinted = [x for x in unhinted if "slim-variable-ttf" in x]

        for file in unhinted:
            android_equivalent[remove_suffixes(Path(file).name)] = {
                "latest": Path("notofonts.github.io") / file,
                "repo_name": repo_name,
                "family_name": family_name,
            }

results = []
for their_font in list(Path(THEIR_DIRECTORY).glob("*.?tf")):
    if (
        "Noto" not in str(their_font)
        or "UI" in str(their_font)
        or "Bold" in str(their_font)
    ):
        continue
    base = remove_suffixes(Path(their_font).name)
    if base not in android_equivalent:
        print(f"Can't find my version of {their_font}", file=os.sys.stderr)
        continue

    my_file = android_equivalent[base]["latest"]
    their_ttfont = TTFont(their_font)
    my_ttfont = TTFont(my_file)
    their_encoded_glyphs = len(their_ttfont["cmap"].getBestCmap().keys())
    noto_encoded_glyphs = len(my_ttfont["cmap"].getBestCmap().keys())
    new_encoded = len(
        set(my_ttfont["cmap"].getBestCmap().keys())
        - set(their_ttfont["cmap"].getBestCmap().keys())
    )
    their_version = "%0.3f" % their_ttfont["head"].fontRevision
    my_version = "%0.3f" % my_ttfont["head"].fontRevision
    their_date = font_datetime(their_ttfont["head"].modified)
    their_bytesize = os.path.getsize(their_font)
    my_bytesize = os.path.getsize(my_file)
    theirs_ymd = their_date.strftime("%Y-%m-%d")
    my_ymd = font_datetime(my_ttfont["head"].modified).strftime("%Y-%m-%d")
    vf_upgrade = "fvar" not in their_ttfont and "fvar" in my_ttfont
    # print(base, my_file, their_version, theirs_ymd, my_version)

    # # Issues closed since then?
    # repo = g.get_repo("notofonts/" + android_equivalent[base]["repo_name"])
    # issues = list(repo.get_issues(since=their_date, state="closed"))
    # issues = [
    #     {"title": issue.title, "number": issue.number, "url": issue.html_url}
    #     for issue in issues
    # ]

    # # Release logs since then?
    # releases = sorted(
    #     [release for release in repo.get_releases() if release.created_at > their_date],
    #     key=lambda x: x.created_at,
    # )

    res_header, data = g._Github__requester.graphql_query(
        query=ISSUES_AND_RELEASES_QUERY,
        variables={
            "owner": "notofonts",
            "name": android_equivalent[base]["repo_name"],
            "since": theirs_ymd + "T00:00:00Z",
        },
    )
    issues = data["data"]["repository"]["issues"]["nodes"]
    issues = [x for x in issues if x.get("closedAt", "") > theirs_ymd + "T00:00:00Z"]
    releases = data["data"]["repository"]["refs"]["nodes"]
    family_name = android_equivalent[base]["family_name"]
    splatted_family = family_name.replace(" ", "")

    release_notes = [
        {
            "version": release["name"],
            "notes": release["target"].get("message", ""),
            "url": f"https://github.com/notofonts/{android_equivalent[base]['repo_name']}/releases/tag/{release['name']}",
        }
        for release in releases
        if release["target"].get("target", {}).get("committedDate", "")
        > theirs_ymd + "T00:00:00Z"
        and splatted_family + "-" in release["name"]
    ]
    # diffenator_dir = PROJECT + "-noto/diff/" + family_name.replace(" ", "")
    # Path(diffenator_dir).mkdir(parents=True, exist_ok=True)
    # ninja_diff([their_ttfont], [my_ttfont], out=diffenator_dir, filter_styles="Regular")
    # diffenator_report = list(Path(diffenator_dir).glob("**/diffenator.html"))
    # if diffenator_report:
    #     diffenator_report = str(diffenator_report[0]).replace(PROJECT + "-noto/", "")
    # else:
    #     diffenator_report = ""
    results.append(
        {
            "family_name": family_name,
            "my_file": str(my_file),
            "their_version": str(their_version),
            "their_bytesize": their_bytesize,
            "my_bytesize": my_bytesize,
            "noto_version": my_version,
            "their_encoded_glyphs": their_encoded_glyphs,
            "noto_encoded_glyphs": noto_encoded_glyphs,
            "new_encoded": new_encoded,
            "their_date": theirs_ymd,
            "noto_date": my_ymd,
            "release_notes": release_notes,
            "issue_count": len(issues),
            "issues": issues,
            "repo_name": android_equivalent[base]["repo_name"],
            # "diffenator": str(diffenator_report),
            "vf_upgrade": vf_upgrade,
        }
    )

seen_repos = set([x["repo_name"] for x in results])
unseen_repos = set(noto_state.keys()) - seen_repos
unseen_families = []
for repo_name in unseen_repos:
    repo = noto_state[repo_name]
    for family_name, family in repo.get("families", {}).items():
        unseen_families.append({"family": family_name, "repo": repo_name})

results = list(sorted(results, key=lambda x: x["family_name"]))

print(
    json.dumps(
        {"results": results, "unseen_families": unseen_families},
        indent=2,
    )
)
