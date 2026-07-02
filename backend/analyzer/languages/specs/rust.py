from ..treesitter_analyzer import LanguageSpec

RUST_SPEC = LanguageSpec(
    language_id="rust",
    ts_language_name="rust",
    function_query="""
(function_item name: (identifier) @name) @func
""",
    class_query="""
(struct_item name: (type_identifier) @name) @class
(enum_item name: (type_identifier) @name) @class
(impl_item type: (type_identifier) @name) @class
(trait_item name: (type_identifier) @name) @class
""",
    import_query="""
(use_declaration argument: (_) @source) @import
""",
    branch_node_types={
        "if_expression", "match_arm", "for_expression",
        "while_expression", "loop_expression",
    },
    entry_point_query="""
(function_item
  name: (identifier) @main
  (#eq? @main "main")) @entry
""",
)
