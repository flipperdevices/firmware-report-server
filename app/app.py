import os
import re
import time
from functools import wraps
from typing import Dict, List, TypedDict

from marshmallow import Schema, fields
from apiflask import APIFlask
from flask import jsonify

from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import desc, func

from app.services.map_parser import parse_sections, save_parsed_data
from app.services.map_db_writer import insertHeader, insertData


app = Flask(__name__)

cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URI")

db = SQLAlchemy()
db.init_app(app)


class MapFileRequestSchema(Schema):
    map_file = fields.Raw(type='file', required=True)


def time_it(func):
    """decorator to time a function"""

    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(f"Function {func.__name__}{args} {kwargs} Took {total_time:.4f} seconds")
        return result

    return timeit_wrapper


def cache_it():
    """decorator to cache a function result"""
    d = {}

    def decorator(func):
        def new_func(param):
            if param not in d:
                d[param] = func(param)
            return d[param]

        return new_func

    return decorator


class Data(db.Model):  # type: ignore
    # +-----------+------------------+------+-----+---------+----------------+
    # | Field     | Type             | Null | Key | Default | Extra          |
    # +-----------+------------------+------+-----+---------+----------------+
    # | header_id | int(10) unsigned | NO   | MUL | NULL    |                |
    # | id        | int(10) unsigned | NO   | PRI | NULL    | auto_increment |
    # | section   | text             | NO   |     | NULL    |                |
    # | address   | text             | NO   |     | NULL    |                |
    # | size      | int(10) unsigned | NO   |     | NULL    |                |
    # | name      | text             | NO   |     | NULL    |                |
    # | lib       | text             | NO   |     | NULL    |                |
    # | obj_name  | text             | NO   |     | NULL    |                |
    # +-----------+------------------+------+-----+---------+----------------+

    __tablename__ = "data"
    header_id = db.Column(db.Integer, db.ForeignKey("header.id"))
    id = db.Column(db.Integer, primary_key=True, nullable=False, autoincrement=True)
    section = db.Column(db.Text, nullable=False)
    address = db.Column(db.Text, nullable=False)
    size = db.Column(db.Integer, nullable=False)
    name = db.Column(db.Text, nullable=False)
    lib = db.Column(db.Text, nullable=False)
    obj_name = db.Column(db.Text, nullable=False)

    @property
    def serialize(self):
        return {
            "header_id": self.header_id,
            "id": self.id,
            "section": self.section,
            "address": self.address,
            "size": self.size,
            "name": self.name,
            "lib": self.lib,
            "obj_name": self.obj_name,
        }


class DataTypedDict(TypedDict):
    header_id: int
    id: int
    address: str
    section: str
    size: int
    name: str
    lib: str
    obj_name: str


class Header(db.Model):  # type: ignore
    # +------------------+------------------+------+-----+---------+----------------+
    # | Field            | Type             | Null | Key | Default | Extra          |
    # +------------------+------------------+------+-----+---------+----------------+
    # | id               | int(10) unsigned | NO   | PRI | NULL    | auto_increment |
    # | datetime         | datetime         | NO   |     | NULL    |                |
    # | commit           | varchar(40)      | NO   |     | NULL    |                |
    # | commit_msg       | text             | NO   |     | NULL    |                |
    # | branch_name      | text             | NO   |     | NULL    |                |
    # | bss_size         | int(10) unsigned | NO   |     | NULL    |                |
    # | text_size        | int(10) unsigned | NO   |     | NULL    |                |
    # | rodata_size      | int(10) unsigned | NO   |     | NULL    |                |
    # | data_size        | int(10) unsigned | NO   |     | NULL    |                |
    # | free_flash_size  | int(10) unsigned | NO   |     | NULL    |                |
    # | pullrequest_id   | int(10) unsigned | YES  |     | NULL    |                |
    # | pullrequest_name | text             | YES  |     | NULL    |                |
    # +------------------+------------------+------+-----+---------+----------------+

    __tablename__ = "header"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    datetime = db.Column(db.DateTime, nullable=False, server_default=func.now())
    commit = db.Column(db.String(40), nullable=False)
    commit_msg = db.Column(db.Text, nullable=False)
    branch_name = db.Column(db.String(32), unique=False, nullable=False)
    bss_size = db.Column(db.Integer, nullable=False)
    text_size = db.Column(db.Integer, nullable=False)
    rodata_size = db.Column(db.Integer, nullable=False)
    data_size = db.Column(db.Integer, nullable=False)
    free_flash_size = db.Column(db.Integer, nullable=False)
    pullrequest_id = db.Column(db.Integer, nullable=True)
    pullrequest_name = db.Column(db.String(128), unique=False, nullable=True)

    @property
    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            "id": self.id,
            "datetime": self.datetime,
            "commit": self.commit,
            "commit_msg": self.commit_msg,
            "branch_name": self.branch_name,
            "bss_size": self.bss_size,
            "text_size": self.text_size,
            "rodata_size": self.rodata_size,
            "data_size": self.data_size,
            "free_flash_size": self.free_flash_size,
            "pullrequest_id": self.pullrequest_id,
            "pullrequest_name": self.pullrequest_name,
        }


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
            if not hash_key in self.hash:
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
            if not key in hashed_data1:
                hashed_data1[key] = hashed_data2[key].copy()
                hashed_data1[key]["size"] = 0

        # equalize the hashe2 with hash1
        for key in hashed_data1:
            if not key in hashed_data2:
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


