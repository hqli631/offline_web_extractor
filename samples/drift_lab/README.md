# Controlled drift laboratory

These five complete HTML documents are authored synthetic fixtures. They model
specific failure mechanisms and must not be reported as independent real-site
validation or be merged into real-page accuracy.

One rule is frozen from reference.html: //div[@role='main']. No per-page repair
or fallback is allowed. Every expected file preserves the same three article
sentences exactly once; navigation, footer, and the duplicated responsive copy
are excluded.

| Fixture | Controlled mutation | Expected applicability | Expected quality |
| --- | --- | --- | --- |
| reference | None | One match, ok | All three paragraphs |
| class-drift | Class renamed only | One match, ok | All three paragraphs |
| role-drift | role main becomes article | Zero matches, rule_no_match | Not extracted |
| duplicate-main | Desktop/mobile duplicate main containers | Two matches, rule_ambiguous | Not extracted |
| content-moved | Closing paragraph moves to sibling section | One match, ok | Incomplete, two of three paragraphs |

The last fixture deliberately proves that a unique match and status=ok are not
content completeness. The gold is full intended article content, not just text
still inside the selected container.

build_fixtures.py authors/verifies the fixtures from literal intended prose,
without importing production code, traversing DOM to create gold, or reading
predictions. It refuses to overwrite a changed artifact. Every HTML and expected
SHA256, mutation definition, reference hash, and predicted mechanism are recorded
in the adjacent source JSON and provenance.json. Source/gold construction occurs
before extraction; no production run is performed by this generator.

The parent experiment runner can consume reuse.json. Expected status and quality
fields are metadata; the current reuse runner may ignore them, so assertions
must be checked explicitly in the final experiment report.
