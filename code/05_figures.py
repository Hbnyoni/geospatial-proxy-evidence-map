"""Step 5 -- manuscript figures in the CHEAQI house style (serif, red / blue / black, white ground,
left and bottom spines only, no titles burned in: captions live in the manuscript).

    python scripts/05_figures.py            -> figs/fig*.png (300 dpi) and .pdf
"""
from __future__ import annotations
import sys, json, pickle, math, textwrap
from pathlib import Path
import numpy as np, pandas as pd, networkx as nx
import matplotlib
import matplotlib.ticker
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Patch, Rectangle
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap, LogNorm, Normalize
import geopandas as gpd
from adjustText import adjust_text

sys.path.insert(0, "/PALS/CHEAQI_Composite_Indicator/scripts")
sys.path.insert(0, str(Path(__file__).parent))
from plot_style import set_house_style, tidy
from cheaqi_palette import RED, BLUE, BLACK, GREY, SEQ, SEQ_B, RED_L, BLUE_L
import gazetteer as G
from importlib import import_module
SC = import_module("02_screen_code")

AMBER = "#f0a202"
CLU = [RED, BLUE, BLACK, AMBER]
V2 = Path(__file__).resolve().parents[1]
FIG, DATA = V2 / "figs", V2 / "data"
A = pickle.load(open(DATA / "analysis.pkl", "rb"))
S = json.loads((DATA / "stats.json").read_text())
inc = A["inc"]
set_house_style(base=15)
plt.rcParams.update({"axes.titlesize": 17, "savefig.dpi": 300, "legend.fontsize": 13.5, "xtick.labelsize": 14, "ytick.labelsize": 14, "axes.labelsize": 15.5})
NE = gpd.read_file("/PALS/CHEAQI_Composite_Indicator/output/manuscript_combined/data/naturalearth_lowres/naturalearth_lowres.shp")
NE = NE[NE.name != "Antarctica"].to_crs("+proj=robin")
NE_FIX = {"France": "FRA", "Norway": "NOR", "Kosovo": None, "N. Cyprus": None, "Somaliland": None}
NE["iso"] = [NE_FIX.get(n, i) if n in NE_FIX else i for n, i in zip(NE.name, NE.iso_a3)]


def letter(ax, s, x=-0.02, y=1.04):
    t = ax.text(x, y, s, transform=ax.transAxes, fontsize=18.2, fontweight="bold", va="bottom", ha="right")
    ax._panel_letter = (s, t)


def save(fig, name):
    """Write the composite figure, and for a multi-panel figure every panel as its own image
    (name_a.png, name_b.png ...), cropped from the same rendering so it can be set at full page width."""
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    for old in FIG.glob(f"{name}_?.png"):
        old.unlink()
    mains = sorted([ax for ax in fig.axes if hasattr(ax, "_panel_letter")], key=lambda a: a.get_position().x0)
    if len(mains) > 1:
        fig.canvas.draw()
        r = fig.canvas.get_renderer()
        inv = fig.dpi_scale_trans.inverted()
        others = [a for a in fig.axes if a not in mains and not any(a in m.child_axes for m in mains)]
        for _, t in (m._panel_letter for m in mains):
            t.set_visible(False)
        groups = []
        for i, ax in enumerate(mains):
            x_lo = ax.get_position().x0 if i else 0
            x_hi = mains[i + 1].get_position().x0 if i + 1 < len(mains) else 1.01
            mine = [ax] + [o for o in others if x_lo <= (o.get_position().x0 + o.get_position().x1) / 2 < x_hi]
            groups.append(mine)
        from matplotlib.transforms import Bbox
        for ax, mine in zip(mains, groups):
            hidden = [a for a in fig.axes if a not in mine and not any(a in m.child_axes for m in mine)]
            for a in hidden:
                a.set_visible(False)
            fig.canvas.draw()
            bb = Bbox.union([a.get_tightbbox(r) for a in mine]).transformed(inv).padded(.12)
            fig.savefig(FIG / f"{name}_{ax._panel_letter[0]}.png", bbox_inches=bb)
            for a in hidden:
                a.set_visible(True)
        for _, t in (m._panel_letter for m in mains):
            t.set_visible(True)
    plt.close(fig)
    print("wrote", name, f"(+{len(mains)} panels)" if len(mains) > 1 else "")


# =============================================================== Figure 1  identification and screening flow
def fig_flow():
    F = S["flow"]
    W, H = 1800, 1680
    fig = plt.figure(figsize=(W / 150, H / 150))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")

    def box(x, y, w, h, text, ec=BLACK, bold=False, fc="white", fs=15):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=14", lw=2, ec=ec, fc=fc))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal", linespacing=1.45)

    def arrow(x0, y0, x1, y1, c=BLACK):
        ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", color=c, lw=1.8, mutation_scale=16, shrinkA=0, shrinkB=0))

    def side(x, y, text, c=BLACK):
        ax.plot([x, x + 45], [y, y], color=c, lw=1.6)
        ax.text(x + 58, y, text, ha="left", va="center", fontsize=14.0, linespacing=1.4)

    cw, gap, m = 520, 260, 150
    xs = [m, m + cw + gap]
    hdr = [("Primary search", BLACK), ("Sensitivity search", BLUE)]
    for (t, c), x in zip(hdr, xs):
        ax.text(x + cw / 2, 60, t, ha="center", va="center", fontsize=18.9, fontweight="bold", color=c)
    ax.text(W - 40, 60, "Identification", ha="right", va="center", fontsize=14.3, style="italic", color=GREY)
    ax.text(W - 40, 640, "Screening", ha="right", va="center", fontsize=14.3, style="italic", color=GREY)
    ax.text(W - 40, 1300, "Included", ha="right", va="center", fontsize=14.3, style="italic", color=GREY)
    # row 1
    box(xs[0], 100, cw, 120, f"Scopus  n = {F['scopus_primary']:,}\nWeb of Science  n = {F['wos_primary']:,}", ec=BLACK)
    box(xs[1], 100, cw, 120, f"Scopus  n = {F['scopus_sens']:,}\nWeb of Science  n = {F['wos_sens']:,}", ec=BLUE)
    # row 2
    box(xs[0], 380, cw, 110, f"Unique records\nn = {F['primary_unique']:,}", ec=BLACK)
    box(xs[1], 380, cw, 110, f"Unique records not in the primary set\nn = {F['sens_unique']:,}", ec=BLUE)
    arrow(xs[0] + cw / 2, 220, xs[0] + cw / 2, 380)
    side(xs[0] + cw / 2, 300, f"Duplicates removed: {F['primary_dup_doi'] + F['primary_dup_title'] + F['primary_dup_fuzzy']:,}\n(DOI {F['primary_dup_doi']}, title {F['primary_dup_title']}, fuzzy {F['primary_dup_fuzzy']})")
    arrow(xs[1] + cw / 2, 220, xs[1] + cw / 2, 380, BLUE)
    side(xs[1] + cw / 2, 300, f"Not article or review: {F['sens_doctype_excluded']}\nDuplicates: {F['sens_dup_within']}\nAlready in primary set: {F['sens_overlap_primary']}", BLUE)
    # row 3 screening
    ex = lambda c: sum(F.get(f"screen_{c}_{k}", 0) for k in ("R1", "R2", "R3", "R4", "R5", "R6", "RH"))
    box(xs[0], 800, cw, 110, f"Included after screening\nn = {F['included_primary']:,}", ec=BLACK)
    box(xs[1], 800, cw, 110, f"Included after screening\nn = {F['included_sens']:,}  (yield {F['sens_yield'] * 100:.0f}%)", ec=BLUE)
    for i, c in enumerate(("primary", "sensitivity")):
        col = BLACK if i == 0 else BLUE
        arrow(xs[i] + cw / 2, 490, xs[i] + cw / 2, 800, col)
        lines = [f"Excluded: {ex(c):,}"] + [f"  {k}  {F.get(f'screen_{c}_{k}', 0)}" for k in ("R1", "R2", "R3", "R4", "R5", "R6", "RH") if F.get(f"screen_{c}_{k}", 0)]
        side(xs[i] + cw / 2, 645, "\n".join(lines), col)
    # merge bar
    y = 1030
    box(m, y, xs[1] + cw - m, 110, f"Analytical corpus  n = {F['included_total']:,}  ({F['included_primary']} primary + {F['included_sens']} sensitivity)", bold=True, fs=17)
    for i in range(2):
        arrow(xs[i] + cw / 2, 910, xs[i] + cw / 2, y, BLACK if i == 0 else BLUE)
    # outputs
    y2 = 1240
    bw = (xs[1] + cw - m - 2 * 60) / 3
    outs = [f"Bibliometric mapping\nall {F['included_total']} records",
            f"Validation sub-corpus\nn = {F['validation_subcorpus']}",
            f"Proxy coding\nfamilies, named proxies,\npollutants, methods, settings"]
    for j, t in enumerate(outs):
        x = m + j * (bw + 60)
        box(x, y2, bw, 130, t, ec=RED if j == 1 else BLACK)
        arrow(x + bw / 2, y + 110, x + bw / 2, y2, RED if j == 1 else BLACK)
    au = S["audit"]
    ax.text(m, 1470, "Exclusion codes: R1 not about air-pollution assessment; R2 'proxy' in an unrelated sense; R3 no geospatial proxy;\n"
                     "R4 biological or material proxy; R5 indoor or occupational only; R6 inventory, chemistry or model-process study;\n"
                     f"RH excluded on human review.  Blinded audit of 120 records: precision {au['precision']:.2f}, negative predictive value {au['npv']:.2f}.",
            ha="left", va="top", fontsize=13.3, color="#333333", linespacing=1.5)
    save(fig, "Fig01_search_flow")


