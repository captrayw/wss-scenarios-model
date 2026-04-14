import numpy as np
from .inputs import ModelInputs
from .water_supply import calculate_water_supply
from .sanitation import calculate_sanitation


def calculate(inputs: ModelInputs) -> dict:
    p = inputs.period
    n_years = p.forecast_end_year - p.model_start_year + 1
    years = np.arange(p.model_start_year, p.forecast_end_year + 1)

    end_asis_year = p.as_is_forecast_start + p.as_is_forecast_length - 1
    perf_start_year = end_asis_year + 1

    def yi(year):
        return year - p.model_start_year

    baseline_flag = (years == p.baseline_year).astype(float)
    historical_flag = (years <= p.baseline_year).astype(float)
    asis_flag = np.array([(1.0 if p.as_is_forecast_start <= y <= end_asis_year else 0.0) for y in years])
    perf_flag = np.array([(1.0 if perf_start_year <= y <= p.target2_year else 0.0) for y in years])
    target1_flag = (years == p.target1_year).astype(float)
    target2_flag = (years == p.target2_year).astype(float)

    common = {
        'years': years,
        'n_years': n_years,
        'yi': yi,
        'baseline_flag': baseline_flag,
        'historical_flag': historical_flag,
        'asis_flag': asis_flag,
        'perf_flag': perf_flag,
        'target1_flag': target1_flag,
        'target2_flag': target2_flag,
        'end_asis_year': end_asis_year,
        'perf_start_year': perf_start_year,
    }

    # Macro calculations
    macro = inputs.macro
    c = inputs.constants

    inflation_index = np.zeros(n_years)
    inflation_index[yi(macro.real_price_year)] = 100.0
    for t in range(yi(macro.real_price_year) - 1, -1, -1):
        inflation_index[t] = inflation_index[t + 1] / (1 + macro.inflation_nepal[t + 1]) if t + 1 < n_years else 0
    for t in range(yi(macro.real_price_year) + 1, n_years):
        inflation_index[t] = inflation_index[t - 1] * (1 + macro.inflation_nepal[t])

    gdp_nominal_npr = np.zeros(n_years)
    gdp_real_npr = np.zeros(n_years)
    for t in range(n_years):
        if macro.gdp_nominal_usd[t] and macro.gdp_nominal_usd[t] > 0:
            gdp_nominal_npr[t] = macro.gdp_nominal_usd[t] * c.thousand * macro.exchange_rate[t]
        elif t > 0:
            gdp_nominal_npr[t] = gdp_nominal_npr[t - 1] * (1 + macro.gdp_growth[t]) * (1 + macro.inflation_nepal[t])
        gdp_real_npr[t] = gdp_nominal_npr[t] * 100 / inflation_index[t] if inflation_index[t] > 0 else 0

    common['inflation_index'] = inflation_index
    common['gdp_nominal_npr'] = gdp_nominal_npr
    common['gdp_real_npr'] = gdp_real_npr

    # Population calculations
    pop = inputs.population
    avg_hh_size_start = pop.total_pop_start / (pop.total_hh_start * c.million)
    avg_hh_size_baseline = pop.total_pop_baseline / (pop.total_hh_baseline * c.million)
    pop_cagr_hist = (pop.total_pop_baseline / pop.total_pop_start) ** (1 / (p.baseline_year - p.model_start_year)) - 1
    hh_size_cagr_hist = (avg_hh_size_baseline / avg_hh_size_start) ** (1 / (p.baseline_year - p.model_start_year)) - 1

    total_pop = np.zeros(n_years)
    avg_hh_size = np.zeros(n_years)
    total_hh = np.zeros(n_years)

    total_pop[0] = pop.total_pop_start
    avg_hh_size[0] = avg_hh_size_start

    for t in range(1, n_years):
        if years[t] <= p.baseline_year:
            total_pop[t] = total_pop[t - 1] * (1 + pop_cagr_hist)
            avg_hh_size[t] = avg_hh_size[t - 1] * (1 + hh_size_cagr_hist)
        else:
            total_pop[t] = total_pop[t - 1] * (1 + pop.pop_growth_projected)
            avg_hh_size[t] = avg_hh_size[t - 1] * (1 + pop.hh_size_growth_projected)

    total_hh = (total_pop / avg_hh_size) / c.million

    common['total_pop'] = total_pop
    common['avg_hh_size'] = avg_hh_size
    common['total_hh'] = total_hh
    common['avg_hh_size_2025'] = avg_hh_size_baseline  # key kept for compatibility

    # Water service level history (from I|General rows 186-204)
    ws = inputs.water_service
    mill = c.million

    total_hh_start_val = pop.total_hh_start
    ws_hh_serv = np.zeros((5, n_years))

    ws_pcts_start = [ws.pct_serv1_start, ws.pct_serv2_start, ws.pct_serv3_start, ws.pct_serv4_start, ws.pct_serv5_start]
    ws_pcts_base = [ws.pct_serv1_baseline, ws.pct_serv2_baseline, ws.pct_serv3_baseline, ws.pct_serv4_baseline, ws.pct_serv5_baseline]

    ws_hh_start = [total_hh_start_val * pct for pct in ws_pcts_start]
    ws_hh_base = [pop.total_hh_baseline * pct for pct in ws_pcts_base]

    ws_cagrs = []
    n_hist = p.baseline_year - p.model_start_year
    for i in range(5):
        if ws_hh_start[i] > 0 and ws_hh_base[i] > 0:
            ws_cagrs.append((ws_hh_base[i] / ws_hh_start[i]) ** (1 / n_hist) - 1)
        elif ws_hh_base[i] > 0:
            ws_cagrs.append(0)
        else:
            ws_cagrs.append(0)

    # Historical water service levels - serv1 uses C|Water supply logic (treated piped from investment)
    # serv2-5 grow at historical CAGR, then adjust to total
    for i in range(5):
        ws_hh_serv[i, 0] = ws_hh_start[i]

    for t in range(1, n_years):
        if years[t] <= p.baseline_year:
            for i in range(5):
                ws_hh_serv[i, t] = ws_hh_serv[i, t - 1] * (1 + ws_cagrs[i]) if ws_cagrs[i] != 0 else ws_hh_serv[i, t - 1]
        else:
            break

    # Adjust historical to sum to total_hh
    for t in range(n_years):
        if years[t] <= p.baseline_year:
            raw_sum = sum(ws_hh_serv[i, t] for i in range(5))
            if raw_sum > 0:
                for i in range(5):
                    ws_hh_serv[i, t] = ws_hh_serv[i, t] + (ws_hh_serv[i, t] / raw_sum) * (total_hh[t] - raw_sum)

    common['ws_hh_serv_historical'] = ws_hh_serv
    common['ws_cagrs_hist'] = ws_cagrs

    # Sanitation service level history
    ss = inputs.sanitation_service
    san_pcts_start = [ss.pct_sserv1_start, ss.pct_sserv2_start, ss.pct_sserv3_start, ss.pct_sserv4_start, ss.pct_sserv5_start]
    san_pcts_base = [ss.pct_sserv1_baseline, ss.pct_sserv2_baseline, ss.pct_sserv3_baseline, ss.pct_sserv4_baseline, ss.pct_sserv5_baseline]

    san_hh_start = [total_hh_start_val * pct for pct in san_pcts_start]
    san_hh_base = [pop.total_hh_baseline * pct for pct in san_pcts_base]

    san_cagrs = []
    for i in range(5):
        if san_hh_start[i] > 0 and san_hh_base[i] > 0:
            san_cagrs.append((san_hh_base[i] / san_hh_start[i]) ** (1 / n_hist) - 1)
        elif san_hh_base[i] > 0:
            san_cagrs.append(0)
        else:
            san_cagrs.append(0)

    san_hh_serv = np.zeros((5, n_years))
    for i in range(5):
        san_hh_serv[i, 0] = san_hh_start[i]

    for t in range(1, n_years):
        if years[t] <= p.baseline_year:
            for i in range(5):
                san_hh_serv[i, t] = san_hh_serv[i, t - 1] * (1 + san_cagrs[i]) if san_cagrs[i] != 0 else san_hh_serv[i, t - 1]
        else:
            break

    for t in range(n_years):
        if years[t] <= p.baseline_year:
            raw_sum = sum(san_hh_serv[i, t] for i in range(5))
            if raw_sum > 0:
                for i in range(5):
                    san_hh_serv[i, t] = san_hh_serv[i, t] + (san_hh_serv[i, t] / raw_sum) * (total_hh[t] - raw_sum)

    common['san_hh_serv_historical'] = san_hh_serv
    common['san_cagrs_hist'] = san_cagrs

    # BAU investment time series
    bau = inputs.bau
    tech = inputs.technical

    # Water supply BAU network investment (I|General row 530 pattern)
    p1_len = bau.period1_end - bau.period1_start + 1
    p2_len = bau.period2_end - bau.period2_start + 1
    p3_len = bau.period3_end - bau.period3_start + 1

    ws_bau_network_inv = np.zeros(n_years)
    for t in range(n_years):
        if asis_flag[t] > 0 or perf_flag[t] > 0:
            if years[t] <= bau.period1_end:
                ws_bau_network_inv[t] = bau.ws_planned_2026_2030 / p1_len
            elif years[t] <= bau.period2_end:
                ws_bau_network_inv[t] = bau.ws_planned_2031_2035 / p2_len
            elif years[t] <= bau.period3_end:
                ws_bau_network_inv[t] = bau.ws_planned_2036_2040 / p3_len
            yrs_from_base = years[t] - p.baseline_year
            ws_bau_network_inv[t] *= (1 + bau.bau_inflation_rate) ** yrs_from_base

    # Water treatment capacity increase (Melamchi phases)
    ws_treatment_increase = np.zeros(n_years)
    for t in range(n_years):
        y = years[t]
        if bau.period1_start <= y <= bau.period1_end:
            ws_treatment_increase[t] = bau.melamchi_phase1_mld / p1_len
        elif bau.period2_start <= y <= bau.period2_end:
            ws_treatment_increase[t] = bau.melamchi_phase2_mld / p2_len

    # WASH budget forecast
    wash_budget = np.zeros(n_years)
    for t in range(n_years):
        if asis_flag[t] > 0 or perf_flag[t] > 0:
            wash_budget[t] = macro.wash_budget_pct_gdp * gdp_real_npr[t] if gdp_real_npr[t] > 0 else 0

    # Water supply total BAU investment (I|General row 526 pattern)
    ws_bau_total = ws_bau_network_inv.copy()

    # Sanitation BAU investments
    san_bau_wwt = np.zeros(n_years)
    san_bau_sewer = np.zeros(n_years)
    san_bau_fsm = np.zeros(n_years)
    san_sewer_pct = bau.san_sewer_inv_hist / bau.san_total_inv_hist if bau.san_total_inv_hist > 0 else (bau.san_sewer_inv_hist or 0.4)
    san_wwt_pct = bau.san_wwt_inv_hist / bau.san_total_inv_hist if bau.san_total_inv_hist > 0 else (bau.san_wwt_inv_hist or 0.16)
    san_fsm_pct = bau.san_fsm_inv_hist / bau.san_total_inv_hist if bau.san_total_inv_hist > 0 else (bau.san_fsm_inv_hist or 0.03)

    for t in range(n_years):
        if asis_flag[t] > 0 or perf_flag[t] > 0:
            total_san_bau = wash_budget[t] * bau.kv_share_avg * bau.sanitation_share_avg if wash_budget[t] > 0 else 0
            san_bau_wwt[t] = total_san_bau * san_wwt_pct
            san_bau_sewer[t] = total_san_bau * san_sewer_pct
            san_bau_fsm[t] = total_san_bau * san_fsm_pct

    san_bau_total = san_bau_wwt + san_bau_sewer + san_bau_fsm

    common['ws_bau_network_inv'] = ws_bau_network_inv
    common['ws_bau_total'] = ws_bau_total
    common['ws_treatment_increase'] = ws_treatment_increase
    common['san_bau_wwt'] = san_bau_wwt
    common['san_bau_sewer'] = san_bau_sewer
    common['san_bau_fsm'] = san_bau_fsm
    common['san_bau_total'] = san_bau_total
    common['wash_budget'] = wash_budget

    # Water requirement per HH per year (dynamic — shrinks as HH size declines)
    water_per_hh_year_arr = tech.ws_water_req_who_lpcd * avg_hh_size * c.days_in_year / c.cubic_meter_liters
    water_per_hh_year = water_per_hh_year_arr[yi(p.baseline_year)]  # baseline value for static calcs
    common['water_per_hh_year'] = water_per_hh_year
    common['water_per_hh_year_arr'] = water_per_hh_year_arr

    ws_results = calculate_water_supply(inputs, common)
    san_results = calculate_sanitation(inputs, common)

    return format_output(years, ws_results, san_results, common)


