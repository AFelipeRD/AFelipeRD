#!/usr/bin/env python3
"""
build_activity.py -- Genera con datos REALES de GitHub (API GraphQL):
    assets/activity.svg            actividad compacta: métricas, mapa de calor y lenguajes
    assets/repo_<nombre>.svg       una tarjeta animada por repositorio (lista REPOS)

Mismo sistema de diseño que el resto del perfil. Solo usa la librería estándar de Python.

Variables de entorno:   GITHUB_TOKEN (en Actions: secrets.GITHUB_TOKEN)   GH_USER (por defecto AFelipeRD)
Modos:
    python scripts/build_activity.py                 # datos reales
    python scripts/build_activity.py --placeholder   # estado vacío honesto (sin datos inventados)
    python scripts/build_activity.py --demo --out X  # SOLO para probar el diseño (datos sintéticos, marcados DEMO)
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import random
import sys
import textwrap
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from ds import ROOT, d, doc, iso_cube, save  # noqa: E402

# Repos que se muestran como tarjetas (el orden es el del README). Edita esta lista si cambias tus repos.
REPOS = ["proyecto-fuga-skandia", "DiFarmaPython-Django", "SecureCodeGit",
         "ComandosGit", "IntroGitHub", "Intro-Github"]

USER_Q = """
query($login:String!){ user(login:$login){
  repositories(ownerAffiliations:OWNER,isFork:false,first:100,privacy:PUBLIC){
    totalCount nodes{ stargazerCount languages(first:6,orderBy:{field:SIZE,direction:DESC}){ edges{ size node{ name } } } } }
  contributionsCollection{ totalCommitContributions
    contributionCalendar{ totalContributions weeks{ contributionDays{ contributionCount date } } } } } }