# =============================================================== Figure 2  growth and methodological transition
# =============================================================== Figure 3  sources, Bradford and countries

# =============================================================== production and sources (Q1)
def fig_performance():
    yr = A["yr"].copy(); b = A["brad"]
    fig = plt.figure(figsize=(21, 7.4))
    gs0 = fig.add_gridspec(1, 4, width_ratios=[1.45, .8, .5, 1.05], wspace=.3)
    ax = fig.add_subplot(gs0[0])
    x = yr.index.values; p = yr.get("primary", 0); s_ = yr.get("sensitivity", 0); part = x == 2026
    ax.bar(x[~part], p[~part], color=BLACK, width=.8, label="Primary search")
    ax.bar(x[~part], s_[~part], bottom=p[~part], color=BLUE, width=.8, label="Sensitivity search only")
    ax.bar(x[part], (p + s_)[part], color="white", ec=GREY, hatch="///", width=.8, lw=.8, label="2026 (to 1 April)")
    ma = pd.Series(yr.total.values, index=x).loc[:2025].rolling(3, center=True).mean()
    ax.plot(ma.index, ma.values, color=RED, lw=2.8, label="3-year moving mean")
    ax.set_xlabel("Publication year"); ax.set_ylabel("Studies"); ax.set_xlim(1987, 2027)
    sg = S["production"]["segments"]
    ax.text(.03, .97, f"n = {S['production']['n']}\n2000–2009: +{sg['2000_2009']['rate'] * 100:.0f}% a year\n2010–2025: plateau, ~{sg['2010_2025']['mean']:.0f} a year",
            transform=ax.transAxes, va="top", fontsize=15, linespacing=1.45)
    ax.legend(loc="upper left", bbox_to_anchor=(0.0, .72), fontsize=13.5)
    tidy(ax); letter(ax, "a")
    ax = fig.add_subplot(gs0[1])
    ax.plot(b["rank"], b["cum"], color=BLACK, lw=2.6)
    z1, z2 = b[b.zone == 1]["rank"].max(), b[b.zone == 2]["rank"].max()
    ax.axvspan(0.8, z1 + .5, color=RED, alpha=.12, lw=0); ax.axvspan(z1 + .5, z2 + .5, color=BLUE, alpha=.08, lw=0)
    ax.set_xscale("log"); ax.set_xlabel("Source rank (log)"); ax.set_ylabel("Cumulative studies")
    ax.text(.97, .04, f"core: {z1} sources,\n{S['sources']['core_share'] * 100:.0f}% of studies\nzone 2: {z2 - z1} sources\nzone 3: {len(b) - z2} sources",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=13.5, linespacing=1.4)
    ax.set_ylim(0, b.cum.max() * 1.05)
    tidy(ax); letter(ax, "b")
    ax = fig.add_subplot(gs0[3])
    top = b.head(12).iloc[::-1]; yy = np.arange(len(top))
    ax.hlines(yy, 0, top.n, color="#bdbdbd", lw=1.6)
    ax.scatter(top.n, yy, s=95, color=[RED if z == 1 else BLUE for z in top.zone], zorder=3)
    ax.set_yticks(yy, [textwrap.shorten(s, 40, placeholder="…") for s in top.source], fontsize=13.5)
    for y_, n in zip(yy, top.n):
        ax.text(n + 1.8, y_, str(n), va="center", fontsize=13)
    ax.set_xlabel("Studies"); ax.set_xlim(0, top.n.max() * 1.18)
    ax.legend(handles=[Line2D([], [], marker="o", ls="", ms=10, color=RED, label="Bradford core"), Line2D([], [], marker="o", ls="", ms=10, color=BLUE, label="Zone 2")],
              loc="lower right", fontsize=13.5)
    tidy(ax); letter(ax, "c", x=-0.9)
    save(fig, "Fig02_production_sources")


