# Paper schema

MindFlow keeps Paper notes flat under `Papers/`. Metadata provides classification;
folders do not. The canonical note template is
`skills/1-literature/paper-digest/references/paper-note-template.md`.

## Controlled values

- `type`: `paper`
- `domains`: `multimodal-understanding | ai-agent | embodied-ai | general-ai`
- `review_status`: `inbox | digested | reviewed`
- `rating`: `1 | 2 | 3`
- rating labels for new output: `Peripheral | Frontier | Foundation`
- identity priority: arXiv ID, DOI, verified official URL plus normalized title

`primary_domain` must be one of the controlled domains and must also appear in
`domains`. New notes use 1–4 controlled tags from `references/tags.md`. Legacy
notes with more tags remain readable and enter review rather than being pruned.

## Stable identity

`arxiv_id` is stored without an `arXiv:` prefix or version suffix. `doi` is stored
without a resolver URL and is case-normalized. URL/title identities are review
candidates, not automatic duplicate evidence. Filename stability takes priority
over repairing date or identity mismatches.

## Zotero boundary

`zotero_item_key` is Zotero's stable library item identifier.
`zotero_citekey` is a mutable citation-key snapshot. They are distinct fields and
must not be substituted for one another. Zotero metadata is optional and does not
replace the official paper as the authority for body text or claims.

## Migration-only fields

`source_vault`, `source_path`, and `date_migrated` record provenance only for
migrated notes. Native MindFlow notes do not require them. Deterministic migration
may add `type` and a high-confidence `arxiv_id`; classification, review state, DOI,
Zotero fields, tags, rating text, and filenames require separate review.
