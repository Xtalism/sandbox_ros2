import os
from glob import glob

from setuptools import setup

package_name = "omni_manipulator_description"

data_files = [
    ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
    ("share/" + package_name, ["package.xml"]),
    ("share/" + package_name + "/launch/", glob("launch/*.py")),
    ("share/" + package_name + "/description/urdf/", glob("description/urdf/*")),
    ("share/" + package_name + "/description/xacro/", glob("description/xacro/*")),
    ("share/" + package_name + "/description/sdf/", glob("description/sdf/*")),
    ("share/" + package_name + "/world/", glob("world/*.world") + glob("world/*.sdf")),
    (
        "share/" + package_name + "/world/bookstore_world/",
        glob("world/bookstore_world/*.world"),
    ),
    ("share/" + package_name + "/rviz/", glob("rviz/*")),
    ("share/" + package_name + "/meshes/collision/", glob("meshes/collision/*")),
    ("share/" + package_name + "/meshes/visual/", glob("meshes/visual/*")),
    ("share/" + package_name + "/config/", glob("config/*")),
]

for root, dirs, files in os.walk("world/bookstore_world/models"):
    for file in files:
        path = os.path.join(root, file)
        destination = os.path.join("share", package_name, root)
        data_files.append((destination, [path]))

setup(
    name=package_name,
    version="0.0.0",
    packages=[package_name],
    data_files=data_files,
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="xtalism",
    maintainer_email="manuel.pina.olivas@gmail.com:",
    description="TODO: Package description",
    license="TODO: License declaration",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [],
    },
)
