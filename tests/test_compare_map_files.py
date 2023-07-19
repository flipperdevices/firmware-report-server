

def test_compare_map_files(cli):
    with open('tests/assets/firmware.elf.map', 'rb') as map_file_reader:
        response = cli.post(
            '/api/v0/map-file/analyse',
            data={
                "name": "Games",
                "color": "A5F4BE",
                "priority": 1,
                'map_file': (map_file_reader.read(), 'firmware.elf.map'),
            },
        )
        print(response.data)
        assert response.status_code == 200