# =============================================================== conceptual evolution (Q2): thematic map + bursts
def fig_themes():
    th = A["themes"].copy()
    b = A["bursts"].head(18).sort_values(["begin", "strength"], ascending=[True, False]).reset_index(drop=True)
    fig = plt.figure(figsize=(21, 9.5))
    gs = fig.add_gridspec(1, 2, width_ratios=[1, 1.15], wspace=.42)
    ax = fig.add_subplot(gs[0])
    cx, cy = th.centrality.median(), th.density.median()
    qc = {"Motor": RED, "Basic": BLUE, "Niche": BLACK, "Emerging or declining": AMBER}
    ax.axvline(cx, color="#9a9a9a", lw=1.2, ls="--"); ax.axhline(cy, color="#9a9a9a", lw=1.2, ls="--")
    ax.scatter(th.centrality, th.density, s=th.occurrences * 4, c=[qc[q] for q in th.quadrant], alpha=.5, edgecolors=[qc[q] for q in th.quadrant], lw=1.8, zorder=3)
    dx, dy = np.ptp(th.centrality), np.ptp(th.density)
    ax.set_xlim(th.centrality.min() - .25 * dx, th.centrality.max() + .25 * dx)
    ax.set_ylim(th.density.min() - .25 * dy, th.density.max() + .25 * dy)
    texts = [ax.text(r.centrality, r.density, "\n".join(textwrap.wrap(r.label, 22)), fontsize=13.5, ha="center", va="center", zorder=5,
                     bbox=dict(boxstyle="round,pad=.15", fc="white", ec="none", alpha=.8)) for r in th.itertuples()]
    adjust_text(texts, ax=ax, x=th.centrality.values, y=th.density.values, expand=(1.25, 1.6), force_static=(.6, .9),
                arrowprops=dict(arrowstyle="-", color="#7a7a7a", lw=.7))
    xl, yl = ax.get_xlim(), ax.get_ylim()
    for (x, y, t, ha, va) in [(xl[1], yl[1], "Motor themes", "right", "top"), (xl[0], yl[1], "Niche themes", "left", "top"),
                              (xl[0], yl[0], "Emerging or\ndeclining themes", "left", "bottom"), (xl[1], yl[0], "Basic themes", "right", "bottom")]:
        ax.text(x, y, t, ha=ha, va=va, fontsize=14, style="italic", color=GREY)
    ax.set_xlabel("Centrality (links to other themes)"); ax.set_ylabel("Density (internal cohesion)")
    ax.set_xticks([]); ax.set_yticks([])
    tidy(ax); letter(ax, "a")
    ax = fig.add_subplot(gs[1])
    y0, y1 = 1995, 2025
    for i, r in b.iterrows():
        y = len(b) - 1 - i
        ax.plot([y0, y1 + 1], [y, y], color="#d0d0d0", lw=6, solid_capstyle="butt", zorder=1)
        ax.plot([r.begin, r.end + 1], [y, y], color=RED, lw=6, solid_capstyle="butt", zorder=2)
        ax.text(y1 + 1.8, y, f"{r.strength:.1f}", ha="left", va="center", fontsize=13.5)
    ax.text(y1 + 1.8, len(b) - .3, "Strength", fontsize=13.5, fontweight="bold", va="bottom")
    ax.set_yticks(range(len(b)), b.keyword[::-1].tolist(), fontsize=14)
    ax.set_xlim(y0, y1 + 1); ax.set_ylim(-.8, len(b) - .2)
    ax.set_xticks(range(1995, 2026, 5)); ax.set_xlabel("Publication year (red: burst period)")
    tidy(ax); ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
    letter(ax, "b", x=-0.32)
    save(fig, "Fig05_themes_bursts")


# =============================================================== methods and validation over time (Q3, Q4)
def fig_trends():
    d = A["dyn"]
    per = [p for p in dict.fromkeys(d.period) if p != "before 2000"]
    xx = np.arange(len(per))
    fig, axs = plt.subplots(1, 3, figsize=(21, 6.6), gridspec_kw=dict(wspace=.28))
    def panel(ax, items, ylab, lt):
        for name, c, mk, lab in items:
            q = d[d.indicator == name].set_index("period").reindex(per)
            ax.fill_between(xx, q.lo * 100, q.hi * 100, color=c, alpha=.13, lw=0)
            ax.plot(xx, q.share * 100, color=c, lw=2.8, marker=mk, ms=8, label=lab)
        n = d[d.indicator == items[0][0]].set_index("period").reindex(per).n
        ax.set_xticks(xx, [f"{p}\n(n = {int(v)})" for p, v in zip(per, n)], fontsize=13)
        ax.set_ylabel(ylab); ax.set_ylim(0, None)
        if len(items) > 2:
            ax.legend(loc="upper center", bbox_to_anchor=(.5, -.2), ncol=2, fontsize=13)
        else:
            ax.legend(loc="upper left", fontsize=13)
        tidy(ax); letter(ax, lt)
    panel(axs[0], [("Dynamic proxy family", RED, "o", "Dynamic proxies"), ("Static families only", BLACK, "^", "Static proxies only"),
                   ("Machine learning", BLUE, "s", "Machine learning"), ("Personal exposure target", AMBER, "D", "Personal exposure")],
          "Share of all studies (%)", "a")
    panel(axs[1], [("Reports validation", BLACK, "o", "Reports any validation")], "Share of all studies (%)", "b")
    axs[1].set_ylim(0, 60)
    panel(axs[2], [("Random or k-fold CV only", BLUE, "s", "Random or k-fold CV only"),
                   ("Spatial, external or temporal validation", RED, "o", "Spatial, external or temporal")], "Share of validated studies (%)", "c")
    save(fig, "Fig08_trends")


# =============================================================== Figure 4  geography of study settings vs authorship
def fig_geography():
    geo = A["geo"].set_index("iso3").studies
    fig = plt.figure(figsize=(15, 6.3))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.75, 1], wspace=.3)
    ax = fig.add_subplot(gs[0])
    w = NE.copy(); w["n"] = w.iso.map(geo)
    w.plot(ax=ax, color="#f1f1f1", edgecolor="#bdbdbd", lw=.35)
    vmax = geo.max()
    w[w.n.notna()].plot(ax=ax, column="n", cmap=SEQ, norm=LogNorm(1, vmax), edgecolor="#8a8a8a", lw=.35)
    ssa = w[w.iso.map(G.REGION) == "SSA"]
    gpd.GeoSeries([ssa.geometry.buffer(0).union_all()], crs=ssa.crs).boundary.plot(ax=ax, color=BLUE, lw=1.3)
    ax.set_axis_off()
    sm = plt.cm.ScalarMappable(cmap=SEQ, norm=LogNorm(1, vmax))
    cax = ax.inset_axes([.5, -.05, .38, .035])
    cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
    cb.set_ticks([1, 3, 10, 30, 100]); cb.set_ticklabels(["1", "3", "10", "30", "100"]); cb.ax.tick_params(labelsize=13.0)
    cb.set_label("Studies set in the country (log scale)", fontsize=13.7)
    g = S["geography"]
    ax.text(.0, -.02, f"Sub-Saharan Africa (outlined):\n{g['ssa_n']} of {S['production']['n']} studies ({g['ssa_share_all'] * 100:.1f}%)\nin {len(g['ssa_countries'])} countries",
            transform=ax.transAxes, fontsize=14.3, color=BLUE, va="top", linespacing=1.4,
            bbox=dict(boxstyle="round,pad=.3", fc="white", ec="none", alpha=.85))
    letter(ax, "a", x=0.02, y=.98)
    ax = fig.add_subplot(gs[1])
    order = ["North America", "Europe & Central Asia", "East Asia & Pacific", "Middle East & North Africa", "South Asia", "Latin America & Caribbean", "Sub-Saharan Africa"]
    code = {v: k for k, v in G.REGION_NAME.items()}
    # setting: a record counts once for every region it is set in; authorship: corresponding-author region
    reg_set = pd.Series([G.REGION_NAME[r] for L in inc.study_regions for r in L if r in G.REGION_NAME]).value_counts()
    located = int((inc.study_regions.map(len) > 0).sum())
    auth = inc.corr_country.map(G.REGION).map(G.REGION_NAME).value_counts()
    nauth = int(inc.corr_country.notna().sum())
    yy = np.arange(len(order))[::-1]
    a1 = np.array([reg_set.get(o, 0) / located * 100 for o in order]); a2 = np.array([auth.get(o, 0) / nauth * 100 for o in order])
    ax.barh(yy + .2, a1, height=.38, color=RED, label=f"Study setting (n = {located})")
    ax.barh(yy - .2, a2, height=.38, color=BLACK, label=f"Corresponding author (n = {nauth})")
    for y_, v1, v2 in zip(yy, a1, a2):
        ax.text(v1 + .8, y_ + .2, f"{v1:.1f}", va="center", fontsize=12.5, color=RED)
        ax.text(v2 + .8, y_ - .2, f"{v2:.1f}", va="center", fontsize=12.5)
    ax.set_yticks(yy, [o.replace(" & ", " &\n") if len(o) > 20 else o for o in order], fontsize=13.7)
    ax.get_yticklabels()[-1].set_color(BLUE); ax.get_yticklabels()[-1].set_fontweight("bold")
    ax.set_xlabel("Share of records (%)"); ax.set_xlim(0, max(a1.max(), a2.max()) * 1.18)
    ax.legend(loc="lower right", fontsize=13.0)
    tidy(ax); letter(ax, "b", x=-0.05)
    save(fig, "Fig09_geography")


