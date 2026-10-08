"""
Draw a regulation WNBA court with matplotlib.

Coordinate system (feet):
    origin (0, 0) = center of the court
    x in [-47, 47]  -> along the length (baselines at x = +/-47)
    y in [-25, 25]  -> along the width  (sidelines at y = +/-25)

WNBA dimensions used:
    Court ............................ 94 ft x 50 ft
    Basket center .................... 5.25 ft from baseline (x = +/-41.75)
    Rim .............................. 18 in diameter (0.75 ft radius)
    Backboard ........................ 6 ft wide, face 4 ft from baseline
    Lane (paint) ..................... 16 ft wide, 19 ft deep (FT line 15 ft from backboard)
    Free-throw circle ................ 6 ft radius (bottom half dashed)
    Restricted area .................. 4 ft radius arc from basket center
    3-point line ..................... 22 ft 1.75 in (6.75 m) arc,
                                       21 ft 7.85 in (6.6 m) in the corners
    Center circle .................... 6 ft radius
    28-foot hash marks ............... 28 ft from each baseline, 3 ft into the court
    Lane-space marks ................. 7 ft (first mark), 8 ft (neutral block),
                                       11 ft and 14 ft from the baseline

Usage:
    python wnba_court.py                 # opens a window
    python wnba_court.py -o court.png    # saves to a file
"""

import argparse

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Arc, Circle, Rectangle

# --- Dimensions (feet) -------------------------------------------------------
HALF_LENGTH = 47.0
HALF_WIDTH = 25.0

BASKET_FROM_BASELINE = 5.25
RIM_RADIUS = 0.75
BACKBOARD_FROM_BASELINE = 4.0
BACKBOARD_HALF_WIDTH = 3.0

LANE_HALF_WIDTH = 8.0
LANE_LENGTH = 19.0  # baseline to free-throw line
FT_CIRCLE_RADIUS = 6.0

RESTRICTED_RADIUS = 4.0

THREE_ARC_RADIUS = 22.146   # 6.75 m
THREE_CORNER_DIST = 21.654  # 6.6 m

CENTER_CIRCLE_RADIUS = 6.0

HASH_28_FROM_BASELINE = 28.0
HASH_28_LENGTH = 3.0

LANE_MARK_LENGTH = 0.5      # lane-space marks extend 6 in outside the lane
LANE_MARKS_FROM_BASELINE = (7.0, 11.0, 14.0)
NEUTRAL_BLOCK = (7.0, 8.0)  # the "low block" (filled)

LOWER_DEF_BOX_OFFSET = 3.0  # baseline marks 3 ft outside each lane line
LOWER_DEF_BOX_LENGTH = 0.5


