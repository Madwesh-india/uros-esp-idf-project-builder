#!/usr/bin/env python3
import sys
import os
import re
import json
import shutil
from git import Repo

# Constants
TEMPLATE_PATH            = "./uRosTemplet"
MICRO_ROS_REPO           = "https://github.com/micro-ROS/micro_ros_espidf_component.git"
CONFIG_FILE              = "./uros_components_config.json"
MICRO_ROS_COMPONENTS     = "./uros_components"
GITIGNORE_PATH           = "./.gitignore"
INTERFACE_GRAPH_PATH     = "./interface_graph.json"
ADDITIONAL_CODES_PATH    = "./rclc_templet_init.json"

# Modes
UDP    = 1
CUSTOM = 2

# Replacement patterns for colcon.meta
REPLACEMENT_TEMPLATES = {
    'transport':      r"(-DRMW_UXRCE_TRANSPORT=)(\w+)",
    'publishers':     r"(-DRMW_UXRCE_MAX_PUBLISHERS=)\d+",
    'subscriptions':  r"(-DRMW_UXRCE_MAX_SUBSCRIPTIONS=)\d+",
    'services':       r"(-DRMW_UXRCE_MAX_SERVICES=)\d+",
    'clients':        r"(-DRMW_UXRCE_MAX_CLIENTS=)\d+",
    'history':        r"(-DRMW_UXRCE_MAX_HISTORY=)\d+",
    'ertps_pub':      r"(-DERTPS_MAX_PUBLISHERS=)\d+",
    'ertps_sub':      r"(-DERTPS_MAX_SUBSCRIPTIONS=)\d+",
    'ertps_srv':      r"(-DERTPS_MAX_SERVICES=)\d+",
    'ertps_cli':      r"(-DERTPS_MAX_CLIENTS=)\d+",
    'ertps_hist':     r"(-DERTPS_MAX_HISTORY=)\d+",
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
        for i, pkg in enumerate(pkg_list, 1):
            print(f"  {i}) {pkg}")
        pidx = int(input("Select package: ")) - 1
        pkg = pkg_list[pidx]

        msgs = list(interface_graph[pkg]['msg'].keys())
        for i, m in enumerate(msgs, 1):
            print(f"    {i}) {m}")
        midx = int(input("Select message type: ")) - 1

        qos = None
        while qos not in ('b', 'r'):
            qos = input("QoS (b = BestEffort, r = Reliable): ").lower()

        qos_str = 'best_effort' if qos == 'b' else 'default'
        pubs.append((name, f"{pkg}/msg/{msgs[midx]}", qos_str))
    return pubs


def prompt_subscriptions(interface_graph, details):
    sub = []
    print("\nDefine your subscriptions:")
    pkg_list = [k for k,v in interface_graph.items() if v.get('msg')]
    for idx in range(details['subscriber_count']):
        name = input(f" Subscription {idx+1} name: ")
        for i, pkg in enumerate(pkg_list, 1):
            print(f"  {i}) {pkg}")
        pidx = int(input("Select package: ")) - 1
        pkg = pkg_list[pidx]

        msgs = list(interface_graph[pkg]['msg'].keys())
        for i, m in enumerate(msgs, 1):
            print(f"    {i}) {m}")
        midx = int(input("Select message type: ")) - 1

        qos = None
        while qos not in ('b', 'r'):
            qos = input("QoS (b = BestEffort, r = Reliable): ").lower()

        qos_str = 'best_effort' if qos == 'b' else 'default'
        sub.append((name, f"{pkg}/msg/{msgs[midx]}", qos_str))
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

def load_additional_templates(path=ADDITIONAL_CODES_PATH):
    if not os.path.exists(path):
        print(f"Error: templates not found at {path}")
        sys.exit(1)
    with open(path, 'r') as f:
        return json.load(f)

def fill_template(template: str, mapping: dict) -> str:
    """Replace each <||Key||> in `template` with mapping[Key]."""
    def repl(m):
        key = m.group(1)
        return str(mapping.get(key, f"<unknown:{key}>"))
    return re.sub(r'<\|\|(.+?)\|\|>', repl, template)

def generate_init_and_callback_codes(
    publishers, subscriptions, services, clients, timers
):
    tpl = load_additional_templates()
    # include a new key 'var_decls' for all declarations
    codes = {k: [] for k in (
        'var_decls',
        'pub_inits','pub_calls',
        'sub_inits','sub_adds','sub_callbacks',
        'srv_inits','srv_adds','srv_callbacks',
        'cli_inits','cli_sends','cli_takes',
        'timer_inits','timer_adds','timer_callbacks'
    )}

    # Optional: track data_variable_declarations
    data_variable_declarations = {}

    # --- Publishers ---
    for name, msg_type, reliability in publishers:
        handler    = f"{name}_publisher"
        msg_var    = f"{name}_msg"
        base_type  = transform_variable(msg_type)
        # 1) declare handler and msg variable
        codes['var_decls'].append(f"rcl_publisher_t   {handler};")
        codes['var_decls'].append(f"{base_type} {msg_var};")
        # 2) track data_variable_declarations
        key = transform_variable(msg_type)
        data_variable_declarations.setdefault(key, []).append(msg_var)
        # 3) init & publish templates
        mapping = {
            "HandlerObject": handler,
            "TopicName":     name,
            "TopicType":     base_type,
            "TopicTypeComa": msg_type.replace('/', ', '),
            "MsgName":       msg_var,
            "Reliability":   reliability
        }
        codes['pub_inits'].append(
            fill_template(tpl['rcl_publisher_t'], mapping)
        )
        codes['pub_calls'].append(
            fill_template(tpl['publish_data'], mapping)
        )

    # --- Subscriptions ---
    for name, msg_type, reliability in subscriptions:
        handler   = f"{name}_subscription"
        msg_var   = f"{name}_msg"
        cb_name   = f"{name}_callback"
        base_type = transform_variable(msg_type)
        codes['var_decls'].append(f"rcl_subscription_t {handler};")
        codes['var_decls'].append(f"{base_type} {msg_var};")
        key = transform_variable(msg_type)
        data_variable_declarations.setdefault(key, []).append(msg_var)
        mapping = {
            "HandlerObject": handler,
            "TopicName":     name,
            "TopicType":     base_type,
            "TopicTypeComa": msg_type.replace('/', ', '),
            "MsgName":       msg_var,
            "CallBackName":  cb_name,
            "Reliability":   reliability
        }
        codes['sub_inits'].append(
            fill_template(tpl['rcl_subscription_t'], mapping)
        )
        codes['sub_adds'].append(
            fill_template(tpl['handler_subscription'], mapping)
        )
        codes['sub_callbacks'].append(
            fill_template(tpl['call_back_subscription'], mapping)
        )

    # --- Services ---
    for name, srv_type in services:
        handler  = f"{name}_service"
        req_var  = f"{name}_request"
        res_var  = f"{name}_response"
        cb_name  = f"{name}_srv_callback"
        # declare service and request/response vars
        codes['var_decls'].append(f"rcl_service_t    {handler};")
        codes['var_decls'].append(
            f"{srv_type.replace('/', '__')}_Request  {req_var};"
        )
        codes['var_decls'].append(
            f"{srv_type.replace('/', '__')}_Response {res_var};"
        )
        key = transform_variable(srv_type)
        data_variable_declarations.setdefault(key, []).extend(
            [req_var, res_var]
        )
        mapping = {
            "HandlerObject": handler,
            "ServiceName":   name,
            "ServiceType":   transform_variable(srv_type),
            "ServiceTypeComa":   srv_type.replace('/', ', '),
            "RequestMsg":    req_var,
            "ResponseMsg":   res_var,
            "CallBackName":  cb_name
        }
        codes['srv_inits'].append(
            fill_template(tpl['rcl_service_t'], mapping)
        )
        codes['srv_adds'].append(
            fill_template(tpl['handler_service'], mapping)
        )
        codes['srv_callbacks'].append(
            fill_template(tpl['call_back_service'], mapping)
        )

    # --- Clients ---
    for name, srv_type in clients:
        handler  = f"{name}_client"
        req_var  = f"{name}_request"
        res_var  = f"{name}_response"
        # declare client and request/response
        codes['var_decls'].append(f"rcl_client_t     {handler};")
        codes['var_decls'].append(
            f"{srv_type.replace('/', '__')}_Request  {req_var};"
        )
        codes['var_decls'].append(
            f"{srv_type.replace('/', '__')}_Response {res_var};"
        )
        key = transform_variable(srv_type)
        data_variable_declarations.setdefault(key, []).extend(
            [req_var, res_var]
        )
        mapping = {
            "HandlerObject": handler,
            "ServiceName":   name,
            "ServiceType":   srv_type,
            "ServiceTypeComa":   srv_type.replace('/', ', '),
            "RequestMsg":    req_var,
            "ResponseMsg":   res_var
        }
        codes['cli_inits'].append(
            fill_template(tpl['rcl_client_t'], mapping)
        )
        codes['cli_sends'].append(
            fill_template(tpl['client_send'], mapping)
        )
        codes['cli_takes'].append(
            fill_template(tpl['client_take'], mapping)
        )

    # --- Timers ---
    for name, rate in timers:
        handler = f"{name}_timer"
        cb_name = f"{name}_timer_callback"
        codes['var_decls'].append(f"rcl_timer_t      {handler};")
        mapping = {
            "HandlerObject": handler,
            "TimerRate":     rate,
            "CallBackName":  cb_name
        }
        codes['timer_inits'].append(
            fill_template(tpl['rcl_timer_t'], mapping)
        )
        codes['timer_adds'].append(
            fill_template(tpl['handler_timer'], mapping)
        )
        codes['timer_callbacks'].append(
            fill_template(tpl['call_back_timer'], mapping)
        )

    # return both the code snippets and the data-variable map
    codes['data_vars'] = data_variable_declarations
    return codes

def apply_code_blocks_to_c(
    project_path: str,
    code_blocks: dict,
    required_imports: list[str],
    details: dict
):
    """
    Reads TEMPLATE_PATH/main/main.c, replaces placeholders, and writes to
    <project_path>/main/main.c
    """
    # 1) Load the template
    template_file = os.path.join(TEMPLATE_PATH, "main", "main.c")
    if not os.path.exists(template_file):
        raise FileNotFoundError(f"Template not found: {template_file}")
    with open(template_file, 'r') as f:
        content = f.read()

    # 2) Build replacement mapping
    # a) Convert import paths into #include lines
    headers_block = "\n".join(f'#include "{hdr}"' for hdr in required_imports)

    # b) Other named placeholders:
    mapping = {
        "Headers":            headers_block,
        "Variables":          "\n".join(   code_blocks.get("var_decls", [])),
        "Callbacks":          "\n\n".join(code_blocks.get("sub_callbacks", [])
                                         + code_blocks.get("srv_callbacks", [])
                                         + code_blocks.get("timer_callbacks", [])),
        "InitializingThings": "\n\n".join(code_blocks.get("pub_inits", [])
                                         + code_blocks.get("sub_inits", [])
                                         + code_blocks.get("srv_inits", [])
                                         + code_blocks.get("cli_inits", [])
                                         + code_blocks.get("timer_inits", [])),
        "AddCallbacks":       "\n".join(code_blocks.get("sub_adds", [])
                                         + code_blocks.get("srv_adds", [])
                                         + code_blocks.get("timer_adds", [])),
        "ExamplePublish":     "\n\n".join(code_blocks.get("pub_calls", [])
                                         + code_blocks.get("cli_sends", [])
                                         + code_blocks.get("cli_takes", [])),
        "Tasks":              "\n".join(code_blocks.get("task_callbacks", [])),
        # Also fill in nodename/namespace
        "Nodename":           details.get("node_name", "node"),
        "Namespace":          details.get("namespace", "")
    }

    # 3) Replace each <||Key||> in the template
    def repl(m):
        key = m.group(1)
        return mapping.get(key, f"<MISSING:{key}>")
    result = re.sub(r'<\|\|(.+?)\|\|>', repl, content)

    # 4) Write out to the project folder under main/main.c
    out_dir = os.path.join(project_path, "main")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "main.c")
    with open(out_file, 'w') as f:
        f.write(result)

    print(f"Generated main.c → {out_file}")


