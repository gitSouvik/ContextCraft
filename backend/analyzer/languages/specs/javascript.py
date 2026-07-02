from ..treesitter_analyzer import LanguageSpec

JAVASCRIPT_SPEC = LanguageSpec(
    language_id="javascript",
    ts_language_name="javascript",
    function_query="""
(function_declaration name: (identifier) @name) @func
(generator_function_declaration name: (identifier) @name) @func
(method_definition name: (property_identifier) @name) @func
(lexical_declaration
  (variable_declarator
    name: (identifier) @name
    value: [(arrow_function) (function_expression)])) @func
""",
    class_query="""
(class_declaration name: (_) @name) @class
""",
    import_query="""
(import_statement source: (string (string_fragment) @source)) @import
(call_expression
  function: (identifier) @req
  arguments: (arguments (string (string_fragment) @source))
  (#eq? @req "require")) @import
""",
    branch_node_types={
        "if_statement", "for_statement", "while_statement",
        "switch_case", "catch_clause", "ternary_expression",
    },
    entry_point_query="""
(call_expression
  function: (member_expression
    object: (identifier)
    property: (property_identifier) @listen)
  (#eq? @listen "listen")) @entry
(if_statement
  condition: (parenthesized_expression
    (binary_expression
      left: (member_expression
        object: (identifier)
        property: (property_identifier) @main)
      right: (identifier) @mod))
  (#eq? @main "main")
  (#eq? @mod "module")) @entry
(export_statement declaration: (function_declaration)) @entry
""",
)
