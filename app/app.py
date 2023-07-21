import os
import re
import time
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from typing import Dict, List, TypedDict

from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from flask_sqlalchemy import SQLAlchemy
from marshmallow import Schema, ValidationError, fields
from sqlalchemy.sql import desc, func

from app.authentication import validate_auth
from app.services.map_parser import parse_sections, save_parsed_data


app = Flask(__name__)

cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URI")

db = SQLAlchemy()
db.init_app(app)


@contextmanager
def session_scope():
    session = db.session
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


INTERESTING_SECTIONS = [
    ".isr_vector",
    ".text",
    ".rodata",
    ".fini_array",
    ".data",
    ".bss",
    ".stabstr",
    "MAPPING_TABLE",
    "MB_MEM1",
    "MB_MEM2",
]


class HashDataHelper:
    def hash_data(
        self, lib: str, obj_name: str, name: str, section: str
    ) -> DataTypedDict:
        value: DataTypedDict = {
            "header_id": 0,
            "id": 0,
            "section": section,
            "address": "",
            "size": 0,
            "name": name,
            "lib": lib,
            "obj_name": obj_name,
        }
        return value

    def hash_key(self, data: DataTypedDict) -> str:
        return f"{data['lib']}/{data['obj_name']}/{data['name']}/{data['section']}"


class HashData:
    def __init__(self, data: List[DataTypedDict]):
        self.hash = {}
        for d in data:
            lib = d["lib"]
            obj_name = d["obj_name"]
            name = d["name"]
            section = d["section"]
            size = d["size"]

            helper = HashDataHelper()
            hash_key = helper.hash_key(d)
            if hash_key not in self.hash:
                self.hash[hash_key] = helper.hash_data(lib, obj_name, name, section)
            self.hash[hash_key]["size"] += size

    def get_hashed_data(self) -> Dict[str, DataTypedDict]:
        return self.hash


class DiffHashData:
    def __init__(self, hash1: HashData, hash2: HashData):
        self.diff: List[DataTypedDict] = []
        hashed_data1 = hash1.get_hashed_data()
        hashed_data2 = hash2.get_hashed_data()

        # equalize the hashe1 with hash2
        for key in hashed_data2:
            if key not in hashed_data1:
                hashed_data1[key] = hashed_data2[key].copy()
                hashed_data1[key]["size"] = 0

        # equalize the hashe2 with hash1
        for key in hashed_data1:
            if key not in hashed_data2:
                hashed_data2[key] = hashed_data1[key].copy()
                hashed_data2[key]["size"] = 0

        # diff between the hashes
        for key in hashed_data1:
            hashed_data1[key]["size"] = (
                hashed_data1[key]["size"] - hashed_data2[key]["size"]
            )
            if hashed_data1[key]["size"] != 0:
                self.diff.append(hashed_data1[key])

    def get_diff(self) -> List[DataTypedDict]:
        return self.diff


class Sections:
    def __init__(self, data: List[DataTypedDict]):
        self.sections = {}
        for entry in data:
            section = entry["section"]

            if section not in self.sections:
                self.sections[section] = {"size": 0, "objects": {}}
            current_section = self.sections[section]
            current_section["size"] += entry["size"]

            obj_name = flipper_path(entry["lib"], entry["obj_name"])
            if obj_name not in current_section["objects"]:
                current_section["objects"][obj_name] = {
                    "size": 0,
                    "symbols": {},
                }
            current_object = current_section["objects"][obj_name]
            current_object["size"] += entry["size"]

            symbol_name = entry["name"]
            if symbol_name not in current_object["symbols"]:
                current_object["symbols"][symbol_name] = 0

            current_object["symbols"][symbol_name] += entry["size"]

    def get_sections(self):
        return self.sections


