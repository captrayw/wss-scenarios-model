import numpy as np
from .inputs import ModelInputs


def sg(arr, t, default=0.0):
    if arr is None or t < 0: return default
    return arr[t] if t < len(arr) else (arr[-1] if arr else default)


def calculate_water_supply(inputs: ModelInputs, common: dict) -> dict:
    p = inputs.period
    c = inputs.constants
    ws = inputs.water_service
    wt = inputs.water_targets
    wc = inputs.water_costs
    wi = inputs.water_interventions
    tech = inputs.technical
    macro = inputs.macro
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

    # Weighted average costs from providers
    total_share = sum(pr.share_pct for pr in wt.providers) or 1.0
    avg_network_cost_per_hh = sum(pr.network_cost_per_hh * pr.share_pct for pr in wt.providers) / total_share if total_share > 0 else 0
    avg_treatment_cost_per_mld = sum(pr.cost_per_mld_treatment * pr.share_pct for pr in wt.providers) / total_share if total_share > 0 else 0

    # ===== SECTION 0: BAU HHs forecast =====
    # Matches Excel C|Water supply rows 29-64

    # Row 34: BAU treated-piped HHs (from network investment)
    network_inv = common['ws_bau_network_inv']
    network_cost_per_hh = avg_network_cost_per_hh if avg_network_cost_per_hh > 0 else (wt.providers[0].network_cost_per_hh if wt.providers else 0)
    bau_increase_network = np.zeros(n)
    for t in range(n):
        if network_cost_per_hh > 0:
            bau_increase_network[t] = network_inv[t] / network_cost_per_hh

    # G32 in Excel = G151 * G103 = (% piped water) × total_hh_baseline
    # where % piped = hh_treated_piped / (hh_treated_piped + hh_no_piped)
    total_piped_hh = ws.hh_treated_piped_baseline + ws.hh_no_piped_baseline
    pct_piped = ws.hh_treated_piped_baseline / total_piped_hh if total_piped_hh > 0 else 0
    pop = inputs.population
    current_treated_piped = pct_piped * pop.total_hh_baseline
    bau_treated_piped = np.zeros(n)
    # Excel formula: row34[baseline+1] = G32 + row31[baseline+1]
    # Then forecast: row34[t] = row34[t-1] + row31[t]
    # Then backfill: row34[t] = row34[t+1] / (1+hist_rate)
    bi = yi(p.baseline_year)
    if bi + 1 < n:
        bau_treated_piped[bi + 1] = current_treated_piped + bau_increase_network[bi + 1]
    for t in range(bi + 2, n):
        bau_treated_piped[t] = bau_treated_piped[t - 1] + bau_increase_network[t]
    # Backfill historical from the first forecast year
    for t in range(bi, -1, -1):
        if t + 1 < n:
            bau_treated_piped[t] = bau_treated_piped[t + 1] / (1 + ws.hist_increase_treated_piped)

    # Row 41: BAU 24/7 water HHs (from treatment capacity additions)
    treatment_increase = common['ws_treatment_increase']
    water_per_hh_adj = water_per_hh * (1 + tech.ws_non_hh_pct_of_hh) if water_per_hh > 0 else 1
    bau_24hr = np.zeros(n)
    # Anchor at baseline: use the serv1 HHs from historical data
    ws_hh = common['ws_hh_serv_historical'].copy()
    serv1_at_baseline = current_treated_piped  # treated piped at baseline
    for t in range(n):
        if years[t] <= p.baseline_year:
            bau_24hr[t] = 0  # not tracked historically
        else:
            ann_increase_m3 = treatment_increase[t] * c.days_in_year * thou
            increase_hh = ann_increase_m3 / water_per_hh_adj / mill
            if t == yi(p.baseline_year) + 1:
                bau_24hr[t] = serv1_at_baseline + increase_hh
            else:
                bau_24hr[t] = bau_24hr[t - 1] + increase_hh

    # Row 42: BAU safely managed = MIN(treated_piped, 24hr) for forecast years
    bau_serv1_unadj = np.zeros(n)
    for t in range(n):
        if years[t] <= p.baseline_year:
            bau_serv1_unadj[t] = bau_treated_piped[t]
        elif bau_24hr[t] > 0:
            bau_serv1_unadj[t] = min(bau_treated_piped[t], bau_24hr[t])
        else:
            bau_serv1_unadj[t] = bau_treated_piped[t]

    # Rows 44-49: BAU other service levels (unadjusted, grow at historical CAGR)
    ws_cagrs = common['ws_cagrs_hist']
    bau_unadj = np.zeros((5, n))
    bau_unadj[0] = bau_serv1_unadj
    for i in range(1, 5):
        for t in range(n):
            if years[t] <= p.baseline_year:
                bau_unadj[i, t] = ws_hh[i, t]
            elif t > 0:
                bau_unadj[i, t] = bau_unadj[i, t - 1] * (1 + ws_cagrs[i])

    # Rows 53-58: Adjust BAU to match total HHs
    # Row 53: serv1 stays as is
    # Row 54: serv2 = total - serv1 - serv3 - serv4 - serv5
    # Row 55-57: serv3-5 adjusted proportionally
    bau_hh = np.zeros((5, n))
    for t in range(n):
        if years[t] <= p.baseline_year:
            # Row 60-64: historical = use treated piped for serv1, remainder for serv2
            bau_hh[0, t] = bau_treated_piped[t]
            bau_hh[1, t] = sum(ws_hh[j, t] for j in range(2)) - bau_treated_piped[t]
            for i in range(2, 5):
                bau_hh[i, t] = ws_hh[i, t]
        else:
            bau_hh[0, t] = bau_unadj[0, t]
            # Adjust serv3-5 proportionally
            unadj_sum = sum(bau_unadj[i, t] for i in range(5))
            for i in range(2, 5):
                if unadj_sum > 0:
                    bau_hh[i, t] = bau_unadj[i, t] + (bau_unadj[i, t] / unadj_sum) * (total_hh[t] - unadj_sum)
                else:
                    bau_hh[i, t] = 0
            # serv2 = residual
            bau_hh[1, t] = total_hh[t] - bau_hh[0, t] - sum(bau_hh[i, t] for i in range(2, 5))

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
    # Excel G160 = G155 × G156 × (1+G158) where G156 = I|G G345 (serv1 network cost)
    existing_stock_baseline = (ws.hh_treated_piped_baseline / mill) * wc.network_cost_per_hh_serv1 * (1 + tech.ws_non_hh_pct_of_hh)
    existing_stock = np.zeros(n)
    existing_stock[yi(p.baseline_year)] = existing_stock_baseline

    # ===== SECTION 3: BAU investment =====
    bau_investment = common['ws_bau_total'].copy()

    # ===== SECTION 4: Investment need & financing gap =====
    # Loop over all providers
    total_provider_capex = np.zeros(n)

    for prov in wt.providers:
        if prov.share_pct <= 0:
            continue

        prov_hh_target = np.zeros(n)
        for t in range(n):
            prov_hh_target[t] = target_hh[0, t] * prov.share_pct

        # Treatment capex
        prov_add_cap = np.zeros(n)
        prov_capex_treatment = np.zeros(n)
        for t in range(n):
            if asis_flag[t] > 0 or perf_flag[t] > 0:
                wph = common['water_per_hh_year_arr'][t] if 'water_per_hh_year_arr' in common else water_per_hh
                cap_needed = prov_hh_target[t] * wph * mill / c.days_in_year / thou
                needed = max(0, cap_needed - prov.existing_capacity_mld)
                if t > 0 and needed > prov_add_cap[t - 1]:
                    new_cap = needed - prov_add_cap[t - 1]
                else:
                    new_cap = 0
                prov_add_cap[t] = needed
                if prov.cost_per_mld_treatment > 0:
                    prov_capex_treatment[t] = new_cap * prov.cost_per_mld_treatment

        # Network capex
        prov_hh_current = prov.current_hh / mill
        prov_capex_network = np.zeros(n)
        for t in range(n):
            if (asis_flag[t] > 0 or perf_flag[t] > 0) and prov_hh_target[t] > prov_hh_current:
                new = prov_hh_target[t] - prov_hh_current
                prev_new = 0
                if t > 0 and years[t - 1] > p.baseline_year:
                    prev_new = max(0, prov_hh_target[t - 1] - prov_hh_current)
                prov_capex_network[t] = max(0, new - prev_new) * prov.network_cost_per_hh

        total_provider_capex += prov_capex_treatment + prov_capex_network

    # Total investment need
    new_capex_hh = total_provider_capex
    new_capex_nonhh = new_capex_hh * tech.ws_non_hh_pct_of_hh  # Excel G272 = non-HH as % of HH
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

    # Convert MLD to annual m3 (millions): MLD × 365 / 1000
    water_sold = ce.ce_water_sold_mld * c.days_in_year / c.cubic_meter_liters
    tariff_current = ce.ce_current_tariff
    cash_bau = water_sold * tariff_current * ce.ce_current_ratio
    cash_improved = np.array([water_sold * tariff_current * ce_rate[t] for t in range(n)])
    additional_cash_ce = cash_improved - cash_bau

    # Cost per HH after efficiency
    avg_network_cost = avg_network_cost_per_hh
    if avg_treatment_cost_per_mld > 0:
        hh_per_mld = (mill / c.cubic_meter_liters) / (water_per_hh / c.days_in_year)
        treatment_cost_per_hh = (avg_treatment_cost_per_mld / hh_per_mld) * mill
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

    # NRW reduction cost (Row 362) = unit_cost × (volume_reduced / days_in_year)
    # G357 = NRW unit cost in NPR per m3/day = USD cost × exchange_rate at baseline
    nrw_unit_cost_npr = wi.nrw_capex_unit_cost_npr if wi.nrw_capex_unit_cost_npr > 0 else wi.nrw_capex_unit_cost_usd * sg(macro.exchange_rate, yi(p.baseline_year), 130)
    nrw_reduction_capex = np.zeros(n)
    for t in range(1, n):
        vol_reduced = physical_reduction[t] - physical_reduction[t - 1]
        if vol_reduced > 0:
            # Lag the volume reduced
            lag_t = min(t + wi.nrw_lag_years, n - 1) if wi.nrw_lag_years > 0 else t
            # Convert annual m3 to m3/day for the unit cost
            nrw_reduction_capex[t] = nrw_unit_cost_npr * (vol_reduced * mill / c.days_in_year) / mill

    # NRW connecting total capex (Row 376 = Row 372 + Row 374 + Row 375)
    # Row 372 = HHs from physical loss reduction × distribution cost after efficiency
    # G368 = avg_network_cost × (1-capeff_gains)
    avg_network_cost_simple = (wc.network_cost_per_hh_serv1 + (wt.providers[1].network_cost_per_hh if len(wt.providers) > 1 else wc.network_cost_per_hh_serv1)) / 2
    dist_cost_after_eff = avg_network_cost_simple * (1 - wi.capeff_gains_pct)
    nrw_connect_new_hh = interv_nrw_hh_physical * dist_cost_after_eff  # Row 372
    nrw_connect_cum = np.cumsum(nrw_connect_new_hh)  # Row 373
    nrw_connect_repl = np.zeros(n)  # Row 374
    nrw_connect_nonhh = np.zeros(n)  # Row 375
    nrw_connecting_capex = np.zeros(n)  # Row 376
    for t in range(n):
        nrw_connect_repl[t] = nrw_connect_cum[t - 1] * repl_rate if t > 0 else 0
        # Row 375 = (R372+R374) × (1-domestic)/domestic
        nrw_connect_nonhh[t] = (nrw_connect_new_hh[t] + nrw_connect_repl[t]) * (1 - tech.ws_pct_domestic) / tech.ws_pct_domestic if tech.ws_pct_domestic > 0 else 0
        nrw_connecting_capex[t] = nrw_connect_new_hh[t] + nrw_connect_repl[t] + nrw_connect_nonhh[t]

    # Total intervention capex deducted from BAU for CapEff (Row 408)
    nrw_total_intervention_capex = nrw_reduction_capex + nrw_connecting_capex

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
            # Excel Row 412: remaining = BAU - replacement_stock - NRW_intervention_capex
            remaining = capeff_bau[t] - capeff_repl - nrw_total_intervention_capex[t]
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
    # G483 = KUKL expenditure / (water_sold_annual_m3 × 1M)
    op_cost_per_m3 = wi.tariff_kukl_op_expenditure / (water_sold * mill) if water_sold > 0 else 0
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
    if avg_network_cost_per_hh > 0:
        interv_loan_hh = interv_loan_new_hh / wc.network_cost_per_hh_serv1  # Excel G513 = I|G G345
    interv_loan_cum_hh = np.cumsum(interv_loan_hh)
    interv_loan_inv = loan_annual_inv.copy()
    interv_loan_cum_inv = np.cumsum(interv_loan_inv)

    # ===== SECTION 6: Apply intervention toggles =====
    t = inputs.toggles
    if not t.ws_collection_nrw_enabled:
        interv_ce_nrw_hh[:] = 0
        interv_ce_nrw_cum_hh[:] = 0
        interv_ce_nrw_inv[:] = 0
        interv_ce_nrw_cum_inv[:] = 0
    if not t.ws_capital_efficiency_enabled:
        interv_capeff_hh[:] = 0
        interv_capeff_cum_hh[:] = 0
    if not t.ws_tariff_enabled:
        interv_tariff_hh[:] = 0
        interv_tariff_cum_hh[:] = 0
        interv_tariff_inv[:] = 0
        interv_tariff_cum_inv[:] = 0
    if not t.ws_borrowing_enabled:
        interv_loan_hh[:] = 0
        interv_loan_cum_hh[:] = 0
        interv_loan_inv[:] = 0
        interv_loan_cum_inv[:] = 0

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
