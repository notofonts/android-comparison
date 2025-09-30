---
toc: false
---

```js
import {filesize} from "filesize";
const showdown = (await import("showdown")).default;
let converter = new showdown.Converter({tables: true, simplifiedAutoLink: true, strikethrough: true, tasklists: true});

const allresults = await FileAttachment("./data/android-diff.json").json();
const notes = await FileAttachment("./data/notes.json").json();

const unseen = allresults["unseen_families"].map( (x) => {
  return {
    family: x.family,
    repo: x.repo,
    notes: notes[x.family] || "",
  };
});

const results = allresults["results"].map( (x) => {
  return {
    version_diff: {"theirs": x.their_version, "noto": x.noto_version},
    bytesize_diff: {"theirs": x.their_bytesize, "noto": x.my_bytesize, "diff": x.my_bytesize - x.their_bytesize},
    notes: notes[x.family_name] || "",
    ...x
  };
});
```

```js

function formatIssues(d) {
  if (!d || !d.length) return "";
  let list = [];
  d.forEach( (x) => {
    list.push(htl.html`<li class="issue"><a href="${x.url}">#${x.number}</a>: ${x.title}</li>`);
  });
  let html = htl.html`<details><summary>${d.length} issue${d.length !== 1 ? "s" : ""} closed</summary><ul>${list}</ul></details>`;
  return html;
}

function formatBytesize(d) {
  if (!d) return "";
  let diff = d.diff;
  let diffStr = diff >= 0 ? `(+${filesize(diff)})` : `(${filesize(diff)})`;
  let color = diff > 0 ? "red" : (diff < 0 ? "green" : "black");
  diffStr = htl.html`<span style="color: ${color}; font-family: monospace;">${diffStr}</span>`;
  return htl.html`${filesize(d.theirs)} → ${filesize(d.noto)} ${diffStr}`;
}

function isHtml(r) { return htl.html({raw: [r ]}) || ""}

function formatReleaseNotes(d) {
  if (!d || !d.length) return "";
  let list = [];
  d.forEach( (x) => {
    list.push(`<li><a href="${x.url}">${x.version}</a>
    <div>${converter.makeHtml(x.notes)}</div></li>`);
  });
  let html = `<details><summary>${d.length} release${d.length !== 1 ? "s" : ""}</summary><ul>${list}</ul></details>`;
  return isHtml(html);
}
```

# Updated fonts as at ${(new Date()).toLocaleDateString("en-US", {year: "numeric", month: "long", day: "numeric"})}

```js
Inputs.table(results,
  {
    header: {
      family_name: "Font Family",
      version_diff: "Version",
      bytesize_diff: "Bytesize",
      release_notes: "Release Notes",
      issues: "Issues Closed",
      new_encoded: "New Codepoints",
      notes: "Notes",
      vf_upgrade: "VF Upgrade?",
    },
    width: {
      "version_diff": "100px",
      "bytesize_diff": "250px",
      "release_notes": "300px",
      "new_encoded": "100px",
      "vf_upgrade": "100px",
    },
    columns: [
      "family_name",
      "version_diff",
      "bytesize_diff",
      "vf_upgrade",
      "new_encoded",
      "release_notes",
      "issues",
      "notes"
    ], 
    format: {
      version_diff: (d) => `${d.theirs} → ${d.noto}`,
      vf_upgrade: (d) => d ? htl.html`<span class='vf'>✔</span>` : "",
      bytesize_diff: formatBytesize,
      release_notes: formatReleaseNotes,
      issues: formatIssues,
      notes: isHtml,
    },
    sortBy: ["family_name"],
    rows: 200,
  }
)
```

# Added fonts

Additionally, the following fonts do not exist in the Android set; they may have been added to Noto since the Android versions were last updated.

```js
Inputs.table(unseen.sort( (a,b) => a.family.localeCompare(b.family) ),
  {
    header: {
      family: "Font Family",
      repo: "Repository",
      notes: "Notes",
    },
    columns: [
      "family",
      "repo",
      "notes",
    ],
    sortBy: ["family"],
    rows: 200,
    format: {
      notes: isHtml,
    },
  }
) 
```