# =============================================================== network helper
def draw_network(ax, g, label_fn, n_labels, size_scale, seed=7, k=None, lab_size=13.7, legend=None, pos=None, node_color=None, edge_grey=False):
    pos = pos or nx.spring_layout(g, weight="assoc", seed=seed, k=k, iterations=300)
    w = np.array([d["assoc"] for *_, d in g.edges(data=True)])
    wmax = np.percentile(w, 98)
    for (a, b, d) in sorted(g.edges(data=True), key=lambda e: e[2]["assoc"]):
        same = g.nodes[a]["cluster"] == g.nodes[b]["cluster"]
        col = "#9a9a9a" if (edge_grey or not same) else CLU[g.nodes[a]["cluster"] % 4]
        al = .06 + .32 * min(d["assoc"] / wmax, 1)
        ax.plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color=col, alpha=al, lw=.4 + 1.6 * min(d["assoc"] / wmax, 1), zorder=1)
    nodes = list(g)
    sz = np.array([g.nodes[n]["n"] for n in nodes])
    cols = [node_color(n) for n in nodes] if node_color else [CLU[g.nodes[n]["cluster"] % 4] for n in nodes]
    ax.scatter([pos[n][0] for n in nodes], [pos[n][1] for n in nodes], s=size_scale * sz, c=cols,
               edgecolors="white", linewidths=1.0, zorder=3, alpha=.95)
    top = sorted(nodes, key=lambda n: -g.nodes[n]["n"])[:n_labels]
    texts = [ax.text(pos[n][0], pos[n][1], label_fn(n), fontsize=lab_size * (1.12 if g.nodes[n]["n"] > np.percentile(sz, 85) else 1), zorder=5,
                     ha="center", va="center", fontweight="bold" if g.nodes[n]["n"] > np.percentile(sz, 85) else "normal",
                     bbox=dict(boxstyle="round,pad=.12", fc="white", ec="none", alpha=.72)) for n in top]
    adjust_text(texts, ax=ax, expand=(1.15, 1.3), arrowprops=dict(arrowstyle="-", color="#7a7a7a", lw=.6))
    ax.set_axis_off()
    draw_network.pos = pos
    if legend:
        ax.legend(handles=[Line2D([], [], marker="o", ls="", ms=10, color=CLU[i], label=l) for i, l in enumerate(legend)], loc="upper left",
                  bbox_to_anchor=(0, -.01), fontsize=13.7, ncol=2)


def cluster_names_kw(g):
    names = []
    for c in range(4):
        mem = sorted([n for n in g if g.nodes[n]["cluster"] == c], key=lambda n: -g.nodes[n]["n"])
        names.append(", ".join(mem[:3]))
    return names


# =============================================================== Figure 5  keyword co-occurrence
KW_NAMES = {0: "Land-use regression and traffic exposure", 1: "Traffic-related health epidemiology",
            2: "Machine learning, sensors and ultrafine particles", 3: "Satellite and spatio-temporal modelling"}


KW_CENTRES = {0: (-2.55, 1.75), 1: (2.55, 1.75), 2: (-2.55, -2.95), 3: (2.55, -2.95)}


def kw_layout(g, seed=3):
    """Concentric group layout: each community is drawn around its own centre, its most-used keyword in the
    middle, the next six on an inner ring and the rest on an outer ring (both ordered by co-occurrence with the
    hub, so related keywords sit side by side). Positions are regular, so labels never pile up."""
    pos, ring = {}, {}
    for c in sorted({g.nodes[n]["cluster"] for n in g}):
        mem = sorted([n for n in g if g.nodes[n]["cluster"] == c], key=lambda n: -g.nodes[n]["n"])
        hub, rest = mem[0], mem[1:]
        cx, cy = KW_CENTRES.get(c, (0, 0))
        pos[hub] = np.array([cx, cy]); ring[hub] = 0
        inner, outer = rest[:6], rest[6:]
        for k, (grp, r) in enumerate(((inner, 1.0), (outer, 1.78))):
            grp = sorted(grp, key=lambda n: -(g[hub][n]["weight"] if g.has_edge(hub, n) else 0))
            # interleave so the strongest links are spread around the ring, not bunched on one side
            grp = grp[::2] + grp[1::2][::-1]
            off = (np.pi / max(len(grp), 1)) * k
            for i, n in enumerate(grp):
                t = 2 * np.pi * i / max(len(grp), 1) + np.pi / 2 + off
                pos[n] = np.array([cx + r * np.cos(t), cy + r * np.sin(t)])
                ring[n] = k + 1
    kw_layout.ring = ring
    return pos