def format_output(years, ws, san, common):
    years_list = years.tolist()
    forecast_mask = [int(y) for y in years if y > common['years'][0]]

    def to_list(arr):
        if isinstance(arr, np.ndarray):
            return [float(x) if not np.isnan(x) else 0.0 for x in arr]
        return arr

    return {
        'years': [int(y) for y in years_list],
        'total_hh': to_list(common['total_hh']),
        'water_supply': {
            'bau_hh_serv': [to_list(ws['bau_hh'][i]) for i in range(5)],
            'target_hh_serv': [to_list(ws['target_hh'][i]) for i in range(5)],
            'target_hh_total': to_list(ws['target_hh_total']),
            'bau_hh_total': to_list(ws['bau_hh_total']),
            'service_gap': to_list(ws['service_gap']),
            'investment_need': to_list(ws['investment_need']),
            'bau_investment': to_list(ws['bau_investment']),
            'financing_gap': to_list(ws['financing_gap']),
            'cumulative_inv_need': to_list(ws['cumulative_inv_need']),
            'cumulative_bau_inv': to_list(ws['cumulative_bau_inv']),
            'interventions': {
                'collection_nrw': {
                    'additional_hh': to_list(ws['interv_ce_nrw_hh']),
                    'cumulative_hh': to_list(ws['interv_ce_nrw_cum_hh']),
                    'investment': to_list(ws['interv_ce_nrw_inv']),
                    'cumulative_inv': to_list(ws['interv_ce_nrw_cum_inv']),
                },
                'capital_efficiency': {
                    'additional_hh': to_list(ws['interv_capeff_hh']),
                    'cumulative_hh': to_list(ws['interv_capeff_cum_hh']),
                },
                'tariff': {
                    'additional_hh': to_list(ws['interv_tariff_hh']),
                    'cumulative_hh': to_list(ws['interv_tariff_cum_hh']),
                    'investment': to_list(ws['interv_tariff_inv']),
                    'cumulative_inv': to_list(ws['interv_tariff_cum_inv']),
                },
                'borrowing': {
                    'additional_hh': to_list(ws['interv_loan_hh']),
                    'cumulative_hh': to_list(ws['interv_loan_cum_hh']),
                    'investment': to_list(ws['interv_loan_inv']),
                    'cumulative_inv': to_list(ws['interv_loan_cum_inv']),
                },
            },
        },
        'sanitation': {
            'bau_hh_serv': [to_list(san['bau_hh'][i]) for i in range(5)],
            'target_hh_serv': [to_list(san['target_hh'][i]) for i in range(5)],
            'target_hh_total': to_list(san['target_hh_total']),
            'bau_hh_total': to_list(san['bau_hh_total']),
            'service_gap': to_list(san['service_gap']),
            'investment_need': to_list(san['investment_need']),
            'bau_investment': to_list(san['bau_investment']),
            'financing_gap': to_list(san['financing_gap']),
            'cumulative_inv_need': to_list(san['cumulative_inv_need']),
            'cumulative_bau_inv': to_list(san['cumulative_bau_inv']),
            'interventions': {
                'collection_efficiency': {
                    'additional_hh': to_list(san['interv_ce_hh']),
                    'cumulative_hh': to_list(san['interv_ce_cum_hh']),
                    'investment': to_list(san['interv_ce_inv']),
                    'cumulative_inv': to_list(san['interv_ce_cum_inv']),
                },
                'capital_efficiency': {
                    'additional_hh': to_list(san['interv_capeff_hh']),
                    'cumulative_hh': to_list(san['interv_capeff_cum_hh']),
                },
                'tariff': {
                    'additional_hh': to_list(san['interv_tariff_hh']),
                    'cumulative_hh': to_list(san['interv_tariff_cum_hh']),
                    'investment': to_list(san['interv_tariff_inv']),
                    'cumulative_inv': to_list(san['interv_tariff_cum_inv']),
                },
                'borrowing': {
                    'additional_hh': to_list(san['interv_loan_hh']),
                    'cumulative_hh': to_list(san['interv_loan_cum_hh']),
                    'investment': to_list(san['interv_loan_inv']),
                    'cumulative_inv': to_list(san['interv_loan_cum_inv']),
                },
                'microfinance': {
                    'additional_hh': to_list(san['interv_mf_hh']),
                    'cumulative_hh': to_list(san['interv_mf_cum_hh']),
                    'investment': to_list(san['interv_mf_inv']),
                    'cumulative_inv': to_list(san['interv_mf_cum_inv']),
                },
            },
        },
    }
