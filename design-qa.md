# Models guided setup QA

Date: 2026-09-07

**Findings**

No actionable P0/P1/P2 findings remain in the redesigned Models page.

**Evidence and comparison scope**

- Source visual truth: `/Users/vavo/.codex/generated_images/01a078ab-a505-7ef1-9fc5-ea15eaf13c01/exec-4cdf341a-a66d-4d46-8fae-df806e8c1d49.png` (option 1, Guided Setup).
- Implementation: `http://127.0.0.1:18788`, Models, Catalog, Video, light theme.
- Final desktop screenshot: `/tmp/lora-models-desktop.png`.
- Responsive evidence: `/tmp/lora-models-mobile.png`, `/tmp/lora-models-mobile-dialog.png`.
- Additional states: `/tmp/lora-models-dark.png`, `/tmp/lora-models-error.png`.
- Source is 1536 x 1024 pixels including generated browser chrome and margins. Its CSS viewport and density are unknown. Implementation is 1440 x 1000 CSS/pixels at DPR 1; mobile is 390 x 844 at DPR 1. Comparison considers the app content region and relative proportions, excluding mock browser chrome; this is not a pixel-difference claim.
- Source and final desktop screenshot were opened together in the same comparison input. Full-view text and controls were legible, so a separate magnified crop was unnecessary. The mobile dialog was also inspected directly for long filenames and reachable controls.
- Screenshots and the mock server are temporary local QA artifacts, not shipped application assets.

**Comparison history**

1. Initial desktop comparison found P2 drift: global orange primary buttons and Continue setup below all families weakened the chosen hierarchy. Scoped blue primary buttons to Models and placed Continue setup directly after the first two family cards. Final desktop evidence confirms both corrections.
2. Mobile comparison found P2 header wrapping: installed count and management actions squeezed the heading and split Refresh onto an awkward line. Changed the mobile header to a vertical layout. Final mobile evidence shows a readable heading and a single management-action line, with no horizontal overflow (document width equals viewport width: 390px).
3. Final combined comparison retains the two prominent video family cards, task selector, three views, and Continue setup hierarchy. No further blocking visual changes identified.

**Required fidelity surfaces**

- Typography: existing system UI font retained; bold 28px desktop family headings and 26px mobile headings reproduce the source hierarchy. Small metadata remains readable; long filenames wrap inside the dialog. Exact generated-font metrics are not inferred.
- Spacing/layout: two equal desktop columns, 24px gap, spacious card interiors, bordered footers, and Continue setup beneath the featured pair. Mobile stacks cards and wraps task controls. Existing shell dimensions are retained.
- Colors/tokens: blue selected tasks and primary actions, neutral cards, subtle borders, existing light/dark tokens. Source pill tint and ghost-button treatment differ slightly to remain consistent with the application.
- Image quality/assets: existing LoRA Pilot logo and shell icons retained. No generated browser chrome, placeholder artwork, or new decorative assets introduced.
- Copy/content: actual manifest entries replace sample counts. Missing workflow files say Not in catalog. Installed describes file presence rather than verified generation. Unsupported mock capability wording and fictional disk usage are omitted.

**Interaction validation**

- Catalog tasks, cross-task search, empty search results, Installed, Downloads, family setup and variant controls checked in the browser.
- Long workflow filenames and source links checked at mobile width; dialog closing and file details exercised.
- Simulated download progress, completion, installed-list refresh, removal, provider failure and Retry checked. A temporary mock-server fixture error was corrected before repeating the failure/retry test successfully.
- Dark theme checked. Browser error log returned no JavaScript errors.
- Node syntax checks passed for all three changed JavaScript modules; 137 Python tests passed; git diff whitespace check passed.

**Open questions and limits**

No design decision blocks this change. Browser testing used simulated API responses and did not download weights or modify real model files. Actual GPU generation, provider authentication, and outstanding manifest repairs remain separate runtime checks. The setup checklist deliberately exposes missing entries instead of claiming a complete installation.

**Implementation checklist**

- [x] Match the selected guided setup hierarchy.
- [x] Preserve individual download, progress, retry and removal operations.
- [x] Check desktop/mobile, light/dark and error states.
- [x] Validate family assignments and exact bundled workflow references.
- [x] Update the model-management guide.

**Follow-up polish**

None required for this scope.

final result: passed
