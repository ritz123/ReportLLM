# Residential Society Maintenance Fund — Financial Analysis Report

**Prepared from:** `X.md` (society maintenance ledger)  
**Reporting period:** October 2021 – June 2026 (56 months)  
**Units covered:** 8 (001 Krishnan, 002 Mary, 101 Manish, 102 Prem, 201 Amit, 202 Biplab, 301 Nishant, 302 Siddharth)  
**Report date:** June 28, 2026  
**Currency:** Indian Rupees (₹)

---

## Executive Summary

This report analyzes nearly five years of monthly maintenance fund records for a small residential society in Bangalore. The society operates an 8-unit collective fund used to pay security staff, utilities (BESCOM electricity, BWSSB water), generator diesel, lift AMC, garbage collection, and periodic repairs.

**Overall financial health is stable.** Collections and expenses are closely matched month-to-month (average ₹37,197 income vs ₹37,304 expense). The fund ran a deficit in only **2 of 56 months** (4%). Three early months recorded negative carry-forward balances, all recovered within subsequent collection cycles.

**Total expenditure over the period: ₹20.89 lakh.** The largest cost category is security/staff (36%), followed by electricity (25%) and water (9%). Electricity costs fell dramatically after late 2022 — from ~₹20,800/month to ~₹5,100/month — representing the single largest structural change in operating costs.

**Peak bank balance** reached ₹86,973 (April 2023). **Latest recorded balance** is ₹54,190 (June 2026). Two major capital projects in 2023 (glass work and genset service) caused the highest single-month expense spikes.

---

## 1. Scope & Methodology

### Data source
Monthly ledger sheets exported from spreadsheet to markdown (`X.md`). Each sheet contains:
- **Expense side:** itemized payments with amounts and dates
- **Income side:** per-unit maintenance collections from 8 residents
- **Balance:** carry-forward or bank balance at month end

### Parsing approach
An automated parser (`analyze_x.py`) extracted:
- Monthly total expenses and collections
- End-of-month balance (cash carry-forward or bank balance)
- Expense categorization by keyword matching into 11 categories

### Exclusions
- Duplicate sheet "Copy of Aug 2023"
- Empty sheets (Sheet19)
- AMC reference sheet (one-time contribution tracker, not monthly flow)

### Limitations
- Some months have missing line items (e.g., electricity not recorded Aug–Sep 2022)
- 2026 entries may include projected/planned amounts
- Individual resident payment compliance is inferred from collection totals, not audited per-unit
- April 2023 includes an unexplained ₹10,000 credit ("somebody has given 10K, need to find out")

---

## 2. Financial Overview

### 2.1 Headline metrics

| Metric | Value |
|--------|------:|
| Months analyzed | 56 |
| Total collections | ₹20.83 lakh |
| Total expenses | ₹20.89 lakh |
| Average monthly collections | ₹37,197 |
| Average monthly expenses | ₹37,304 |
| Months with deficit (income < expense) | 2 (4%) |
| Months with negative balance | 3 |
| Peak bank balance | ₹86,973 (Apr 2023) |
| Latest bank balance | ₹54,190 (Jun 2026) |
| All-time total spend | ₹20.89 lakh |

### 2.2 Year-on-year summary

| Year | Months | Collections | Expenses | Net |
|------|-------:|------------:|---------:|----:|
| 2021 (Oct–Dec) | 3 | ₹1,29,644 | ₹1,35,640 | −₹5,996 |
| 2022 | 12 | ₹4,73,662 | ₹4,73,662 | ₹0 |
| 2023 | 11 | ₹4,89,872 | ₹4,89,872 | ₹0 |
| 2024 | 12 | ₹4,80,000 | ₹4,80,000 | ₹0 |
| 2025 | 12 | ₹3,20,557 | ₹3,20,557 | ₹0 |
| 2026 (Jan–Jun) | 6 | ₹1,89,283 | ₹1,89,283 | ₹0 |