"""


def gql(query, variables, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-activity"})
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if payload.get("errors") and not payload.get("data"):
        sys.exit("GraphQL error: " + json.dumps(payload["errors"]))
    return payload["data"]


def fetch_repos(login, token):
    body = " ".join(
        f'r{i}: repository(owner:$login,name:"{n}"){{ name description stargazerCount forkCount primaryLanguage{{ name }} }}'
        for i, n in enumerate(REPOS))
    data = gql("query($login:String!){ " + body + " }", {"login": login}, token)
    return {n: data.get(f"r{i}") for i, n in enumerate(REPOS)}


# --------------------------------------------------------------------------- datos de prueba / vacío
def demo_data():
    rnd = random.Random(3)
    start = dt.date.today() - dt.timedelta(days=52 * 7 + dt.date.today().weekday() + 1)
    weeks = []
    for w in range(53):
        days = []
        for k in range(7):
            c = 0 if rnd.random() < 0.55 else rnd.choice([1, 1, 2, 3, 5, 8])
            days.append({"contributionCount": c, "date": (start + dt.timedelta(days=w * 7 + k)).isoformat()})
        weeks.append({"contributionDays": days})
    langs = {"edges": [{"size": 52, "node": {"name": "Python"}}, {"size": 30, "node": {"name": "SQL"}}, {"size": 18, "node": {"name": "JavaScript"}}]}
    return {"repositories": {"totalCount": 6, "nodes": [{"stargazerCount": 0, "languages": langs}]},
            "contributionsCollection": {"totalCommitContributions": 0,
                                        "contributionCalendar": {"totalContributions": 0, "weeks": weeks}}}


# Semillas del estado vacío: SOLO lo que ya se vio en el perfil (se reemplaza con datos reales en el primer sync)
SEEDS = {
    "proyecto-fuga-skandia": {"description": "Modelo predictivo basado en IA (Random Forest) para anticipar la fuga de clientes en Skandia, integrando datos semiestructurados (JSON) y desplegado como un microservicio local.",
                              "primaryLanguage": {"name": "Python"}, "stargazerCount": 0, "forkCount": 0},
    "DiFarmaPython-Django": {"description": None, "primaryLanguage": {"name": "JavaScript"}, "stargazerCount": 0, "forkCount": 0},
    "SecureCodeGit": {"description": None, "primaryLanguage": {"name": "Python"}, "stargazerCount": 0, "forkCount": 0},
}


# --------------------------------------------------------------------------- utilidades
def dsx(sec, css=""):
    """Atributo style combinado: retardo de animación + estilos propios (evita atributos duplicados)."""
    return f' style="animation-delay:{sec:.2f}s;{css}"'


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


LANG = {"Python": "dat", "SQL": "dat", "JavaScript": "sig", "HTML": "sig", "TypeScript": "dat", "CSS": "bds", "Go": "bds"}


def lang_accent(name):
    return LANG.get(name, "bds")


def streaks(weeks):
    days = [x for w in weeks for x in w["contributionDays"] if x["date"] <= dt.date.today().isoformat()]
    best = cur = 0
    for x in days:
        cur = cur + 1 if x["contributionCount"] > 0 else 0
        best = max(best, cur)
    now = 0
    for x in reversed(days):
        if x["contributionCount"] > 0:
            now += 1
        elif x is days[-1]:
            continue
        else:
            break
    return now, best


# --------------------------------------------------------------------------- activity (compacto)
def render_activity(u, demo, placeholder):
    cc = u["contributionsCollection"]
    cal, repos = cc["contributionCalendar"], u["repositories"]
    weeks = cal["weeks"]
    stars = sum(n["stargazerCount"] for n in repos["nodes"])
    now, best = streaks(weeks)
    langs = {}
    for n in repos["nodes"]:
        for e in (n["languages"] or {}).get("edges", []):
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:4]
    tot = sum(v for _, v in top) or 1
    W, H = 700, 184
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    tag = "DEMO · datos sintéticos" if demo else ("pendiente de la primera sincronización" if placeholder else f"sincronizado {stamp} UTC")
    b = ['<defs><linearGradient id="sh" x1="0" y1="0" x2="1" y2="0"><stop offset="0" style="stop-color:var(--t1)" stop-opacity="0"/>'
         '<stop offset=".5" style="stop-color:var(--t1)" stop-opacity=".16"/><stop offset="1" style="stop-color:var(--t1)" stop-opacity="0"/></linearGradient>'
         '<clipPath id="hm"><rect x="24" y="96" width="480" height="64"/></clipPath></defs>',
         f'<rect class="card" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12"/>',
         f'<g class="in"{d(0)}><rect x="24" y="20" width="6" height="6" rx="1.5" style="fill:var(--sig)"/><text class="lbl" x="38" y="27.5">05 · ACTIVITY.SYNC</text></g>',
         f'<g class="in"{d(0.1)}><text class="small" x="{W - 24}" y="27.5" text-anchor="end" style="fill:var(--{"sig" if demo else "t3"})">{tag}</text></g>']
    vals = ["—"] * 5 if placeholder else [cal["totalContributions"], cc["totalCommitContributions"], repos["totalCount"], stars, f"{now} / {best}"]
    labs = ["CONTRIB. · 12 MESES", "COMMITS", "REPOS PÚBLICOS", "ESTRELLAS", "RACHA ACT. / MÁX."]
    tw = (W - 48 - 4 * 8) / 5
    for i, (lab, val) in enumerate(zip(labs, vals)):
        x = 24 + i * (tw + 8)
        b.append(f'<g class="pop"{d(0.15 + i * 0.07)}><rect class="node" x="{x:.1f}" y="38" width="{tw:.1f}" height="40" rx="8"/>'
                 f'<text class="nl" x="{x + 10:.1f}" y="53" style="font-size:7.5px">{lab}</text>'
                 f'<text class="sans" x="{x + 10:.1f}" y="70" style="font-size:16px;font-weight:700;fill:var(--t1)">{val}</text></g>')
    mx = max([x["contributionCount"] for w in weeks for x in w["contributionDays"]] or [1]) or 1
    cell, gap, x0, y0 = 7, 2, 24, 96
    for ci, w in enumerate(weeks):
        for ri, x in enumerate(w["contributionDays"]):
            c = x["contributionCount"]
            lvl = 0 if c == 0 else min(4, 1 + int(3 * (c - 1) / max(mx - 1, 1)))
            fill = "var(--s2)" if lvl == 0 else "var(--sig)"
            op = "" if lvl == 0 else ' fill-opacity="%s"' % [0, .28, .5, .75, 1][lvl]
            b.append(f'<rect class="pop" x="{x0 + ci * (cell + gap)}" y="{y0 + ri * (cell + gap)}" width="{cell}" height="{cell}" rx="1.8" '
                     f'fill="{fill}"{op}{d(0.3 + ci * 0.012)}><title>{x["date"]}: {c}</title></rect>')
    b.append('<g clip-path="url(#hm)"><rect class="sheen" x="-60" y="96" width="60" height="64" fill="url(#sh)"/></g>')
    lx = 24 + 5 * 9 + 8
    b.append(f'<text class="small" x="24" y="176">menos</text>')
    for i, o in enumerate([0, .28, .5, .75, 1]):
        f = "var(--s2)" if o == 0 else "var(--sig)"
        op = "" if o == 0 else ' fill-opacity="%s"' % o
        b.append(f'<rect x="{58 + i * 11}" y="169" width="8" height="8" rx="2" fill="{f}"{op}/>')
    b.append('<text class="small" x="118" y="176">más</text>')
    # lenguajes
    px = 528
    b.append(f'<g class="in"{d(0.9)}><text class="lbl" x="{px}" y="104">LENGUAJES</text><rect x="{px}" y="112" width="148" height="7" rx="3.5" style="fill:var(--s2)"/></g>')
    cols = ["dat", "sig", "t2", "datd"]
    x = px
    for i, (n, v) in enumerate(top):
        w = 148 * v / tot
        b.append(f'<rect class="bar" x="{x:.1f}" y="112" width="{max(w - 1.5, 2):.1f}" height="7" rx="3"{dsx(1.0 + i * 0.1, f"fill:var(--{cols[i]})")}/>')
        b.append(f'<g class="in"{d(1.3 + i * 0.08)}><circle cx="{px + 4}" cy="{134 + i * 14}" r="3" style="fill:var(--{cols[i]})"/>'
                 f'<text class="tag" x="{px + 13}" y="{137.5 + i * 14}">{esc(n)} {v / tot * 100:.0f}%</text></g>')
        x += w
    if not top:
        b.append(f'<text class="small" x="{px}" y="140">Sin código aún.</text>')
    css = ".sheen{animation:sheen 4.2s cubic-bezier(.45,0,.25,1) infinite}\n@keyframes sheen{from{transform:translateX(0)}to{transform:translateX(560px)}}"
    return doc(W, H, "".join(b), "Actividad en GitHub",
               f"Contribuciones del último año: {cal['totalContributions']}; repos públicos: {repos['totalCount']}; racha actual {now}, mayor {best}.", css)


# --------------------------------------------------------------------------- tarjeta de repo
def repo_card(name, info, i):
    W, H = 224, 128
    info = info or {}
    desc = (info.get("description") or "").strip()
    lang = (info.get("primaryLanguage") or {}).get("name")
    acc = lang_accent(lang) if lang else "bds"
    lines = textwrap.wrap(desc, 33)[:2] if desc else []
    if desc and len(textwrap.wrap(desc, 33)) > 2:
        lines[1] = lines[1][:30].rstrip() + "…"
    shown = name if len(name) <= 21 else name[:20] + "…"
    stars, forks = info.get("stargazerCount", 0), info.get("forkCount", 0)
    b = [f'<defs><clipPath id="c"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="12"/></clipPath>'
         '<linearGradient id="sh" x1="0" y1="0" x2="1" y2="0"><stop offset="0" style="stop-color:var(--t1)" stop-opacity="0"/>'
         '<stop offset=".5" style="stop-color:var(--t1)" stop-opacity=".14"/><stop offset="1" style="stop-color:var(--t1)" stop-opacity="0"/></linearGradient></defs>']
    inner = [f'<rect class="card" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12"/>',
             f'<rect class="orbitb" x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" style="stroke:var(--{acc if acc != "bds" else "dat"})" stroke-width="1.6" '
             f'stroke-linecap="round" pathLength="1000" stroke-dasharray="46 954" stroke-opacity=".9"/>',
             f'<g class="pop"{d(0.1 + i * 0.08)}>{iso_cube(30, 44, 9, acc, h=8, shadow=False, delay=i * 0.4)}</g>',
             f'<text class="sans in" x="52" y="40"{dsx(0.15 + i * 0.08, "font-size:12px;font-weight:650;fill:var(--t1)")}>{esc(shown)}</text>']
    if lines:
        for k, ln in enumerate(lines):
            inner.append(f'<text class="sans in" x="18" y="{68 + k * 14}"{dsx(0.25 + i * 0.08 + k * 0.05, "font-size:10px;fill:var(--t2)")}>{esc(ln)}</text>')
    else:
        inner.append(f'<text class="sans in" x="18" y="68"{dsx(0.25 + i * 0.08, "font-size:10px;fill:var(--t3)")}>Sin descripción todavía.</text>')
    if lang:
        inner.append(f'<g class="in"{d(0.4 + i * 0.08)}><circle class="pulse" cx="22" cy="108" r="3.5" style="fill:var(--{acc if acc != "bds" else "t2"})"/>'
                     f'<text class="tag" x="31" y="111.5">{esc(lang)}</text></g>')
    inner.append(f'<g class="in"{d(0.45 + i * 0.08)}><text class="tag" x="{W - 18}" y="111.5" text-anchor="end">★ {stars}  ·  forks {forks}</text></g>')
    inner.append(f'<g clip-path="url(#c)"><rect class="shine" x="-70" y="0" width="70" height="{H}" fill="url(#sh)" style="animation-delay:{i * 0.7:.1f}s"/></g>')
    b.append(f'<g class="repo-float" style="animation-delay:-{i * 0.6:.1f}s">{"".join(inner)}</g>')
    css = f""".repo-float{{animation:rf 4.4s ease-in-out infinite}}
