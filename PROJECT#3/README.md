# Project 3 — Autonomous Mobile Robot (AMR) Navigation
### DecodeLabs Robotics & Automation Internship — Industrial Training Kit

## 🎯 Goal
Program a wheeled robot (simulated) to navigate a maze, map its
environment from LiDAR data, and dynamically re-route when an unexpected
obstacle appears — without ever being given the maze's true blueprint.

## 📁 Folder contents

```
project3/
├── README.md
├── requirements.txt
├── maze_environment.py       ← ground-truth maze, start/goal, scripted dynamic obstacle
├── lidar_simulator.py        ← simulated 360° LiDAR + 2D occupancy grid builder
├── astar_pathfinder.py       ← A* pathfinding over the occupancy grid
├── robot_navigation_sim.py   ← main simulation loop (run this)
└── output/
    └── navigation_result.png ← generated after running (ground truth vs. robot's map + path)
```

> **Why a simulation instead of real hardware?** The brief asks for
> *simulated* LiDAR data and a maze — there's no physical robot or real
> sensor feed involved. This project builds the full navigation stack
> (perception → mapping → planning → dynamic replanning) as a runnable
> Python simulation, which is exactly how AMR software is developed and
> tested before it ever touches a real chassis.

## 🧠 How the three requirements are implemented

### 1. Simulated LiDAR → 2D Occupancy Grid (`lidar_simulator.py`)
- Casts 32 rays outward from the robot's current cell, up to 6 cells of
  range — a simplified 360° LiDAR sweep.
- Every ray marches forward through the **ground-truth map** (which the
  robot itself never sees directly) and reports what it hits.
- Each scan merges into a persistent **Occupancy Grid** with three states:
  `-1` unknown, `0` known-free, `1` known-occupied — the standard SLAM
  occupancy-grid representation.

### 2. A* Pathfinding (`astar_pathfinder.py`)
- Classic A* with Manhattan-distance heuristic, 4-connected movement.
- Runs **only against the robot's occupancy grid**, never the ground
  truth — the robot can only plan using what it has actually sensed.
- Unknown cells are treated as traversable (a real AMR has to be willing
  to explore unseen space), while known-occupied cells are always
  impassable.

### 3. Dynamic Obstacle Avoidance (`robot_navigation_sim.py`, main loop)
- Before every single move, the robot re-scans with LiDAR.
- If the next cell on its planned path has become occupied (either a
  wall it just discovered, or the scripted dynamic obstacle), it
  **immediately re-plans a full new A* route** from its current position.
- The maze is deliberately built with **two doorways** through its
  center wall, so a genuine alternate route always exists — this project
  scripts an obstacle appearing in one doorway partway through the run,
  forcing the robot to detect it and re-route through the other.

## ▶️ How to run

```bash
pip install numpy matplotlib --break-system-packages
python3 robot_navigation_sim.py
```

### Sample console output
```
Mission: navigate from (1, 1) to (10, 10)
Grid size: 12x12

Step 0: initial LiDAR scan complete. Planned path length = 19 cells.
Step 4: ⚠️  DYNAMIC OBSTACLE appeared at (5, 6)!
Step 9: 🛑 Obstacle detected at (5, 6) — path blocked! Replanning...
Step 9: ✅ New path found, length = 11 cells.

🎉 SUCCESS: robot reached goal (10, 10) in 19 steps (19 cells traveled).

Visualization saved to: output/navigation_result.png
```

The saved image shows two side-by-side panels:
- **Left** — the hidden ground-truth maze (for grading/comparison only)
- **Right** — what the robot actually built from LiDAR scans, its full
  trajectory, and the exact cell where it detected the obstacle and
  replanned (red triangle marker)

## 🔧 Tuning knobs
| Setting | File | Effect |
|---|---|---|
| `N_RAYS`, `MAX_RANGE` | `lidar_simulator.py` | LiDAR angular resolution / sensor range |
| `GRID_SIZE`, `START`, `GOAL` | `maze_environment.py` | Maze size and mission endpoints |
| `DYNAMIC_OBSTACLE_CELL`, `_TRIGGER_STEP` | `maze_environment.py` | Where/when the surprise obstacle appears |
| Heuristic / connectivity | `astar_pathfinder.py` | Switch to 8-connected or a different heuristic |

## 📝 What to submit
1. The four `.py` files
2. `output/navigation_result.png`
3. The console log showing the replan event (proves obstacle avoidance
   actually triggered, not just that the robot got lucky)
4. A short note on how you'd extend this toward Dijkstra's algorithm or
   a finer angular LiDAR resolution
