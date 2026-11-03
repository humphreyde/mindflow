---
title: "Fast-WAM: Do World Action Models Need Test-time Future Imagination?"
type: research-source
canonical_id: "url:https://yuantianyuan01.github.io/FastWAM/"
source_type: article
platform: project-page
creator: Fast-WAM authors
url: "https://yuantianyuan01.github.io/FastWAM/"
alternate_urls: []
published: 2026
captured: 2026-09-17
capture_status: summarized
evidence_role: author-statement
related_papers: ["[[Papers/2603-FastWAM|Fast-WAM]]"]
related_authors: []
related_code: ["Fast-WAM Code Companion"]
duration_minutes: 
---

# Fast-WAM: Do World Action Models Need Test-time Future Imagination?

<!-- source-source:start -->
## Source

- Link: [Source](<https://yuantianyuan01.github.io/FastWAM/>)
- Platform: project-page
- Creator: Fast-WAM authors
- Published: 2026
- Direct relationships:
  - Related papers: [[Papers/2603-FastWAM|Fast-WAM]]
  - Related code: Fast-WAM Code Companion
<!-- source-source:end -->

<!-- source-summary:start -->
## Summary

The authors argue that Fast-WAM keeps video co-training during training but removes explicit future-video generation at inference, remaining competitive while reducing latency; this is first-party project-page evidence, not independent verification.
<!-- source-summary:end -->

<!-- source-insights:start -->
## Key Insights

### Video co-training as a representation-learning signal

- Claim: The project page attributes most WAM benefit to video co-training during training rather than explicit test-time future generation.
- Source anchor: Video Co-Training Matters More Than Test-Time Imagination in WAMs
- Relation: explains
- Evidence: author-statement
- Targets: [[Papers/2603-FastWAM#训练与推理路径]], Fast-WAM-code

### Single-pass latent action inference

- Claim: The project page describes processing current clean latent tokens once and directly generating actions, avoiding iterative future-video denoising.
- Source anchor: A WAM That Drops Future Imagination at Test Time
- Relation: explains
- Evidence: author-statement
- Targets: [[Papers/2603-FastWAM#训练与推理路径]], Fast-WAM-code
<!-- source-insights:end -->

<!-- source-connections:start -->
## Connections to Papers and Code

- Related papers: [[Papers/2603-FastWAM|Fast-WAM]]
- Related code: Fast-WAM Code Companion
<!-- source-connections:end -->

<!-- source-verification:start -->
## Verification and Tensions

- Evidence role: author-statement
<!-- source-verification:end -->

## Personal Notes