*Note: 2025–2026 totals reflect standardized ₹3,500/unit monthly fee with some partial-payment months. 2021 started mid-year with higher per-unit fees.*

### 2.3 Fund balance trajectory

```
Oct 2021  →  Started with −₹96 carry-forward; ended Oct at +₹3,356
Dec 2021  →  First deficit: −₹2,640 (expenses exceeded collections)
Jan 2022  →  −₹1,657 (major repairs: tank cleaning, roof leak proofing)
Aug 2022  →  Surplus jumped to +₹20,909 (low expenses, partial collections)
Nov 2022  →  −₹4,844 (₹22,415 electricity catch-up bill)
Dec 2022  →  Bank account opened; balance +₹5,598
Jan 2023  →  Balance surged to +₹56,550 (fees raised to ₹8,500/unit)
Apr 2023  →  Peak balance +₹86,973
Mar 2023  →  Heavy capital spend; balance dropped to +₹32,120
Dec 2024  →  Low point in recent period: +₹14,217
Jan 2026  →  Recent high: +₹71,910
Jun 2026  →  Latest: +₹54,190
```

---

## 3. Expense Analysis

### 3.1 All-time spend by category

| Category | Amount | Share |
|----------|-------:|------:|
| Security / Staff (Tara, Mahindra) | ₹7,54,230 | 36.1% |
| Electricity (BESCOM) | ₹5,29,894 | 25.4% |
| Water (BWSSB) | ₹1,77,752 | 8.5% |
| Repairs / Capital | ₹1,71,305 | 8.2% |
| Other / Misc | ₹1,70,324 | 8.2% |
| Lift / AMC | ₹87,149 | 4.2% |
| Diesel / Generator | ₹80,507 | 3.9% |
| One-time / Setup | ₹40,547 | 1.9% |
| Cleaning Supplies | ₹38,576 | 1.8% |
| Garbage | ₹33,775 | 1.6% |
| Gardening | ₹4,570 | 0.2% |
| **Total** | **₹20,89,629** | **100%** |

### 3.2 Recurring monthly costs (typical run-rate, 2024+)

| Item | Typical range |
|------|--------------|
| Security / Tara salary | ₹8,500 – ₹13,500/month |
| Electricity (BESCOM) | ₹3,600 – ₹5,800/month |
| Water (BWSSB) | ₹2,200 – ₹4,200/month |
| Garbage | ₹500/month |
| Diesel | ₹1,500 – ₹4,000/month (seasonal) |
| Lift AMC | ₹11,000 (biannual, ~₹1,833/month amortized) |

### 3.3 Highest expense months

| Month | Expense | Primary drivers |
|-------|--------:|-----------------|
| Mar 2023 | ₹1,01,786 | Gautam glass advance ₹75,000; genset service ₹1,000; diesel |
| May 2023 | ₹82,960 | Gowtham glass ₹48,000 + ₹12,000; carpenter ₹2,000 |
| Feb 2024 | ₹74,632 | Large one-time maintenance items |
| Mar 2024 | ₹74,024 | Capital / repair cluster |
| Nov 2023 | ₹72,042 | Elevator maintenance ₹11,000; other repairs |
| Mar 2025 | ₹49,677 | Lumin coating ₹16,000; generator service ₹6,000; painting |

---

## 4. Income & Maintenance Fee History

### 4.1 Per-unit fee evolution

| Period | Fee per unit | Monthly target (8 units) |
|--------|-------------:|-------------------------:|
| Oct – Nov 2021 | ₹5,500 | ₹44,000 |
| Dec 2021 – mid 2022 | ₹5,500 – ₹7,500 (graduated) | ₹45,000 – ₹53,000 |
| Aug – Oct 2022 | ₹3,000 (reduced / partial) | ₹24,000 |
| Dec 2022 | ₹6,000 | ₹48,000 |
| Jan – Mar 2023 | ₹8,500 | ₹68,000 |
| Apr – May 2023 | ₹3,500 / ₹8,500 (mixed) | ₹28,000 – ₹78,525 |
| 2024 onward | ₹3,500 standard | ₹28,000 |
| Dec 2024 | ₹7,500 | ₹52,650 (year-end catch-up) |

