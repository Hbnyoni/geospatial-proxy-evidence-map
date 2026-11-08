#!/usr/bin/env python3
"""Re-author four figures for a 6.30 in portrait column.

  Fig08_trends_print        the three 'change by period' panels merged into one
                            figure (a over b+c) -- this retires Supplementary
                            Figures S6 and S7, which were the same chart again
  Fig07_proxy_families_a_print   Figure 6a, with the legend moved off the bars
  Fig09_geography_a_print        Figure 8, legend and note below the map
  Fig03_collaboration_print      Supplementary Figure S2, legend below the map

Everything is drawn at the width it is placed, so 8 pt stays 8 pt on the page.
"""
from __future__ import annotations
import sys
from pathlib import Path
from importlib import import_module
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import LogNorm
import geopandas as gpd

sys.path.insert(0, str(Path(__file__).parent))
F = import_module("05_figures")
A, S, NE, G, inc = F.A, F.S, F.NE, F.G, F.inc
RED, BLUE, BLACK, GREY, AMBER, SEQ = F.RED, F.BLUE, F.BLACK, F.GREY, F.AMBER, F.SEQ
tidy = F.tidy
FIG = F.FIG
COL = 6.30

F.set_house_style(base=9)
plt.rcParams.update({"savefig.dpi": 600, "savefig.bbox": "standard",
                     "legend.fontsize": 7.6, "xtick.labelsize": 8.0,
                     "ytick.labelsize": 8.0, "axes.labelsize": 9.0})


def save(fig, stem):
    fig.savefig(FIG / f"{stem}.png", bbox_inches=None)
    w, h = fig.get_size_inches()
    print(f"  {stem}.png  {w:.2f} x {h:.2f} in  ratio {w/h:.2f}")


def letter(ax, s, x=-.085, y=1.02):
    ax.text(x, y, s, transform=ax.transAxes, fontsize=10.0, fontweight="bold",
            va="bottom", ha="right")


# ========================== Figure 7: the three period panels, merged ==========
d = A["dyn"]
per = [p for p in dict.fromkeys(d.period) if p != "before 2000"]
xx = np.arange(len(per))

fig = plt.figure(figsize=(COL, 6.05))
gs = fig.add_gridspec(2, 2, height_ratios=[1.12, 1.00], hspace=.52, wspace=.46,
                      left=.115, right=.965, top=.965, bottom=.085)


def panel(ax, items, ylab, lt, legend_below, ncol=2):
    for name, c, mk, lab in items:
        # a misspelt indicator would silently draw an empty line, as it once did
        assert name in set(d.indicator), f"no indicator named {name!r}"
        q = d[d.indicator == name].set_index("period").reindex(per)
        ax.fill_between(xx, q.lo * 100, q.hi * 100, color=c, alpha=.13, lw=0)
        ax.plot(xx, q.share * 100, color=c, lw=1.5, marker=mk, ms=4, label=lab)
    n = d[d.indicator == items[0][0]].set_index("period").reindex(per).n
    ax.set_xticks(xx, [f"{p}\n(n = {int(v)})" for p, v in zip(per, n)], fontsize=7.0)
    ax.set_ylabel(ylab, fontsize=8.6); ax.set_ylim(0, None)
    if legend_below:
        ax.legend(loc="upper center", bbox_to_anchor=(.5, -.20), ncol=ncol,
                  fontsize=7.4, frameon=False, columnspacing=1.4, handletextpad=.5)
    else:
        ax.legend(loc="upper left", fontsize=7.0, frameon=False, handletextpad=.5)
    tidy(ax); letter(ax, lt)


ax = fig.add_subplot(gs[0, :])
panel(ax, [("Dynamic proxy family", RED, "o", "Dynamic proxies"),
           ("Static families only", BLACK, "^", "Static proxies only"),
           ("Machine learning", BLUE, "s", "Machine learning"),
           ("Personal exposure target", AMBER, "D", "Personal exposure")],
      "Share of all studies (%)", "a", True, ncol=4)

