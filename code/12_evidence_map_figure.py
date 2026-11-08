#!/usr/bin/env python3
"""Figure 10, revised: the two-dimensional evidence map that replaces the single priority score.

(a) prominence against the validation rate, with Wilson intervals and quadrants;
(b) the validation rate with its count, denominator and interval shown separately;
(c) how often each proxy holds a top-tier place across 2,000 bootstrap resamples of the corpus.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from adjustText import adjust_text

sys.path.insert(0, "/PALS/CHEAQI_Composite_Indicator/scripts")
from plot_style import set_house_style, tidy
from cheaqi_palette import RED, BLUE, BLACK, GREY

V2 = Path(__file__).resolve().parents[1]
FIG, TAB, DATA = V2 / "figs", V2 / "tables", V2 / "data"
R = pd.read_csv(TAB / "T_evidence_map.csv")
E = json.loads((DATA / "evidence_map.json").read_text())
N = R[~R.is_aggregate].copy()
AG = R[R.is_aggregate].copy()
set_house_style(base=15)
plt.rcParams.update({"savefig.dpi": 600, "legend.fontsize": 13.3, "xtick.labelsize": 14, "ytick.labelsize": 14, "axes.labelsize": 15.5})
AFR = {"Household fuel use", "Biomass and open burning", "Fire activity and burned area",
       "Land surface temperature", "Night-time lights", "Settlement and socio-economic status", "Boundary-layer height"}
pm, vm = E["median_prominence"], E["median_validation_rate"]
# short forms for the scatter; the full names are in panels b and c and in Table 3
SHORT = {"Land use or land cover class": "Land use / cover", "Built-up or impervious surface": "Built-up surface",
         "Distance or proximity to roads": "Road proximity", "Elevation and terrain": "Elevation",
         "Traffic volume or intensity": "Traffic volume", "Reanalysis or NWP fields": "Reanalysis fields",
         "Chemical-transport or dispersion model output": "CTM / dispersion", "Household fuel use": "Household fuel",
         "Biomass and open burning": "Open burning", "Fire activity and burned area": "Fire activity",
         "Land surface temperature": "Land surface temp.", "Night-time lights": "Night lights",
         "Settlement and socio-economic status": "Settlement / SES", "Boundary-layer height": "Boundary-layer height"}

fig = plt.figure(figsize=(25.6, 12.2))
gs = fig.add_gridspec(1, 3, width_ratios=[1.26, 1.00, 0.78], wspace=1.16)

# ---------------------------------------------------------------- (a) evidence map
ax = fig.add_subplot(gs[0])
ax.axvline(pm, color="#9a9a9a", lw=1, ls="--", zorder=1)
ax.axhline(vm, color="#9a9a9a", lw=1, ls="--", zorder=1)
# uncertainty first, so the markers sit on top
for r in N.itertuples():
    ax.plot([r.prominence, r.prominence], [r.val_lo, r.val_hi], color="#B9C0C7", lw=1.5, zorder=2, solid_capstyle="round")
col = [RED if d else BLACK for d in N.dynamic_proxy]
ax.scatter(N.prominence, N.validation_rate, s=20 + N.records * 1.15, facecolors=col,
           edgecolors="white", lw=.9, alpha=.88, zorder=4)
for r in AG.itertuples():
    ax.plot([r.prominence, r.prominence], [r.val_lo, r.val_hi], color="#D4D9DE", lw=1.4, zorder=2)
ax.scatter(AG.prominence, AG.validation_rate, s=20 + AG.records * 1.15, facecolors="white",
           edgecolors=[RED if d else BLACK for d in AG.dynamic_proxy], lw=1.6, zorder=4)
lab = N[(N.top8_stability >= .49) | N.proxy.isin(AFR)]
texts = [ax.text(r.prominence, r.validation_rate, SHORT.get(r.proxy, r.proxy), fontsize=12.6, zorder=6,
                 color=RED if r.dynamic_proxy else BLACK, fontweight="bold" if r.proxy in AFR else "normal",
                 bbox=dict(boxstyle="round,pad=.08", fc="white", ec="none", alpha=.82)) for r in lab.itertuples()]
adjust_text(texts, ax=ax, x=N.prominence.values, y=N.validation_rate.values, expand=(1.55, 2.1),
            force_text=(.95, 1.5), force_static=(.55, 1.0), max_move=95, iter_lim=700,
            ensure_inside_axes=True, arrowprops=dict(arrowstyle="-", color="#8a8a8a", lw=.5))
ax.set_xlabel("Bibliometric prominence (mean percentile of frequency\nand co-use centrality)")
ax.set_ylabel("Share of the proxy's studies reporting a validation\n(with 95% Wilson interval)")
ax.set_xlim(-.06, 1.12); ax.set_ylim(-.035, 1.045)
ax.set_yticks([0, .2, .4, .6, .8, 1.0])
rr, pp = E["rho_prominence_vs_validation_rate"]
rc, _ = E["rho_prominence_vs_validation_counts"]
# the two quadrant names that would sit over data go above the panel; the other two sit on the floor
ax.text(.005, 1.012, "Validated, peripheral", transform=ax.transAxes, ha="left", va="bottom",
        fontsize=13.2, color=GREY, style="italic")
ax.text(.995, 1.012, "Established", transform=ax.transAxes, ha="right", va="bottom",
        fontsize=13.2, color=GREY, style="italic")
ax.text(.005, .008, "Under-studied", transform=ax.transAxes, ha="left", va="bottom",
        fontsize=13.2, color=GREY, style="italic", zorder=7)
ax.text(.995, .008, "Prominent, weakly validated", transform=ax.transAxes, ha="right", va="bottom",
        fontsize=13.2, color=GREY, style="italic", zorder=7)
ax.text(.60, .985, f"prominence vs validation rate   \u03c1 = {rr:+.2f} (p = {float(pp):.2f})\n"
                   f"prominence vs validation counts   \u03c1 = {rc:.2f}",
        ha="center", va="top", fontsize=14.0, zorder=7,
        bbox=dict(boxstyle="round,pad=.34", fc="white", ec="#DDE1E5", lw=.9))
ax.legend(handles=[Line2D([], [], marker="o", ls="", ms=10, color=BLACK, label="static proxy"),
                   Line2D([], [], marker="o", ls="", ms=10, color=RED, label="dynamic proxy"),
                   Line2D([], [], marker="o", ls="", ms=10, mfc="white", mec=BLACK, label="aggregate category"),
                   Line2D([], [], color="#B9C0C7", lw=1.8, label="95% Wilson interval")],
          loc="upper center", bbox_to_anchor=(.5, 1.165), ncol=2, frameon=False, fontsize=13.0,
          handletextpad=.5, columnspacing=2.2)
tidy(ax)
ax.text(-0.02, 1.20, "a", transform=ax.transAxes, fontsize=18.2, fontweight="bold", va="bottom", ha="right")
ax.text(.5, -.215, "bold label: relevant to African sources", transform=ax.transAxes,
        ha="center", va="top", fontsize=12.6, color=GREY)

# ------------------------------------------- (b) rate, count, denominator, interval
ax = fig.add_subplot(gs[1])
t = N.sort_values("validation_rate").reset_index(drop=True)
yy = np.arange(len(t))
has = t.spatial_or_external > 0
ax.hlines(yy, t.val_lo, t.val_hi, color="#B9C0C7", lw=2.1, zorder=2)
ax.scatter(t.validation_rate, yy, s=46, facecolors=[BLUE if h else "white" for h in has],
           edgecolors=BLUE, lw=1.5, zorder=3)
ax.axvline(vm, color="#9a9a9a", lw=1, ls="--", zorder=1)
for y_, r in zip(yy, t.itertuples()):
    ax.text(1.06, y_, f"{r.validated}/{r.records}", va="center", fontsize=12.0, color=BLACK)
ax.text(1.06, len(t) - .45, "k / n", fontsize=12.4, color=GREY, va="bottom")
ax.set_yticks(yy, list(t.proxy), fontsize=12.4)
ax.set_xlabel("Share of studies reporting a validation")
ax.set_xlim(0, 1.34); ax.set_ylim(-.9, len(t) - .1)
ax.set_xticks([0, .2, .4, .6, .8, 1.0])
ax.legend(handles=[Line2D([], [], marker="o", ls="", ms=9, color=BLUE, label="at least one spatial or\nexternal design"),
                   Line2D([], [], marker="o", ls="", ms=9, mfc="white", mec=BLUE, label="none")],
          loc="upper left", bbox_to_anchor=(-.01, 1.0), fontsize=12.0, frameon=False)
tidy(ax)
ax.text(-0.72, 1.06, "b", transform=ax.transAxes, fontsize=18.2, fontweight="bold", va="bottom", ha="right")

# --------------------------------------------------- (c) bootstrap rank stability
ax = fig.add_subplot(gs[2])
t = N[N.top8_stability > 0.005].sort_values("top8_stability").reset_index(drop=True)
yy = np.arange(len(t))
ax.barh(yy, t.top8_stability, color=[RED if d else BLACK for d in t.dynamic_proxy], height=.68, zorder=3)
ax.axvline(.90, color=GREY, lw=1.1, ls="--", zorder=2)
for y_, v in zip(yy, t.top8_stability):
    ax.text(v + .018, y_, f"{v:.2f}".lstrip("0"), va="center", fontsize=12.0)
ax.set_yticks(yy, list(t.proxy), fontsize=12.4)
ax.set_xlabel("Top-eight stability\n(2,000 bootstrap resamples)")
ax.set_xlim(0, 1.17); ax.set_ylim(-.9, len(t) - .1)
ax.set_xticks([0, .25, .5, .75, 1.0])
ax.text(.90, len(t) - .5, "0.90", ha="center", va="bottom", fontsize=12.0, color=GREY)
tidy(ax)
ax.text(-0.95, 1.06, "c", transform=ax.transAxes, fontsize=18.2, fontweight="bold", va="bottom", ha="right")

fig.canvas.draw()
from matplotlib.transforms import Bbox
inv = fig.dpi_scale_trans.inverted()
axes = fig.axes
_all = Bbox.union([a.get_tightbbox(fig.canvas.get_renderer()).transformed(inv) for a in axes])
_full = Bbox.from_extents(_all.x0 - .18, _all.y0 - .18, _all.x1 + .18, _all.y1 + .18)
fig.savefig(FIG / "Fig11_evidence_map.png", bbox_inches=_full)
fig.savefig(FIG / "Fig11_evidence_map.pdf", bbox_inches=_full)
for key, ax in zip("abc", axes):
    for t_ in ax.texts:
        if t_.get_text() in ("a", "b", "c") and t_.get_fontweight() == "bold":
            t_.set_visible(False)
W_in = fig.get_size_inches()[0]
bb = [ax.get_tightbbox(fig.canvas.get_renderer()).transformed(inv) for ax in axes]
pos = [ax.get_position() for ax in axes]
for i, (key, b) in enumerate(zip("abc", bb)):
    # a panel owns its own axes plus whatever sits to its left (tick labels); it never
    # reaches into the next panel's label strip
    lo = b.x0 - .12 if i == 0 else max(b.x0 - .12, pos[i - 1].x1 * W_in + .22)
    hi = b.x1 + .12 if i == len(axes) - 1 else min(b.x1 + .12, pos[i].x1 * W_in + .14)
    print(f"  panel {key}: tight=({b.x0:.2f},{b.x1:.2f}) axes=({pos[i].x0*W_in:.2f},{pos[i].x1*W_in:.2f}) -> ({lo:.2f},{hi:.2f})")
    fig.savefig(FIG / f"Fig11_evidence_map_{key}.png",
                bbox_inches=Bbox.from_extents(lo, b.y0 - .12, hi, b.y1 + .12))
print("wrote", FIG / "Fig11_evidence_map.png")
for k in "abc":
    print("wrote", FIG / f"Fig11_evidence_map_{k}.png")