def draw_kw(ax, g, pos, node_color=None, hulls=True, edge_min=2):
    import matplotlib.patheffects as pe
    from shapely.geometry import Point
    sz = np.array([g.nodes[n]["n"] for n in g])
    halo = [pe.withStroke(linewidth=4, foreground="white")]
    if hulls:
        for c, name in KW_NAMES.items():
            cx, cy = KW_CENTRES[c]
            circ = Point(cx, cy).buffer(2.2)
            x, y = circ.exterior.xy
            ax.fill(x, y, color=CLU[c], alpha=.06, lw=0, zorder=0)
            ax.plot(x, y, color=CLU[c], alpha=.4, lw=1.3, zorder=0)
            ax.text(cx, cy + 2.3 if cy > 0 else cy - 2.3, textwrap.fill(name, 30), color=CLU[c] if CLU[c] != BLACK else "#333333", fontsize=19,
                    linespacing=1.1,
                    fontweight="bold", ha="center", va="bottom" if cy > 0 else "top", zorder=6, path_effects=halo)
    E = [(a_, b_, d) for a_, b_, d in g.edges(data=True) if d["weight"] >= edge_min]
    wmax = max(d["weight"] for *_, d in E)
    for a_, b_, d in sorted(E, key=lambda e: e[2]["weight"]):
        same = g.nodes[a_]["cluster"] == g.nodes[b_]["cluster"]
        col = (CLU[g.nodes[a_]["cluster"]] if same else "#8a8a8a") if node_color is None else "#9a9a9a"
        f = d["weight"] / wmax
        al = (.15 + .55 * f) if same else (.06 + .35 * f)
        if same:
            ax.plot([pos[a_][0], pos[b_][0]], [pos[a_][1], pos[b_][1]], color=col, alpha=al, lw=.7 + 5 * f, zorder=1, solid_capstyle="round")
        else:                               # links between communities curve gently through the gap
            (x0, y0), (x1, y1) = pos[a_], pos[b_]
            mx, my = (x0 + x1) / 2, (y0 + y1) / 2
            t = np.linspace(0, 1, 30); cxp, cyp = mx * .55, my * .55
            bx = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cxp + t ** 2 * x1
            by = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cyp + t ** 2 * y1
            ax.plot(bx, by, color=col, alpha=al, lw=.5 + 3.5 * f, zorder=1)
    cols = [node_color(n) for n in g] if node_color else [CLU[g.nodes[n]["cluster"]] for n in g]
    ax.scatter([pos[n][0] for n in g], [pos[n][1] for n in g], s=60 + 14 * sz, c=cols, edgecolors="white", linewidths=1.6, zorder=3)
    big = np.percentile(sz, 80)
    for n, v in zip(g, sz):
        fs = 13 + 8 * np.sqrt(v / sz.max())
        c = np.array(KW_CENTRES[g.nodes[n]["cluster"]])
        d = pos[n] - c
        rad = np.sqrt(60 + 14 * v) / 72 * .11        # node radius in data units (approx.)
        if np.linalg.norm(d) < 1e-6:                 # hub: label under the node
            ax.text(c[0], c[1] - rad - .08, n, fontsize=fs + 2, ha="center", va="top", fontweight="bold", zorder=5, path_effects=halo)
            continue
        u = d / np.linalg.norm(d)
        ang = np.degrees(np.arctan2(u[1], u[0]))
        ha = "left" if u[0] > .25 else ("right" if u[0] < -.25 else "center")
        va = "bottom" if u[1] > .25 else ("top" if u[1] < -.25 else "center")
        tp = pos[n] + u * (rad + .07)
        ax.text(tp[0], tp[1], n, fontsize=fs, ha=ha, va=va, zorder=5, fontweight="bold" if v >= big else "normal", path_effects=halo)
    ax.set_axis_off(); ax.set_aspect("equal")
    ax.set_xlim(-5.9, 5.9); ax.set_ylim(-6.3, 5.0)


def vos_layout(g, seed=3):
    """VOSviewer-like map: distances shrink with association strength (Kamada-Kawai), giving clusters
    that sit side by side with breathing room; communities are nudged apart slightly."""
    h = g.copy()
    for a_, b_, d in h.edges(data=True):
        d["dist"] = 1 / np.log1p(d["assoc"])
    pos = nx.kamada_kawai_layout(h, weight="dist")
    P = np.array([pos[n] for n in g]); P = (P - P.mean(0)) / P.std(0)
    pos = {n: P[i] for i, n in enumerate(g)}
    for c in {g.nodes[n]["cluster"] for n in g}:
        mem = [n for n in g if g.nodes[n]["cluster"] == c]
        m = np.mean([pos[n] for n in mem], axis=0)
        for n in mem:
            pos[n] = pos[n] + .45 * m
    return pos


def _shade(rgb, f):
    rgb = np.array(matplotlib.colors.to_rgb(rgb))
    return tuple(rgb + (1 - rgb) * f) if f > 0 else tuple(rgb * (1 + f))


def draw_vos(ax, g, pos, colour_of, scale=1.0):
    """Shaded bubbles, centred labels sized by frequency, thin curved links in the cluster colour."""
    import matplotlib.patheffects as pe
    from matplotlib.patches import Circle
    sz = np.array([g.nodes[n]["n"] for n in g]); smax = sz.max()
    rad = {n: (.045 + .19 * np.sqrt(g.nodes[n]["n"] / smax)) * scale for n in g}
    # collision relaxation: bubbles keep their neighbourhood but no longer pile on one another
    pos = {n: np.array(v, float) for n, v in pos.items()}
    nodes = list(g)
    for _ in range(300):
        moved = False
        for i, a_ in enumerate(nodes):
            for b_ in nodes[i + 1:]:
                d = pos[b_] - pos[a_]; dist = np.linalg.norm(d) + 1e-9
                need = 1.9 * (rad[a_] + rad[b_]) + .12
                if dist < need:
                    push = (need - dist) / 2 * d / dist
                    pos[a_] -= push; pos[b_] += push; moved = True
        if not moved:
            break
    # the twelve largest keywords carry centred labels: push them apart until the label boxes clear
    big = sorted(g, key=lambda n: -g.nodes[n]["n"])[:12]
    P_ = np.array(list(pos.values())); span = np.ptp(P_[:, 0]) + 1.4
    upt = span / (ax.get_position().width * ax.figure.get_figwidth() * 72)      # data units per point
    def box(n):
        fs = 13.5 + 17 * np.sqrt(g.nodes[n]["n"] / smax)
        return len(n) * fs * .58 * upt / 2 + .03, fs * 1.25 * upt / 2 + .02
    for _ in range(200):
        moved = False
        for i, a_ in enumerate(big):
            for b_ in big[i + 1:]:
                (wa, ha_), (wb, hb_) = box(a_), box(b_)
                d = pos[b_] - pos[a_]
                ox, oy = wa + wb - abs(d[0]), ha_ + hb_ - abs(d[1])
                if ox > 0 and oy > 0:
                    if oy < ox:
                        sgn = 1 if d[1] >= 0 else -1; pos[a_][1] -= sgn * oy / 2; pos[b_][1] += sgn * oy / 2
                    else:
                        sgn = 1 if d[0] >= 0 else -1; pos[a_][0] -= sgn * ox / 2; pos[b_][0] += sgn * ox / 2
                    moved = True
        if not moved:
            break
    draw_vos.pos = pos
    E = [(a_, b_, d) for a_, b_, d in g.edges(data=True) if d["weight"] >= 2]
    wmax = max(d["weight"] for *_, d in E)
    for a_, b_, d in sorted(E, key=lambda e: e[2]["weight"]):
        (x0, y0), (x1, y1) = pos[a_], pos[b_]
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        cx, cy = mx - (y1 - y0) * .18, my + (x1 - x0) * .18
        t = np.linspace(0, 1, 30)
        bx = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1
        by = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1
        f = d["weight"] / wmax
        ax.plot(bx, by, color=colour_of(a_), alpha=.18 + .4 * f, lw=.5 + 3.2 * f, zorder=1)
    # bubbles, small on top of large, each with a soft highlight to give the VOSviewer sphere look
    for n in sorted(g, key=lambda n: -g.nodes[n]["n"]):
        x, y = pos[n]; r = rad[n]; c = colour_of(n)
        ax.add_patch(Circle((x, y), r, color=_shade(c, -.15), alpha=.92, zorder=2, lw=0))
        for k in range(1, 7):
            f = k / 7
            ax.add_patch(Circle((x - r * .25 * f, y + r * .25 * f), r * (1 - .8 * f), color=_shade(c, .1 + .45 * f), alpha=.55, zorder=2, lw=0))
    halo = [pe.withStroke(linewidth=3, foreground="white")]
    # set the limits first so label extents can be measured, then place labels largest first,
    # trying the centre and four offsets; a small label with no free spot is left out, as in VOSviewer
    P = np.array(list(pos.values()))
    ax.set_aspect("equal"); ax.set_xlim(P[:, 0].min() - .7, P[:, 0].max() + .7); ax.set_ylim(P[:, 1].min() - .6, P[:, 1].max() + .6)
    fig_ = ax.figure; fig_.canvas.draw(); r_ = fig_.canvas.get_renderer()
    from matplotlib.transforms import Bbox
    def cbox(m):
        (x0, y0), (x1, y1) = ax.transData.transform([pos[m] - rad[m], pos[m] + rad[m]])
        return Bbox([[x0, y0], [x1, y1]]).expanded(.85, .85)
    nodebox = {m: cbox(m) for m in g}
    placed = []
    order = sorted(g, key=lambda n: -g.nodes[n]["n"])
    must = set(order[:12])                       # the twelve largest are labelled first, centred on their bubble
    for n in order[:12]:
        v = g.nodes[n]["n"]; fs = 13.5 + 17 * np.sqrt(v / smax)
        lab = n[0].upper() + n[1:] if n.islower() else n
        t = ax.text(pos[n][0], pos[n][1], lab, fontsize=fs, ha="center", va="center", color="#1a1a1a", zorder=6, path_effects=halo, fontfamily="DejaVu Sans")
        placed.append(t.get_window_extent(r_).expanded(1.03, 1.08))
    for n in order[12:]:
        v = g.nodes[n]["n"]; fs = 13.5 + 17 * np.sqrt(v / smax)
        lab = n[0].upper() + n[1:] if n.islower() else n
        x, y = pos[n]; rr = rad[n]
        ok = False
        for dx, dy, ha, va in ((0, 0, "center", "center"), (0, rr + .04, "center", "bottom"), (0, -rr - .04, "center", "top"),
                               (rr + .04, 0, "left", "center"), (-rr - .04, 0, "right", "center")):
            t = ax.text(x + dx, y + dy, lab, fontsize=fs, ha=ha, va=va, color="#1a1a1a", zorder=5, path_effects=halo, fontfamily="DejaVu Sans")
            bb = t.get_window_extent(r_).expanded(1.03, 1.08)
            others = [nodebox[m] for m in g if m != n and g.nodes[m]["n"] >= v * .5]
            free = not any(bb.overlaps(o) for o in placed) and not any(bb.overlaps(o) for o in others)
            if free:
                placed.append(bb); ok = True; break
            t.remove()
        if not ok and n in must:                 # a major keyword is always named, centred on its bubble
            ax.text(x, y, lab, fontsize=fs, ha="center", va="center", color="#1a1a1a", zorder=5, path_effects=halo, fontfamily="DejaVu Sans")
        elif not ok:
            g.nodes[n]["unlabelled"] = True
    ax.set_axis_off()