ax = fig.add_subplot(gs[1, 0])
panel(ax, [("Reports validation", BLACK, "o", "Reports any validation")],
      "Share of all studies (%)", "b", False)
ax.set_ylim(0, 60)

ax = fig.add_subplot(gs[1, 1])
panel(ax, [("Random or k-fold CV only", BLUE, "s", "Random or k-fold CV only"),
           ("Spatial, external or temporal validation", RED, "o",
            "Spatial, external or temporal")],
      "Share of validated studies (%)", "c", False)
save(fig, "Fig08_trends_print")
plt.close(fig)

# ===================== Figure 6a: records by family, legend clear of the bars ==
fam = A["famdf"].copy()
order = fam.index.tolist()
fig = plt.figure(figsize=(COL, 5.55))
ax = fig.add_subplot(111)
fig.subplots_adjust(left=.335, right=.985, top=.985, bottom=.165)
yy = np.arange(len(order))[::-1]
ax.barh(yy, fam.records, color="#d9d9d9", height=.7, label="All records")
ax.barh(yy, fam.validation_records, color=RED, height=.7, label="Validation sub-corpus")
for y_, n_, s_ in zip(yy, fam.records, fam.share):
    ax.text(n_ + 4, y_, f"{n_}  ({s_ * 100:.0f}%)", va="center", fontsize=7.6)
ax.set_yticks(yy, order, fontsize=8.0)
ax.set_xlabel("Records"); ax.set_xlim(0, fam.records.max() * 1.30)
# below the axis: the one place that cannot collide with a bar or a count label
ax.legend(loc="upper center", bbox_to_anchor=(.5, -.115), ncol=2, fontsize=7.6,
          frameon=False, columnspacing=1.8, handletextpad=.6)
tidy(ax)
save(fig, "Fig07_proxy_families_a_print")
plt.close(fig)

# ======================= Figure 8: study settings, legend below the map ========
# size the canvas to the map's own aspect, or geopandas leaves a band of white
x0, y0, x1, y1 = NE.total_bounds
MAP_ASPECT = (y1 - y0) / (x1 - x0)
BAND = 1.02                                   # inches for the colour bar and note
map_w = COL * .99
fig_h = map_w * MAP_ASPECT + BAND

geo = A["geo"].set_index("iso3").studies
fig = plt.figure(figsize=(COL, fig_h))
ax = fig.add_axes([.005, BAND / fig_h, .99, 1 - BAND / fig_h])
w = NE.copy(); w["n"] = w.iso.map(geo)
w.plot(ax=ax, color="#f1f1f1", edgecolor="#bdbdbd", lw=.25)
vmax = geo.max()
w[w.n.notna()].plot(ax=ax, column="n", cmap=SEQ, norm=LogNorm(1, vmax),
                    edgecolor="#8a8a8a", lw=.25)
ssa = w[w.iso.map(G.REGION) == "SSA"]
gpd.GeoSeries([ssa.geometry.buffer(0).union_all()], crs=ssa.crs).boundary.plot(
    ax=ax, color=BLUE, lw=.9)
ax.set_axis_off()
cax = fig.add_axes([.56, .40 / fig_h, .33, .030 * 4.6 / fig_h])
cb = fig.colorbar(plt.cm.ScalarMappable(cmap=SEQ, norm=LogNorm(1, vmax)),
                  cax=cax, orientation="horizontal")
cb.set_ticks([1, 3, 10, 30, 100]); cb.set_ticklabels(["1", "3", "10", "30", "100"])
cb.ax.tick_params(labelsize=7.4)
cb.set_label("Studies set in the country (log scale)", fontsize=8.0)
g = S["geography"]
fig.text(.045, .50 / fig_h, f"Sub-Saharan Africa (outlined): {g['ssa_n']} of "
                            f"{S['production']['n']} studies "
                            f"({g['ssa_share_all'] * 100:.1f}%) in "
                            f"{len(g['ssa_countries'])} countries",
         fontsize=8.2, color=BLUE, va="center", ha="left")
save(fig, "Fig09_geography_a_print")
plt.close(fig)

