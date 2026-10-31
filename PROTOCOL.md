# Fixed contract action-accounting audit

## Decision and prior source hold

Determine how current transaction counts, zero-dollar actions and signed financial adjustments differ from net obligation totals in a fixed post-award cohort. The useful decision is what to retain in a contract-administration review queue before substituting dollars for activity.

The original pre-award modification classifier remains unexecuted. Official disclosure describes publication delays after contract actions, with longer exceptions. Neither action dates nor current award summaries establish feature availability before award. This execution does not fit, validate or imply that classifier. It is a separate, source-informed retrospective audit using established accounting and ranking arithmetic. No new estimator or scientific-priority claim.

Only official API contracts, search-filter definitions, agency metadata and the USAspending disclosure PDF have been inspected. No contract/transaction cohort or study outcomes have been requested. NASA is a fixed civilian agency choice to keep the convenience cohort narrow; it does not represent other agencies or contract populations. Selection is source informed, not blind.

## Fixed current cohort and capture

Request the first page of 20 current prime contract awards from the official spending_by_award endpoint. Award type codes A, B, C and D; NASA awarding toptier agency; calendar 2024 new_awards_only filter; ascending Award ID; page 1, limit 20, subawards false. Use explicit new_awards_only rather than the source's differing default start/end date semantics.

Retain all returned cases in their captured order, including ties, with stable case IDs C01 onward. No replacements or alternate agency/date/amount filters after seeing outcomes. This is a bounded API-page convenience cohort, not a random sample or all NASA contracts. Fewer than 20 cases, duplicate generated award keys, mismatched agency/type/base-year assertions or unusable base dates fail the source gate; do not substitute cases.

Search fields: Award ID, generated_internal_id, Base Obligation Date, Awarding Agency, Awarding Agency Code, Contract Award Type. No award-dollar filter or amount-based selection. Do not request names, addresses, recipient IDs or descriptions as search fields. The source may return extra fields; native payloads stay private.

For each selected generated award ID, GET the official transaction-count endpoint before and after capture, and POST transactions sorted action_date ascending, page 1, limit 5000. The fixed cap is 5000 per award. Any hasNext, count drift, missing/duplicated IDs, noncontract type or count disagreement fails complete-history capture. No partial history is silently accepted. Capture one final repeat of the identical award query and require identical selected keys/base assertions. These controls detect specific changes, not atomic or original-vintage proof. At most one targeted repair of a demonstrated request/implementation defect; do not retry unchanged access denials.

Preserve exact requests, native response bytes, UTC retrieval times, hashes, source schema assertions and all exclusions privately. Public factual projection contains case/contract/transaction source keys, source calendar dates, modification tokens, type codes and signed federal_action_obligation tokens only. No vendor names, contact data, addresses, narratives, assistance-to-individuals data or recipient ranking. IDs identify public government transactions, not people.

## Fixed follow-up and accounting

Use each current Base Obligation Date as an asserted source calendar origin. Study actions with 0 <= (action_date - base_date).days < 365, so day 364 is included and day 365 excluded. The capture must occur after the last case's complete calendar follow-up. Retain before-base, day-365-or-later and missing/invalid dates separately. This is one current view of a historical action window, not an immutable historical snapshot or pre-award availability.

Count singleton valid source transaction keys, retaining full record accounting. Never infer transaction chronology from modification-number lexical or numeric order. Preserve modification tokens as source labels; do not equate each token, row or post-base day with an independently verified legal modification or staff task. Same-day actions cannot be ordered from a calendar date.

Parse money from native JSON numeric tokens as exact decimals. Retain positive, negative and zero values with their sign. Missing, nonnumeric or nonfinite money remains unavailable. Count finite-amount rows, unknown-amount rows, positive/zero/negative counts, positive obligations, signed negative obligations, gross absolute obligations and net obligations for every case. A financial total/rank is eligible only when every in-window eligible transaction has finite money; an empty valid window has zero actions but monetary totals remain unavailable. Do not silently turn missing amounts or no history into zero dollars.

For complete nonempty windows with gross absolute obligations > 0, net-offset fraction = (gross absolute obligations - abs(net obligations)) / gross absolute obligations. When gross = 0, retain that ratio unavailable. This algebra measures signed offsetting within observed obligations, not waste, savings, churn cost, paid cash, cash recovery or an agency error rate. Obligation is not outlay or realized expense.

## Fixed comparisons and complete exports

Primary comparison: top-five queue by in-window transaction count versus top-five by net obligations, over the same jointly eligible cases. Sort descending by the relevant value, break ties by fixed case ID, retain every rank and tied value, and take min(5, joint eligible count). Report both complete queues, overlap count, union count and exact Jaccard ratio with denominators. Do not optimize five or select another ranking after outcomes. Five is a small authored review-capacity illustration, not validated staffing capacity.

Report complete case accounts and complete source-row classifications. Fixed cumulative count probes at days 30, 90 and 365 use 0 <= day < horizon. Also retain counts of same-day records, distinct modification tokens and missing tokens as descriptive diagnostics; do not promote them to verified task counts. No predictive accuracy, calibration, significance, uncertainty interval or causal claim from this convenience cohort.

Three planned figures: per-case transaction counts beside net-obligation values with separate labeled units; complete case net-offset fractions with unavailable states; and per-case cumulative count probes at 30/90/365 days. Source-bound artist/coordinate checks must independently reconstruct values and visible encodings; no truncated dollar axes, unspecified denominator or omitted adverse case.

## Independent checks, exercise and freeze

Implement capture/projection first, then independently reconcile native numeric tokens, identity, all counts, dates and source hashes. Use a distinct checker with datetime parsing, SQLite calendar controls and exact Fraction arithmetic without importing production aggregation/ranking functions. Before computing ranking/offset comparisons, commit the source projection and actual hashes of its data, methods, authored fixtures, environment and this protocol. Source values may be visible during capture and reconciliation; commit order does not imply blindness.

Meaningful fixtures cover signed/zero/missing money, invalid/ambiguous IDs, empty windows, 364/365-day boundaries, leap-year origins, tied ranks, before-origin actions, same-day ambiguity, unavailable ratios and unsupported availability conversions. Retain all failures. A local implementation exercise must run actual source-backed case accounts and reject using current action dates as pre-award publication evidence or dollars as staff hours. No deployment or measured benefit.

Before release: reproduce every frozen output in two isolated full-history checkouts using recorded Python versions; verify every plotted source value and coordinate; bind manuscript values to actual used source exports and inspect every rendered page; audit staged/canonical bytes and explicit independent-manuscript scope; require exact candidate/main Linux success, identical tested/merged trees, remote annotated tag and accurate portfolio metadata.

## Acceptance and limitations

Source/count consistency, complete current row accounting, independent exact arithmetic, meaningful boundaries, readable complete figures/paper, public/private separation and remote release proof are required pass/fail gates. Each must pass. A finite pass count is not universal correctness. A failed or unknown gate cannot be replaced by style or self-scoring.

The historical proposal and source timing hold remain available. Do not infer a national workload rate, staff hours, contract performance, risky vendors, fraud, funding need, causal impact, production use or realized saving. Formal-publication projects including Azure optimization remain private. Default local review caps apply: three substantive rounds, 45 active review minutes and 60 review-specific calls; source acquisition, coding and release execution are separate.
