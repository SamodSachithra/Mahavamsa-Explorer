import json
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Load results ─────────────────────────────────────────────────────
RESULTS_PATH = "data/evaluation/evaluation_results.json"
OUTPUT_DIR   = "data/evaluation"

with open(RESULTS_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

summary = data["summary"]
results = data["results"]
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Theme ─────────────────────────────────────────────────────────────
GOLD       = "#C8920A"
DARK_BROWN = "#2C1810"
CREAM      = "#FDF6EC"
MED_BROWN  = "#8B6914"
TEAL       = "#0F6E56"
CORAL      = "#993C1D"
PURPLE     = "#3C3489"
BLUE       = "#185FA5"
GREEN      = "#3B6D11"
LIGHT_GRAY = "#F1EFE8"

plt.rcParams.update({
    "figure.facecolor":  CREAM,
    "axes.facecolor":    CREAM,
    "axes.edgecolor":    DARK_BROWN,
    "axes.labelcolor":   DARK_BROWN,
    "xtick.color":       DARK_BROWN,
    "ytick.color":       DARK_BROWN,
    "text.color":        DARK_BROWN,
    "font.family":       "serif",
    "axes.spines.top":   False,
    "axes.spines.right": False,
})

# ══════════════════════════════════════════════════════════════════════
# FIGURE 1 — Accuracy by Question ID
# ══════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(14, 5))
fig.patch.set_facecolor(CREAM)

ids     = [r["id"]             for r in results]
scores  = [r["accuracy_score"] for r in results]
diffs   = [r["difficulty"]     for r in results]

color_map = {"easy": TEAL, "medium": GOLD, "hard": CORAL}
colors    = [color_map[d] for d in diffs]

bars = ax.bar(ids, scores, color=colors, edgecolor=DARK_BROWN, linewidth=0.5, width=0.6)

# Value labels on bars
for bar, score in zip(bars, scores):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
            f"{score:.0%}", ha="center", va="bottom", fontsize=9, color=DARK_BROWN, fontweight="bold")

ax.axhline(summary["average_accuracy"], color=DARK_BROWN, linestyle="--",
           linewidth=1.2, label=f"Average {summary['average_accuracy']:.0%}")

ax.set_ylim(0, 1.15)
ax.set_ylabel("Accuracy Score", fontsize=11)
ax.set_xlabel("Question ID", fontsize=11)
ax.set_title("GraphRAG — Accuracy Score per Question", fontsize=14,
             fontweight="bold", color=DARK_BROWN, pad=16)

legend_patches = [
    mpatches.Patch(color=TEAL,  label="Easy"),
    mpatches.Patch(color=GOLD,  label="Medium"),
    mpatches.Patch(color=CORAL, label="Hard"),
    plt.Line2D([0],[0], color=DARK_BROWN, linestyle="--", label=f"Avg {summary['average_accuracy']:.0%}"),
]
ax.legend(handles=legend_patches, loc="upper right", fontsize=9)
ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
ax.set_yticklabels(["0%","25%","50%","75%","100%"])

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "fig1_accuracy_per_question.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved: fig1_accuracy_per_question.png")

# ══════════════════════════════════════════════════════════════════════
# FIGURE 2 — Accuracy by Difficulty
# ══════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(7, 5))
fig.patch.set_facecolor(CREAM)

diffs  = ["easy", "medium", "hard"]
d_scores = [summary["results_by_difficulty"][d] for d in diffs]
d_colors = [TEAL, GOLD, CORAL]

bars = ax.bar(diffs, d_scores, color=d_colors, edgecolor=DARK_BROWN, linewidth=0.7, width=0.5)
for bar, score in zip(bars, d_scores):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
            f"{score:.0%}", ha="center", va="bottom", fontsize=13,
            color=DARK_BROWN, fontweight="bold")

ax.set_ylim(0, 1.2)
ax.set_ylabel("Average Accuracy", fontsize=11)
ax.set_xlabel("Difficulty Level", fontsize=11)
ax.set_title("Accuracy by Question Difficulty", fontsize=14,
             fontweight="bold", color=DARK_BROWN, pad=16)
ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
ax.set_yticklabels(["0%","25%","50%","75%","100%"])

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "fig2_accuracy_by_difficulty.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved: fig2_accuracy_by_difficulty.png")

# ══════════════════════════════════════════════════════════════════════
# FIGURE 3 — Accuracy by Category
# ══════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(9, 5))
fig.patch.set_facecolor(CREAM)

cats      = list(summary["results_by_category"].keys())
cat_scores = [summary["results_by_category"][c] for c in cats]
cat_colors = [BLUE, TEAL, GOLD, CORAL, PURPLE, GREEN, MED_BROWN, DARK_BROWN][:len(cats)]

bars = ax.barh(cats, cat_scores, color=cat_colors, edgecolor=DARK_BROWN, linewidth=0.5, height=0.5)
for bar, score in zip(bars, cat_scores):
    ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height()/2,
            f"{score:.0%}", va="center", fontsize=11,
            color=DARK_BROWN, fontweight="bold")

ax.set_xlim(0, 1.2)
ax.set_xlabel("Average Accuracy", fontsize=11)
ax.set_title("Accuracy by Question Category", fontsize=14,
             fontweight="bold", color=DARK_BROWN, pad=16)
ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
ax.set_xticklabels(["0%","25%","50%","75%","100%"])

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "fig3_accuracy_by_category.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved: fig3_accuracy_by_category.png")

# ══════════════════════════════════════════════════════════════════════
# FIGURE 4 — Response Time per Question
# ══════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(14, 5))
fig.patch.set_facecolor(CREAM)

times  = [r["response_time_seconds"] for r in results]
avg_t  = summary["average_response_time"]

