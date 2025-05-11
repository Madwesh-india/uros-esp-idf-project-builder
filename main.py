import sys
import os
import re
import json
import shutil
from git import Repo

TEMPLET_PATH = "./uRosTemplet"
MICRO_ROS_REPO = "https://github.com/micro-ROS/micro_ros_espidf_component.git"
CONFIG_FILE = "./uros_components_config.json"
MICRO_ROS_COMPONENTS = "./uros_components"

def main():
    with open(CONFIG_FILE, "r+") as json_file:
        try:
            config_obj = json.load(json_file)
        except json.JSONDecodeError:
            config_obj = {}

        if "ROS_DISTRO" in config_obj:
            print(f"ROS2 DISTRIBUTION: {config_obj['ROS_DISTRO']}")
        else:
            config_obj["ROS_DISTRO"] = input("ROS2 DISTRIBUTION: ")

        if not config_obj.get("ROS_DISTRO_BASE_CLONED", False):
            base_dest = os.path.join(MICRO_ROS_COMPONENTS, "base", "micro_ros_espidf_component")
            Repo.clone_from(
                MICRO_ROS_REPO,
                base_dest,
                branch=config_obj["ROS_DISTRO"]
            )
            config_obj["ROS_DISTRO_BASE_CLONED"] = True

        json_file.seek(0)
        json.dump(config_obj, json_file, indent=4)
        json_file.truncate()

    target_path = input("Target Location: ")
    expanded_path = os.path.expanduser(target_path)

    if not os.path.exists(expanded_path):
        try:
            os.makedirs(expanded_path)
            print(f"Created directory: {expanded_path}")
        except Exception as e:
            print(f"Failed to create directory: {e}")
            sys.exit(1)

    project_name = input("Project Name: ")
    project_path = os.path.join(expanded_path, project_name)


    if os.path.exists(project_path):
        print(f"Error: '{project_path}' already exists. Choose a different project name or remove it first.")
        sys.exit(1)

    try:
        shutil.copytree(TEMPLET_PATH, project_path)
        print(f"Copied template into: {project_path}")
    except Exception as e:
        print(f"Failed to copy template: {e}")
        sys.exit(1)

    node_name = input("Node Name: ")
    namespace_name = input("Namespace Name: ")

    publisher_count = int(input("Publisher Count: "))
    subscriber_count = int(input("Subscriber Count: "))
    service_count = int(input("Service Count: "))
    client_count = int(input("Client Count: "))
    mode = int(input(
"""1) UDP (WiFi)
2) Custom (Serial)
Select Mode (1 or 2): 
"""))
    
    

if __name__ == "__main__":
    main()
