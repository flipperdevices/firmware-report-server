

class Data(db.Model):  # type: ignore
    # +-----------+------------------+------+-----+---------+----------------+
    # | Field     | Type             | Null | Key | Default | Extra          |
    # +-----------+------------------+------+-----+---------+----------------+
    # | header_id | int(10) unsigned | NO   | MUL | NULL    |                |
    # | id        | int(10) unsigned | NO   | PRI | NULL    | auto_increment |
    # | section   | text             | NO   |     | NULL    |                |
    # | address   | text             | NO   |     | NULL    |                |
    # | size      | int(10) unsigned | NO   |     | NULL    |                |
    # | name      | text             | NO   |     | NULL    |                |
    # | lib       | text             | NO   |     | NULL    |                |
    # | obj_name  | text             | NO   |     | NULL    |                |
    # +-----------+------------------+------+-----+---------+----------------+

    __tablename__ = "data"
    header_id = db.Column(db.Integer, db.ForeignKey("header.id"))
    id = db.Column(db.Integer, primary_key=True, nullable=False, autoincrement=True)
    section = db.Column(db.Text, nullable=False)
    address = db.Column(db.Text, nullable=False)
    size = db.Column(db.Integer, nullable=False)
    name = db.Column(db.Text, nullable=False)
    lib = db.Column(db.Text, nullable=False)
    obj_name = db.Column(db.Text, nullable=False)

    @property
    def serialize(self):
        return {
            "header_id": self.header_id,
            "id": self.id,
            "section": self.section,
            "address": self.address,
            "size": self.size,
            "name": self.name,
            "lib": self.lib,
            "obj_name": self.obj_name,
        }


class DataTypedDict(TypedDict):
    header_id: int
    id: int
    address: str
    section: str
    size: int
    name: str
    lib: str
    obj_name: str


class Header(db.Model):  # type: ignore
    # +------------------+------------------+------+-----+---------+----------------+
    # | Field            | Type             | Null | Key | Default | Extra          |
    # +------------------+------------------+------+-----+---------+----------------+
    # | id               | int(10) unsigned | NO   | PRI | NULL    | auto_increment |
    # | datetime         | datetime         | NO   |     | NULL    |                |
    # | commit           | varchar(40)      | NO   |     | NULL    |                |
    # | commit_msg       | text             | NO   |     | NULL    |                |
    # | branch_name      | text             | NO   |     | NULL    |                |
    # | bss_size         | int(10) unsigned | NO   |     | NULL    |                |
    # | text_size        | int(10) unsigned | NO   |     | NULL    |                |
    # | rodata_size      | int(10) unsigned | NO   |     | NULL    |                |
    # | data_size        | int(10) unsigned | NO   |     | NULL    |                |
    # | free_flash_size  | int(10) unsigned | NO   |     | NULL    |                |
    # | pullrequest_id   | int(10) unsigned | YES  |     | NULL    |                |
    # | pullrequest_name | text             | YES  |     | NULL    |                |
    # +------------------+------------------+------+-----+---------+----------------+

    __tablename__ = "header"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    datetime = db.Column(db.DateTime, nullable=False, server_default=func.now())
    commit = db.Column(db.String(40), nullable=False)
    commit_msg = db.Column(db.Text, nullable=False)
    branch_name = db.Column(db.String(32), unique=False, nullable=False)
    bss_size = db.Column(db.Integer, nullable=False)
    text_size = db.Column(db.Integer, nullable=False)
    rodata_size = db.Column(db.Integer, nullable=False)
    data_size = db.Column(db.Integer, nullable=False)
    free_flash_size = db.Column(db.Integer, nullable=False)
    pullrequest_id = db.Column(db.Integer, nullable=True)
    pullrequest_name = db.Column(db.String(128), unique=False, nullable=True)

    @property
    def serialize(self):
        """Return object data in easily serializable format"""
        return {
            "id": self.id,
            "datetime": self.datetime,
            "commit": self.commit,
            "commit_msg": self.commit_msg,
            "branch_name": self.branch_name,
            "bss_size": self.bss_size,
            "text_size": self.text_size,
            "rodata_size": self.rodata_size,
            "data_size": self.data_size,
            "free_flash_size": self.free_flash_size,
            "pullrequest_id": self.pullrequest_id,
            "pullrequest_name": self.pullrequest_name,
        }


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
