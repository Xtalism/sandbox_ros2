import os
from pathlib import Path

from ament_index_python.packages import (
    get_package_share_directory,
)
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


def generate_launch_description():
    use_robot_state_pub = LaunchConfiguration("use_robot_state_pub")
    urdf_file = LaunchConfiguration("urdf_file")
    use_joint_state_pub = LaunchConfiguration("use_joint_state_pub")
    use_sim_time = LaunchConfiguration("use_sim_time", default=True)
    bringup_dir = get_package_share_directory("omni_manipulator_description")
    world = os.path.join(bringup_dir, "world", "depot.sdf")

    # Changed to use URDF with xacro processing
    urdf_path = os.path.join(
        bringup_dir, "urdf", "omni_manipulator_description.xacro.urdf"
    )
    robot_desc = ParameterValue(Command(["xacro ", urdf_path]), value_type=str)

    # Robot controllers configuration
    robot_controllers = PathJoinSubstitution(
        [
            bringup_dir,
            "config",
            "mecanum_drive_controller.yaml",
        ]
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
        arguments=[urdf_file],
    )

    gz_resource_path = SetEnvironmentVariable(
        name="GZ_SIM_RESOURCE_PATH",
        value=":".join(
            [
                os.path.join(bringup_dir, "world"),
                str(Path(bringup_dir).parent.resolve()),
            ]
        ),
    )

    # Single bridge node using config file
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        parameters=[
            {
                "config_file": os.path.join(bringup_dir, "config", "gz_bridge.yaml"),
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

    # Spawn the robot in Gazebo
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
            "0.1",
        ],
        output="screen",
    )

    # Clock bridge for simulation time
    clock_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
        output="screen",
    )

    # Controller spawners with event handlers for proper sequencing
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

    rviz_config_file = os.path.join(bringup_dir, "config", "config.rviz")
    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config_file],
        parameters=[{"use_sim_time": True}],
    )

    tf_map = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        arguments=["0", "0", "0", "0", "0", "0", "map", "odom"],
    )

    # Launch!
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "use_sim_time", default_value="True", description="Use sim time if true"
            ),
            DeclareLaunchArgument(
                "urdf_file",
                default_value=os.path.join(
                    bringup_dir, "urdf", "omni_manipulator_description.xacro.urdf"
                ),
                description="URDF file path",
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
            gz_resource_path,
            gz_sim,
            clock_bridge,
            bridge,
            start_robot_state_publisher_cmd,
            spawn_entity,
            tf_map,
            rviz_node,
            start_joint_state_publisher_cmd,
            # Event handlers for proper controller initialization sequence
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
        ]
    )