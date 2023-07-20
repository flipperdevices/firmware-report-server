import os

import pytest

from app.app import app
from app.app import db


@pytest.fixture(scope='session')
def cli():
    client = app.test_client()
    client.environ_base['HTTP_AUTHORIZATION'] = 'Bearer ' + os.getenv('APP_AUTH_TOKEN')

    with app.app_context():
        db.drop_all()
        db.create_all()

    return client


@pytest.fixture(scope="class")
def prepare_input_map_file_data():
    data = {
        'branch_name': 'dev',
        'commit_hash': 'sdfvm432k423c2osdvgbers7t8ve35c0493i54v',
        'commit_msg': 'new commit',
        'pull_id': 1,
        'pull_name': 'push pr',
        "bss_size": 8200,
        "text_size": 547708,
        "rodata_size": 146240,
        "data_size": 1568,
        "free_flash_size": 352720,
    }
    return data
