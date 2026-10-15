#!/usr/bin/env python3
"""
build_activity.py -- Genera assets/activity.svg con métricas REALES de GitHub (API GraphQL).

Mismo sistema de diseño que el resto del perfil (tokens, tema claro/oscuro, animaciones de resorte).
Solo usa la librería estándar: no hay dependencias que instalar en el workflow.

Variables de entorno:
    GITHUB_TOKEN   token (en Actions: secrets.GITHUB_TOKEN)
    GH_USER        usuario (por defecto AFelipeRD)

Modos:
    python scripts/build_activity.py                  # datos reales -> assets/activity.svg
    python scripts/build_activity.py --demo --out X   # SOLO para probar el diseño (datos sintéticos, marcados "DEMO")
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import random
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ds import ROOT, d, doc, save  # noqa: E402

QUERY = """
query($login:String!){ user(login:$login){
  repositories(ownerAffiliations:OWNER,isFork:false,first:100,privacy:PUBLIC){
    totalCount
    nodes{ stargazerCount languages(first:6,orderBy:{field:SIZE,direction:DESC}){ edges{ size node{ name } } } } }
  contributionsCollection{
    totalCommitContributions totalPullRequestContributions
    contributionCalendar{ totalContributions weeks{ contributionDays{ contributionCount date } } } } } }
