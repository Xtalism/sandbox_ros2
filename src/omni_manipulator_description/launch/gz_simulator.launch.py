"""Full mobile-manipulator bringup: Gazebo + nav2/slam + MoveIt.

The description, meshes, worlds and navigation parameters all come out of
mecanum_description and manipulator_description - this package only owns the
combined xacro, the combined controller file and the MoveIt config.
"""

import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    RegisterEventHandler,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from omni_manipulator_description.moveit_config import (
    build_moveit_config,
    robot_xacro_path,
)


def generate_launch_description():
    use_joint_state_pub = LaunchConfiguration("use_joint_state_pub")
    use_moveit = LaunchConfiguration("use_moveit")
    use_sim_time = LaunchConfiguration("use_sim_time", default=True)

    bringup_dir = get_package_share_directory("omni_manipulator_description")
    mecanum_dir = get_package_share_directory("mecanum_description")
    manipulator_dir = get_package_share_directory("manipulator_description")
    slam_toolbox_share = get_package_share_directory("slam_toolbox")
    nav2_bringup_share = get_package_share_directory("nav2_bringup")

    world = os.path.join(mecanum_dir, "world", "bookstore_world", "bookstore.world")

    slam_toolbox_launch_source = os.path.join(
        slam_toolbox_share, "launch", "online_async_launch.py"
    )
    nav2_launch_source = os.path.join(
        nav2_bringup_share, "launch", "navigation_launch.py"
    )
    nav2_config_path = os.path.join(mecanum_dir, "config", "nav2_params.yaml")
    slam_config_path = os.path.join(mecanum_dir, "config", "slam_toolbox_params.yaml")
    laser_filters_config_path = os.path.join(
        mecanum_dir, "config", "laser_filters.yaml"
    )
    ekf_config_path = os.path.join(mecanum_dir, "config", "ekf.yaml")
    gz_bridge_config_path = os.path.join(mecanum_dir, "config", "gz_bridge.yaml")

    urdf_path = robot_xacro_path()
    robot_desc = ParameterValue(Command(["xacro ", urdf_path]), value_type=str)

    moveit_config = build_moveit_config()

    robot_controllers = PathJoinSubstitution(
        [bringup_dir, "config", "omni_manipulator_controllers.yaml"]
    )
    start_robot_state_publisher_cmd = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="both",
        parameters=[{"use_sim_time": True}, {"robot_description": robot_desc}],
    )
    start_joint_state_publisher_cmd = Node(
        condition=IfCondition(use_joint_state_pub),
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
        name="joint_state_publisher_gui",
        output="screen",
        arguments=[urdf_path],
    )
    # The meshes now live in two other packages, so gz needs the share root of
    # each one on its resource path or every package:// URI in the combined
    # description resolves to nothing and the robot spawns invisible.
    gz_resource_path = SetEnvironmentVariable(
        name="GZ_SIM_RESOURCE_PATH",
        value=":".join(
            [
                os.path.join(mecanum_dir, "world"),
                os.path.join(mecanum_dir, "world", "bookstore_world"),
                os.path.join(mecanum_dir, "world", "bookstore_world", "models"),
                str(Path(mecanum_dir).parent.resolve()),
                str(Path(manipulator_dir).parent.resolve()),
                str(Path(bringup_dir).parent.resolve()),
            ]
        ),
    )
    # Without this, gz-sim's headless sensor rendering (Sensors system,
    # used by gpu_lidar and imu) falls back to Mesa's EGL/DRI2 path,
    # which fails on NVIDIA proprietary drivers ("failed to create dri2
    # screen") and silently produces zero sensor data. Forces the NVIDIA
    # EGL implementation instead.
    egl_vendor = SetEnvironmentVariable(
        name="__EGL_VENDOR_LIBRARY_FILENAMES",
        value="/usr/share/glvnd/egl_vendor.d/10_nvidia.json",
    )
    glx_vendor = SetEnvironmentVariable(
        name="__GLX_VENDOR_LIBRARY_NAME",
        value="nvidia",
    )
    laser_filter_node = Node(
        package="laser_filters",
        executable="scan_to_scan_filter_chain",
        parameters=[laser_filters_config_path],
        remappings=[
            ("scan", "/scan_raw"),
            ("scan_filtered", "/scan"),
        ],
    )
    robot_localization_node = Node(
        package="robot_localization",
        executable="ekf_node",
        name="ekf_filter_node",
        output="screen",
        parameters=[
            ekf_config_path,
            {"use_sim_time": True},
        ],
        remappings=[
            ("odometry/filtered", "/odom"),
        ],
    )
    voxel_marker_node = Node(
        package="nav2_costmap_2d",
        executable="nav2_costmap_2d_markers",
        name="local_costmap_voxel_markers",
        output="screen",
        parameters=[{"use_sim_time": True}],
        remappings=[
            ("voxel_grid", "/local_costmap/voxel_grid"),
            ("visualization_marker", "/local_costmap/voxel_marker"),
        ],
    )
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        parameters=[
            {
                "config_file": gz_bridge_config_path,
                "qos_overrides./tf_static.publisher.durability": "transient_local",
                "use_sim_time": True,
            }
        ],
        output="screen",
    )
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            [
                os.path.join(
                    get_package_share_directory("ros_gz_sim"),
                    "launch",
                    "gz_sim.launch.py",
                )
            ]
        ),
        launch_arguments={"gz_args": ["-r -v 4 ", world]}.items(),
    )
    spawn_entity = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-name",
            "robot",
            "-topic",
            "/robot_description",
            "-x",
            "0",
            "-y",
            "0",
            "-z",
            "0.058",
        ],
        output="screen",
    )
    clock_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
        output="screen",
    )
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            "/controller_manager",
        ],
        output="screen",
    )
    mecanum_drive_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "mecanum_drive_controller",
            "--param-file",
            robot_controllers,
            "--controller-manager",
            "/controller_manager",
        ],
        output="screen",
    )
    manipulator_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "manipulator_controller",
            "--param-file",
            robot_controllers,
            "--controller-manager",
            "/controller_manager",
        ],
        output="screen",
    )
    rviz_config_file = os.path.join(bringup_dir, "rviz", "config.rviz")
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config_file],
        parameters=[
            {"use_sim_time": True},
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.joint_limits,
        ],
    )
    slam_toolbox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(slam_toolbox_launch_source),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "slam_params_file": slam_config_path,
        }.items(),
    )
    nav2_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(nav2_launch_source),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "params_file": nav2_config_path,
        }.items(),
    )
    moveit = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(bringup_dir, "launch", "moveit.launch.py")
        ),
        condition=IfCondition(use_moveit),
        launch_arguments={"use_sim_time": use_sim_time}.items(),
    )
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time", default_value="True", description="Use sim time if true"
            ),
            DeclareLaunchArgument(
                "use_robot_state_pub",
                default_value="True",
                description="Whether to start the robot state publisher",
            ),
            DeclareLaunchArgument(
                "use_joint_state_pub",
                default_value="False",
                description="Whether to start the joint state publisher",
            ),
            DeclareLaunchArgument(
                "use_moveit",
                default_value="True",
                description="Whether to start move_group for the arm",
            ),
            gz_resource_path,
            egl_vendor,
            glx_vendor,
            gz_sim,
            clock_bridge,
            bridge,
            start_robot_state_publisher_cmd,
            spawn_entity,
            rviz_node,
            start_joint_state_publisher_cmd,
            laser_filter_node,
            robot_localization_node,
            voxel_marker_node,
            slam_toolbox,
            nav2_bringup,
            moveit,
            RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=spawn_entity,
                    on_exit=[joint_state_broadcaster_spawner],
                )
            ),
            RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=joint_state_broadcaster_spawner,
                    on_exit=[mecanum_drive_controller_spawner],
                )
            ),
            RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=mecanum_drive_controller_spawner,
                    on_exit=[manipulator_controller_spawner],
                )
            ),
        ]
    )
