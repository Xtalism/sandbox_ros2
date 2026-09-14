"""Shared MoveIt configuration for the mobile manipulator.

Both moveit.launch.py (which starts move_group) and gz_simulator.launch.py
(which needs the same parameters for RViz's MotionPlanning display) build the
config from here, so the two can't drift apart.
"""

import os

from ament_index_python.packages import get_package_share_directory
from moveit_configs_utils import MoveItConfigsBuilder

PACKAGE = "omni_manipulator_description"
ROBOT_NAME = "omni_manipulator"


def robot_xacro_path():
    return os.path.join(
        get_package_share_directory(PACKAGE),
        "description",
        "xacro",
        "omni_manipulator_description.urdf.xacro",
    )


def build_moveit_config():
    return (
        MoveItConfigsBuilder(ROBOT_NAME, package_name=PACKAGE)
        .robot_description(file_path=robot_xacro_path())
        .robot_description_semantic(file_path="config/omni_manipulator.srdf")
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .joint_limits(file_path="config/joint_limits.yaml")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        # OMPL only. Pilz was a poor fit twice over: it rejects the empty
        # planner_id RViz sends unless you pick PTP/LIN/CIRC by hand, and its
        # LIN/CIRC commands plan straight-line Cartesian paths, which need
        # full 6-DOF pose IK - this arm has 5 joints and solves position-only
        # (see config/kinematics.yaml).
        .planning_pipelines(pipelines=["ompl"])
        .to_moveit_configs()
    )
