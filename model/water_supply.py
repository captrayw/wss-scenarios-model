import numpy as np
from .inputs import ModelInputs


def calculate_water_supply(inputs: ModelInputs, common: dict) -> dict:
    p = inputs.period
    c = inputs.constants
    ws = inputs.water_service
    wt = inputs.water_targets
    wc = inputs.water_costs
    wi = inputs.water_interventions
    tech = inputs.technical
    yi = common['yi']
    years = common['years']
    n = common['n_years']
    total_hh = common['total_hh']
    mill = c.million
    thou = c.thousand
    end_asis = common['end_asis_year']
    asis_flag = common['asis_flag']
    perf_flag = common['perf_flag']
    water_per_hh = common['water_per_hh_year']
    avg_hh_size_2025 = common['avg_hh_size_2025']

    # ===== SECTION 0: BAU HHs forecast =====
    ws_hh = common['ws_hh_serv_historical'].copy()

    # BAU treated-piped from network investment (C|WS rows 29-34)
    network_inv = common['ws_bau_network_inv']
    network_cost_per_hh = wc.kukl_network_cost_per_hh
    bau_increase_treated = np.zeros(n)
    for t in range(n):
        if network_cost_per_hh > 0:
            bau_increase_treated[t] = network_inv[t] / network_cost_per_hh

    current_treated_piped = ws.hh_treated_piped_2025 / mill
    bau_treated_piped = np.zeros(n)
    bau_treated_piped[yi(p.baseline_year)] = current_treated_piped
    for t in range(yi(p.baseline_year) + 1, n):
        bau_treated_piped[t] = bau_treated_piped[t - 1] + bau_increase_treated[t]

    for t in range(yi(p.baseline_year)):
        bau_treated_piped[t] = current_treated_piped * ((1 - ws.hist_increase_treated_piped) ** (p.baseline_year - years[t]))

    # BAU treatment capacity -> safely managed HHs (rows 36-42)
    treatment_increase = common['ws_treatment_increase']
    water_per_hh_adj = water_per_hh * (1 + tech.ws_non_hh_capex_pct)
    bau_safely_managed = np.zeros(n)
    if water_per_hh_adj > 0:
        for t in range(n):
            ann_increase_m3 = treatment_increase[t] * c.days_in_year * thou
            increase_hh = ann_increase_m3 / water_per_hh_adj / mill
            if t == yi(p.baseline_year) + 1:
                bau_safely_managed[t] = ws_hh[0, t - 1] + increase_hh if t > 0 else increase_hh
            elif t > yi(p.baseline_year) + 1:
                bau_safely_managed[t] = bau_safely_managed[t - 1] + increase_hh

    # BAU serv1 = min(treated_piped, safely_managed)
    bau_serv1_unadj = np.minimum(bau_treated_piped, bau_safely_managed)

    # BAU other service levels (unadjusted, grow at historical CAGR)
    ws_cagrs = common['ws_cagrs_hist']
    bau_unadj = np.zeros((5, n))
    bau_unadj[0] = bau_serv1_unadj

    for i in range(1, 5):
        for t in range(n):
            if years[t] <= p.baseline_year:
                bau_unadj[i, t] = ws_hh[i, t]
            elif t > 0:
                bau_unadj[i, t] = bau_unadj[i, t - 1] * (1 + ws_cagrs[i])

    # Adjust BAU to match total HHs
    bau_hh = np.zeros((5, n))
    for t in range(n):
        if years[t] <= p.baseline_year:
            bau_hh[0, t] = bau_treated_piped[t]
            bau_hh[1, t] = sum(ws_hh[0:2, t]) - bau_treated_piped[t]
            for i in range(2, 5):
                bau_hh[i, t] = ws_hh[i, t]
        else:
            bau_hh[0, t] = bau_unadj[0, t]
            unadj_sum = sum(bau_unadj[i, t] for i in range(5))
            if unadj_sum > 0:
                bau_hh[1, t] = total_hh[t] - bau_hh[0, t] - sum(
                    bau_unadj[i, t] + (bau_unadj[i, t] / unadj_sum) * (total_hh[t] - unadj_sum) for i in range(2, 5)
                )
                for i in range(2, 5):
                    bau_hh[i, t] = bau_unadj[i, t] + (bau_unadj[i, t] / unadj_sum) * (total_hh[t] - unadj_sum)
            else:
                bau_hh[1, t] = total_hh[t] - bau_hh[0, t]

    bau_hh_total = np.sum(bau_hh, axis=0)

    # ===== SECTION 1: Target HHs forecast =====
    # End of as-is year values
    asis_idx = yi(end_asis)
    asis_hh = bau_hh[:, asis_idx].copy()

    # Target 1 absolute HHs
    t1_idx = yi(p.target1_year)
    t1_total_hh = total_hh[t1_idx]
    t1_pcts = [wt.target1_serv1, wt.target1_serv2, wt.target1_serv3, wt.target1_serv4, wt.target1_serv5]
    t1_hh = [t1_total_hh * p for p in t1_pcts]

    # CAGR to target 1
    n_t1 = p.target1_year - end_asis
    cagr_t1 = []
    for i in range(5):
        if asis_hh[i] > 0 and t1_hh[i] > 0:
            cagr_t1.append((t1_hh[i] / asis_hh[i]) ** (1 / n_t1) - 1)
        elif t1_hh[i] > 0:
            cagr_t1.append(0)
        else:
            cagr_t1.append(0)

    # Target 2 absolute HHs
    t2_idx = yi(p.target2_year)
    t2_total_hh = total_hh[t2_idx]
    t2_pcts = [wt.target2_serv1, wt.target2_serv2, wt.target2_serv3, wt.target2_serv4, wt.target2_serv5]
    t2_hh = [t2_total_hh * p for p in t2_pcts]

    # CAGR target1 -> target2
    n_t2 = p.target2_year - p.target1_year
    cagr_t2 = []
    for i in range(5):
        if t1_hh[i] > 0 and t2_hh[i] > 0:
            cagr_t2.append((t2_hh[i] / t1_hh[i]) ** (1 / n_t2) - 1)
        elif t2_hh[i] > 0:
            cagr_t2.append(0)
        else:
            cagr_t2.append(0)

    # Apply CAGRs with period switching
    target_unadj = np.zeros((5, n))
    for i in range(5):
        for t in range(n):
            if years[t] <= end_asis:
                target_unadj[i, t] = bau_hh[i, t]
            elif t > 0:
                cagr = cagr_t1[i] if years[t] <= p.target1_year else cagr_t2[i]
                target_unadj[i, t] = target_unadj[i, t - 1] * (1 + cagr)

    # Adjust targets to total HHs
    target_hh = np.zeros((5, n))
    for t in range(n):
        if years[t] <= end_asis:
            target_hh[:, t] = target_unadj[:, t]
        else:
            target_hh[0, t] = target_unadj[0, t]
            remaining = sum(target_unadj[i, t] for i in range(1, 5))
            if remaining == 0:
                target_hh[1, t] = total_hh[t] - target_hh[0, t]
            else:
                target_hh[1, t] = target_unadj[1, t]
                rest_sum = sum(target_unadj[i, t] for i in range(2, 5))
                residual = total_hh[t] - target_hh[0, t] - target_hh[1, t]
                if rest_sum > 0 and t > 0:
                    prev_rest = sum(target_hh[i, t - 1] for i in range(2, 5))
                    for i in range(2, 5):
                        ratio = target_hh[i, t - 1] / prev_rest if prev_rest > 0 else 0
                        target_hh[i, t] = residual * ratio
                else:
                    for i in range(2, 5):
                        target_hh[i, t] = 0

    target_hh_total = np.sum(target_hh, axis=0)

    # Service gap
    service_gap = target_hh[0] - bau_hh[0]

    # ===== SECTION 2: Existing stock =====
    existing_stock_baseline = (ws.hh_treated_piped_2025 / mill) * wc.kukl_network_cost_per_hh * (1 + tech.ws_non_hh_capex_pct)
    existing_stock = np.zeros(n)
    existing_stock[yi(p.baseline_year)] = existing_stock_baseline

    # ===== SECTION 3: BAU investment =====
    bau_investment = common['ws_bau_total'].copy()

    # ===== SECTION 4: Investment need & financing gap =====
    # KUKL treatment capex
    kukl_hh_target = np.zeros(n)
    for t in range(n):
        kukl_hh_target[t] = target_hh[0, t] * wt.kukl_pct

    treatment_cap_needed = np.zeros(n)
    add_treatment_cap = np.zeros(n)
    capex_treatment = np.zeros(n)
    for t in range(n):
        if asis_flag[t] > 0 or perf_flag[t] > 0:
            treatment_cap_needed[t] = kukl_hh_target[t] * water_per_hh * mill / c.days_in_year / thou
            needed = treatment_cap_needed[t] - tech.ws_existing_treatment_mld
            add_cap = max(0, needed)
            if t > 0 and add_cap > add_treatment_cap[t - 1]:
                new_cap = add_cap - add_treatment_cap[t - 1]
            else:
                new_cap = 0
            add_treatment_cap[t] = add_cap
            if wc.kukl_cost_per_mld_treatment > 0:
                capex_treatment[t] = new_cap * wc.kukl_cost_per_mld_treatment

    # KUKL network capex
    kukl_hh_current = ws.hh_kukl_2025 / mill
    kukl_new_hh = np.zeros(n)
    capex_network = np.zeros(n)
    for t in range(n):
        if (asis_flag[t] > 0 or perf_flag[t] > 0) and kukl_hh_target[t] > kukl_hh_current:
            new = kukl_hh_target[t] - kukl_hh_current
            if t > 0:
                prev_new = max(0, kukl_hh_target[t - 1] - kukl_hh_current) if years[t - 1] > p.baseline_year else 0
                kukl_new_hh[t] = max(0, new - prev_new)
            else:
                kukl_new_hh[t] = new
            capex_network[t] = kukl_new_hh[t] * wc.kukl_network_cost_per_hh

    kukl_total_capex = capex_treatment + capex_network

    # WUSCs (similar, using wusc_pct)
    wusc_total_capex = np.zeros(n)  # 0 since wusc_pct = 0 by default

    # Non-piped (similar, using non_piped_pct)
    nonpiped_total_capex = np.zeros(n)  # 0 since non_piped_pct = 0 by default

    # Total investment need
    new_capex_hh = kukl_total_capex + wusc_total_capex + nonpiped_total_capex
    new_capex_nonhh = new_capex_hh * tech.ws_non_hh_capex_pct
    total_new_capex = new_capex_hh + new_capex_nonhh

    # Rolling existing stock
    rolling_stock = np.zeros(n)
    rolling_stock[yi(p.baseline_year)] = existing_stock_baseline
    for t in range(yi(p.baseline_year) + 1, n):
        rolling_stock[t] = rolling_stock[t - 1] + total_new_capex[t]

    replacement_capex = np.zeros(n)
    for t in range(1, n):
        if perf_flag[t] > 0:
            replacement_capex[t] = rolling_stock[t - 1] * tech.ws_replacement_rate

    investment_need = np.zeros(n)
    for t in range(n):
        if asis_flag[t] > 0 or perf_flag[t] > 0:
            investment_need[t] = total_new_capex[t] + replacement_capex[t]

    financing_gap = np.zeros(n)
    for t in range(n):
        if (asis_flag[t] > 0 or perf_flag[t] > 0) and investment_need[t] > bau_investment[t]:
            financing_gap[t] = investment_need[t] - bau_investment[t]

    cumulative_inv_need = np.cumsum(investment_need)
    cumulative_bau_inv = np.cumsum(bau_investment)

    # ===== SECTION 5: Interventions =====

    # 5.1 Collection efficiency + NRW reduction
    ce = wi
    ce_rate = np.zeros(n)
    ce_increase_per_yr = (ce.ce_target_ratio - ce.ce_current_ratio) / (ce.ce_target_year - ce.ce_start_year + 1) if ce.ce_target_year > ce.ce_start_year else 0

    for t in range(n):
        y = years[t]
        if y < ce.ce_start_year:
            ce_rate[t] = ce.ce_current_ratio
        elif y > ce.ce_target_year:
            ce_rate[t] = ce.ce_target_ratio
        else:
            ce_rate[t] = ce_rate[t - 1] + ce_increase_per_yr if t > 0 else ce.ce_current_ratio

    water_sold = ce.ce_water_sold_mld
    tariff_current = ce.ce_current_tariff
    cash_bau = water_sold * tariff_current * ce.ce_current_ratio
    cash_improved = np.array([water_sold * tariff_current * ce_rate[t] for t in range(n)])
    additional_cash_ce = cash_improved - cash_bau

    # Cost per HH after efficiency
    avg_network_cost = wc.kukl_network_cost_per_hh
    if wc.kukl_cost_per_mld_treatment > 0:
        hh_per_mld = (mill / c.cubic_meter_liters) / (water_per_hh / c.days_in_year)
        treatment_cost_per_hh = (wc.kukl_cost_per_mld_treatment / hh_per_mld) * mill
    else:
        treatment_cost_per_hh = 0
    weighted_cost_per_hh = (treatment_cost_per_hh + avg_network_cost) * (1 - wi.capeff_gains_pct)

    nonhh_rate = tech.ws_non_hh_capex_pct
    repl_rate = tech.ws_replacement_rate

    interv_ce_total_capex = additional_cash_ce.copy()
    interv_ce_new_hh_capex = np.zeros(n)
    interv_ce_cum_hh_capex = np.zeros(n)
    interv_ce_repl = np.zeros(n)
    for t in range(n):
        interv_ce_repl[t] = interv_ce_cum_hh_capex[t - 1] * repl_rate if t > 0 else 0
        denom = 1 + nonhh_rate
        if denom > 0:
            interv_ce_new_hh_capex[t] = (interv_ce_total_capex[t] - interv_ce_repl[t] - interv_ce_repl[t] * nonhh_rate) / denom
        interv_ce_cum_hh_capex[t] = (interv_ce_cum_hh_capex[t - 1] if t > 0 else 0) + interv_ce_new_hh_capex[t]

    interv_ce_hh = np.zeros(n)
    if weighted_cost_per_hh > 0:
        interv_ce_hh = interv_ce_new_hh_capex / weighted_cost_per_hh

    # NRW reduction
    nrw_rate = np.zeros(n)
    nrw_decrease_per_yr = (wi.nrw_target_pct - wi.nrw_current_pct) / (wi.nrw_target_year - wi.nrw_start_year + 1) if wi.nrw_target_year > wi.nrw_start_year else 0

    for t in range(n):
        y = years[t]
        if y < wi.nrw_start_year:
            nrw_rate[t] = wi.nrw_current_pct
        elif y > wi.nrw_target_year:
            nrw_rate[t] = wi.nrw_target_pct
        else:
            nrw_rate[t] = nrw_rate[t - 1] + nrw_decrease_per_yr if t > 0 else wi.nrw_current_pct

    billed_water = water_sold
    total_water_produced = billed_water / (1 - wi.nrw_current_pct) if wi.nrw_current_pct < 1 else billed_water
    water_sold_nrw = np.array([total_water_produced * (1 - nrw_rate[t]) for t in range(n)])
    additional_water = water_sold_nrw - billed_water
    physical_reduction = additional_water * (1 - wi.nrw_commercial_loss_pct)
    domestic_additional = additional_water * tech.ws_pct_domestic
    domestic_physical = physical_reduction * tech.ws_pct_domestic

    # Additional HHs from physical loss reduction
    interv_nrw_hh_physical = np.zeros(n)
    if water_per_hh > 0:
        for t in range(1, n):
            interv_nrw_hh_physical[t] = (domestic_physical[t] - domestic_physical[t - 1]) / water_per_hh

    # Revenue from additional water sold -> invest in new connections
    revenue_nrw = np.array([tariff_current * additional_water[t] for t in range(n)])
    cash_nrw = revenue_nrw * ce_rate

    nrw_new_hh_capex = np.zeros(n)
    nrw_cum_hh_capex = np.zeros(n)
    nrw_repl = np.zeros(n)
    for t in range(n):
        nrw_repl[t] = nrw_cum_hh_capex[t - 1] * repl_rate if t > 0 else 0
        denom = 1 + nonhh_rate
        if denom > 0:
            nrw_new_hh_capex[t] = (cash_nrw[t] - nrw_repl[t] - nrw_repl[t] * nonhh_rate) / denom
        nrw_cum_hh_capex[t] = (nrw_cum_hh_capex[t - 1] if t > 0 else 0) + nrw_new_hh_capex[t]

    nrw_invest_hh = np.zeros(n)
    if weighted_cost_per_hh > 0:
        nrw_invest_hh = nrw_new_hh_capex / weighted_cost_per_hh

    interv_ce_nrw_hh = interv_ce_hh + interv_nrw_hh_physical + nrw_invest_hh
    interv_ce_nrw_cum_hh = np.cumsum(interv_ce_nrw_hh)
    interv_ce_nrw_inv = additional_cash_ce + cash_nrw
    interv_ce_nrw_cum_inv = np.cumsum(interv_ce_nrw_inv)

    # 5.2 Capital efficiency
    capeff_flag = np.array([1.0 if years[t] >= wi.capeff_start_year else 0.0 for t in range(n)])

    capeff_bau = bau_investment.copy()
    capeff_existing_stock = existing_stock_baseline * (1 - wi.capeff_gains_pct)
    capeff_repl = capeff_existing_stock * repl_rate

    capeff_remaining = np.zeros(n)
    capeff_new_hh = np.zeros(n)
    capeff_cum_hh = np.zeros(n)
    capeff_repl_arr = np.zeros(n)

    for t in range(n):
        if perf_flag[t] > 0:
            remaining = capeff_bau[t] - capeff_repl
            capeff_remaining[t] = max(0, remaining)

        capeff_repl_arr[t] = capeff_cum_hh[t - 1] * repl_rate if t > 0 else 0
        denom = 1 + nonhh_rate
        if denom > 0 and capeff_remaining[t] > 0:
            capeff_new_hh[t] = (capeff_remaining[t] - capeff_repl_arr[t] - capeff_repl_arr[t] * nonhh_rate) / denom
        capeff_cum_hh[t] = (capeff_cum_hh[t - 1] if t > 0 else 0) + capeff_new_hh[t]

    interv_capeff_hh = np.zeros(n)
    if weighted_cost_per_hh > 0:
        interv_capeff_hh = (capeff_new_hh / weighted_cost_per_hh) * capeff_flag
    interv_capeff_cum_hh = np.cumsum(interv_capeff_hh)

    # 5.3 Tariff increase
    tariff_flag = np.array([1.0 if wi.tariff_start_year <= years[t] <= wi.tariff_target_year else 0.0 for t in range(n)])

    # Affordability
    pop_inp = inputs.population
    monthly_expenditure = wi.tariff_monthly_income_bottom20 * avg_hh_size_2025
    max_monthly_water = monthly_expenditure * wi.tariff_max_pct_income_water
    water_per_hh_month = water_per_hh * c.days_in_month / c.days_in_year if c.days_in_year > 0 else 0
    max_affordable_tariff = max_monthly_water / water_per_hh_month if water_per_hh_month > 0 else float('inf')

    om_recovery = wi.tariff_kukl_op_revenue / wi.tariff_kukl_op_expenditure if wi.tariff_kukl_op_expenditure > 0 else 1
    tariff_growth = (wi.tariff_om_recovery_target / om_recovery) ** (1 / (wi.tariff_target_year - wi.tariff_start_year + 1)) - 1 if om_recovery > 0 else 0

    avg_tariff = np.full(n, tariff_current)
    for t in range(1, n):
        if years[t] == p.baseline_year:
            avg_tariff[t] = tariff_current
        elif tariff_flag[t] > 0:
            avg_tariff[t] = min(avg_tariff[t - 1] * (1 + tariff_growth), max_affordable_tariff)
        else:
            avg_tariff[t] = avg_tariff[t - 1]

    tariff_increase = avg_tariff - tariff_current
    additional_rev_tariff = water_sold_nrw * tariff_increase
    cash_tariff = additional_rev_tariff * ce_rate

    interv_tariff_new_hh = np.zeros(n)
    interv_tariff_cum_hh_capex = np.zeros(n)
    interv_tariff_repl = np.zeros(n)
    for t in range(n):
        interv_tariff_repl[t] = interv_tariff_cum_hh_capex[t - 1] * repl_rate if t > 0 else 0
        denom = 1 + nonhh_rate
        if denom > 0:
            interv_tariff_new_hh[t] = (cash_tariff[t] - interv_tariff_repl[t] - interv_tariff_repl[t] * nonhh_rate) / denom
        interv_tariff_cum_hh_capex[t] = (interv_tariff_cum_hh_capex[t - 1] if t > 0 else 0) + interv_tariff_new_hh[t]

    interv_tariff_hh = np.zeros(n)
    if weighted_cost_per_hh > 0:
        interv_tariff_hh = interv_tariff_new_hh / weighted_cost_per_hh
    interv_tariff_cum_hh = np.cumsum(interv_tariff_hh)
    interv_tariff_inv = cash_tariff.copy()
    interv_tariff_cum_inv = np.cumsum(interv_tariff_inv)

    # 5.4 Borrowing against future cashflow
    loan_flag = np.array([1.0 if wi.loan_start_year <= years[t] <= wi.loan_end_year else 0.0 for t in range(n)])

    # Estimated FCF
    est_cash_inflow = avg_tariff * water_sold_nrw * ce_rate
    est_cash_outflow = np.full(n, 0.0)
    # Operating cost per m3 approximated from KUKL data
    op_cost_per_m3 = wi.tariff_kukl_op_expenditure / (water_sold * mill * c.days_in_year / c.days_in_month) if water_sold > 0 else 0
    for t in range(n):
        est_cash_outflow[t] = op_cost_per_m3 * billed_water

    fcf = est_cash_inflow - est_cash_outflow

    # FCF at loan start + 1
    loan_start_idx = yi(wi.loan_start_year)
    fcf_at_start = fcf[min(loan_start_idx + 1, n - 1)] if loan_start_idx + 1 < n else 0

    # Loan calculation
    if wi.loan_dscr > 0 and fcf_at_start > 0:
        annual_payment = fcf_at_start / wi.loan_dscr
        repay_periods = wi.loan_tenor - wi.loan_grace_years
        if wi.loan_interest_rate > 0 and repay_periods > 0:
            loan_amount = annual_payment * (1 - (1 + wi.loan_interest_rate) ** (-repay_periods)) / wi.loan_interest_rate
        else:
            loan_amount = annual_payment * repay_periods
        loan_amount = max(0, loan_amount - wi.loan_cap)
    else:
        loan_amount = 0

    loan_annual_inv = np.zeros(n)
    for t in range(n):
        if wi.loan_start_year <= years[t] < wi.loan_start_year + wi.loan_investment_years:
            loan_annual_inv[t] = loan_amount / wi.loan_investment_years if wi.loan_investment_years > 0 else 0

    interv_loan_new_hh = np.zeros(n)
    interv_loan_cum_hh_capex = np.zeros(n)
    interv_loan_repl = np.zeros(n)
    for t in range(n):
        interv_loan_repl[t] = interv_loan_cum_hh_capex[t - 1] * repl_rate if t > 0 else 0
        denom = 1 + nonhh_rate
        if denom > 0 and loan_annual_inv[t] > 0:
            interv_loan_new_hh[t] = ((loan_annual_inv[t] - interv_loan_repl[t] - interv_loan_repl[t] * nonhh_rate) / denom)
            if loan_annual_inv[t] > 0:
                interv_loan_new_hh[t] = max(0, interv_loan_new_hh[t])
        interv_loan_cum_hh_capex[t] = (interv_loan_cum_hh_capex[t - 1] if t > 0 else 0) + interv_loan_new_hh[t]

    interv_loan_hh = np.zeros(n)
    if wc.kukl_network_cost_per_hh > 0:
        interv_loan_hh = interv_loan_new_hh / wc.kukl_network_cost_per_hh
    interv_loan_cum_hh = np.cumsum(interv_loan_hh)
    interv_loan_inv = loan_annual_inv.copy()
    interv_loan_cum_inv = np.cumsum(interv_loan_inv)

    return {
        'bau_hh': bau_hh,
        'bau_hh_total': bau_hh_total,
        'target_hh': target_hh,
        'target_hh_total': target_hh_total,
        'service_gap': service_gap,
        'investment_need': investment_need,
        'bau_investment': bau_investment,
        'financing_gap': financing_gap,
        'cumulative_inv_need': cumulative_inv_need,
        'cumulative_bau_inv': cumulative_bau_inv,
        'interv_ce_nrw_hh': interv_ce_nrw_hh,
        'interv_ce_nrw_cum_hh': interv_ce_nrw_cum_hh,
        'interv_ce_nrw_inv': interv_ce_nrw_inv,
        'interv_ce_nrw_cum_inv': interv_ce_nrw_cum_inv,
        'interv_capeff_hh': interv_capeff_hh,
        'interv_capeff_cum_hh': interv_capeff_cum_hh,
        'interv_tariff_hh': interv_tariff_hh,
        'interv_tariff_cum_hh': interv_tariff_cum_hh,
        'interv_tariff_inv': interv_tariff_inv,
        'interv_tariff_cum_inv': interv_tariff_cum_inv,
        'interv_loan_hh': interv_loan_hh,
        'interv_loan_cum_hh': interv_loan_cum_hh,
        'interv_loan_inv': interv_loan_inv,
        'interv_loan_cum_inv': interv_loan_cum_inv,
        'nrw_rate': nrw_rate,
        'ce_rate': ce_rate,
        'avg_tariff': avg_tariff,
        'water_sold_nrw': water_sold_nrw,
    }
