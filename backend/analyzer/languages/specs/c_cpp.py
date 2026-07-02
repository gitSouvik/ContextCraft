from ..treesitter_analyzer import LanguageSpec

C_SPEC = LanguageSpec(
    language_id="c",
    ts_language_name="c",
    function_query="""
(function_definition
  declarator: (function_declarator
    declarator: (identifier) @name)) @func
""",
    class_query="""
(struct_specifier name: (type_identifier) @name) @class
(union_specifier name: (type_identifier) @name) @class
""",
    import_query="""
(preproc_include path: [(string_literal) (system_lib_string)] @source) @import
""",
    branch_node_types={
        "if_statement", "for_statement", "while_statement",
        "case_statement", "do_statement",
    },
    entry_point_query="""
(function_definition
  declarator: (function_declarator
    declarator: (identifier) @main)
  (#eq? @main "main")) @entry
""",
)

CPP_SPEC = LanguageSpec(
    language_id="cpp",
    ts_language_name="cpp",
    function_query="""
(function_definition
  declarator: (function_declarator
    declarator: [(identifier) (field_identifier)] @name)) @func
""",
    class_query="""
(class_specifier name: (type_identifier) @name) @class
(struct_specifier name: (type_identifier) @name) @class
""",
    import_query="""
(preproc_include path: [(string_literal) (system_lib_string)] @source) @import
""",
    branch_node_types={
        "if_statement", "for_statement", "while_statement",
        "case_statement", "do_statement",
    },
    entry_point_query="""
(function_definition
  declarator: (function_declarator
    declarator: (identifier) @main)
  (#eq? @main "main")) @entry
""",
)