def get_commits_by_branch_id(branch_id: int) -> List[DataTypedDict]:
    """Get all commits by branch id"""
    result = (
        Data.query.filter(Data.header_id == branch_id)
        .filter(Data.section.in_(INTERESTING_SECTIONS))
        .filter(Data.size > 0)
        .all()
    )
    return [row.serialize for row in result]


def minify_path(path: str):
    """Minify path to be more readable"""
    if "arm-none-eabi/" in path:
        return path.rsplit("arm-none-eabi/", 1)[1]
    else:
        return path.replace("build/f7-firmware-D/", "")


def flipper_path(lib, obj_name):
    """Make a readable path given that we have libraries"""
    lib = minify_path(lib)
    obj_name = minify_path(obj_name)
    if lib:
        lib = lib.rsplit(".a", 1)[0]
        lib = lib.rsplit("/lib", 1)
        lib = "/".join(lib)
        path = f"{lib}/{obj_name}"
    else:
        path = f"{obj_name}"
    return path


class Sections:
    def __init__(self, data: List[DataTypedDict]):
        self.sections = {}
        for entry in data:
            section = entry["section"]

            if not section in self.sections:
                self.sections[section] = {"size": 0, "objects": {}}
            current_section = self.sections[section]
            current_section["size"] += entry["size"]

            obj_name = flipper_path(entry["lib"], entry["obj_name"])
            if not obj_name in current_section["objects"]:
                current_section["objects"][obj_name] = {
                    "size": 0,
                    "symbols": {},
                }
            current_object = current_section["objects"][obj_name]
            current_object["size"] += entry["size"]

            symbol_name = entry["name"]
            if not symbol_name in current_object["symbols"]:
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

                if not part in current["next"]:
                    current["next"][part] = {"sections": {}, "next": {}}
                current = current["next"][part]

                if not section in current["sections"]:
                    current["sections"][section] = {
                        "size": 0,
                        "names": {},
                    }
                current_section = current["sections"][section]
                current_section["size"] += size

                if not name in current_section["names"]:
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

with app.app_context():
    db.create_all()

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
            if not username in pull_request_user_branches:
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
def api_v0_analyse_map_file():
    """Analyse map file"""
    if (map_file := request.files.get('map_file')) is None:
        return {"status": "error", "details": "Map file is required!"}, 400

    parsed_sections = parse_sections(map_file)
    # print(parsed_sections)
    save_parsed_data(parsed_sections, 'firmware.elf.map.all')

    from sqlalchemy import insert

    session = db.session

    # commit_hash = os.getenv("COMMIT_HASH")
    # commit_msg = os.getenv("COMMIT_MSG")
    # branch_name = os.getenv("BRANCH_NAME")
    # bss_size = os.getenv("BSS_SIZE")
    # text_size = os.getenv("TEXT_SIZE")
    # rodata_size = os.getenv("RODATA_SIZE")
    # data_size = os.getenv("DATA_SIZE")
    # free_flash_size = os.getenv("FREE_FLASH_SIZE")
    # pull_id = os.getenv("PULL_ID")
    # pull_name = os.getenv("PULL_NAME")

    # from datetime import datetime

    # header_new = Header(
    #     datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    #     commit=commit_hash,
    #     commit_msg=commit_msg,
    #     branch_name=branch_name,
    #     bss_size=bss_size,
    #     text_size=text_size,
    #     rodata_size=rodata_size,
    #     data_size=data_size,
    #     free_flash_size=free_flash_size,
    #     pullrequest_id=pull_id,
    #     pullrequest_name=pull_name
    # )
    # session.add(header_new)

    header_new = Data(
        section=section,
        address=address,
        size=size,
        name=name,
        lib=lib,
        obj_name=obj_name,
    )
    session.add(header_new)
    session.commit()

    # header_new = Header(
    #     datetime=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    #     commit=commit_hash,
    #     commit_msg=commit_msg,
    #     branch_name=branch_name,
    #     bss_size=bss_size,
    #     text_size=text_size,
    #     rodata_size=rodata_size,
    #     data_size=data_size,
    #     free_flash_size=free_flash_size,
    #     pullrequest_id=pull_id,
    #     pullrequest_name=pull_name
    # )
    # session.add(header_new)
    # session.commit()
    print(stmt)

    # header_id = insertHeader(parseEnv(), dbCurs, dbConn)
    # insertData(parseFile(reportFile, header_id), dbCurs, dbConn)

    return jsonify({"status": "Map file has been inserted!"})


@app.route("/api/v0/ping", methods=["GET"])
@cross_origin()
def api_v0_ping():
    """Ping"""
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(debug=True)
