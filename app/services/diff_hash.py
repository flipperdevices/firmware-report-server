from app.models import DataTypedDict


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
    def __init__(self, data: list[DataTypedDict]):
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

    def get_hashed_data(self) -> dict[str, DataTypedDict]:
        return self.hash


class DiffHashData:
    def __init__(self, hash1: HashData, hash2: HashData):
        self.diff: list[DataTypedDict] = []
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

    def get_diff(self) -> list[DataTypedDict]:
        return self.diff
