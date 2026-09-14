"""move_group for the mobile manipulator.

Brings up MoveIt against the combined description only - no simulator, no
robot_state_publisher, no controllers. gz_simulator.launch.py includes this
after Gazebo is up; run it on its own against real hardware that already
publishes /robot_description, /joint_states and the arm's
follow_joint_trajectory action.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from omni_manipulator_description.moveit_config import build_moveit_config


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")
    moveit_config = build_moveit_config()

    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {"use_sim_time": use_sim_time},
            # RViz's MotionPlanning display picks the SRDF up off this topic
            # instead of needing it passed as a parameter of its own.
            {"publish_robot_description_semantic": True},
        ],
        arguments=["--ros-args", "--log-level", "info"],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time",
                default_value="True",
                description="Use sim time if true",
            ),
            move_group_node,
        ]
    )
