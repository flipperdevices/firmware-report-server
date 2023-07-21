

class DataTypedDict(TypedDict):
    header_id: int
    id: int
    address: str
    section: str
    size: int
    name: str
    lib: str
    obj_name: str


class MapFileRequestSchema(Schema):
    commit_hash = fields.String(required=True)
    commit_msg = fields.String(required=True)
    branch_name = fields.String(required=True)
    bss_size = fields.Integer(required=True)
    text_size = fields.Integer(required=True)
    rodata_size = fields.Integer(required=True)
    data_size = fields.Integer(required=True)
    free_flash_size = fields.Integer(required=True)
    pull_id = fields.Integer(required=True)
    pull_name = fields.String(required=True)