def fig_keywords():
    g = A["KW"]
    pos = vos_layout(g)
    fig, axs = plt.subplots(1, 2, figsize=(32, 15), gridspec_kw=dict(wspace=.02))
    draw_vos(axs[0], g, pos, lambda n: CLU[g.nodes[n]["cluster"]])
    letter(axs[0], "a", x=0.02, y=.99)
    axs[0].legend(handles=[Line2D([], [], marker="o", ls="", ms=16, color=CLU[c], label=KW_NAMES[c]) for c in sorted(KW_NAMES)],
                  loc="upper center", bbox_to_anchor=(.5, -.0), ncol=2, fontsize=16, frameon=False)
    yrs = np.array([g.nodes[n]["mean_year"] for n in g])
    norm = Normalize(np.nanpercentile(yrs, 5), np.nanpercentile(yrs, 95))
    cm = plt.get_cmap("cheaqi_div")
    draw_vos(axs[1], g, draw_vos.pos, lambda n: cm(norm(g.nodes[n]["mean_year"])))
    letter(axs[1], "b", x=0.02, y=.99)
    cax = axs[1].inset_axes([.3, -.05, .4, .022])
    cb = fig.colorbar(plt.cm.ScalarMappable(cmap=cm, norm=norm), cax=cax, orientation="horizontal")
    cb.set_label("Average publication year of the keyword", fontsize=16); cb.ax.tick_params(labelsize=15)
    cb.ax.xaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%d"))
    save(fig, "Fig04_keyword_network")


# =============================================================== Figure 6  thematic map and trend topics
# =============================================================== Figure 7  co-citation
def fig_cocitation():
    g = A["CC"]
    labs = {n: g.nodes[n]["label"] for n in g}
    names = []
    for c in range(4):
        mem = sorted([n for n in g if g.nodes[n]["cluster"] == c], key=lambda n: -g.nodes[n]["n"])
        if mem:
            names.append(f"{c + 1}  " + ", ".join(labs[m] for m in mem[:2]) + f"  ({len(mem)} references)")
    fig, ax = plt.subplots(figsize=(13, 10))
    draw_network(ax, g, lambda n: labs[n], n_labels=34, size_scale=2.4, seed=11, k=.6, lab_size=12.7, legend=names)
    save(fig, "Fig06_cocitation")


SHORT = {"Land use and built environment": "Land use", "Road and traffic": "Road", "Meteorology": "Meteorology", "Population and settlement": "Population",
         "Satellite atmospheric": "Satellite", "Topography": "Topography", "Hybrid and composite": "Hybrid", "Industrial and point sources": "Industrial",
         "Vegetation and land surface": "Vegetation", "Fire and smoke": "Fire"}


