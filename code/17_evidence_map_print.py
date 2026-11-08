#!/usr/bin/env python3
"""Figure 10, re-authored at the size it is printed.

The three-panel version was drawn 21 inches wide and placed 3.9 inches wide, a
5.3-fold reduction that left its labels at about 2 pt.  This redraws it for a
6.3-inch text column at 1:1, as two stacked panels:

  (a) prominence against the validation rate, with Wilson intervals and quadrants;
  (b) how often each proxy holds a top-eight place across 2,000 bootstrap resamples.

The old middle panel -- the validation rate of all 34 proxies with counts,
denominators and intervals -- is never cited in the body text and repeats the
rate column of Table 3, so it becomes Supplementary Figure S9, drawn at the same
1:1 scale.
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

COL = 6.30                      # the manuscript's text width, in inches
set_house_style(base=9)
plt.rcParams.update({"savefig.dpi": 600, "legend.fontsize": 8.0,
                     "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
                     "axes.labelsize": 9.0,
                     # the house style crops to the artwork; here the canvas must stay
                     # exactly one text column wide, or the 1:1 sizing is lost on placement
                     "savefig.bbox": "standard"})

AFR = {"Household fuel use", "Biomass and open burning", "Fire activity and burned area",
       "Land surface temperature", "Night-time lights",
       "Settlement and socio-economic status", "Boundary-layer height"}
pm, vm = E["median_prominence"], E["median_validation_rate"]
SHORT = {"Land use or land cover class": "Land use / cover",
         "Built-up or impervious surface": "Built-up surface",
         "Distance or proximity to roads": "Road proximity",
         "Elevation and terrain": "Elevation",
         "Traffic volume or intensity": "Traffic volume",
         "Reanalysis or NWP fields": "Reanalysis fields",
         "Chemical-transport or dispersion model output": "CTM / dispersion",
         "Household fuel use": "Household fuel", "Biomass and open burning": "Open burning",
         "Fire activity and burned area": "Fire activity",
         "Land surface temperature": "Land surface temp.", "Night-time lights": "Night lights",
         "Settlement and socio-economic status": "Settlement / SES",
         "Boundary-layer height": "Boundary-layer ht."}
# y-axis names keep their full wording except the one that overruns the label strip
AXIS = {"Chemical-transport or dispersion model output": "Chemical-transport or dispersion"}


def save(fig, stem):
    # the canvas IS the column, so what is drawn at 9 pt prints at 9 pt
    # (plot_style patches savefig to write the .pdf alongside the .png)
    fig.savefig(FIG / f"{stem}.png", bbox_inches=None)
    print(f"  wrote {stem}.png / .pdf  ({fig.get_size_inches()[0]:.2f} x "
          f"{fig.get_size_inches()[1]:.2f} in, drawn 1:1 for a {COL:.2f} in column)")


# ============================================================ Figure 10 (a, b)
fig = plt.figure(figsize=(COL, 7.75))
# the two panels need different left margins: (b) carries full proxy names on its
# y axis, (a) carries only numbers, so one shared gridspec would clip (b)
gs_a = fig.add_gridspec(1, 1, left=.150, right=.985, top=.945, bottom=.525)
gs_b = fig.add_gridspec(1, 1, left=.368, right=.975, top=.400, bottom=.058)

# ---------------------------------------------------------- (a) evidence map
ax = fig.add_subplot(gs_a[0])
ax.axvline(pm, color="#9a9a9a", lw=.8, ls="--", zorder=1)
ax.axhline(vm, color="#9a9a9a", lw=.8, ls="--", zorder=1)
for r in N.itertuples():
    ax.plot([r.prominence, r.prominence], [r.val_lo, r.val_hi],
            color="#B9C0C7", lw=.9, zorder=2, solid_capstyle="round")
col = [RED if d else BLACK for d in N.dynamic_proxy]
ax.scatter(N.prominence, N.validation_rate, s=7 + N.records * .42, facecolors=col,
           edgecolors="white", lw=.5, alpha=.88, zorder=4)
for r in AG.itertuples():
    ax.plot([r.prominence, r.prominence], [r.val_lo, r.val_hi],
            color="#D4D9DE", lw=.85, zorder=2)
ax.scatter(AG.prominence, AG.validation_rate, s=7 + AG.records * .42, facecolors="white",
           edgecolors=[RED if d else BLACK for d in AG.dynamic_proxy], lw=.9, zorder=4)

lab = N[(N.top8_stability >= .49) | N.proxy.isin(AFR)]
texts = [ax.text(r.prominence, r.validation_rate, SHORT.get(r.proxy, r.proxy),
                 fontsize=7.0, zorder=6, color=RED if r.dynamic_proxy else BLACK,
                 fontweight="bold" if r.proxy in AFR else "normal",
                 bbox=dict(boxstyle="round,pad=.06", fc="white", ec="none", alpha=.84))
         for r in lab.itertuples()]
adjust_text(texts, ax=ax, x=N.prominence.values, y=N.validation_rate.values,
            expand=(1.45, 1.9), force_text=(.9, 1.4), force_static=(.5, .95),
            max_move=55, iter_lim=700, ensure_inside_axes=True,
            arrowprops=dict(arrowstyle="-", color="#8a8a8a", lw=.4))

ax.set_xlabel("Bibliometric prominence\n(mean percentile of frequency and co-use centrality)")
ax.set_ylabel("Share of the proxy's studies\nreporting a validation (95% Wilson)")
ax.set_xlim(-.06, 1.12); ax.set_ylim(-.035, 1.06)
ax.set_yticks([0, .2, .4, .6, .8, 1.0])
rr, pp = E["rho_prominence_vs_validation_rate"]
rc, _ = E["rho_prominence_vs_validation_counts"]
for x_, ha, lbl in ((.005, "left", "Validated, peripheral"), (.995, "right", "Established")):
    ax.text(x_, 1.008, lbl, transform=ax.transAxes, ha=ha, va="bottom",
            fontsize=7.2, color=GREY, style="italic")
for x_, ha, lbl in ((.005, "left", "Under-studied"), (.995, "right", "Prominent, weakly validated")):
    ax.text(x_, .006, lbl, transform=ax.transAxes, ha=ha, va="bottom",
            fontsize=7.2, color=GREY, style="italic", zorder=7)
ax.text(.615, .975, f"prominence vs validation rate  ρ = {rr:+.2f} (p = {float(pp):.2f})\n"
                    f"prominence vs validation counts  ρ = {rc:.2f}",
        transform=ax.transAxes, ha="center", va="top", fontsize=7.0, zorder=7,
        bbox=dict(boxstyle="round,pad=.28", fc="white", ec="#DDE1E5", lw=.7))
ax.legend(handles=[Line2D([], [], marker="o", ls="", ms=4.2, color=BLACK, label="static proxy"),
                   Line2D([], [], marker="o", ls="", ms=4.2, color=RED, label="dynamic proxy"),
                   Line2D([], [], marker="o", ls="", ms=4.2, mfc="white", mec=BLACK,
                          label="aggregate category"),
                   Line2D([], [], color="#B9C0C7", lw=1.4, label="95% Wilson interval")],
          loc="upper center", bbox_to_anchor=(.5, 1.145), ncol=4, frameon=False,
          fontsize=7.0, handletextpad=.4, columnspacing=1.1)
tidy(ax)
fig.text(.012, .972, "a", fontsize=10.5, fontweight="bold", va="bottom", ha="left")
# what bold labels mean is stated in the caption; repeating it in the figure only
# costs vertical space that panel b needs

# --------------------------------------------- (b) bootstrap top-eight stability
ax = fig.add_subplot(gs_b[0])
t = N[N.top8_stability > 0.005].sort_values("top8_stability").reset_index(drop=True)
yy = np.arange(len(t))
ax.barh(yy, t.top8_stability, color=[RED if d else BLACK for d in t.dynamic_proxy],
        height=.66, zorder=3)
ax.axvline(.90, color=GREY, lw=.9, ls="--", zorder=2)
for y_, v in zip(yy, t.top8_stability):
    ax.text(v + .013, y_, f"{v:.2f}".lstrip("0"), va="center", fontsize=7.2)
ax.set_yticks(yy, [AXIS.get(x, x) for x in t.proxy], fontsize=7.8)
ax.set_xlabel("Proportion of 2,000 bootstrap resamples holding a top-eight place")
ax.set_xlim(0, 1.13); ax.set_ylim(-.85, len(t) - .15)
ax.set_xticks([0, .25, .5, .75, 1.0])
ax.text(.90, len(t) - .45, "0.90", ha="center", va="bottom", fontsize=7.0, color=GREY)
tidy(ax)
fig.text(.012, .408, "b", fontsize=10.5, fontweight="bold", va="bottom", ha="left")

save(fig, "Fig11_evidence_map_print")
plt.close(fig)

# ================================================ Supplementary Figure S9 (old b)
fig = plt.figure(figsize=(COL, 7.70))
ax = fig.add_subplot(111)
fig.subplots_adjust(left=.395, right=.845, top=.955, bottom=.072)
t = N.sort_values("validation_rate").reset_index(drop=True)
yy = np.arange(len(t))
has = t.spatial_or_external > 0
ax.hlines(yy, t.val_lo, t.val_hi, color="#B9C0C7", lw=1.3, zorder=2)
ax.scatter(t.validation_rate, yy, s=17, facecolors=[BLUE if h else "white" for h in has],
           edgecolors=BLUE, lw=.9, zorder=3)
ax.axvline(vm, color="#9a9a9a", lw=.8, ls="--", zorder=1)
for y_, r in zip(yy, t.itertuples()):
    ax.text(1.045, y_, f"{r.validated}/{r.records}", va="center", fontsize=7.4, color=BLACK)
ax.text(1.045, len(t) - .30, "k / n", fontsize=7.6, color=GREY, va="bottom")
ax.set_yticks(yy, [AXIS.get(x, x) for x in t.proxy], fontsize=7.8)
ax.set_xlabel("Share of the proxy's studies reporting a validation")
# headroom at the top so the legend sits above the data rather than across them
ax.set_xlim(0, 1.21); ax.set_ylim(-.85, len(t) + 2.3)
ax.set_xticks([0, .2, .4, .6, .8, 1.0])
ax.legend(handles=[Line2D([], [], marker="o", ls="", ms=4.0, color=BLUE,
                          label="at least one spatial or external design"),
                   Line2D([], [], marker="o", ls="", ms=4.0, mfc="white", mec=BLUE,
                          label="none")],
          loc="upper left", bbox_to_anchor=(.012, .995), fontsize=7.2, frameon=False,
          handletextpad=.4)
tidy(ax)
save(fig, "FigS09_validation_rates")
plt.close(fig)
