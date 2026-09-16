# ControlPilot Settings: version 1 verification

final result: passed

The selected reference is `/Users/vavo/.codex/generated_images/01a078ab-a505-7ef1-9fc5-ea15eaf13c01/exec-d11f7414-265d-4c3b-8f8d-cea550412596.png`. The implementation was verified at `http://127.0.0.1:18789/` in the Settings view, using an isolated temporary workspace.

The final desktop screenshot is `/tmp/lora-settings-v1-desktop-final.png`. Reference and implementation are both 1487 by 1058 pixels. The browser viewport was 1487 by 1058 CSS pixels with device pixel ratio 1, so no density normalization was needed. Both comparison images show General, light theme, expanded sidebar, and disabled compact/sidebar URL defaults. Both images were opened together in one comparison tool response.

Typography uses the existing system font stack. The page heading, section headings, body copy, and control labels follow the selected hierarchy. The implementation keeps the existing global sidebar size and typography rather than enlarging the rest of the application to match the generated mock. The retained left-menu theme switch is an explicit user requirement.

The layout preserves the four horizontal category tabs, continuous form surface, two theme choices, separated preference rows, help column, and bottom save action. Initial review found cramped typography and a rounded active tab inherited from global styles. The implementation increased type sizes and spacing, removed tab rounding, stretched the help divider, and enlarged the save button. The final comparison found no actionable P0, P1, or P2 differences. Slight differences in generated-image font metrics and control density remain acceptable within the existing application shell.

Colors use existing light/dark tokens with scoped orange selection states. The source logo and existing navigation icons remain in use; no raster replacements or new decorative assets were introduced. Copy preserves the mock's intent while correcting its claim of automatic saving: preferences save explicitly, while the menu theme switch applies immediately. Controls and labels are clearly readable in the full-resolution comparison, so an additional focused crop was unnecessary.

Mobile screenshots are `/tmp/lora-settings-v1-mobile.png` and `/tmp/lora-settings-v1-mobile-dark.png`, captured at 390 by 844 CSS pixels. An initial mobile pass showed an uneven three-plus-one tab wrap and a detached Clear action. The final layout uses two columns for mobile tabs and a full-width credential field before its actions. All four panels have document width 390 pixels, with no horizontal overflow. The final mobile light/dark screenshots confirm readable controls and the responsive help column.

Browser interactions verified the left-menu theme switch synchronizes the General theme selection, General saving applies appearance, compact sidebar persists after reload, the sidebar can be expanded again, tab clicks and Home-key navigation work, and shutdown defaults save without scheduling shutdown. The mobile menu retained its theme switch and updated the Settings radio state. Browser warning/error logs were empty.

The full Python suite passed 172 tests. The new frontend regression test executes Settings JavaScript and covers tab keyboard behavior, masked saved credentials, successful General saves, failure before saving, and partial failure after appearance has saved. JavaScript syntax and whitespace checks passed. Credential changes and service restarts were not exercised against live services; their existing API handlers remain in place.

No implementation fixes remain from this review. The production Docker image and running pod have not been updated by this change.

---

# Models — version 1 correction

Date: 2026-09-07

**Findings**

The previous report's pass was invalid for the user's selection: it compared the implementation against Guided Setup (version 2). Version 1 is Workflow Catalog. This report supersedes that comparison.

No actionable P0/P1/P2 differences remain within the Models redesign scope.

**Visual evidence**

- Correct source: `/Users/vavo/.codex/generated_images/01a078ab-a505-7ef1-9fc5-ea15eaf13c01/exec-fe9d53e4-323d-47e4-a1ab-6018484859f1.png`.
- Preview: `http://127.0.0.1:18788/`, Models → Catalog, LTX-2.5 selected, light theme.
- Desktop: `/tmp/lora-models-v1-desktop.png`.
- Mobile list: `/tmp/lora-models-v1-mobile.png`.
- Mobile detail: `/tmp/lora-models-v1-mobile-detail.png`.
- Dark state: `/tmp/lora-models-v1-dark.png`.
- Source: 1488 x 1058 raster. Implementation: 1488 x 1058 CSS/pixels, DPR 1. Mobile: 390 x 844 CSS/pixels, DPR 1. Intermediate desktop: 1100 x 900 CSS/pixels, DPR 1.
- The source's 42px direction-label strip is excluded from app-region comparison; the existing application shell remains intact. The source uses illustrative data; the implementation uses real manifest entries with simulated installation state.
- Source and saved desktop capture were opened together in the same comparison input. Headings, controls, component rows and badges were legible at full view; additional crops were unnecessary. Mobile detail and dark-state screenshots were separately inspected.
- Screenshots and preview fixtures are temporary local QA artifacts. Family thumbnails are bundled application assets.

**Comparison history**

1. P1 — wrong design selected: large blue cards and modal setup replaced the requested orange row catalog and inline panel. Replaced the card grid with selectable family rows, task/family dropdowns and a persistent right-hand details panel. Removed the task-button strip and Continue setup section.
2. P2 — first corrected rendering had a narrower panel, undersized row thumbnails, and a short primary button. Set the desktop panel to 414px, thumbnails to 72px, and Review installation to 54px high. The revised combined comparison shows the intended row density and list/panel proportions.
3. Required groups now follow diffusion model, encoder, VAEs and upscaler order. Selecting another family resets the detail body to its beginning. Final responsive checks show no horizontal overflow at 390px or 1100px.

**Fidelity surfaces**

- Typography: existing system UI font retained; 30px page heading, 25px panel title, 17px family names and 13px secondary row text maintain the reference hierarchy. Long filenames wrap inside expanded details.
- Layout/spacing: tabs above the title; search plus two dropdowns; compact divided rows; orange selected row; independently scrollable detail content. Mobile presents the selected panel above the list and keeps its Close control outside the scrolling body.
- Colors/tokens: scoped orange navigation, tabs, selections and actions replace blue. Neutral panels and green file-state badges adapt to light/dark themes. Existing shell logo and navigation sizing are preserved.
- Images/icons: five individually generated family tiles match the source's teal/black/purple treatments. They are optimized to 192px square for the 72px desktop slots. Standard component/chevron icons reuse the application's existing assets. Other real catalog families use the existing model icon.
- Copy/content: real FLUX/Qwen entries replace nonexistent illustrative variants; absent catalog files retain source links. File presence says Installed rather than Verified. Access settings opens the existing settings view; no unsupported automatic access-check claim is made.

**Interaction checks**

- Task/family filters, search, empty results and keyboard search clearing passed.
- Family selection, inline detail closing, grouped requirements, Review installation and variant expansion passed.
- Simulated individual download, progress, completion, provider failure and retry passed; the installed count and states refreshed.
- Mobile list and component panel, intermediate desktop width and dark theme inspected.
- Browser error log returned no JavaScript errors.
- JavaScript syntax checks, 137 Python tests and git diff whitespace checks passed.

**Limits and follow-up polish**

Preview API responses are simulated; no real weights were downloaded or removed. Manifest repairs and GPU generation remain separate. The unchanged API helper can expose a JSON-formatted detail in a start-failure message (P3); the activity view shows the plain error and retry action.

**Implementation checklist**

- [x] Correct version 1 source selected and visually compared.
- [x] Orange catalog rows and right-hand panel implemented.
- [x] Existing download operations preserved and exercised.
- [x] Responsive and dark states checked.
- [x] User guide updated.

final result: passed
