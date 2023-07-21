

def get_commits_by_branch_id(branch_id: int) -> List[DataTypedDict]:
    """Get all commits by branch id"""
    INTERESTING_SECTIONS = [
        ".isr_vector",
        ".text",
        ".rodata",
        ".fini_array",
        ".data",
        ".bss",
        ".stabstr",
        "MAPPING_TABLE",
        "MB_MEM1",
        "MB_MEM2",
    ]
    result = (
        Data.query.filter(Data.header_id == branch_id)
        .filter(Data.section.in_(INTERESTING_SECTIONS))
        .filter(Data.size > 0)
        .all()
    )
    return [row.serialize for row in result]