def main():
    # 1) Load config & interface graph
    config          = load_or_init_config()
    interface_graph = load_interface_graph()

    # 2) Prompt for ROS distro if missing
    if 'ROS_DISTRO' not in config:
        config['ROS_DISTRO'] = input("Enter ROS 2 distribution: ")
        save_config(config)

    # 3) Clone base micro-ROS component (once per distro)
    base_dest = clone_base_component(config)
    save_config(config)

    # 4) Project skeleton
    target_dir   = prompt_target_and_create()
    details      = prompt_project_details()
    project_path = copy_template(target_dir, details['project_name'])

    # 5) Prepare (and cache) custom component variant
    comp_dest, _ = prepare_component(config, base_dest, details)
    link_component(project_path, comp_dest)
    save_config(config)

    # 6) Prompt for all your ROS 2 entities
    pubs = prompt_publishers(   interface_graph, details)
    subs = prompt_subscriptions(interface_graph, details)
    srvs = prompt_services(     interface_graph, details)
    clis = prompt_clients(      interface_graph, details)
    tmrs = prompt_timers(       details)

    # 7) Generate all rclc init/callback snippets
    code_blocks = generate_init_and_callback_codes(pubs, subs, srvs, clis, tmrs)

    # 8) Collect all required C headers from your topics/services/actions
    required_imports = []
    for name, typ, *_ in pubs + subs:
        required_imports.append(transform_path(typ))
    for name, typ in srvs + clis:
        required_imports.append(transform_path(typ))
    required_imports = sorted(set(required_imports))

    # 9) Render main.c with everything in place
    apply_code_blocks_to_c(
        project_path=project_path,
        code_blocks=code_blocks,
        required_imports=required_imports,
        details=details
    )


if __name__ == '__main__':
    main()