# =============================================================== Figure 8  proxy families
def fig_families():
    fam = A["famdf"].copy()
    fp = A["fp"].copy()
    co = A["co"].copy()
    order = fam.index.tolist()
    fig = plt.figure(figsize=(16, 6.6))
    gs = fig.add_gridspec(1, 3, width_ratios=[.85, 1.2, 1.0], wspace=.5)
    ax = fig.add_subplot(gs[0])
    yy = np.arange(len(order))[::-1]
    ax.barh(yy, fam.records, color="#d9d9d9", height=.7, label="All records")
    ax.barh(yy, fam.validation_records, color=RED, height=.7, label="Validation sub-corpus")
    for y_, n, s in zip(yy, fam.records, fam.share):
        ax.text(n + 4, y_, f"{n}  ({s * 100:.0f}%)", va="center", fontsize=12.7)
    ax.set_yticks(yy, order, fontsize=13.7); ax.set_xlabel("Records"); ax.set_xlim(0, fam.records.max() * 1.32)
    ax.legend(loc="center right", fontsize=13.0)
    tidy(ax); letter(ax, "a", x=-0.7)
    ax = fig.add_subplot(gs[1])
    cols = ["PM2.5", "PM10", "NO2/NOx", "BC/EC", "UFP", "O3", "SO2", "CO", "VOC/PAH"]
    m = fp.loc[order, cols]
    share = m.div(fam.records.reindex(order), axis=0) * 100
    im = ax.imshow(share.values, cmap=SEQ, aspect="auto", vmin=0, vmax=60)
    for i in range(share.shape[0]):
        for j in range(share.shape[1]):
            v = share.values[i, j]
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=12.2, color="white" if v > 33 else BLACK)
    ax.set_xticks(range(len(cols)), [c.replace("NO2/NOx", "NO$_2$/NO$_x$").replace("PM2.5", "PM$_{2.5}$").replace("PM10", "PM$_{10}$").replace("O3", "O$_3$").replace("SO2", "SO$_2$") for c in cols], rotation=45, ha="right", fontsize=13.0)
    ax.set_yticks(range(len(order)), [SHORT[o] for o in order], fontsize=13.0)
    for s_ in ax.spines.values(): s_.set_visible(False)
    ax.tick_params(length=0)
    cb = fig.colorbar(im, ax=ax, fraction=.04, pad=.02); cb.set_label("% of the family's records naming the pollutant", fontsize=13.0); cb.ax.tick_params(labelsize=12.3)
    letter(ax, "b", x=-0.12)
    ax = fig.add_subplot(gs[2])
    n = fam.records.reindex(order).values
    jac = co.loc[order, order].values / (n[:, None] + n[None, :] - co.loc[order, order].values)
    np.fill_diagonal(jac, np.nan)
    mask = np.triu(np.ones_like(jac, dtype=bool), 0)
    jm = np.where(mask, np.nan, jac)
    im = ax.imshow(jm, cmap=SEQ_B.reversed(), vmin=0, vmax=.4, aspect="auto")
    for i in range(len(order)):
        for j in range(i):
            v = jac[i, j]
            ax.text(j, i, f"{v:.2f}".lstrip("0"), ha="center", va="center", fontsize=11.4, color="white" if v > .22 else BLACK)
    short = SHORT
    _unused = {"Land use and built environment": "Land use", "Road and traffic": "Road", "Meteorology": "Meteorology", "Population and settlement": "Population",
             "Satellite atmospheric": "Satellite", "Topography": "Topography", "Hybrid and composite": "Hybrid", "Industrial and point sources": "Industrial",
             "Vegetation and land surface": "Vegetation", "Fire and smoke": "Fire"}
    ax.set_xticks(range(len(order)), [short[o] for o in order], rotation=55, ha="right", fontsize=13.0)
    ax.set_yticks(range(len(order)), [short[o] for o in order], fontsize=13.0)
    for s_ in ax.spines.values(): s_.set_visible(False)
    ax.tick_params(length=0)
    cb = fig.colorbar(im, ax=ax, fraction=.045, pad=.02); cb.set_label("Co-use (Jaccard index)", fontsize=13.0); cb.ax.tick_params(labelsize=12.3)
    letter(ax, "c", x=-0.15)
    save(fig, "Fig07_proxy_families")


# =============================================================== Figure 9  validation design and exposure target
# =============================================================== Figure 10  proxy prioritisation
def fig_ranking():
    r = A["rank"].copy()
    fig = plt.figure(figsize=(21, 10.5))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.35, 1], wspace=.55)
    ax = fig.add_subplot(gs[0])
    ax.axvline(.5, color="#9a9a9a", lw=1, ls="--"); ax.axhline(.5, color="#9a9a9a", lw=1, ls="--")
    col = [RED if d else BLACK for d in r.dynamic]
    fc = ["white" if a else c for a, c in zip(r["aggregate"], col)]
    ax.scatter(r.prominence, r.validation_score, s=18 + r.records * 1.1, facecolors=fc, edgecolors=col, lw=1.5, alpha=.85, zorder=3)
    # label the top fifteen and the proxies that matter for African settings; the rest are in Table S3
    AFR = {"Household fuel use", "Biomass and open burning", "Fire activity and burned area", "Land surface temperature", "Night-time lights",
           "Settlement and socio-economic status", "Boundary-layer height"}
    lab = r[(r.index < 6) | r.proxy.isin(AFR)]      # the full ordering is in panel b
    texts = [ax.text(row.prominence, row.validation_score, row.proxy, fontsize=12.5, zorder=5, color=RED if row.dynamic else BLACK,
                     fontweight="bold" if row.proxy in AFR else "normal",
                     bbox=dict(boxstyle="round,pad=.08", fc="white", ec="none", alpha=.8)) for row in lab.itertuples()]
    adjust_text(texts, ax=ax, x=r.prominence.values, y=r.validation_score.values, expand=(1.35, 1.9), force_text=(.7, 1.1), force_static=(.45, .8),
                arrowprops=dict(arrowstyle="-", color="#8a8a8a", lw=.5))
    ax.set_xlabel("Bibliometric prominence (frequency and co-use centrality, percentile)")
    ax.set_ylabel("Validation evidence (validated and spatially or externally\nvalidated records, percentile)")
    ax.set_xlim(-.08, 1.12); ax.set_ylim(-.05, 1.09)
    ax.text(.0, 1.05, f"Spearman ρ = {S['ranking']['rho_prominence_validation']:.2f}", ha="left", va="top", fontsize=15.0)
    ax.legend(handles=[Line2D([], [], marker="o", ls="", ms=10, color=BLACK, label="static proxy"),
                       Line2D([], [], marker="o", ls="", ms=10, color=RED, label="dynamic proxy"),
                       Line2D([], [], marker="o", ls="", ms=10, mfc="white", mec=BLACK, label="aggregate category")], loc="lower right", fontsize=13.3,
              title="bold label: relevant to African sources", title_fontsize=12.3)
    tidy(ax); letter(ax, "a")
    ax = fig.add_subplot(gs[1])
    t = r[~r["aggregate"]].head(20).iloc[::-1]
    yy = np.arange(len(t))
    ax.barh(yy, t.priority, color=[RED if d else BLACK for d in t.dynamic], height=.68)
    for y_, p, rec, v, s in zip(yy, t.priority, t.records, t.validation_records, t.ssa_records):
        ax.text(p + .01, y_, f"{rec} / {v} / {s}", va="center", fontsize=12.2)
    ax.set_yticks(yy, t.proxy, fontsize=13.3)
    ax.set_xlabel("Priority score (mean of the two percentiles)"); ax.set_xlim(0, 1.22)
    ax.text(1.0, len(t) + .2, "records / validated / SSA", ha="right", fontsize=12.5, color=GREY)
    tidy(ax); letter(ax, "b", x=-0.62)
    save(fig, "Fig11_proxy_priority")