class Files:
    def __init__(self, data: List[DataTypedDict]):
        self.files = {"sections": {}, "next": {}}
        for d in data:
            path = flipper_path(d["lib"], d["obj_name"])
            name = d["name"]
            section = d["section"]
            size = d["size"]

            path_parts = path.split("/")
            current = self.files
            for part in path_parts:
                if part not in current["next"]:
                    current["next"][part] = {"sections": {}, "next": {}}
                current = current["next"][part]

                if section not in current["sections"]:
                    current["sections"][section] = {
                        "size": 0,
                        "names": {},
                    }
                current_section = current["sections"][section]
                current_section["size"] += size

                if name not in current_section["names"]:
                    current_section["names"][name] = 0
                current_section["names"][name] += size

        def tree_flatten(node, get_children, flatten_func, value_key, key=""):
            store = {"next": {}, value_key: node[value_key]}
            childrens = get_children(node)
            for child in childrens:
                if node[value_key] == childrens[child][value_key]:
                    key += "/" + child
                else:
                    key = child

                store["next"][key] = tree_flatten(
                    childrens[child], get_children, flatten_func, value_key, key
                )

            store = flatten_func(store, value_key)
            return store

        def next(node):
            return node["next"]

        def flatten(node, value_key):
            if node["next"] != {}:
                new_node = {}
                for first_key in node["next"]:
                    first_node = node["next"][first_key]
                    if first_node["next"] == {}:
                        new_node[first_key] = first_node
                        continue

                    second_key = list(first_node["next"].keys())[0]
                    second_node = first_node["next"][second_key]
                    if second_node[value_key] == first_node[value_key]:
                        new_node[second_key] = second_node
                        continue
                    else:
                        new_node[first_key] = first_node

                node["next"] = new_node

            return node

        self.files = tree_flatten(self.files, next, flatten, "sections")
        flatten(self.files, "sections")
        self.files = self.files["next"]

    def get_files(self):
        return self.files


@app.route("/api/v0/commit_diff_data", methods=["GET"])
@cross_origin()
def api_v0_commit_diff_data():
    """Get data that differs between two commits"""

    branch_ids = request.args.get("branch_ids")
    if not branch_ids:
        return jsonify({"error": "missing branch_ids"}), 400

    branch_ids = branch_ids.split(",")
    if len(branch_ids) != 2:
        return jsonify({"error": "branch_ids must be two"}), 400

    branch_id_current = int(branch_ids[0])
    branch_id_previous = int(branch_ids[1])
    hash_current = HashData(get_commits_by_branch_id(branch_id_current))
    hash_previous = HashData(get_commits_by_branch_id(branch_id_previous))
    diff = DiffHashData(hash_current, hash_previous)
    sections = Sections(diff.get_diff())
    files = Files(diff.get_diff())

    response = {
        "sections": sections.get_sections(),
        "files": files.get_files(),
    }
    return jsonify(response)


@app.route("/api/v0/commit_brief_data", methods=["GET"])
@cross_origin()
def api_v0_commit_brief_data():
    """Get brief commit data"""

    branch_id = request.args.get("branch_id")
    if branch_id is None:
        return jsonify({"error": "Missing branch_id"}), 400

    data = get_commits_by_branch_id(int(branch_id))
    sections = Sections(data)
    files = Files(data)

    response = {
        "sections": sections.get_sections(),
        "files": files.get_files(),
    }
    return jsonify(response)


@app.route("/api/v0/commit_full_data", methods=["GET"])
@cross_origin()
def api_v0_commit_full_data():
    """Get full commit data"""
    branch_id = request.args.get("branch_id")
    if branch_id is None:
        return jsonify({"error": "Missing branch_id"}), 400

    data = get_commits_by_branch_id(int(branch_id))
    return jsonify(data)


