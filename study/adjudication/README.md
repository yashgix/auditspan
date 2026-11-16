# Second-model adjudication of the hold-out disagreements

This folder holds a second, separate set of labels for 30 hold-out findings. It is **not blind, not a person's
check and not expert ground truth.** The blind Codex labels in `study/heldout/` are unchanged, and the blind scores
stay the headline. The scores against these labels are a separate row in `results/heldout.json`
(`second_model`).

## Which findings
The 30 hold-out findings where the frozen v2 rules, the Codex labels and the auditor's form disagree in a way that
moves a score, plus two where v2 and Codex agree and only the form differs:
- Part 1 (items 1-5): v2 and Codex give different letters. These move v2's precision.
- Part 2 (items 6-28): v2 found nothing, and Codex says a label or title states letters. These move recall.
- Part 3 (items 29-30): v2 and Codex agree, the form differs. No score moves.

The 28 findings Codex labelled from body sentences only were not reviewed.

## Rules
1. Judge only what the finding's own text states as the compliance requirement of that finding.
2. A requirement counts as stated only in a label, title or section heading. A requirement found only in a body
   sentence (Condition, Effect, Cause and so on) counts as "body only".
3. "Reporting" about the audit itself (a late single audit, the reporting package, the SEFA) is not L. The 2 CFR 200
   subpart title "Cost Principles" is not B. A cited regulation alone is not enough.
4. Letters are the SF-SAC key: A activities allowed, B allowable costs, C cash management, E eligibility, F equipment,
   G matching, H period of performance, I procurement, J program income, L reporting, M subrecipient monitoring,
   N special tests and provisions, P other.

## How a decision becomes a label
Codes: V = v2's letters are right, C = Codex is right, O:X = the text states letters X, B = stated only in a body
sentence, N = not stated, A = agree with v2 and Codex. V and O:X replace the letters and keep Codex's location.
B keeps the letters and moves the location to a body sentence. N sets the label to none. C and A change nothing.
`findingtrace/heldout.py` applies `decisions.jsonl` to the Codex labels and scores v2 against the result.

## Who decided
1. ChatGPT (OpenAI) answered all 30 items on 15 Nov 2026. It was **not blind**: for every item it saw the v2 letters,
   the Codex letters and the auditor's form.
2. Claude (Anthropic) then checked each answer against the rules above. Three answers counted body text where the
   rules do not, and were corrected: item 1 (ChatGPT V, now C), item 4 (C, now V) and item 12 (C, now O:N). Items 7,
   8 and 10 are interpretive and were kept as ChatGPT answered.
3. No person has checked these labels.

Disagreements with Codex: ChatGPT's answers differ from Codex on 9 of the 30 items (1, 5, 6, 7, 8, 9, 10, 11, 28).
After the corrections, 10 labels differ from Codex (4, 5, 6, 7, 8, 9, 10, 11, 12, 28).

