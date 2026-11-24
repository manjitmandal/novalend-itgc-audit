# Glossary — plain-English audit terms used in this project

| Term | Plain-English meaning | Where it appears in NovaLend |
|---|---|---|
| **ITGC (IT General Controls)** | Everyday rules around IT systems: who can get in, who can change them, how new systems are built, and whether they run reliably. They make system output trustworthy. | The four domains audited for LendCore |
| **Application control** | A control built into one system, e.g. a system blocking a loan above a limit. | Out of scope; relies on ITGCs |
| **Financially significant system** | A system whose data feeds the financial statements. | LendCore and its database |
| **Audit objective** | The exact question the audit answers. | "Were LendCore ITGCs designed and operating effectively for FY 2025-26?" |
| **Audit criteria** | The rules reality is measured against. | "Leavers disabled within 1 business day" |
| **Risk** | Something that *could* go wrong and affect an objective (event → cause → consequence). | R-APD-02: leavers keep working access |
| **Inherent risk** | Risk before considering any controls. | Risk register, scored Likelihood × Impact |
| **Residual risk** | Risk remaining after controls. | Discussed in deficiency evaluation |
| **Control** | A rule or activity that prevents or detects a problem. | APD-02 leaver removal |
| **Control objective** | What the control must achieve. | "Leavers' access is removed promptly" |
| **Preventive / detective** | Preventive stops a problem; detective finds it afterwards. | APD-01 preventive; APD-03 detective |
| **Manual / automated** | Done by a person, or enforced by the system. | PC-03 automated (release tool permissions) |
| **Key control** | A control relied on to address a risk; always tested. | 12 of 15 controls |
| **RCM (Risk and Control Matrix)** | Table linking each risk to the controls that address it, with owner, frequency, evidence and test approach. | `02_RCM/NovaLend_RCM.xlsx` |
| **Walkthrough** | Following one real transaction end to end to confirm how a process works. | `04_Walkthroughs` |
| **Test of Design (ToD)** | Would the control work if it ran as described? | `05_Test_of_Design` |
| **Test of Operating Effectiveness (ToE)** | Did the control actually work, every time, all year? | `08_Test_of_Operating_Effectiveness` |
| **Population** | Every item a control applied to during the period. | 141 normal deployments |
| **IPE (Information Produced by the Entity)** | Reports or data from the company's systems used as evidence. Must be checked for completeness and accuracy. | The 13 system extracts |
| **Completeness and accuracy** | Nothing missing, nothing altered. | Record counts, duplicates, date coverage checks |
| **Sample** | The items selected from a population for testing. | 25 of 141 deployments |
| **Random seed** | A fixed number that makes random selection repeatable. | 20260515 |
| **Attribute** | A specific thing that must be true for a control to pass. | "Approved on or before deployment" |
| **Exception** | A tested item where an attribute failed. | 18 exceptions (EXC-01 to EXC-18) |
| **Full-population analytics** | Running the test on every record instead of a sample. | Found 11 exceptions sampling missed |
| **Condition / Criteria / Cause / Impact / Recommendation** | The five parts of a well-written finding: what we found, what should happen, why, so what, what to do. | Exception log, management letter |
| **Compensating control** | Another control that reduces the same risk when the main control fails. Only counted if it worked. | Quarterly access review considered for leavers — it also failed |
| **Control deficiency** | A control is missing or did not operate, with limited impact. | 7 controls |
| **Significant deficiency** | Serious enough to report to the Audit Committee, but less than a material weakness. | SD-1 access, SD-2 dev/prod segregation, SD-3 change authorisation |
| **Material weakness** | A reasonable possibility that a material misstatement won't be prevented or detected. | None identified within scope |
| **Root cause** | The underlying reason a control failed (found by asking "why?" repeatedly). | Email-based leaver hand-off |
| **Segregation of duties (SoD)** | One person shouldn't be able to both make and approve/deploy a change. | Developer deployed own change (EXC-12) |
| **Emergency change** | Urgent fix deployed before normal approval, approved afterwards. | Must be approved within 2 business days |
| **UAT (User Acceptance Testing)** | Business users confirm a change works before it goes live. | PC-01, PD-02 |
| **Management letter** | Report to the Audit Committee with findings, ratings and agreed actions. | `10_Reporting/Management_Letter.pdf` |
| **Remediation** | Actions management takes to fix a finding. | `Remediation_Tracker.xlsx` |
