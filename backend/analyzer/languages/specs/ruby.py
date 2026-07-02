from ..treesitter_analyzer import LanguageSpec

RUBY_SPEC = LanguageSpec(
    language_id="ruby",
    ts_language_name="ruby",
    function_query="""
(method name: (identifier) @name) @func
(singleton_method name: (identifier) @name) @func
""",
    class_query="""
(class name: (constant) @name) @class
(module name: (constant) @name) @class
""",
    import_query="""
(call
  method: (identifier) @req
  arguments: (argument_list (string) @source)
  (#eq? @req "require")) @import
(call
  method: (identifier) @req
  arguments: (argument_list (string) @source)
  (#eq? @req "require_relative")) @import
""",
    branch_node_types={
        "if", "elsif", "unless", "while", "until",
        "case", "rescue", "when",
    },
    # `if __FILE__ == $0` — tree-sitter-ruby parses $0 as global_variable
    # and __FILE__ as identifier; the structure can vary; skip query-based detection
    # and rely on filename heuristics instead.
    entry_point_query=None,
)
