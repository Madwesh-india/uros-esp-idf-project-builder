import sys
import os
import re
import json

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

    

if __name__ == "__main__":
    main()
