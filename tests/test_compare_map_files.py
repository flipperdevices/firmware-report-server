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
        header_1 = Header.query.filter(Header.id == 1).first().serialize
        header_2 = Header.query.filter(Header.id == 2).first().serialize

        assert header_1['commit'] == header_2['commit']
        assert header_1['commit_msg'] == header_2['commit_msg']
        assert header_1['branch_name'] == header_2['branch_name']
        assert header_1['bss_size'] == header_2['bss_size']
        assert header_1['text_size'] == header_2['text_size']
        assert header_1['rodata_size'] == header_2['rodata_size']
        assert header_1['data_size'] == header_2['data_size']
        assert header_1['free_flash_size'] == header_2['free_flash_size']
        assert header_1['pullrequest_id'] == header_2['pullrequest_id']
        assert header_1['pullrequest_name'] == header_2['pullrequest_name']

        data_1 = Data.query.filter(Data.id == 1).all()
        data_2 = Data.query.filter(Data.id == 2).all()

        assert len(data_1) == len(data_2)

        for i in range(len(data_1)):
            assert data_1[i].serialize['section'] == data_2[i].serialize['section']
            assert data_1[i].serialize['address'] == data_2[i].serialize['address']
            assert data_1[i].serialize['size'] == data_2[i].serialize['size']
            assert data_1[i].serialize['name'] == data_2[i].serialize['name']
            assert data_1[i].serialize['lib'] == data_2[i].serialize['lib']
            assert data_1[i].serialize['obj_name'] == data_2[i].serialize['obj_name']
