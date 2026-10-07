# Limitations

Hygiene checks use configured filename suffixes; arbitrary binaries and every possible text format are not parsed. Linked descendants are skipped rather than analyzed. Large-file findings apply even to formats whose text is not inspected. The tool is intended for ordinary editable source trees, not hostile concurrent filesystem mutation or permission-repair tasks.

The credential patterns are deliberately small and can produce false positives or miss secrets. They must not be used to certify that a repository is safe to publish. Whitespace exemptions do not disable the separate credential heuristics. Findings do not print matched credential text.

The reference check uses a lightweight regular expression. It checks file/directory existence inside the selected root, not heading or block anchors, link titles, encoded paths, complex nested-parenthesis syntax, reference-style links, or remote availability. Inline document-name mentions are matched by basename. Code examples can produce false positives. Use a full Markdown-aware checker when that coverage is required.

Fix mode handles only ordinary trailing whitespace and final newline repair. It is an explicit mutation, not the default. Review findings and rerun after repairs. It does not automatically remove credentials, rewrite program indentation or make binary files smaller.
