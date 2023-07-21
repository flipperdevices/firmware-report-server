

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