## All 30 decisions
| # | finding | Codex | ChatGPT | final | resulting label | note |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2023-12-GSAFAC-0000378024 2023-003 | none | V | C (corrected) | unchanged | Corrected by Claude. The only B evidence is the cited subpart title "Cost Principles", which the protocol excludes. ChatGPT's reason (wrong pay rates) comes from body text. |
| 2 | 2024-09-GSAFAC-0000375749 2024-001 | none | C | C | unchanged | Same as Codex. |
| 3 | 2023-06-GSAFAC-0000386117 2023-004 | none | C | C | unchanged | Same as Codex. |
| 4 | 2022-06-GSAFAC-0000344738 2022-009 | LM (title) | C | V (corrected) | L (title) | Corrected by Claude. M appears only in the Effect section, a body sentence. Under the label-or-title rule the stated requirement is L only. |
| 5 | 2024-12-GSAFAC-0000378202 2024-002 | IP (label) | V | V | I (label) | ChatGPT: the label "Audit requirement 2 CFR Part 200" does not state P. |
| 6 | 2025-06-GSAFAC-0000390053 2025-001 | P (label) | O:E | O:E | E (label) | ChatGPT: the Criteria line states tenant eligibility, not generic program administration. |
| 7 | 2025-03-GSAFAC-0000378244 2025-001 | P (title) | O:N | O:N | N (title) | ChatGPT: wage rate requirements for this program are special tests and provisions (N), not P. Interpretive. |
| 8 | 2024-12-GSAFAC-0000379153 2024-001 | P (title) | O:N | O:N | N (title) | ChatGPT: wage rate requirements are special tests and provisions (N), not P. Interpretive. |
| 9 | 2023-12-GSAFAC-0000371385 2023-001 | P (title) | N | N | none | ChatGPT: expense allocation and financial management do not state a listed requirement. |
| 10 | 2023-09-GSAFAC-0000385438 2023-002 | P (title) | O:I | O:I | I (title) | ChatGPT: the Criteria line states contractor oversight under 2 CFR 200.318(b), a procurement standard. Interpretive. |
| 11 | 2025-04-GSAFAC-0000385028 2025-003 | I (label) | N | N | none | ChatGPT: HUD's auditor code I (failure to maintain property) is not Uniform Guidance requirement I (procurement). |
| 12 | 2024-12-GSAFAC-0000386773 2024-004 | EN (title) | C | O:N (corrected) | N (title) | Corrected by Claude. N is stated in the heading. E appears only in the Effect section, a body sentence, so it does not count. |
| 13 | 2025-06-GSAFAC-0000389543 2025-002 | I (title) | C | C | unchanged | Same as Codex. |
| 14 | 2023-06-GSAFAC-0000372331 2023-014 | E (title) | C | C | unchanged | Same as Codex. |
| 15 | 2024-12-GSAFAC-0000382385 2024-005 | L (label) | C | C | unchanged | Same as Codex. |
| 16 | 2024-09-GSAFAC-0000381391 2024-003 | N (label) | C | C | unchanged | Same as Codex. |
| 17 | 2024-12-GSAFAC-0000367150 2024-002 | N (label) | C | C | unchanged | Same as Codex. |
| 18 | 2024-06-GSAFAC-0000376484 2024-006 | L (title) | C | C | unchanged | Same as Codex. |
| 19 | 2024-06-GSAFAC-0000385908 2024-013 | L (label) | C | C | unchanged | Same as Codex. |
| 20 | 2024-12-GSAFAC-0000384513 2024-002 | L (label) | C | C | unchanged | Same as Codex. |
| 21 | 2024-12-GSAFAC-0000379743 2024-004 | I (title) | C | C | unchanged | Same as Codex. |
| 22 | 2024-12-GSAFAC-0000388031 2024-002 | I (label) | C | C | unchanged | Same as Codex. |
| 23 | 2025-05-GSAFAC-0000387661 2025-001 | N (label) | C | C | unchanged | Same as Codex. |
| 24 | 2023-12-GSAFAC-0000353950 2023-002 | E (title) | C | C | unchanged | Same as Codex. |
| 25 | 2024-12-GSAFAC-0000383942 2024-006 | N (label) | C | C | unchanged | Same as Codex. |
| 26 | 2023-06-GSAFAC-0000379613 2023-057 | L (title) | C | C | unchanged | Same as Codex. |
| 27 | 2024-12-GSAFAC-0000369422 2024-001 | E (label) | C | C | unchanged | Same as Codex. |
| 28 | 2024-12-GSAFAC-0000378268 2024-001 | L (title) | B | B | L (prose) | ChatGPT: the title alone does not state it. The body establishes quarterly reporting. |
| 29 | 2023-06-GSAFAC-0000385665 2023-003 | I (title) | A | A | unchanged | Same as Codex. |
| 30 | 2022-06-GSAFAC-0000369236 2022-003 | IM (label) | A | A | unchanged | Same as Codex. |
