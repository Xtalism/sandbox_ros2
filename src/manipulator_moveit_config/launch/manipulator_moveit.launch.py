import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    is_sim = LaunchConfiguration("is_sim")
    is_sim_arg = DeclareLaunchArgument(
        "is_sim",
        default_value="true",
        description="Whether to run in simulation or on real hardware",
    )

    moveit_config = (
        MoveItConfigsBuilder(
            "manipulator_description", package_name="manipulator_moveit_config"
        )
        .robot_description(
            file_path=os.path.join(
                get_package_share_directory("manipulator_description"),
                "description",
                "xacro",
                "manipulator_description.urdf.xacro",
            )
        )
        .robot_description_semantic(file_path="config/manipulator_description.srdf")
        .trajectory_execution(file_path="config/moveit_controllers.yaml")
        .robot_description_kinematics(file_path="config/kinematics.yaml")
        .to_moveit_configs()
    )

    move_group_node = Node(
        package="moveit_ros_move_group",
        executable="move_group",
        output="screen",
        parameters=[
            moveit_config.to_dict(),
            {"use_sim_time": is_sim},
            {"publish_robot_description_semantic": True},
        ],
        arguments=["--ros-args", "--log-level", "info"],
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="log",
        arguments=["-d", str(moveit_config.package_path / "config" / "moveit.rviz")],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
        ],
    )

    return LaunchDescription(
        [
            is_sim_arg,
            move_group_node,
            rviz_node,
        ]
    )
