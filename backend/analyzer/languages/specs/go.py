from ..treesitter_analyzer import LanguageSpec

GO_SPEC = LanguageSpec(
    language_id="go",
    ts_language_name="go",
    function_query="""
(function_declaration name: (identifier) @name) @func
(method_declaration name: (field_identifier) @name) @func
""",
    class_query="""
(type_declaration
  (type_spec name: (type_identifier) @name)) @class
""",
    import_query="""
(import_spec path: (interpreted_string_literal) @source) @import
""",
    branch_node_types={
        "if_statement", "for_statement", "expression_switch_statement",
        "case_clause", "select_statement",
    },
    entry_point_query="""
(function_declaration
  name: (identifier) @main
  (#eq? @main "main")) @entry
""",
)
