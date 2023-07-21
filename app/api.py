import re
from datetime import datetime

from flask import jsonify, request
from flask_cors import cross_origin
from marshmallow import ValidationError
from sqlalchemy.sql import desc, func

from app.auth import validate_auth
from app.services.map_parser import parse_sections, save_parsed_data


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
