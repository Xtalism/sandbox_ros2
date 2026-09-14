from glob import glob

from setuptools import setup

package_name = "omni_manipulator_description"

# No meshes, worlds or sensor xacros here: the description pulls those
# straight out of mecanum_description and manipulator_description, which are
# exec_depends in package.xml.
data_files = [
    ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
    ("share/" + package_name, ["package.xml", ".setup_assistant"]),
    ("share/" + package_name + "/launch/", glob("launch/*.py")),
    ("share/" + package_name + "/description/xacro/", glob("description/xacro/*")),
    ("share/" + package_name + "/rviz/", glob("rviz/*")),
    ("share/" + package_name + "/config/", glob("config/*")),
]

setup(
    name=package_name,
    version="0.0.0",
    packages=[package_name],
    data_files=data_files,
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="xtalism",
    maintainer_email="manuel.pina.olivas@gmail.com:",
    description="Mecanum base with the 5-DOF manipulator mounted on top: nav2 for the base, MoveIt 2 for the arm.",
    license="TODO: License declaration",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [],
    },
)
