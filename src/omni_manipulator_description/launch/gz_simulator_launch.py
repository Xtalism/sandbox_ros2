import os
from ament_index_python.packages import get_package_share_directory
from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration, Command
from launch.actions import DeclareLaunchArgument,SetEnvironmentVariable
from launch_ros.actions import Node
import launch_ros.descriptions
from launch_ros.parameter_descriptions import ParameterValue
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from pathlib import Path
from launch.conditions import IfCondition

def generate_launch_description():
    use_robot_state_pub = LaunchConfiguration('use_robot_state_pub')
    urdf_file= LaunchConfiguration('urdf_file')
    use_joint_state_pub = LaunchConfiguration('use_joint_state_pub')
    use_sim_time = LaunchConfiguration('use_sim_time')
    bringup_dir = get_package_share_directory('omni_manipulator_description')
    world = os.path.join(bringup_dir , "world", "depot.sdf")
    
    # Changed to use URDF with xacro processing
    urdf_path = os.path.join(bringup_dir, 'urdf', 'omni-manipulator-description.urdf')
    robot_desc = ParameterValue(
        Command(['xacro ', urdf_path]),
        value_type=str
    )

    start_robot_state_publisher_cmd = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='both',
        parameters=[
            {'use_sim_time': True},
            {'robot_description': robot_desc}
        ])
    
    start_joint_state_publisher_cmd = Node(
        condition=IfCondition(use_joint_state_pub),
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        output='screen',
        arguments=[urdf_file])

    gz_resource_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=':'.join([
            os.path.join(bringup_dir, 'world'),
            str(Path(bringup_dir).parent.resolve())
        ])
    )

    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        output='screen',
        parameters=[{'use_sim_time': True}],
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        parameters=[{
            'config_file': os.path.join(bringup_dir, 'config', 'gz_bridge.yaml'),
            'qos_overrides./tf_static.publisher.durability': 'transient_local',
        }],
        output='screen'
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

    # Spawn the robot in Gazebo - Gazebo will auto-convert URDF to SDF
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
            "2.0",
        ],
        output="screen",
    )

    rviz_config_file = os.path.join(bringup_dir, 'rviz', 'config.rviz')
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': True}],
    )

    gz_bridge_node = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            "/camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo",
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            "/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist",
            "/imu@sensor_msgs/msg/Imu@gz.msgs.IMU",
            "/joint_states@sensor_msgs/msg/JointState@gz.msgs.Model",
            "/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry",
            "/rgb_image@sensor_msgs/msgs/Image@",
            "/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan",
            "/tf@tf2_msgs/msg/TFMessage@gz.msgs.Pose_V",
            "/tf_static@tf2_msgs/msg/TFMessage@gz.msgs.Pose_V",
        ],
        output="screen",
        parameters=[
            {'use_sim_time': True},
        ]
    )

    tf_map= Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        arguments= ["0", "0", "0", "0", "0", "0", "map", "odom"])

    # Launch!
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time',default_value='True',description='Use sim time if true'),
        DeclareLaunchArgument('urdf_file',default_value=os.path.join(bringup_dir, 'urdf', 'omni-manipulator-description.urdf'),description='URDF file path'),
        DeclareLaunchArgument('use_robot_state_pub',default_value='True',description='Whether to start the robot state publisher'),
        DeclareLaunchArgument('use_joint_state_pub',default_value='True',description='Whether to start the joint state publisher'),
        gz_resource_path,
        gz_sim,bridge, spawn_entity,start_robot_state_publisher_cmd,tf_map,joint_state_publisher,rviz_node,gz_bridge_node,start_joint_state_publisher_cmd
    ])