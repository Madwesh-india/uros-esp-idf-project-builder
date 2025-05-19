#!/usr/bin/env python3
import sys
import os
import re
import json
import shutil
from git import Repo

# Constants
TEMPLATE_PATH = "./uRosTemplet"
MICRO_ROS_REPO = "https://github.com/micro-ROS/micro_ros_espidf_component.git"
CONFIG_FILE = "./uros_components_config.json"
MICRO_ROS_COMPONENTS = "./uros_components"
GITIGNORE_PATH = "./.gitignore"
INTERFACE_GRAPH_PATH = "./interface_graph.json"

# Modes
UDP = 1
CUSTOM = 2

# Replacement patterns
REPLACEMENT_TEMPLATES = {
    'transport': r"(-DRMW_UXRCE_TRANSPORT=)(\w+)",
    'publishers': r"(-DRMW_UXRCE_MAX_PUBLISHERS=)\d+",
    'subscriptions': r"(-DRMW_UXRCE_MAX_SUBSCRIPTIONS=)\d+",
    'services': r"(-DRMW_UXRCE_MAX_SERVICES=)\d+",
    'clients': r"(-DRMW_UXRCE_MAX_CLIENTS=)\d+",
    'history': r"(-DRMW_UXRCE_MAX_HISTORY=)\d+",
    'ertps_pub': r"(-DERTPS_MAX_PUBLISHERS=)\d+",
    'ertps_sub': r"(-DERTPS_MAX_SUBSCRIPTIONS=)\d+",
    'ertps_srv': r"(-DERTPS_MAX_SERVICES=)\d+",
    'ertps_cli': r"(-DERTPS_MAX_CLIENTS=)\d+",
    'ertps_hist': r"(-DERTPS_MAX_HISTORY=)\d+",
}


def load_or_init_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w') as f:
            json.dump({}, f, indent=4)
    with open(CONFIG_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)