# ============ Supplementary Figure S2: collaboration, legend below the map =====
import networkx as nx
coll = A["coll"]
is_ssa = lambda r: G.REGION.get(r.a) == "SSA" or G.REGION.get(r.b) == "SSA"
coll = coll[(coll.w >= 2) | coll.apply(is_ssa, axis=1)]
cc = pd.Series(dict(A["CN"].nodes(data="n")))
w = NE.copy()
w["pt"] = w.geometry.representative_point()
xy = {i: (p.x, p.y) for i, p in zip(w.iso, w.pt) if i}

BAND = .78
fig_h = map_w * MAP_ASPECT + BAND
fig = plt.figure(figsize=(COL, fig_h))
ax = fig.add_axes([.005, BAND / fig_h, .99, 1 - BAND / fig_h])
w.plot(ax=ax, color="#f1f1f1", edgecolor="#c4c4c4", lw=.22)
w[w.iso.map(G.REGION) == "SSA"].plot(ax=ax, color="#dbe8f7", edgecolor="#c4c4c4", lw=.22)
wmax = coll.w.max()
for r in coll.sort_values("w").itertuples():
    if r.a not in xy or r.b not in xy:
        continue
    (xa, ya), (xb, yb) = xy[r.a], xy[r.b]
    ssa_link = G.REGION.get(r.a) == "SSA" or G.REGION.get(r.b) == "SSA"
    mx, my = (xa + xb) / 2, (ya + yb) / 2
    dx, dy = xb - xa, yb - ya
    cx, cy = mx - dy * .18, my + dx * .18
    t = np.linspace(0, 1, 40)
    bx = (1 - t) ** 2 * xa + 2 * (1 - t) * t * cx + t ** 2 * xb
    by = (1 - t) ** 2 * ya + 2 * (1 - t) * t * cy + t ** 2 * yb
    ax.plot(bx, by, color=RED if ssa_link else BLUE,
            alpha=(.55 if ssa_link else .12 + .5 * r.w / wmax),
            lw=(.5 + .8 * r.w / wmax) if ssa_link else (.3 + 2.2 * r.w / wmax),
            zorder=3 if ssa_link else 2)
nodes = [(c, n) for c, n in cc.items() if c in xy and n]
ax.scatter([xy[c][0] for c, _ in nodes], [xy[c][1] for c, _ in nodes],
           s=[2 + n * .45 for _, n in nodes],
           color=[RED if G.REGION.get(c) == "SSA" else BLACK for c, _ in nodes],
           edgecolors="white", lw=.4, zorder=4)
lab = sorted(nodes, key=lambda t: -t[1])[:12] + \
      [(c, n) for c, n in nodes if G.REGION.get(c) == "SSA"]
texts = [ax.text(xy[c][0], xy[c][1], G.NAME.get(c, c), ha="center", fontsize=7.0,
                 zorder=5, color=RED if G.REGION.get(c) == "SSA" else BLACK,
                 bbox=dict(boxstyle="round,pad=.08", fc="white", ec="none", alpha=.75))
         for c, n in lab]
F.adjust_text(texts, ax=ax, x=[xy[c][0] for c, _ in nodes],
              y=[xy[c][1] for c, _ in nodes], expand=(1.2, 1.5),
              arrowprops=dict(arrowstyle="-", color="#7a7a7a", lw=.4))
ax.set_axis_off()
col = S["collaboration"]
fig.legend(handles=[Line2D([], [], color=BLUE, lw=1.6, alpha=.6,
                           label="co-authorship link (\u2265 2 papers)"),
                    Line2D([], [], color=RED, lw=1.6,
                           label=f"link involving Sub-Saharan Africa "
                                 f"(all {col['ssa_links']} drawn)"),
                    Line2D([], [], marker="o", ls="", ms=3.4, color=BLACK,
                           label="country (area = papers)")],
           loc="lower center", bbox_to_anchor=(.5, .02), ncol=3, fontsize=7.2,
           frameon=False, columnspacing=1.6, handletextpad=.5)
save(fig, "Fig03_collaboration_print")
plt.close(fig)
print("\ndone")
