import os

import pytest
from flask import Flask

from app.app import app
# # Override databases
# motor_client = AsyncIOMotorClient(MONGO_TEST_URI)
# db = motor_client[MONGO_TEST_URI.split("/")[-1]]


TEST_AUTH_TOKEN = "*"


# @pytest.fixture()
# def app():
# #     app = app
# #     # app = Flask(__name__)
# #     # app.config.update({
# #     #     "TESTING": True,
# #     #     "SQLALCHEMY_DATABASE_URI": os.environ.get("DATABASE_URI")
# #     # })
#     yield app


@pytest.fixture()
def cli():
    client = app.test_client()
    client.environ_base['HTTP_AUTHORIZATION'] = 'Bearer ' + TEST_AUTH_TOKEN
    return client


@pytest.fixture(scope="class")
def prepare_input_map_file_data():
    data = {
        "bss_size": 8200,
        "text_size": 547708,
        "rodata_size": 146240,
        "data_size": 1568,
        "free_flash_size": 352720,
    }
    return data
