import numpy as np
from .inputs import ModelInputs


def calculate_sanitation(inputs: ModelInputs, common: dict) -> dict:
    p = inputs.period
    c = inputs.constants
    ss = inputs.sanitation_service
    st = inputs.sanitation_targets
    sc = inputs.sanitation_costs
    si = inputs.sanitation_interventions
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
    avg_hh_size_2025 = common['avg_hh_size_2025']
    water_per_hh = common['water_per_hh_year']

    # ===== SECTION 0: BAU HHs forecast =====
    san_hh = common['san_hh_serv_historical'].copy()

    # BAU wastewater treatment capacity
    san_bau_wwt = common['san_bau_wwt']
    wwt_cost_per_mld = sc.kukl_wwt_cost_per_mld if sc.kukl_wwt_cost_per_mld > 0 else (
        tech.san_existing_wwtp_mld  # placeholder
    )

    wastewater_per_hh = water_per_hh * tech.san_wastewater_factor
    ww_treatment_increase = np.zeros(n)
    for t in range(n):
        if (asis_flag[t] > 0 or perf_flag[t] > 0) and sc.kukl_wwt_cost_per_mld > 0:
            ww_treatment_increase[t] = san_bau_wwt[t] / sc.kukl_wwt_cost_per_mld

    bau_ww_hh_increase = np.zeros(n)
    if wastewater_per_hh > 0:
        for t in range(n):
            ann_m3 = ww_treatment_increase[t] * c.days_in_year * thou
            bau_ww_hh_increase[t] = ann_m3 / wastewater_per_hh / mill

    current_ww_treated_hh = ss.hh_sewered_wwt_2025 / mill
    bau_ww_treated = np.zeros(n)
    bau_ww_treated[yi(p.baseline_year)] = current_ww_treated_hh
    for t in range(yi(p.baseline_year) + 1, n):
        bau_ww_treated[t] = bau_ww_treated[t - 1] + bau_ww_hh_increase[t]

    # BAU sewerage network
    san_bau_sewer = common['san_bau_sewer']
    sewer_cost_per_hh = sc.sewer_network_cost_per_hh
    bau_sewer_increase = np.zeros(n)
    if sewer_cost_per_hh > 0:
        for t in range(n):
            bau_sewer_increase[t] = san_bau_sewer[t] / sewer_cost_per_hh

    current_sewer_hh = ss.hh_sewered_2025 / mill
    bau_sewer = np.zeros(n)
    bau_sewer[yi(p.baseline_year)] = current_sewer_hh
    for t in range(yi(p.baseline_year) + 1, n):
        bau_sewer[t] = bau_sewer[t - 1] + bau_sewer_increase[t]

    # BAU fecal sludge management
    san_bau_fsm = common['san_bau_fsm']
    fst_cost_per_mld = sc.cost_per_mld_fst * mill if sc.cost_per_mld_fst > 0 else tech.san_avg_capex_per_mld_fst * mill
    fs_per_hh_year = (sc.fs_per_person_per_day_liters / c.cubic_meter_liters) * avg_hh_size_2025 * c.days_in_year

    bau_fst_increase = np.zeros(n)
    for t in range(n):
        if (asis_flag[t] > 0 or perf_flag[t] > 0) and fst_cost_per_mld > 0:
            bau_fst_increase[t] = san_bau_fsm[t] / (fst_cost_per_mld / mill)

    current_fst_hh = ss.hh_onsite_2025 / mill * 0  # Approximation: starts near 0
    bau_fst = np.zeros(n)
    if fs_per_hh_year > 0:
        for t in range(yi(p.baseline_year) + 1, n):
            ann_m3 = bau_fst_increase[t] * c.days_in_year * thou
            bau_fst[t] = bau_fst[t - 1] + ann_m3 / (wastewater_per_hh * mill) if wastewater_per_hh > 0 else 0

    # BAU serv1 (safely managed) = sewer + fst
    bau_serv1 = bau_sewer + bau_fst
    for t in range(n):
        if years[t] <= p.baseline_year:
            bau_serv1[t] = san_hh[0, t]

    # BAU service levels (unadjusted, grow at historical CAGR)
    san_cagrs = common['san_cagrs_hist']
    bau_unadj = np.zeros((5, n))
    bau_unadj[0] = bau_serv1

    for i in range(1, 5):
        for t in range(n):
            if years[t] <= p.baseline_year:
                bau_unadj[i, t] = san_hh[i, t]
            elif t > 0:
                bau_unadj[i, t] = bau_unadj[i, t - 1] * (1 + san_cagrs[i])

    # Adjust BAU to match total HHs
    bau_hh = np.zeros((5, n))
    for t in range(n):
        if years[t] <= p.baseline_year:
            bau_hh[:, t] = san_hh[:, t]
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
    asis_idx = yi(end_asis)
    asis_hh = bau_hh[:, asis_idx].copy()

    t1_idx = yi(p.target1_year)
    t1_total_hh = total_hh[t1_idx]
    t1_pcts = [st.target1_sserv1, st.target1_sserv2, st.target1_sserv3, st.target1_sserv4, st.target1_sserv5]
    t1_hh = [t1_total_hh * pct for pct in t1_pcts]

    n_t1 = p.target1_year - end_asis
    cagr_t1 = []
    for i in range(5):
        if asis_hh[i] > 0 and t1_hh[i] > 0:
            cagr_t1.append((t1_hh[i] / asis_hh[i]) ** (1 / n_t1) - 1)
        elif t1_hh[i] > 0:
            cagr_t1.append(0)
        else:
            cagr_t1.append(0)

    t2_idx = yi(p.target2_year)
    t2_total_hh = total_hh[t2_idx]
    t2_pcts = [st.target2_sserv1, st.target2_sserv2, st.target2_sserv3, st.target2_sserv4, st.target2_sserv5]
    t2_hh = [t2_total_hh * pct for pct in t2_pcts]

    n_t2 = p.target2_year - p.target1_year
    cagr_t2 = []
    for i in range(5):
        if t1_hh[i] > 0 and t2_hh[i] > 0:
            cagr_t2.append((t2_hh[i] / t1_hh[i]) ** (1 / n_t2) - 1)
        elif t2_hh[i] > 0:
            cagr_t2.append(0)
        else:
            cagr_t2.append(0)

    target_unadj = np.zeros((5, n))
    for i in range(5):
        for t in range(n):
            if years[t] <= end_asis:
                target_unadj[i, t] = bau_hh[i, t]
            elif t > 0:
                cagr = cagr_t1[i] if years[t] <= p.target1_year else cagr_t2[i]
                target_unadj[i, t] = target_unadj[i, t - 1] * (1 + cagr)

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
                residual = total_hh[t] - target_hh[0, t] - target_hh[1, t]
                if t > 0:
                    prev_rest = sum(target_hh[i, t - 1] for i in range(2, 5))
                    for i in range(2, 5):
                        ratio = target_hh[i, t - 1] / prev_rest if prev_rest > 0 else 0
                        target_hh[i, t] = residual * ratio

    target_hh_total = np.sum(target_hh, axis=0)
    service_gap = target_hh[0] - bau_hh[0]

    # ===== SECTION 2: Existing stock =====
    existing_stock_baseline = (ss.hh_sewered_2025 / mill) * sc.kukl_sewer_cost_per_hh * (1 + tech.san_non_hh_capex_pct)
    existing_stock = np.zeros(n)
    existing_stock[yi(p.baseline_year)] = existing_stock_baseline

    # ===== SECTION 3: BAU investment =====
    bau_investment = common['san_bau_total'].copy()

    # ===== SECTION 4: Investment need & financing gap =====
    # Sewered KUKL
    kukl_hh_target = np.zeros(n)
    for t in range(n):
        kukl_hh_target[t] = target_hh[0, t] * st.sewered_kukl_pct

    # WWT capacity needed
    capex_wwt = np.zeros(n)
    add_wwt_cap = np.zeros(n)
    for t in range(n):
        if asis_flag[t] > 0 or perf_flag[t] > 0:
            cap_needed = kukl_hh_target[t] * wastewater_per_hh * mill / c.days_in_year / thou
            needed = max(0, cap_needed - tech.san_existing_wwtp_mld)
            if t > 0 and needed > add_wwt_cap[t - 1]:
                new_cap = needed - add_wwt_cap[t - 1]
            else:
                new_cap = 0
            add_wwt_cap[t] = needed
            if sc.kukl_wwt_cost_per_mld > 0:
                capex_wwt[t] = new_cap * sc.kukl_wwt_cost_per_mld

    # Sewerage network capex
    kukl_sewer_current = ss.hh_kukl_sewer_2025 / mill
    capex_sewer = np.zeros(n)
    for t in range(n):
        if (asis_flag[t] > 0 or perf_flag[t] > 0) and kukl_hh_target[t] > kukl_sewer_current:
            new = kukl_hh_target[t] - kukl_sewer_current
            prev_new = 0
            if t > 0 and years[t - 1] > p.baseline_year:
                prev_new = max(0, kukl_hh_target[t - 1] - kukl_sewer_current)
            incremental = max(0, new - prev_new)
            capex_sewer[t] = incremental * sc.kukl_sewer_cost_per_hh

    kukl_total = capex_wwt + capex_sewer

    # On-site sanitation capex
    onsite_hh_target = np.zeros(n)
    for t in range(n):
        onsite_hh_target[t] = target_hh[0, t] * st.onsite_collection_treatment_pct

    current_onsite_hh = ss.hh_onsite_2025 / mill
    capex_onsite_facility = np.zeros(n)
    capex_emptying = np.zeros(n)
    capex_fst = np.zeros(n)
    add_fst_cap = np.zeros(n)  # separate tracker for FST capacity (not WWT)
    for t in range(n):
        if (asis_flag[t] > 0 or perf_flag[t] > 0) and onsite_hh_target[t] > current_onsite_hh:
            new_onsite = onsite_hh_target[t] - current_onsite_hh
            prev_onsite = 0
            if t > 0 and years[t - 1] > p.baseline_year:
                prev_onsite = max(0, onsite_hh_target[t - 1] - current_onsite_hh)
            incremental = max(0, new_onsite - prev_onsite)
            capex_onsite_facility[t] = incremental * sc.onsite_facility_capex

            # FS collection trucks
            fs_generated = onsite_hh_target[t] * fs_per_hh_year
            trips_needed = (fs_generated * mill) / sc.truck_size_m3 if sc.truck_size_m3 > 0 else 0
            trucks_needed = np.ceil(trips_needed / sc.trips_per_truck_year) if sc.trips_per_truck_year > 0 else 0
            if t > 0:
                prev_fs = max(0, (onsite_hh_target[t - 1] if years[t - 1] > p.baseline_year else 0)) * fs_per_hh_year
                prev_trips = (prev_fs * mill) / sc.truck_size_m3 if sc.truck_size_m3 > 0 else 0
                prev_trucks = np.ceil(prev_trips / sc.trips_per_truck_year) if sc.trips_per_truck_year > 0 else 0
                new_trucks = max(0, trucks_needed - prev_trucks)
            else:
                new_trucks = trucks_needed
            capex_emptying[t] = new_trucks * sc.fs_truck_cost_mill

            # FS treatment (uses its own capacity tracker, separate from WWT)
            fst_cap_needed = onsite_hh_target[t] * fs_per_hh_year * mill / c.days_in_year / thou
            fst_needed = max(0, fst_cap_needed - tech.san_existing_fst_mld)
            if t > 0:
                new_fst = max(0, fst_needed - add_fst_cap[t - 1]) if fst_needed > add_fst_cap[t - 1] else 0
            else:
                new_fst = fst_needed
            add_fst_cap[t] = fst_needed
            capex_fst[t] = new_fst * sc.cost_per_mld_fst

    onsite_total = capex_onsite_facility + capex_emptying + capex_fst

    # Total investment need
    new_capex_hh = kukl_total + onsite_total
    new_capex_nonhh = new_capex_hh * tech.san_non_hh_capex_pct
    total_new_capex = new_capex_hh + new_capex_nonhh

    rolling_stock = np.zeros(n)
    rolling_stock[yi(p.baseline_year)] = existing_stock_baseline
    for t in range(yi(p.baseline_year) + 1, n):
        rolling_stock[t] = rolling_stock[t - 1] + total_new_capex[t]

    replacement_capex = np.zeros(n)
    for t in range(1, n):
        if perf_flag[t] > 0:
            replacement_capex[t] = rolling_stock[t - 1] * tech.san_replacement_rate

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
    nonhh_rate = tech.san_non_hh_capex_pct
    repl_rate = tech.san_replacement_rate

    # Weighted avg cost per HH for sanitation
    avg_sewer_cost = sc.kukl_sewer_cost_per_hh * st.sewered_kukl_pct + sc.wusc_sewer_cost_per_hh * st.sewered_wusc_pct if (st.sewered_kukl_pct + st.sewered_wusc_pct) > 0 else sc.kukl_sewer_cost_per_hh
    if sc.kukl_wwt_cost_per_mld > 0:
        hh_per_mld = (mill / c.cubic_meter_liters) / (water_per_hh / c.days_in_year)
        wwt_cost_per_hh = (sc.kukl_wwt_cost_per_mld / hh_per_mld) * mill
    else:
        wwt_cost_per_hh = 0
    weighted_cost_per_hh = (wwt_cost_per_hh + avg_sewer_cost) * (1 - si.capeff_gains_pct)
    if weighted_cost_per_hh <= 0:
        weighted_cost_per_hh = avg_sewer_cost

    # 5.1 Collection efficiency
    ce_rate = np.zeros(n)
    ce_increase_per_yr = (si.ce_target_ratio - si.ce_current_ratio) / (si.ce_target_year - si.ce_start_year + 1) if si.ce_target_year > si.ce_start_year else 0

    for t in range(n):
        y = years[t]
        if y < si.ce_start_year:
            ce_rate[t] = si.ce_current_ratio
        elif y > si.ce_target_year:
            ce_rate[t] = si.ce_target_ratio
        else:
            ce_rate[t] = ce_rate[t - 1] + ce_increase_per_yr if t > 0 else si.ce_current_ratio

    # Water supply data from water_supply calc (passed via common)
    ws_water_sold = inputs.water_interventions.ce_water_sold_mld
    sewer_tariff_pct = si.ce_sewer_tariff_pct_water
    ws_tariff = inputs.water_interventions.ce_current_tariff

    wastewater_billed = ws_water_sold * si.ce_wastewater_collected_pct
    cash_bau_san = wastewater_billed * (ws_tariff * sewer_tariff_pct) * si.ce_current_ratio
    cash_improved_san = np.array([wastewater_billed * (ws_tariff * sewer_tariff_pct) * ce_rate[t] for t in range(n)])
    additional_cash_ce = cash_improved_san - cash_bau_san

    interv_ce_total = additional_cash_ce.copy()
    interv_ce_new_hh = np.zeros(n)
    interv_ce_cum_hh_capex = np.zeros(n)
    interv_ce_repl = np.zeros(n)
    for t in range(n):
        interv_ce_repl[t] = interv_ce_cum_hh_capex[t - 1] * repl_rate if t > 0 else 0
        denom = 1 + nonhh_rate
        if denom > 0:
            interv_ce_new_hh[t] = (interv_ce_total[t] - interv_ce_repl[t] - interv_ce_repl[t] * nonhh_rate) / denom
        interv_ce_cum_hh_capex[t] = (interv_ce_cum_hh_capex[t - 1] if t > 0 else 0) + interv_ce_new_hh[t]

    interv_ce_hh = np.zeros(n)
    if weighted_cost_per_hh > 0:
        interv_ce_hh = interv_ce_new_hh / weighted_cost_per_hh
    interv_ce_cum_hh = np.cumsum(interv_ce_hh)
    interv_ce_inv = additional_cash_ce.copy()
    interv_ce_cum_inv = np.cumsum(interv_ce_inv)

    # 5.2 Capital efficiency
    capeff_flag = np.array([1.0 if years[t] >= si.capeff_start_year else 0.0 for t in range(n)])
    capeff_repl_const = existing_stock_baseline * repl_rate

    capeff_remaining = np.zeros(n)
    capeff_new_hh = np.zeros(n)
    capeff_cum_hh = np.zeros(n)
    capeff_repl_arr = np.zeros(n)
    for t in range(n):
        if perf_flag[t] > 0:
            capeff_remaining[t] = max(0, bau_investment[t] - capeff_repl_const)
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
    tariff_flag = np.array([1.0 if si.tariff_start_year <= years[t] <= si.tariff_target_year else 0.0 for t in range(n)])

    # Affordability check
    monthly_expenditure = inputs.water_interventions.tariff_monthly_income_bottom20 * avg_hh_size_2025
    max_monthly_san = monthly_expenditure * si.tariff_max_pct_income_san
    ww_per_hh_month = wastewater_per_hh * c.days_in_month / c.days_in_year if c.days_in_year > 0 else 0
    max_affordable_san_tariff = max_monthly_san / ww_per_hh_month if ww_per_hh_month > 0 else float('inf')

    san_tariff_current = ws_tariff * sewer_tariff_pct
    san_tariff_growth = si.san_tariff_growth_rate

    avg_san_tariff = np.full(n, san_tariff_current)
    for t in range(1, n):
        if years[t] == p.baseline_year:
            avg_san_tariff[t] = san_tariff_current
        elif tariff_flag[t] > 0:
            avg_san_tariff[t] = min(avg_san_tariff[t - 1] * (1 + san_tariff_growth), max_affordable_san_tariff)
        else:
            avg_san_tariff[t] = avg_san_tariff[t - 1]

    tariff_increase = avg_san_tariff - san_tariff_current
    ww_billed_nrw = wastewater_billed  # Simplified: use water supply NRW data if available
    additional_rev_tariff = ww_billed_nrw * tariff_increase
    cash_tariff = additional_rev_tariff * ce_rate

    interv_tariff_new_hh = np.zeros(n)
    interv_tariff_cum_capex = np.zeros(n)
    interv_tariff_repl = np.zeros(n)
    for t in range(n):
        interv_tariff_repl[t] = interv_tariff_cum_capex[t - 1] * repl_rate if t > 0 else 0
        denom = 1 + nonhh_rate
        if denom > 0:
            interv_tariff_new_hh[t] = (cash_tariff[t] - interv_tariff_repl[t] - interv_tariff_repl[t] * nonhh_rate) / denom
        interv_tariff_cum_capex[t] = (interv_tariff_cum_capex[t - 1] if t > 0 else 0) + interv_tariff_new_hh[t]

    interv_tariff_hh = np.zeros(n)
    if weighted_cost_per_hh > 0:
        interv_tariff_hh = interv_tariff_new_hh / weighted_cost_per_hh
    interv_tariff_cum_hh = np.cumsum(interv_tariff_hh)
    interv_tariff_inv = cash_tariff.copy()
    interv_tariff_cum_inv = np.cumsum(interv_tariff_inv)

    # 5.4 Borrowing
    loan_flag = np.array([1.0 if si.loan_start_year <= years[t] <= si.loan_end_year else 0.0 for t in range(n)])

    est_cash_inflow = avg_san_tariff * ww_billed_nrw * ce_rate
    est_cash_outflow = np.array([si.loan_avg_cost_per_ww_billed * ww_billed_nrw for _ in range(n)])
    fcf = est_cash_inflow - est_cash_outflow

    loan_start_idx = yi(si.loan_start_year)
    fcf_at_start = fcf[min(loan_start_idx + 1, n - 1)] if loan_start_idx + 1 < n else 0

    if si.loan_dscr > 0 and fcf_at_start > 0:
        annual_payment = fcf_at_start / si.loan_dscr
        repay_periods = si.loan_tenor - si.loan_grace_years
        if si.loan_interest_rate > 0 and repay_periods > 0:
            loan_amount = annual_payment * (1 - (1 + si.loan_interest_rate) ** (-repay_periods)) / si.loan_interest_rate
        else:
            loan_amount = annual_payment * repay_periods
        loan_amount = max(0, loan_amount)
    else:
        loan_amount = 0

    loan_annual = np.zeros(n)
    for t in range(n):
        if si.loan_start_year <= years[t] < si.loan_start_year + si.loan_investment_years:
            loan_annual[t] = loan_amount / si.loan_investment_years if si.loan_investment_years > 0 else 0

    interv_loan_new_hh = np.zeros(n)
    interv_loan_cum_capex = np.zeros(n)
    interv_loan_repl = np.zeros(n)
    for t in range(n):
        interv_loan_repl[t] = interv_loan_cum_capex[t - 1] * repl_rate if t > 0 else 0
        denom = 1 + nonhh_rate
        if denom > 0 and loan_annual[t] > 0:
            interv_loan_new_hh[t] = max(0, (loan_annual[t] - interv_loan_repl[t] - interv_loan_repl[t] * nonhh_rate) / denom)
        interv_loan_cum_capex[t] = (interv_loan_cum_capex[t - 1] if t > 0 else 0) + interv_loan_new_hh[t]

    interv_loan_hh = np.zeros(n)
    if sc.sewer_network_cost_per_hh > 0:
        interv_loan_hh = interv_loan_new_hh / sc.sewer_network_cost_per_hh
    interv_loan_cum_hh = np.cumsum(interv_loan_hh)
    interv_loan_inv = loan_annual.copy()
    interv_loan_cum_inv = np.cumsum(interv_loan_inv)

    # 5.5 Microfinance for on-site sanitation
    mf_flag = np.array([1.0 if si.mf_start_year <= years[t] <= si.mf_end_year else 0.0 for t in range(n)])

    # Microfinance affordability
    mf_annual_debt = 0
    if si.mf_interest_rate > 0 and si.mf_tenor > 0:
        mf_annual_debt = si.mf_interest_rate * si.mf_onsite_cost / (1 - (1 + si.mf_interest_rate) ** (-si.mf_tenor))
    mf_annual_emptying = si.mf_collection_cost / sc.emptying_frequency_years if sc.emptying_frequency_years > 0 else 0
    mf_total_annual = mf_annual_debt + mf_annual_emptying

    mf_min_income = mf_total_annual / si.mf_max_pct_income if si.mf_max_pct_income > 0 else float('inf')
    mf_pct_hh = si.mf_high_percentile - si.mf_low_percentile
    mf_total_hh = inputs.population.total_hh_2025 * mf_pct_hh
    mf_years = si.mf_end_year - si.mf_start_year
    mf_annual_hh = mf_total_hh / mf_years if mf_years > 0 else 0

    interv_mf_hh = np.zeros(n)
    for t in range(1, n):
        if mf_flag[t] > 0:
            # Additional on-site HHs = change in target on-site * 0.5 * flag
            change = target_hh[0, t] * st.onsite_collection_treatment_pct - (target_hh[0, t - 1] * st.onsite_collection_treatment_pct if t > 0 else 0)
            interv_mf_hh[t] = change * si.mf_adoption_rate * mf_flag[t]

    interv_mf_cum_hh = np.cumsum(interv_mf_hh)
    interv_mf_inv = interv_mf_hh * (si.mf_onsite_cost + si.mf_collection_cost)
    interv_mf_cum_inv = np.cumsum(interv_mf_inv)

    # ===== SECTION 6: Apply intervention toggles =====
    tog = inputs.toggles
    if not tog.san_collection_enabled:
        interv_ce_hh[:] = 0
        interv_ce_cum_hh[:] = 0
        interv_ce_inv[:] = 0
        interv_ce_cum_inv[:] = 0
    if not tog.san_capital_efficiency_enabled:
        interv_capeff_hh[:] = 0
        interv_capeff_cum_hh[:] = 0
    if not tog.san_tariff_enabled:
        interv_tariff_hh[:] = 0
        interv_tariff_cum_hh[:] = 0
        interv_tariff_inv[:] = 0
        interv_tariff_cum_inv[:] = 0
    if not tog.san_borrowing_enabled:
        interv_loan_hh[:] = 0
        interv_loan_cum_hh[:] = 0
        interv_loan_inv[:] = 0
        interv_loan_cum_inv[:] = 0
    if not tog.san_microfinance_enabled:
        interv_mf_hh[:] = 0
        interv_mf_cum_hh[:] = 0
        interv_mf_inv[:] = 0
        interv_mf_cum_inv[:] = 0

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
        'interv_ce_hh': interv_ce_hh,
        'interv_ce_cum_hh': interv_ce_cum_hh,
        'interv_ce_inv': interv_ce_inv,
        'interv_ce_cum_inv': interv_ce_cum_inv,
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
        'interv_mf_hh': interv_mf_hh,
        'interv_mf_cum_hh': interv_mf_cum_hh,
        'interv_mf_inv': interv_mf_inv,
        'interv_mf_cum_inv': interv_mf_cum_inv,
    }