def load_interface_graph():
    if not os.path.exists(INTERFACE_GRAPH_PATH):
        print(f"Error: Interface graph not found at {INTERFACE_GRAPH_PATH}")
        sys.exit(1)
    with open(INTERFACE_GRAPH_PATH, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print("Error: Failed to parse interface graph JSON.")
            sys.exit(1)


def update_gitignore(path_entry):
    os.makedirs(os.path.dirname(GITIGNORE_PATH), exist_ok=True)
    with open(GITIGNORE_PATH, 'a+') as gi:
        gi.seek(0)
        lines = gi.read().splitlines()
        if path_entry not in lines:
            gi.write(f"{path_entry}/\n")


def clone_base_component(config):
    base_dest = os.path.join(MICRO_ROS_COMPONENTS, 'base', 'micro_ros_espidf_component')
    if not config.get('ROS_DISTRO_BASE_CLONED', False):
        print("Cloning micro-ROS base component...")
        Repo.clone_from(MICRO_ROS_REPO, base_dest, branch=config['ROS_DISTRO'])
        # remove git metadata
        for d in ['.git', '.github']:
            p = os.path.join(base_dest, d)
            if os.path.exists(p):
                shutil.rmtree(p)
        update_gitignore(os.path.relpath(base_dest))
        config['ROS_DISTRO_BASE_CLONED'] = True
    return base_dest


def prompt_target_and_create():
    target = input("Enter target directory (will create if missing): ")
    tgt = os.path.expanduser(target)
    os.makedirs(tgt, exist_ok=True)
    return tgt


def copy_template(tgt, project_name):
    project_path = os.path.join(tgt, project_name)
    if os.path.exists(project_path):
        print(f"Error: Project '{project_path}' already exists.")
        sys.exit(1)
    shutil.copytree(TEMPLATE_PATH, project_path)
    print(f"Template copied to {project_path}")
    return project_path


def prompt_project_details():
    details = {}
    details['project_name'] = input("Project Name: ")
    details['node_name'] = input("Node Name: ")
    details['namespace'] = input("Namespace: ")
    details['publisher_count'] = int(input("Number of publishers: "))
    details['subscriber_count'] = int(input("Number of subscribers: "))
    details['service_count'] = int(input("Number of services: "))
    details['client_count'] = int(input("Number of clients: "))
    details['max_history'] = int(input("Max history: "))
    details['max_timers'] = int(input("Max timers: "))
    mode = None
    while mode not in (UDP, CUSTOM):
        mode = int(input("Mode (1=UDP, 2=Custom): "))
    details['mode'] = mode
    return details


def generate_component_code(details):
    return f"micro_{details['mode']}{details['publisher_count']}{details['subscriber_count']}{details['service_count']}{details['client_count']}{details['max_history']}"


def prepare_component(config, base_dest, details):
    comp_code = generate_component_code(details)
    rel_dest = os.path.join(MICRO_ROS_COMPONENTS, comp_code, 'micro_ros_espidf_component')
    abs_dest = os.path.abspath(rel_dest)
    if not config.get(comp_code, False):
        shutil.copytree(base_dest, abs_dest)
        update_gitignore(os.path.relpath(abs_dest))
        # edit colcon.meta
        meta_path = os.path.join(abs_dest, 'colcon.meta')
        text = open(meta_path).read()
        repls = {
            REPLACEMENT_TEMPLATES['transport']: ('custom' if details['mode']==CUSTOM else 'udp'),
            REPLACEMENT_TEMPLATES['publishers']: details['publisher_count'],
            REPLACEMENT_TEMPLATES['subscriptions']: details['subscriber_count'],
            REPLACEMENT_TEMPLATES['services']: details['service_count'],
            REPLACEMENT_TEMPLATES['clients']: details['client_count'],
            REPLACEMENT_TEMPLATES['history']: details['max_history'],
            REPLACEMENT_TEMPLATES['ertps_pub']: details['publisher_count'],
            REPLACEMENT_TEMPLATES['ertps_sub']: details['subscriber_count'],
            REPLACEMENT_TEMPLATES['ertps_srv']: details['service_count'],
            REPLACEMENT_TEMPLATES['ertps_cli']: details['client_count'],
            REPLACEMENT_TEMPLATES['ertps_hist']: details['max_history'],
        }
        for pat, val in repls.items():
            text = re.sub(pat, fr"\g<1>{val}", text)
        with open(meta_path, 'w') as mf:
            mf.write(text)
        config[comp_code] = True
    return abs_dest, comp_code


def link_component(project_path, comp_dest):
    link_path = os.path.join(project_path, 'components', 'micro_ros_espidf_component')
    os.makedirs(os.path.dirname(link_path), exist_ok=True)
    if not os.path.exists(link_path):
        os.symlink(comp_dest, link_path)
        print(f"Linked component at {link_path}")


def prompt_publishers(interface_graph, details):
    pubs = []
    print("\nDefine your publishers:")
    pkg_list = [k for k,v in interface_graph.items() if v.get('msg')]
    for idx in range(details['publisher_count']):
        name = input(f" Publisher {idx+1} name: ")
        for i,pkg in enumerate(pkg_list,1): print(f"  {i}) {pkg}")
        pidx = int(input("Select package: "))-1
        pkg = pkg_list[pidx]
        msgs = list(interface_graph[pkg]['msg'].keys())
        for i,m in enumerate(msgs,1): print(f"    {i}) {m}")
        midx = int(input("Select message type: "))-1
        pubs.append((name, f"{pkg}/msg/{msgs[midx]}"))
    return pubs


def prompt_subscriptions(interface_graph, details):
    sub = []
    print("\nDefine your subscriptions:")
    pkg_list = [k for k,v in interface_graph.items() if v.get('msg')]
    for idx in range(details['subscriber_count']):
        name = input(f" Subscription {idx+1} name: ")
        for i,pkg in enumerate(pkg_list,1): print(f"  {i}) {pkg}")
        pidx = int(input("Select package: "))-1
        pkg = pkg_list[pidx]
        msgs = list(interface_graph[pkg]['msg'].keys())
        for i,m in enumerate(msgs,1): print(f"    {i}) {m}")
        midx = int(input("Select message type: "))-1
        sub.append((name, f"{pkg}/msg/{msgs[midx]}"))
    return sub

def prompt_services(interface_graph, details):
    srvs = []
    print("\nDefine your services:")
    pkg_list = [k for k, v in interface_graph.items() if v.get('srv')]
    for idx in range(details['service_count']):
        name = input(f" Service {idx+1} name: ")
        for i, pkg in enumerate(pkg_list, 1):
            print(f"  {i}) {pkg}")
        pidx = int(input("Select package: ")) - 1
        pkg = pkg_list[pidx]
        srvs_list = list(interface_graph[pkg]['srv'].keys())
        for i, s in enumerate(srvs_list, 1):
            print(f"    {i}) {s}")
        sidx = int(input("Select service type: ")) - 1
        srvs.append((name, f"{pkg}/srv/{srvs_list[sidx]}"))
    return srvs

def prompt_clients(interface_graph, details):
    clis = []
    print("\nDefine your clients:")
    pkg_list = [k for k, v in interface_graph.items() if v.get('srv')]
    for idx in range(details['client_count']):
        name = input(f" Client {idx+1} name: ")
        for i, pkg in enumerate(pkg_list, 1):
            print(f"  {i}) {pkg}")
        pidx = int(input("Select package: ")) - 1
        pkg = pkg_list[pidx]
        srvs_list = list(interface_graph[pkg]['srv'].keys())
        for i, s in enumerate(srvs_list, 1):
            print(f"    {i}) {s}")
        sidx = int(input("Select service type: ")) - 1
        clis.append((name, f"{pkg}/srv/{srvs_list[sidx]}"))
    return clis


def prompt_timers(details):
    timers = []
    print("\nDefine your timers:")
    for idx in range(details['max_timers']):
        name = input(f" Timer {idx+1} name: ")
        rate = float(input(f" Timer {idx+1} rate (Hz): "))
        timers.append((name, rate))
    return timers

def transform_path(input_str):
    parts = input_str.strip().split('/')
    if len(parts) != 3:
        raise ValueError("Input must be in the form 'value1/value2/value3'")

    head, mid, tail = parts

    # Convert tail to snake_case with leading capitals converted to _x
    tail_snake = re.sub(r'(?<!^)([A-Z])', r'_\1', tail).lower()

    return f"{head}/{mid}/{tail_snake}.h"

def transform_variable(input_str):
    parts = input_str.strip().split('/')
    if len(parts) != 3:
        raise ValueError("Input must be in the form 'value1/value2/value3'")

    head, mid, tail = parts
    return f"{head}__{mid}__{tail}"

def main():
    config = load_or_init_config()
    interface_graph = load_interface_graph()

    if 'ROS_DISTRO' not in config:
        config['ROS_DISTRO'] = input("Enter ROS 2 distribution: ")
    save_config(config)

    base_dest = clone_base_component(config)
    save_config(config)

    target_dir = prompt_target_and_create()
    details = prompt_project_details()
    project_path = copy_template(target_dir, details['project_name'])

    comp_dest, comp_code = prepare_component(config, base_dest, details)
    link_component(project_path, comp_dest)
    save_config(config)

    publishers = prompt_publishers(interface_graph, details)
    subscriptions = prompt_subscriptions(interface_graph, details)
    services = prompt_services(interface_graph, details)
    clients = prompt_clients(interface_graph, details)
    timers = prompt_timers(details)
    
    print("\nConfigured publishers:", publishers)
    print("\nConfigured subscriptions:", subscriptions)
    print("\nConfigured services:", services)
    print("\nConfigured clients:", clients)
    print("\nConfigured timers:", timers)

    requied_imports = []
    variable_declarations = []

    for imports in [*publishers, *subscriptions, *services, *clients]:
        requied_imports.append(transform_path(imports[1]))

    


if __name__ == '__main__':
    main()