"""


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-activity"})
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        sys.exit("GraphQL error: " + json.dumps(payload["errors"]))
    return payload["data"]["user"]


def demo_data():
    rnd = random.Random(3)
    start = dt.date.today() - dt.timedelta(days=52 * 7 + dt.date.today().weekday() + 1)
    weeks = []
    for w in range(53):
        days = []
        for k in range(7):
            day = start + dt.timedelta(days=w * 7 + k)
            c = 0 if rnd.random() < 0.55 else rnd.choice([1, 1, 2, 3, 5, 8])
            days.append({"contributionCount": c, "date": day.isoformat()})
        weeks.append({"contributionDays": days})
    langs = [{"edges": [{"size": 52, "node": {"name": "Python"}}, {"size": 30, "node": {"name": "SQL"}}, {"size": 18, "node": {"name": "JavaScript"}}]}]
    return {"repositories": {"totalCount": 6, "nodes": [{"stargazerCount": 0, "languages": langs[0]}]},
            "contributionsCollection": {"totalCommitContributions": 0, "totalPullRequestContributions": 0,
                                        "contributionCalendar": {"totalContributions": 0, "weeks": weeks}}}


def streaks(weeks):
    days = [x for w in weeks for x in w["contributionDays"] if x["date"] <= dt.date.today().isoformat()]
    best = cur = 0
    for x in days:
        cur = cur + 1 if x["contributionCount"] > 0 else 0
        best = max(best, cur)
    now = 0
    for x in reversed(days):                       # racha actual (hoy sin actividad no la rompe todavía)
        if x["contributionCount"] > 0:
            now += 1
        elif x is days[-1]:
            continue
        else:
            break
    return now, best


def render(u, demo, placeholder=False):
    cc = u["contributionsCollection"]
    cal = cc["contributionCalendar"]
    weeks = cal["weeks"]
    repos = u["repositories"]
    stars = sum(n["stargazerCount"] for n in repos["nodes"])
    now, best = streaks(weeks)
    langs = {}
    for n in repos["nodes"]:
        for e in (n["languages"] or {}).get("edges", []):
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
    total_l = sum(v for _, v in top) or 1

    W, H = 904, 352
    b = [f'<rect class="card" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12"/>',
         f'<g class="in"{d(0)}><rect x="24" y="26" width="6" height="6" rx="1.5" fill="var(--sig)"/>'
         f'<text class="lbl" x="38" y="33.5">05 · ACTIVITY.SYNC</text></g>',
         f'<text class="ttl sans in" x="24" y="60"{d(0.06)}>Actividad en GitHub</text>']
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    tag = "DEMO · datos sintéticos" if demo else f"sincronizado {stamp} UTC"
    tone = "sig" if demo else "t3"
    b.append(f'<g class="in"{d(0.1)}><text class="small" x="{W - 24}" y="33.5" text-anchor="end" style="fill:var(--{tone})">{tag}</text></g>')

    if placeholder:
        tag = "pendiente de la primera sincronización"
        b[-1] = f'<g class="in"{d(0.1)}><text class="small" x="{W - 24}" y="33.5" text-anchor="end">{tag}</text></g>'
    tiles = [("CONTRIB. · 12 MESES", cal["totalContributions"]), ("COMMITS", cc["totalCommitContributions"]),
             ("REPOS PÚBLICOS", repos["totalCount"]), ("ESTRELLAS", stars), ("RACHA ACTUAL / MAYOR", f"{now} / {best}")]
    if placeholder:
        tiles = [(lab, "—") for lab, _ in tiles]
    tw = (W - 48 - 4 * 12) / 5
    for i, (lab, val) in enumerate(tiles):
        x = 24 + i * (tw + 12)
        b.append(f'<g class="pop"{d(0.15 + i * 0.07)}><rect class="node" x="{x:.1f}" y="82" width="{tw:.1f}" height="58" rx="8"/>'
                 f'<text class="nl" x="{x + 12:.1f}" y="102" style="font-size:8.5px">{lab}</text>'
                 f'<text class="sans" x="{x + 12:.1f}" y="128" style="font-size:23px;font-weight:700;fill:var(--t1);letter-spacing:-.02em">{val}</text></g>')
    # mapa de calor: 5 niveles sobre el acento de señal
    mx = max([x["contributionCount"] for w in weeks for x in w["contributionDays"]] or [1]) or 1
    cell, gap, x0, y0 = 13, 3, 24, 164
    for ci, w in enumerate(weeks):
        for ri, x in enumerate(w["contributionDays"]):
            c = x["contributionCount"]
            lvl = 0 if c == 0 else min(4, 1 + int(3 * (c - 1) / max(mx - 1, 1)))
            fill = "var(--s2)" if lvl == 0 else "var(--sig)"
            op = "" if lvl == 0 else f' fill-opacity="{[0, .28, .5, .75, 1][lvl]}"'
            b.append(f'<rect class="pop" x="{x0 + ci * (cell + gap)}" y="{y0 + ri * (cell + gap)}" width="{cell}" height="{cell}" rx="2.5" '
                     f'fill="{fill}"{op}{d(0.3 + ci * 0.014)}><title>{x["date"]}: {c}</title></rect>')
    # leyenda
    lx = W - 24 - 5 * 15 - 60
    b.append(f'<text class="small" x="{lx}" y="{y0 + 7 * 16 + 14}" text-anchor="end">menos</text>')
    for i, o in enumerate([0, .28, .5, .75, 1]):
        f = "var(--s2)" if o == 0 else "var(--sig)"
        op = "" if o == 0 else ' fill-opacity="%s"' % o
        b.append(f'<rect x="{lx + 8 + i * 15}" y="{y0 + 7 * 16 + 5}" width="12" height="12" rx="2.5" fill="{f}"{op}/>')
    b.append(f'<text class="small" x="{lx + 8 + 5 * 15 + 4}" y="{y0 + 7 * 16 + 14}">más</text>')
    # lenguajes (por tamaño de código en repos propios)
    ly = y0 + 7 * 16 + 22
    cols = ["dat", "sig", "t2", "datd", "sigd"]
    x = 24
    full = W - 48
    b.append(f'<g class="in"{d(0.9)}><rect x="24" y="{ly}" width="{full}" height="8" rx="4" fill="var(--s2)"/></g>')
    lg = []
    for i, (name, size) in enumerate(top):
        w = full * size / total_l
        b.append(f'<rect class="bar" x="{x:.1f}" y="{ly}" width="{max(w - 2, 2):.1f}" height="8" rx="3" fill="var(--{cols[i]})"{d(1.0 + i * 0.1)}/>')
        lg.append((x, name, size / total_l, cols[i]))
        x += w
    lx2 = 24
    for _, name, frac, col in lg:
        b.append(f'<g class="in"{d(1.4)}><circle cx="{lx2 + 4}" cy="{ly + 24}" r="3.5" fill="var(--{col})"/>'
                 f'<text class="tag" x="{lx2 + 13}" y="{ly + 27.5}">{name} {frac * 100:.0f}%</text></g>')
        lx2 += 13 + len(f"{name} {frac * 100:.0f}%") * 6.1 + 18
    if not top:
        b.append(f'<text class="small" x="24" y="{ly + 27}">Sin código en repos propios todavía.</text>')
    return doc(W, H, "".join(b), "Actividad en GitHub",
               f"Contribuciones del último año: {cal['totalContributions']}; repos públicos: {repos['totalCount']}; racha actual {now}, mayor {best}.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--placeholder", action="store_true", help="Estado vacío inicial (sin datos) hasta que corra el workflow")
    ap.add_argument("--out", default=str(ROOT / "assets" / "activity.svg"))
    ap.add_argument("--preview", default=None)
    a = ap.parse_args()
    if a.demo or a.placeholder:
        user = demo_data()
        if a.placeholder:
            for w in user["contributionsCollection"]["contributionCalendar"]["weeks"]:
                for x in w["contributionDays"]:
                    x["contributionCount"] = 0
            user["repositories"]["nodes"] = []
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("Falta GITHUB_TOKEN")
        user = fetch(os.environ.get("GH_USER", "AFelipeRD"), token)
    save(a.out, render(user, a.demo, a.placeholder), a.preview)
    print("OK", a.out)