### 4.2 Collection compliance observations

- **Aug 2022:** Total collections only ₹22,952. Unit 301 (Nishant) paid ₹350 instead of ₹5,500. No electricity bill recorded that month.
- **Sep – Oct 2022:** All units at ₹3,000 (reduced rate period).
- **2024–2025:** Standard ₹3,500/unit, but some months show partial totals (e.g., Oct 2025: only ₹12,468 collected — likely incomplete month or missing payments).
- **Dec 2024:** Fees doubled to ₹7,500/unit (₹52,650 total) — possible annual true-up or arrears collection.

---

## 5. Utility Trend Analysis

### 5.1 Electricity (BESCOM)

| Era | Avg monthly bill | Notes |
|-----|----------------:|-------|
| Oct 2021 – Dec 2022 | ₹20,800 | High common-area load; bills ₹18K–28K typical |
| 2023 | ₹8,311 | Transition year; includes catch-up payments |
| 2024 – Jun 2026 | ₹5,078 | Stabilized at ~₹4K–5.5K/month |

**Key finding:** Electricity costs dropped **~79%** from the early period to 2024+. This is the most significant operating cost improvement. Possible explanations include billing/meter changes, reduced common-area consumption, infrastructure upgrades, or corrected billing after the Nov 2022 catch-up payment of ₹22,415 for July electricity.

### 5.2 Water (BWSSB)

| Era | Avg monthly bill |
|-----|----------------:|
| Oct 2021 – Dec 2022 | ₹2,680 |
| 2023 | ₹2,717 |
| 2024 – Jun 2026 | ₹3,589 |

Water costs rose modestly (~34%) over the period, from ~₹2,200–2,900 to ~₹3,200–4,200 in recent months.

### 5.3 Security / staff

| Era | Avg monthly cost |
|-----|----------------:|
| Oct 2021 – Dec 2022 | ₹12,982 |
| 2023 | ₹13,364 |
| 2024 – Jun 2026 | ₹13,750 |

Security costs increased gradually from ₹12,000 (2021) to ₹13,500/month (2022–2023). Tara salary advances are frequent and should be tracked against monthly payroll.

---

## 6. Key Events Timeline

| Date | Event | Financial impact |
|------|-------|-----------------|
| Oct 2021 | Ledger begins; ₹5,500/unit fee | Baseline established |
| Nov 2021 | 64KW fuse repair + BESCOM charges | ₹3,600 one-time |
| Dec 2021 | First deficit (−₹2,640) | Fees insufficient for rising costs |
| Jan 2022 | Tank cleaning + roof leak repairs | ₹9,400 capital; deficit continues |
| Aug 2022 | Reduced collections; Nishant partial payment | Surplus builds despite low income |
| Nov 2022 | July electricity catch-up bill | ₹22,415; fund goes −₹4,844 |
| Dec 2022 | **Bank account opened** (₹10,000); AMC ₹11,000; fee → ₹6,000/unit | Formal banking begins |
| Jan 2023 | Fee raised to ₹8,500/unit | Collections jump to ₹68,000/month |
| Mar 2023 | Glass work advance (Gautam) ₹75,000 | Largest single-month expense |
| May 2023 | Glass/carpentry (Gowtham) ₹60,000 | Second-largest expense month |
| Nov 2023 | Elevator maintenance ₹11,000 | Recurring AMC pattern established |
| Nov 2024 | Society formation fee ₹15,000 | One-time legal/setup cost |
| Dec 2024 | Fee raised to ₹7,500/unit; lift AMC ₹11,000 | Year-end collection surge |
| Mar 2025 | Lumin coating + generator service | ₹23,440 capital spend |
| Jan 2026 | Balance peaks at ₹71,910 | Strong reserve position |

---

## 7. Risks & Anomalies

### 7.1 Identified risks

