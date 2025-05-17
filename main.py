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
GITIGNORE_PATH = "./.gitignore"

UDP = 1
CUSTOM = 2

def main():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump({}, f, indent=4)

    json_file = open(CONFIG_FILE, "r+")

    try:
        config_obj = json.load(json_file)
    except json.JSONDecodeError:
        config_obj = {}

    if "ROS_DISTRO" in config_obj:
        print(f"ROS2 DISTRIBUTION: {config_obj['ROS_DISTRO']}")
    else:
        config_obj["ROS_DISTRO"] = input("ROS2 DISTRIBUTION: ")

    base_dest = os.path.join(MICRO_ROS_COMPONENTS, "base", "micro_ros_espidf_component")
    if not config_obj.get("ROS_DISTRO_BASE_CLONED", False):
        Repo.clone_from(
            MICRO_ROS_REPO,
            base_dest,
            branch=config_obj["ROS_DISTRO"]
        )
        config_obj["ROS_DISTRO_BASE_CLONED"] = True

        for folder in [".git", ".github"]:
            dir_to_remove = os.path.join(base_dest, folder)
            if os.path.exists(dir_to_remove):
                shutil.rmtree(dir_to_remove)

        with open(GITIGNORE_PATH, "a+") as gitignore:
            gitignore.seek(0)
            existing = gitignore.read().splitlines()
            base_dest_ignore = base_dest[2:]
            if base_dest_ignore not in existing:
                gitignore.write(f"{base_dest_ignore}/\n")

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
    max_history = int(input("Max History: "))
    max_timer = int(input("Max Timers: "))
    
    replacements = {
        r"(-DRMW_UXRCE_MAX_PUBLISHERS=)\d+":               publisher_count,
        r"(-DRMW_UXRCE_MAX_SUBSCRIPTIONS=)\d+":            subscriber_count,
        r"(-DRMW_UXRCE_MAX_SERVICES=)\d+":                 service_count,
        r"(-DRMW_UXRCE_MAX_CLIENTS=)\d+":                  client_count,
        r"(-DRMW_UXRCE_MAX_HISTORY=)\d+":                  max_history,

        r"(-DERTPS_MAX_PUBLISHERS=)\d+":                   publisher_count,
        r"(-DERTPS_MAX_SUBSCRIPTIONS=)\d+":                subscriber_count,
        r"(-DERTPS_MAX_SERVICES=)\d+":                     service_count,
        r"(-DERTPS_MAX_CLIENTS=)\d+":                      client_count,
        r"(-DERTPS_MAX_HISTORY=)\d+":                      max_history,
    }

    mode = int(input(
"""1) UDP (WiFi)
2) Custom (Serial)
Select Mode (1 or 2): 
"""))
    
    component_code = f"micro_{mode}{publisher_count}{subscriber_count}{service_count}{client_count}{max_history}"
    project_component_path = os.path.join(project_path, "components", "micro_ros_espidf_component")
    rel_component_dest = os.path.join(MICRO_ROS_COMPONENTS, component_code, "micro_ros_espidf_component")
    component_dest = os.path.abspath(rel_component_dest)

    if not config_obj.get(component_code, False):
        shutil.copytree(base_dest, component_dest)

        with open(GITIGNORE_PATH, "a+") as gitignore:
            gitignore.seek(0)
            existing = gitignore.read().splitlines()

            rel_component_dest_ignore = rel_component_dest[2:]
            if rel_component_dest_ignore not in existing:
                gitignore.write(f"{rel_component_dest_ignore}/\n")

        with open(os.path.join(component_dest, "colcon.meta"), "r+") as f:
            text = f.read()

            for pattern, new_val in replacements.items():
                text = re.sub(pattern, fr"\g<1>{new_val}", text)
            f.seek(0)
            f.write(text)
            f.truncate()

        config_obj[component_code] = True

        json_file.seek(0)
        json.dump(config_obj, json_file, indent=4)
        json_file.truncate()

    os.symlink(component_dest, project_component_path)

    json_file.close()

    publisher_names = []
    publisher_Types = []

    for i in range(int(publisher_count)):
        publisher_names.append(input(f"Publisher{i} Name: "))


if __name__ == "__main__":
    main()