.orbitb{{animation:ob 7s linear infinite;animation-delay:-{i * 1.1:.1f}s}}
.shine{{transform:skewX(-18deg);animation:shn 5.2s cubic-bezier(.45,0,.25,1) infinite}}
@keyframes rf{{0%,100%{{transform:translateY(1px)}}50%{{transform:translateY(-3px)}}}}
@keyframes ob{{to{{stroke-dashoffset:-1000}}}}
@keyframes shn{{0%{{transform:translateX(0) skewX(-18deg)}}55%,100%{{transform:translateX({W + 90}px) skewX(-18deg)}}}}"""
    return doc(W, H, "".join(b), f"Repositorio {name}", f"Tarjeta del repositorio {name}. {desc}", css)


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--placeholder", action="store_true", help="Estado vacío inicial (sin datos inventados)")
    ap.add_argument("--out", default=str(ROOT / "assets" / "activity.svg"))
    ap.add_argument("--preview", default=None)
    a = ap.parse_args()
    out_dir = pathlib.Path(a.out).parent
    if a.demo or a.placeholder:
        user = demo_data()
        repos = {n: SEEDS.get(n, {}) for n in REPOS}
        if a.placeholder:
            for w in user["contributionsCollection"]["contributionCalendar"]["weeks"]:
                for x in w["contributionDays"]:
                    x["contributionCount"] = 0
            user["repositories"]["nodes"] = []
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("Falta GITHUB_TOKEN")
        login = os.environ.get("GH_USER", "AFelipeRD")
        user = gql(USER_Q, {"login": login}, token)["user"]
        repos = fetch_repos(login, token)
    save(a.out, render_activity(user, a.demo, a.placeholder), a.preview)
    for i, n in enumerate(REPOS):
        save(out_dir / f"repo_{n.lower()}.svg", repo_card(n, repos.get(n), i), a.preview)
    print("OK", a.out, "+", len(REPOS), "tarjetas de repo")


if __name__ == "__main__":
    main()