def _draw_half(ax, side, color, lw):
    """Draw one half's basket-area elements. side = -1 (left) or +1 (right)."""
    s = side
    baseline_x = s * HALF_LENGTH
    hoop_x = s * (HALF_LENGTH - BASKET_FROM_BASELINE)
    board_x = s * (HALF_LENGTH - BACKBOARD_FROM_BASELINE)
    ft_x = s * (HALF_LENGTH - LANE_LENGTH)

    # Arc angles: left half opens toward +x (theta around 0), right half toward -x.
    face = 0.0 if s < 0 else 180.0

    def x_from_baseline(d):
        return s * (HALF_LENGTH - d)

    # Hoop and connector (backboard face -> rim)
    ax.add_patch(Circle((hoop_x, 0), RIM_RADIUS, fill=False, ec=color, lw=lw))
    ax.plot([board_x, hoop_x - s * RIM_RADIUS], [0, 0], color=color, lw=lw)

    # Backboard
    ax.plot([board_x, board_x], [-BACKBOARD_HALF_WIDTH, BACKBOARD_HALF_WIDTH],
            color=color, lw=lw * 2)

    # Paint (lane)
    ax.add_patch(Rectangle((min(baseline_x, ft_x), -LANE_HALF_WIDTH),
                           LANE_LENGTH, 2 * LANE_HALF_WIDTH,
                           fill=True, fc="#e8d5b9", ec=color, lw=lw, zorder=0))
    ax.add_patch(Rectangle((min(baseline_x, ft_x), -LANE_HALF_WIDTH),
                           LANE_LENGTH, 2 * LANE_HALF_WIDTH,
                           fill=False, ec=color, lw=lw))

    # Free-throw circle: solid half outside the lane, dashed half inside
    ax.add_patch(Arc((ft_x, 0), 2 * FT_CIRCLE_RADIUS, 2 * FT_CIRCLE_RADIUS,
                     theta1=face - 90, theta2=face + 90, ec=color, lw=lw))
    ax.add_patch(Arc((ft_x, 0), 2 * FT_CIRCLE_RADIUS, 2 * FT_CIRCLE_RADIUS,
                     theta1=face + 90, theta2=face + 270, ec=color, lw=lw,
                     linestyle=(0, (4, 4))))

    # Restricted area: 4 ft arc + straight segments back to the backboard face
    ax.add_patch(Arc((hoop_x, 0), 2 * RESTRICTED_RADIUS, 2 * RESTRICTED_RADIUS,
                     theta1=face - 90, theta2=face + 90, ec=color, lw=lw))
    for y in (-RESTRICTED_RADIUS, RESTRICTED_RADIUS):
        ax.plot([board_x, hoop_x], [y, y], color=color, lw=lw)

    # 3-point line: straight corner segments + arc
    corner_dx = np.sqrt(THREE_ARC_RADIUS**2 - THREE_CORNER_DIST**2)
    corner_end_x = hoop_x - s * corner_dx
    for y in (-THREE_CORNER_DIST, THREE_CORNER_DIST):
        ax.plot([baseline_x, corner_end_x], [y, y], color=color, lw=lw)
    theta = np.degrees(np.arctan2(THREE_CORNER_DIST, corner_dx))
    ax.add_patch(Arc((hoop_x, 0), 2 * THREE_ARC_RADIUS, 2 * THREE_ARC_RADIUS,
                     theta1=face - theta, theta2=face + theta, ec=color, lw=lw))

    # Lane-space marks (outside the lane lines)
    for d in LANE_MARKS_FROM_BASELINE:
        x = x_from_baseline(d)
        for sign in (-1, 1):
            y0 = sign * LANE_HALF_WIDTH
            ax.plot([x, x], [y0, y0 + sign * LANE_MARK_LENGTH], color=color, lw=lw)

    # Neutral-zone block (low block), filled
    x0, x1 = sorted((x_from_baseline(NEUTRAL_BLOCK[0]), x_from_baseline(NEUTRAL_BLOCK[1])))
    for sign in (-1, 1):
        y0 = LANE_HALF_WIDTH if sign > 0 else -LANE_HALF_WIDTH - LANE_MARK_LENGTH
        ax.add_patch(Rectangle((x0, y0), x1 - x0, LANE_MARK_LENGTH,
                               fc=color, ec=color, lw=lw))

    # Lower defensive box marks on the baseline
    for sign in (-1, 1):
        y = sign * (LANE_HALF_WIDTH + LOWER_DEF_BOX_OFFSET)
        ax.plot([baseline_x, baseline_x - s * LOWER_DEF_BOX_LENGTH], [y, y],
                color=color, lw=lw)

    # 28-foot hash marks (frontcourt throw-in line), both sidelines
    x28 = x_from_baseline(HASH_28_FROM_BASELINE)
    for sign in (-1, 1):
        y0 = sign * HALF_WIDTH
        ax.plot([x28, x28], [y0, y0 - sign * HASH_28_LENGTH], color=color, lw=lw)


def draw_court(ax=None, color="black", lw=1.5, court_color="#f5e6cf"):
    """Draw the full WNBA court on `ax` and return it."""
    if ax is None:
        _, ax = plt.subplots(figsize=(14, 7.5))

    # Floor and boundary
    ax.add_patch(Rectangle((-HALF_LENGTH, -HALF_WIDTH), 2 * HALF_LENGTH, 2 * HALF_WIDTH,
                           fc=court_color, ec="none", zorder=-1))
    ax.add_patch(Rectangle((-HALF_LENGTH, -HALF_WIDTH), 2 * HALF_LENGTH, 2 * HALF_WIDTH,
                           fill=False, ec=color, lw=lw * 1.5))

    # Half-court line and center circle
    ax.plot([0, 0], [-HALF_WIDTH, HALF_WIDTH], color=color, lw=lw)
    ax.add_patch(Circle((0, 0), CENTER_CIRCLE_RADIUS, fill=False, ec=color, lw=lw))

    for side in (-1, 1):
        _draw_half(ax, side, color, lw)

    ax.set_xlim(-HALF_LENGTH - 2, HALF_LENGTH + 2)
    ax.set_ylim(-HALF_WIDTH - 2, HALF_WIDTH + 2)
    ax.set_aspect("equal")
    ax.set_xlabel("x (ft)")
    ax.set_ylabel("y (ft)")
    ax.set_xticks(np.arange(-47, 48, 47 / 2))
    ax.set_yticks(np.arange(-25, 26, 12.5))
    ax.set_title("WNBA Court")
    return ax


def main():
    parser = argparse.ArgumentParser(description="Draw a WNBA court diagram.")
    parser.add_argument("-o", "--output", help="save to this file instead of showing")
    args = parser.parse_args()

    ax = draw_court()
    plt.tight_layout()
    if args.output:
        plt.savefig(args.output, dpi=200)
        print(f"Saved {args.output}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
