# Project 1 — Robotic Arm Kinematics & Path Planning
### DecodeLabs Robotics & Automation Internship — Industrial Training Kit

## 🎯 Goal
Program a simulated 6-axis robotic arm to move its end-effector accurately
from **Point A** to **Point B**, computing the required joint angles with
Inverse Kinematics (IK) and generating a smooth, collision-free
trajectory — without colliding with an obstacle placed in the workspace.

## 📁 Folder contents

```
project1/
├── README.md                     ← this file
├── requirements.txt
├── forward_kinematics.py         ← DH-parameter FK (joint angles -> XYZ pose)
├── inverse_kinematics.py         ← damped-least-squares IK solver
├── trajectory_planner.py         ← quintic time-scaling + collision-aware path
├── robotic_arm_sim.py            ← main simulation loop (run this)
└── output/
    └── arm_trajectory_result.png ← generated after running
```

> **Why matplotlib instead of real ROS/RViz/Gazebo?** The brief's tools
> (ROS, RViz, Gazebo) are a full robotics middleware stack that isn't
> installable in this environment. Every piece of *math* those tools
> exist to run — forward kinematics, inverse kinematics, collision-aware
> trajectory generation — is implemented for real in the `.py` files
> below, from scratch, using NumPy. `robotic_arm_sim.py`'s matplotlib
> render stands in for the "RViz" visualization step (does the arm reach
> the target without colliding?), which is the actual deliverable the
> brief cares about. Section "🔧 Porting this to real ROS 2" below shows
> exactly how each module maps onto real ROS 2 / MoveIt nodes.

## 🧠 The pipeline (matches the slide deck's IPO architecture)

### Input Stage — defining the goal (`robotic_arm_sim.py`)
A 6-DOF arm is defined via a standard Denavit-Hartenberg (DH) table
(`forward_kinematics.py`). The mission is a Cartesian **Point A**, a
Cartesian **Point B**, and a spherical obstacle placed between them —
mirroring the slides' "homogeneous transformation matrix" target pose
and TF2 transform tree concepts (simplified here to a single fixed base
frame, since there's no live sensor feed to buffer).

### Process Stage — the math

**1. Forward Kinematics** (`forward_kinematics.py`)
Chains six DH transformation matrices to answer *"if the joints are at
these angles, where is the hand?"* — deterministic, always exactly one
solution, exactly as described on the "Arrow of Causality" slide.

**2. Inverse Kinematics** (`inverse_kinematics.py`)
Answers the harder question — *"what joint angles reach this XYZ
point?"* — using **Damped Least Squares** (a Levenberg-Marquardt-style
Jacobian solver): a numerical `finite-difference` position Jacobian is
inverted with a damping term every iteration so the solver doesn't blow
up near singularities (`det(J(q)) -> 0` on the "Local Minima Trap"
slide), and every result is joint-limit-clamped so it's physically
realizable. This is a hand-rolled stand-in for the deck's "Solver
Diagnostic Matrix" — closer in spirit to Orocos-KDL's numerical approach
than to TRAC-IK's hybrid solver, but damped specifically to avoid
Orocos-KDL's main documented weakness (36.9% success rate on the slide)
around joint limits and singularities.

**3. Collision-Aware Trajectory Generation** (`trajectory_planner.py`)
- A straight-line Cartesian path A → B is time-scaled with a **quintic
  (5th-order) polynomial**, giving the exact position/velocity/
  acceleration curves shown on the "Output Stage" slide — zero velocity
  and acceleration at both endpoints, smooth in between.
- Before accepting that path, every point on it is checked against the
  obstacle's safety radius (a simplified stand-in for the FCL / Flexible
  Collision Library check on the "Collision Avoidance" slide). If the
  straight line would clip the obstacle, the planner fires a
  **`TRAJECTORY ABORT`** and replans through a single lifted via-point
  above the obstacle, then re-validates both new segments before
  accepting them.
- IK is then solved at every waypoint along the accepted path, each
  solve **warm-started** from the previous waypoint's solution so
  consecutive joint configurations stay close together (no wild jumps
  frame-to-frame).

### Output Stage — the result
`robotic_arm_sim.py` prints a per-waypoint joint-angle log (the same
shape of data a real `control_msgs/action/FollowJointTrajectory` message
would carry — sequential position waypoints ready for a motor driver),
plus a final success/failure summary and end-effector position error.
It then renders a 3D visualization: the full end-effector path, the
obstacle's safety zone, and the arm's link geometry at four key frames
along the trajectory.

## ▶️ How to run

```bash
pip install numpy matplotlib --break-system-packages
python3 robotic_arm_sim.py
```

### Sample console output
```
Mission: move end-effector from A=[0.3, -0.25, 0.25] to B=[0.3, 0.25, 0.25]
Obstacle: center=[0.3, 0.0, 0.25], radius=0.09 m

TRAJECTORY ABORT: direct A -> B path intersects obstacle safety zone...
New path found via lift point [0.3, 0.0, 0.49]. Both segments verified clear.

Solving IK across 40 waypoints...
  All 40 waypoints solved within 1.0 mm tolerance.

🎉 SUCCESS: trajectory fully resolved to joint space.
Path replanned around obstacle: True
Final end-effector position error vs Point B: 0.478 mm

Visualization saved to: output/arm_trajectory_result.png
```

The saved image shows the obstacle as a translucent wireframe sphere,
the planned end-effector path bending up and around it, and the arm's
own link geometry rendered at four points along the motion (color-coded
start → end) so you can visually confirm no link passes through the
obstacle.

## 🔧 Tuning knobs
| Setting | File | Effect |
|---|---|---|
| `POINT_A`, `POINT_B`, `OBSTACLE_CENTER/RADIUS` | `robotic_arm_sim.py` | Mission geometry |
| `DH_PARAMS`, `JOINT_LIMITS_DEG` | `forward_kinematics.py` | Arm's physical dimensions / joint range |
| `DAMPING_LAMBDA`, `POSITION_TOLERANCE_M`, `MAX_ITERATIONS` | `inverse_kinematics.py` | IK solver aggressiveness vs. stability |
| `N_WAYPOINTS`, `lift_height`, collision `margin` | `trajectory_planner.py` / `robotic_arm_sim.py` | Path resolution and how much clearance counts as "safe" |

## 🔧 Porting this to real ROS 2
| This project | Real ROS 2 equivalent |
|---|---|
| `forward_kinematics.py` DH chain | `robot_state_publisher` + URDF/TF2 tree |
| `inverse_kinematics.py` damped least squares | MoveIt's IK plugin (KDL / TRAC-IK / IKFast) |
| `trajectory_planner.py` collision check | MoveIt's Planning Scene + FCL collision checking |
| `robotic_arm_sim.py` joint-angle log | `control_msgs/action/FollowJointTrajectory` goal sent to a hardware/Gazebo controller |
| matplotlib render | RViz (kinematic intent) / Gazebo (physical execution with gravity + PID tuning) |

## 📝 What to submit
1. The four `.py` files
2. `output/arm_trajectory_result.png`
3. The console log showing the `TRAJECTORY ABORT` + replan event (proves
   collision avoidance actually triggered, not just that the straight
   line happened to miss the obstacle)
4. A short note on how you'd extend this toward a full 6-DOF pose target
   (position + orientation) instead of position-only IK, and toward a
   real ROS 2 / MoveIt pipeline