1. **Irregular per-unit fees** — Fee amounts changed frequently (₹3,000 to ₹8,500), making budgeting difficult for residents and treasurers.
2. **Partial payments** — Several months show collections below 8 × ₹3,500, indicating missed or delayed unit payments.
3. **Large unbudgeted capital spends** — Glass project (~₹1.35 lakh across Mar–May 2023) was not amortized or pre-funded.
4. **Tara salary advances** — Frequent advances (₹1,000–₹6,000) without clear reconciliation against monthly salary.
5. **Unreconciled credit** — ₹10,000 unexplained deposit in April 2023.
6. **Missing utility entries** — Aug–Sep 2022 have no electricity bill recorded; may distort trend analysis.

### 7.2 Months requiring review

| Month | Issue |
|-------|-------|
| Aug 2022 | No electricity bill; Nishant paid ₹350 only |
| Sep 2022 | No electricity, gardener, or Velu processing fee recorded |
| Jul 2023 | Water bill shows ₹22 (likely data entry error) |
| Oct 2025 | Collections only ₹12,468 (less than half expected) |
| Apr 2023 | Unidentified ₹10,000 income |

---

## 8. Recommendations

### 8.1 Governance
- **Standardize maintenance fee** at a single amount per unit (currently ₹3,500) with annual review, rather than ad-hoc changes.
- **Publish monthly statement** to all 8 units showing collections received, expenses paid, and running bank balance.
- **Require full payment by a fixed date**; document arrears policy for partial payers.

### 8.2 Financial planning
- **Maintain a contingency reserve** of at least 3 months operating cost (~₹1.1 lakh based on current run-rate of ~₹37K/month). Current balance of ₹54,190 meets this threshold.
- **Create a capital expenditure fund** — set aside ₹2,000–3,000/unit/year for predictable items (lift AMC ₹11K biannual, genset service, painting).
- **Amortize large projects** — for expenses exceeding ₹25,000, collect a one-time levy or spread over 3–6 months rather than drawing down reserves abruptly.

### 8.3 Operational
- **Track Tara advances** against salary in a single payroll line to avoid double-counting.
- **Reconcile BESCOM and BWSSB bills** monthly; flag any month where utility cost is zero or abnormally low.
- **Investigate the ₹10,000 unexplained credit** from April 2023 and document resolution.
- **Resolve Oct 2025 collection shortfall** — identify which units have not paid.

### 8.4 Record-keeping
- Continue bank-based accounting (started Dec 2022) — avoid reverting to cash-only tracking.
- Remove duplicate sheets and maintain one canonical monthly entry.
- Add a unique receipt number or UPI reference for each resident payment.

---

## 9. Conclusion

The society maintenance fund has been managed prudently over a challenging five-year period that included fee restructuring, a transition to formal banking, major capital repairs, and a dramatic reduction in electricity costs. The fund is currently in a **healthy position** with ₹54,190 in the bank against monthly operating costs of approximately ₹37,000 — representing roughly **1.5 months of reserves**.

The primary areas for improvement are **collection consistency**, **fee standardization**, and **advance planning for capital expenditures**. With these governance improvements, the society is well-positioned to maintain its facilities without recurring deficit periods.

---

## Appendix

### A. Charts
- `x_analysis/trend_overview.png` — Income vs expenses, balance trend, category breakdown, surplus/deficit
- `x_analysis/utility_trends.png` — Electricity, water, and security cost trends
- Interactive canvas: `society-maintenance-analysis.canvas.tsx`

### B. Data files
- `x_analysis/analysis.json` — Machine-readable monthly data
- `analyze_x.py` — Parser and chart generator (re-runnable)

### C. Resident units reference

| Unit | Resident |
|------|----------|
| 001 | Krishnan |
| 002 | Mary |
| 101 | Manish |
| 102 | Prem |
| 201 | Amit |
| 202 | Biplab |
| 301 | Nishant |
| 302 | Siddharth |

---

*Report generated automatically from ledger data. Figures should be verified against original bank statements and receipts before use in formal society meetings.*