# =============================================================== keyword bursts (CiteSpace-style timeline)
# =============================================================== country collaboration map
def fig_collaboration():
    coll = A["coll"]
    is_ssa = lambda r: G.REGION.get(r.a) == "SSA" or G.REGION.get(r.b) == "SSA"
    coll = coll[(coll.w >= 2) | coll.apply(is_ssa, axis=1)]          # every African link is drawn
    cc = pd.Series(dict(A["CN"].nodes(data="n")))
    w = NE.copy()
    w["pt"] = w.geometry.representative_point()
    xy = {i: (p.x, p.y) for i, p in zip(w.iso, w.pt) if i}
    # small states missing from the low-resolution layer
    fig, ax = plt.subplots(figsize=(15, 7.6))
    w.plot(ax=ax, color="#f1f1f1", edgecolor="#c4c4c4", lw=.35)
    w[w.iso.map(G.REGION) == "SSA"].plot(ax=ax, color="#dbe8f7", edgecolor="#c4c4c4", lw=.35)
    wmax = coll.w.max()
    for r in coll.sort_values("w").itertuples():
        if r.a not in xy or r.b not in xy:
            continue
        (x0, y0), (x1, y1) = xy[r.a], xy[r.b]
        ssa = G.REGION.get(r.a) == "SSA" or G.REGION.get(r.b) == "SSA"
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        dx, dy = x1 - x0, y1 - y0
        cx, cy = mx - dy * .18, my + dx * .18
        t = np.linspace(0, 1, 40)
        bx = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t ** 2 * x1
        by = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t ** 2 * y1
        ax.plot(bx, by, color=RED if ssa else BLUE, alpha=(.55 if ssa else .12 + .5 * r.w / wmax), lw=(.9 + 1.5 * r.w / wmax) if ssa else (.5 + 4 * r.w / wmax), zorder=3 if ssa else 2)
    nodes = [(c, n) for c, n in cc.items() if c in xy and n]
    ax.scatter([xy[c][0] for c, _ in nodes], [xy[c][1] for c, _ in nodes], s=[8 + n * 1.6 for _, n in nodes],
               color=[RED if G.REGION.get(c) == "SSA" else BLACK for c, _ in nodes], edgecolors="white", lw=.8, zorder=4)
    lab = sorted(nodes, key=lambda t: -t[1])[:12] + [(c, n) for c, n in nodes if G.REGION.get(c) == "SSA"]
    texts = [ax.text(xy[c][0], xy[c][1], G.NAME.get(c, c), ha="center", fontsize=12.3, zorder=5,
                     color=RED if G.REGION.get(c) == "SSA" else BLACK,
                     bbox=dict(boxstyle="round,pad=.1", fc="white", ec="none", alpha=.75)) for c, n in lab]
    adjust_text(texts, ax=ax, x=[xy[c][0] for c, _ in nodes], y=[xy[c][1] for c, _ in nodes], expand=(1.2, 1.5),
                arrowprops=dict(arrowstyle="-", color="#7a7a7a", lw=.5))
    ax.set_axis_off()
    col = S["collaboration"]
    ax.legend(handles=[Line2D([], [], color=BLUE, lw=2.5, alpha=.6, label="co-authorship link (≥ 2 papers)"),
                       Line2D([], [], color=RED, lw=2.5, label=f"link involving Sub-Saharan Africa (all {col['ssa_links']} drawn)"),
                       Line2D([], [], marker="o", ls="", color=BLACK, label="country (area = papers)")],
              loc="lower left", fontsize=13.7)
    save(fig, "Fig03_collaboration")


# =============================================================== three-field plot
def fig_threefield():
    f = A["flows"].copy()
    cols = ["region", "family", "validation"]
    order = {
        "region": ["North America", "Europe & Central Asia", "East Asia & Pacific", "Other low- and middle-income regions", "Global, multi-region or not stated", "Sub-Saharan Africa"],
        "family": ["Land use and built environment", "Road and traffic", "Meteorology", "Population and settlement", "Satellite atmospheric", "Topography", "Other families"],
        "validation": ["Spatial, external or temporal hold-out", "Random or k-fold cross-validation", "Validation, design not stated", "No validation reported"]}
    colour = {"region": lambda k: BLUE if k == "Sub-Saharan Africa" else BLACK,
              "family": lambda k: RED if k in ("Meteorology", "Satellite atmospheric") else BLACK,
              "validation": lambda k: RED if k.startswith("Spatial") else (BLUE if k.startswith("Random") else "#8a8a8a")}
    tot = f.w.sum(); gap = .012; H = 1.0
    X = {"region": 0, "family": 1, "validation": 2}; bw = .05
    pos = {}
    for c in cols:
        sz = f.groupby(c).w.sum().reindex(order[c]).fillna(0)
        avail = H - gap * (len(sz) - 1); y = H
        for k, v in sz.items():
            h = v / tot * avail
            pos[(c, k)] = [y - h, y]; y -= h + gap
    fig, ax = plt.subplots(figsize=(16, 9))
    def band(x0, a0, a1, x1, b0, b1, color, alpha):
        t = np.linspace(0, 1, 50); s_ = 3 * t ** 2 - 2 * t ** 3
        xs = x0 + (x1 - x0) * t
        ax.fill_between(xs, a0 + (b0 - a0) * s_, a1 + (b1 - a1) * s_, color=color, alpha=alpha, lw=0)
    for (c1, c2) in (("region", "family"), ("family", "validation")):
        g = f.groupby([c1, c2]).w.sum().reset_index()
        off1 = {k: pos[(c1, k)][1] for k in order[c1]}; off2 = {k: pos[(c2, k)][1] for k in order[c2]}
        g["o1"] = g[c1].map(order[c1].index); g["o2"] = g[c2].map(order[c2].index)
        for r in g.sort_values(["o1", "o2"]).itertuples():
            k1, k2, v = getattr(r, c1), getattr(r, c2), r.w
            avail = H - gap * (len(order[c1]) - 1)
            h = v / tot * avail
            a1 = off1[k1]; a0 = a1 - h; off1[k1] = a0
            b1 = off2[k2]; b0 = b1 - h; off2[k2] = b0
            ssa = k1 == "Sub-Saharan Africa"
            colr = BLUE if ssa else (RED if (c2 == "validation" and k2.startswith("Spatial")) else "#9a9a9a")
            band(X[c1] + bw / 2, a0, a1, X[c2] - bw / 2, b0, b1, colr, .55 if (ssa or colr == RED) else .22)
    for (c, k), (lo, hi) in pos.items():
        ax.add_patch(Rectangle((X[c] - bw / 2, lo), bw, hi - lo, color=colour[c](k), zorder=3))
        n = f[f[c] == k].w.sum()
        txt = f"{k}  ({n:.0f})"
        if c == "region":
            ax.text(X[c] - bw / 2 - .02, (lo + hi) / 2, txt, ha="right", va="center", fontsize=14.3)
        elif c == "validation":
            ax.text(X[c] + bw / 2 + .02, (lo + hi) / 2, txt, ha="left", va="center", fontsize=14.3)
        else:
            ax.text(X[c], (lo + hi) / 2, txt, ha="center", va="center", fontsize=13.7, zorder=5,
                    bbox=dict(boxstyle="round,pad=.15", fc="white", ec="none", alpha=.85))
    for c, t in (("region", "Study setting"), ("family", "Proxy family"), ("validation", "Validation design")):
        ax.text(X[c], H + .03, t, ha="center", fontsize=16.9, fontweight="bold")
    ax.set_xlim(-.85, 2.85); ax.set_ylim(-.02, H + .07); ax.set_axis_off()
    save(fig, "Fig10_three_field")


if __name__ == "__main__":
    which = sys.argv[1:] or ["flow", "performance", "collaboration", "geography", "keywords", "themes", "cocitation", "families",
                             "trends", "threefield", "ranking"]
    for w in which:
        globals()[f"fig_{w}"]()
