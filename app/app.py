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

from app.models import DataTypedDict
from app.utils import flipper_path
from app.auth import validate_auth
from app.services.map_parser import parse_sections, save_parsed_data


app = Flask(__name__)

cors = CORS(app)
app.config["CORS_HEADERS"] = "Content-Type"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URI")


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


if __name__ == "__main__":
    app.run(debug=True)
