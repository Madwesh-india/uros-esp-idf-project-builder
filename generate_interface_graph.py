#!/usr/bin/env python3
import os
import re
import json
import argparse
from collections import defaultdict

ARR_RE = re.compile(r'^(?P<base>.+?)\[\s*(?:<=\d+)?\s*\]$')
STR_RE = re.compile(r'^(?P<base>string|wstring)<=\s*(?P<max>\d+)$')
FIELD_RE = re.compile(r'^(?P<rawtype>[^\s#]+)\s+(?P<name>\w+)')

MSG_REGISTRY = {}

def split_modifiers(rawtype):
    m = ARR_RE.match(rawtype)
    if m:
        return m.group('base'), True
    if STR_RE.match(rawtype):
        return "string", False
    return rawtype, False

def parse_block(lines):
    d = {}
    for line in lines:
        raw = line.split('#', 1)[0].strip()
        if not raw:
            continue
        # Skip constant definitions (lines containing '=' in field decl)
        if '=' in raw:
            continue
        m = FIELD_RE.match(raw)
        if not m:
            continue
        base, arr = split_modifiers(m.group('rawtype'))
        entry = {"type": base, "array": arr}

        # If nested message type, attach its fields
        for full, nested in MSG_REGISTRY.items():
            if full.endswith(f"/{base}"):
                entry["fields"] = nested
                break

        d[m.group('name')] = entry
    return d

def find_interface_files(roots):
    files = []
    for root in roots:
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                if filename.endswith((".msg", ".srv", ".action")):
                    files.append(os.path.join(dirpath, filename))
    return files

def extract_package_name(path, roots):
    for root in roots:
        if path.startswith(root):
            rel = os.path.relpath(path, root)
            return rel.split(os.sep)[0]
    return "unknown_package"

def collect_interfaces(roots):
    interfaces = defaultdict(lambda: {"msg": {}, "srv": {}, "action": {}})

    # First pass: collect .msg
    for path in find_interface_files(roots):
        if not path.endswith(".msg"):
            continue
        pkg = extract_package_name(path, roots)
        name = os.path.splitext(os.path.basename(path))[0]
        with open(path) as f:
            lines = f.read().splitlines()
        full_name = f"{pkg}/{name}"
        MSG_REGISTRY[full_name] = parse_block(lines)

    # Second pass: parse all interfaces
    for path in find_interface_files(roots):
        pkg = extract_package_name(path, roots)
        kind = (
            "msg" if path.endswith(".msg") else
            "srv" if path.endswith(".srv") else
            "action"
        )
        name = os.path.splitext(os.path.basename(path))[0]

        with open(path) as f:
            lines = f.read().splitlines()

        if kind == "msg":
            interfaces[pkg][kind][name] = parse_block(lines)

        elif kind == "srv":
            if '---' in lines:
                i = lines.index('---')
                req, res = lines[:i], lines[i+1:]
            else:
                req, res = lines, []
            interfaces[pkg][kind][name] = {
                "request": parse_block(req),
                "response": parse_block(res)
            }

        elif kind == "action":
            sections = [[], [], []]
            section = 0
            for line in lines:
                if line.strip() == "---":
                    section += 1
                    continue
                if section < 3:
                    sections[section].append(line)
            interfaces[pkg][kind][name] = {
                "goal": parse_block(sections[0]),
                "result": parse_block(sections[1]),
                "feedback": parse_block(sections[2])
            }

    return interfaces

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse ROS .msg/.srv/.action files into nested JSON")
    parser.add_argument("--share-dir", action="append", required=True,
                        help="Can be specified multiple times: paths to 'install/share' or 'src/' folders")
    args = parser.parse_args()

    result = collect_interfaces(args.share_dir)
    with open("interface_graph.json", "w") as f:
        json.dump(result, f, indent=2)

    stats = {
        "messages": sum(len(v["msg"]) for v in result.values()),
        "services": sum(len(v["srv"]) for v in result.values()),
        "actions": sum(len(v["action"]) for v in result.values())
    }

    print(f"Wrote {stats['messages']} msgs, {stats['services']} srvs, {stats['actions']} actions → interface_graph.json")


# python3 generate_interface_graph.py     --share-dir PATH
