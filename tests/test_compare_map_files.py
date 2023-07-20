import os.path
from datetime import datetime
from pathlib import Path

from flask.testing import FlaskClient
from pytest import MonkeyPatch

from tests.source import map_mariadb_insert
from tests.source import map_parser
from app.app import Data, Header, session_scope, app


def test_analyse_map_file(cli: FlaskClient, prepare_input_map_file_data: dict):
    """
    Test to run the parser from an endpoint and save it to the database
    Args:
        cli: Server test client
        prepare_input_map_file_data: Prepared fields to be sent to the server

    Returns:
        Nothing
    """
    with open('tests/assets/firmware.elf.map', 'rb') as map_file_reader:
        response = cli.post(
            '/api/v0/map-file/analyse',
            data=prepare_input_map_file_data | {'map_file': map_file_reader},
        )
        assert response.status_code == 200

    with app.test_request_context():
        assert Header.query.filter(Header.id == 1).first() is not None
        assert len(Data.query.filter(Data.id == 1).all()) > 0


def test_run_map_parser(cli: FlaskClient, prepare_input_map_file_data: dict, tmp_path: Path, monkeypatch: MonkeyPatch):
    """
    Test to run the parser from a file and save it to the database
    Args:
        cli: Server test client
        prepare_input_map_file_data: Prepared fields to be sent to the server
        tmp_path: Temporary dir for parsed map file
        monkeypatch: Mocks

    Returns:
        Nothing
    """
    # Emulate
    # parse sections
    parsed_sections = map_parser.parse_sections('tests/assets/firmware.elf.map')

    # save file to temporary dir
    parsed_map_filename = 'firmware.elf.map.all'
    output_file = os.path.join(tmp_path, parsed_map_filename)
    map_parser.save_parsed_data(parsed_sections, output_file)

    # mock parse arguments with our data model
    def mocked_parse_args():
        class Arguments:
            db_user = 'root'
            db_pass = 'root'
            db_host = 'localhost'
            db_port = 3306
            db_name = 'amap_reports_test'
            report_file = output_file
        return Arguments()

    def mocked_parse_env():
        return [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            prepare_input_map_file_data['commit_hash'],
            prepare_input_map_file_data['commit_msg'],
            prepare_input_map_file_data['branch_name'],
            prepare_input_map_file_data['bss_size'],
            prepare_input_map_file_data['text_size'],
            prepare_input_map_file_data['rodata_size'],
            prepare_input_map_file_data['data_size'],
            prepare_input_map_file_data['free_flash_size'],
            prepare_input_map_file_data['pull_id'],
            prepare_input_map_file_data['pull_name'],
        ]

    monkeypatch.setattr("tests.source.map_mariadb_insert.parseArgs", mocked_parse_args)
    monkeypatch.setattr("tests.source.map_mariadb_insert.parseEnv", mocked_parse_env)

    # run save into mariadb
    map_mariadb_insert.main()

    with app.test_request_context():
        assert Header.query.filter(Header.id == 2).first() is not None
        assert len(Data.query.filter(Data.id == 2).all()) > 0


def test_compare_data(cli: FlaskClient, prepare_input_map_file_data: dict, monkeypatch: MonkeyPatch):

    with app.test_request_context():
        header_1 = Header.query.filter(Header.id == 1).first()
        header_2 = Header.query.filter(Header.id == 2).first()

        print(header_1.serialize)
        assert False
        # headers = session.query(Header).all()
        # assert len(headers) == 1
    # ...
    #
    # with app.test_request_context():
    #     session = db.session
    #     headers = session.query(Header).all()
    #
    # print(headers[0].serialize)
