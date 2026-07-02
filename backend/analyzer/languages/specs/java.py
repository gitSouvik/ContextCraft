from ..treesitter_analyzer import LanguageSpec

JAVA_SPEC = LanguageSpec(
    language_id="java",
    ts_language_name="java",
    function_query="""
(method_declaration name: (identifier) @name) @func
(constructor_declaration name: (identifier) @name) @func
""",
    class_query="""
(class_declaration name: (identifier) @name) @class
(interface_declaration name: (identifier) @name) @class
(enum_declaration name: (identifier) @name) @class
""",
    import_query="""
(import_declaration (scoped_identifier) @source) @import
""",
    branch_node_types={
        "if_statement", "for_statement", "while_statement",
        "switch_label", "catch_clause", "ternary_expression",
    },
    # Java main: `public static void main(String[] args)` — too complex to query precisely;
    # fall back to filename heuristic (Main.java) in the analyzer
    entry_point_query=None,
)