@app.route("/api/v0/branch", methods=["GET"])
@cross_origin()
def api_v0_branch():
    """
    Get branch info for dev,
    for other branches get last commit from branch
    and last commit from dev before date of last commit to branch
    """

    branch_name = request.args.get("branch_name")
    if branch_name is None:
        return jsonify({"error": "branch_name is required"}), 400

    headers = []
    if branch_name == "dev":
        dev_branch = (
            Header.query.filter(Header.branch_name == branch_name)
            .order_by(Header.datetime)
            .all()
        )
        headers = [h.serialize for h in dev_branch]
    else:
        # select last header for branch
        branch = (
            Header.query.filter(Header.branch_name == branch_name)
            .order_by(desc(Header.datetime))
            .limit(1)
        )

        # select latest header for dev before branch
        if branch.count() != 0:
            dev_branch = (
                Header.query.filter(Header.branch_name == "dev")
                .filter(Header.datetime < branch.first().datetime)
                .order_by(desc(Header.datetime))
                .limit(1)
            )

            if dev_branch.count() > 0:
                headers.append(dev_branch.first().serialize)
            headers.append(branch.first().serialize)

    return jsonify(headers)


@app.route("/api/v0/branches", methods=["GET"])
@cross_origin()
def api_v0_branches():
    """Get all branches, sorted by type"""
    session = db.session
    headers = (
        session.query(Header.branch_name, func.count(Header.branch_name))
        .order_by(Header.datetime)
        .group_by(Header.branch_name)
        .all()
    )

    main_branches = []
    release_branches = []
    release_candidate_branches = []
    misc_branches = []
    pull_request_user_branches = {}

    # example: 0.69.0
    release_pattern = re.compile(r"^\d+\.\d+\.\d+$")
    # example: 0.69.0-rc
    release_candidate_pattern = re.compile(r"^\d+\.\d+\.\d+-rc$")

    for header in headers:
        name = header[0]
        count = header[1]

        if name == "dev":
            main_branches.append({"branch_name": name, "count": count})
        elif release_pattern.match(name):
            release_branches.append({"branch_name": name, "count": count})
        elif release_candidate_pattern.match(name):
            release_candidate_branches.append({"branch_name": name, "count": count})
        elif "/" in name:
            username, _ = name.split("/", 1)
            if username not in pull_request_user_branches:
                pull_request_user_branches[username] = {"branches": [], "count": 0}

            pull_request_user_branches[username]["branches"].append(
                {"branch_name": name, "count": count}
            )
        else:
            misc_branches.append({"branch_name": name, "count": count})

    for pull_request_user_branch in pull_request_user_branches:
        pull_request_user_branches[pull_request_user_branch]["count"] = len(
            pull_request_user_branches[pull_request_user_branch]["branches"]
        )

    return jsonify(
        {
            "main_branches": main_branches,
            "release_branches": release_branches,
            "release_candidate_branches": release_candidate_branches,
            "misc_branches": misc_branches,
            "pull_request_user_branches": pull_request_user_branches,
        }
    )


@app.route("/api/v0/map-file/analyse", methods=["POST"])
@cross_origin()
@validate_auth
def api_v0_analyse_map_file():
    """Analyse map file"""
    try:
        result = MapFileRequestSchema().load(request.form)
    except ValidationError as err:
        return jsonify(err.messages), 400

    if (map_file := request.files.get("map_file")) is None:
        return {"map_file": ["Missing data for required field."]}, 400

    parsed_sections = parse_sections(map_file)
    parsed_sections = save_parsed_data(parsed_sections)

    with session_scope() as session:
        header_new = Header(
            datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            commit=result["commit_hash"],
            commit_msg=result["commit_msg"],
            branch_name=result["branch_name"],
            bss_size=result["bss_size"],
            text_size=result["text_size"],
            rodata_size=result["rodata_size"],
            data_size=result["data_size"],
            free_flash_size=result["free_flash_size"],
            pullrequest_id=result["pull_id"],
            pullrequest_name=result["pull_name"],
        )
        session.add(header_new)
        session.flush()

        for parsed_section in parsed_sections:
            data = Data(
                header_id=header_new.id,
                section=parsed_section["section_name"],
                address=parsed_section["address"],
                size=parsed_section["size"],
                name=parsed_section["demangled_name"],
                lib=parsed_section["module_name"],
                obj_name=parsed_section["file_name"],
            )
            session.add(data)

    return jsonify({"status": "ok"})


@app.route("/api/v0/ping", methods=["GET"])
@cross_origin()
def api_v0_ping():
    """Ping"""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True)