bars = ax.bar(ids, times, color=BLUE, edgecolor=DARK_BROWN, linewidth=0.5, width=0.6, alpha=0.85)
for bar, t in zip(bars, times):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
            f"{t:.1f}s", ha="center", va="bottom", fontsize=8, color=DARK_BROWN)

ax.axhline(avg_t, color=CORAL, linestyle="--", linewidth=1.2,
           label=f"Average {avg_t:.1f}s")

ax.set_ylabel("Response Time (seconds)", fontsize=11)
ax.set_xlabel("Question ID", fontsize=11)
ax.set_title("GraphRAG — Response Time per Question", fontsize=14,
             fontweight="bold", color=DARK_BROWN, pad=16)
ax.legend(fontsize=10)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "fig4_response_time.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved: fig4_response_time.png")

# ══════════════════════════════════════════════════════════════════════
# FIGURE 5 — Graph Triples Used per Question
# ══════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(14, 5))
fig.patch.set_facecolor(CREAM)

triple_counts = [r["graph_triples_count"] for r in results]

bars = ax.bar(ids, triple_counts, color=TEAL, edgecolor=DARK_BROWN,
              linewidth=0.5, width=0.6, alpha=0.85)
for bar, count in zip(bars, triple_counts):
    if count > 0:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1,
                str(count), ha="center", va="bottom", fontsize=9, color=DARK_BROWN)

ax.set_ylabel("Number of Graph Triples", fontsize=11)
ax.set_xlabel("Question ID", fontsize=11)
ax.set_title("Knowledge Graph Triples Retrieved per Question", fontsize=14,
             fontweight="bold", color=DARK_BROWN, pad=16)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "fig5_graph_triples.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved: fig5_graph_triples.png")

# ══════════════════════════════════════════════════════════════════════
# FIGURE 6 — Summary Dashboard
# ══════════════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(14, 8))
fig.patch.set_facecolor(CREAM)
fig.suptitle("Mahavamsa GraphRAG — Evaluation Dashboard",
             fontsize=16, fontweight="bold", color=DARK_BROWN, y=0.98)

# Top left — accuracy per question
ax1 = fig.add_subplot(2, 3, (1, 2))
bars = ax1.bar(ids, scores, color=colors, edgecolor=DARK_BROWN, linewidth=0.4, width=0.6)
ax1.axhline(summary["average_accuracy"], color=DARK_BROWN, linestyle="--", linewidth=1)
ax1.set_ylim(0, 1.2)
ax1.set_title("Accuracy per Question", fontsize=11, fontweight="bold")
ax1.set_yticks([0, 0.5, 1.0])
ax1.set_yticklabels(["0%","50%","100%"])
ax1.tick_params(axis='x', labelsize=7)

# Top right — KPI boxes
ax2 = fig.add_subplot(2, 3, 3)
ax2.axis("off")
kpis = [
    ("Overall Accuracy", f"{summary['average_accuracy']:.0%}", GOLD),
    ("Avg Response Time", f"{summary['average_response_time']:.1f}s", BLUE),
    ("Total Questions", str(summary['total_questions']), TEAL),
]
for i, (label, value, color) in enumerate(kpis):
    y = 0.75 - i * 0.32
    ax2.add_patch(mpatches.FancyBboxPatch((0.05, y), 0.9, 0.25,
        boxstyle="round,pad=0.02", facecolor=color, alpha=0.15,
        edgecolor=color, linewidth=1.5, transform=ax2.transAxes))
    ax2.text(0.5, y + 0.18, value, ha="center", va="center",
             fontsize=18, fontweight="bold", color=color, transform=ax2.transAxes)
    ax2.text(0.5, y + 0.06, label, ha="center", va="center",
             fontsize=9, color=DARK_BROWN, transform=ax2.transAxes)

# Bottom left — by difficulty
ax3 = fig.add_subplot(2, 3, 4)
ax3.bar(diffs, d_scores, color=d_colors, edgecolor=DARK_BROWN, linewidth=0.5, width=0.5)
for i, (d, s) in enumerate(zip(diffs, d_scores)):
    ax3.text(i, s + 0.03, f"{s:.0%}", ha="center", fontsize=10, fontweight="bold")
ax3.set_ylim(0, 1.2)
ax3.set_title("By Difficulty", fontsize=11, fontweight="bold")
ax3.set_yticks([0, 0.5, 1.0])
ax3.set_yticklabels(["0%","50%","100%"])

# Bottom middle — by category
ax4 = fig.add_subplot(2, 3, 5)
ax4.barh(cats, cat_scores, color=cat_colors, edgecolor=DARK_BROWN, linewidth=0.4, height=0.5)
ax4.set_xlim(0, 1.2)
ax4.set_title("By Category", fontsize=11, fontweight="bold")
ax4.set_xticks([0, 0.5, 1.0])
ax4.set_xticklabels(["0%","50%","100%"])
ax4.tick_params(axis='y', labelsize=8)

# Bottom right — response time
ax5 = fig.add_subplot(2, 3, 6)
ax5.bar(ids, times, color=BLUE, edgecolor=DARK_BROWN, linewidth=0.4, width=0.6, alpha=0.85)
ax5.axhline(avg_t, color=CORAL, linestyle="--", linewidth=1)
ax5.set_title("Response Time (s)", fontsize=11, fontweight="bold")
ax5.tick_params(axis='x', labelsize=7)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "fig6_dashboard.png"), dpi=150, bbox_inches="tight")
plt.close()
print("Saved: fig6_dashboard.png")

print(f"\nAll 6 graphs saved to: {OUTPUT_DIR}/")
print("Use these in your final project report.")