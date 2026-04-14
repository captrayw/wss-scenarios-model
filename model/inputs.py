from pydantic import BaseModel
from typing import List, Optional


class CountryConfig(BaseModel):
    country: str = "Nepal"
    area: str = "Kathmandu Valley"
    area_type: str = "Urban"  # Urban, Rural, National
    currency: str = "NPR"
    currency_usd: str = "USD"
    provider1_name: str = "KUKL"  # Main utility
    provider2_name: str = "WUSCs"  # Secondary providers
    # Water service level labels (JMP ladder)
    ws_serv1_name: str = "Treated-piped"
    ws_serv2_name: str = "Basic"
    ws_serv3_name: str = "Limited"
    ws_serv4_name: str = "Unimproved"
    ws_serv5_name: str = "No Service"
    # Sanitation service level labels
    san_serv1_name: str = "Safely managed"
    san_serv2_name: str = "Basic"
    san_serv3_name: str = "Limited"
    san_serv4_name: str = "Unimproved"
    san_serv5_name: str = "No Service"


class WaterProviderConfig(BaseModel):
    name: str = "Provider"
    share_pct: float = 0.0
    current_hh: int = 0
    network_cost_per_hh: float = 0.0
    cost_per_mld_treatment: float = 0.0
    existing_capacity_mld: float = 0.0


class SanitationProviderConfig(BaseModel):
    name: str = "Provider"
    share_pct: float = 0.0
    current_hh_sewer: int = 0
    current_hh_wwt: int = 0
    sewer_cost_per_hh: float = 0.0
    wwt_cost_per_mld: float = 0.0
    existing_wwt_capacity_mld: float = 0.0


class PeriodInputs(BaseModel):
    model_start_year: int = 2011
    forecast_end_year: int = 2040
    baseline_year: int = 2025
    as_is_forecast_start: int = 2026
    as_is_forecast_length: int = 2
    target1_year: int = 2030
    target2_year: int = 2040


class Constants(BaseModel):
    hours_in_day: int = 24
    days_in_month: int = 30
    days_in_year: int = 365
    months_in_year: int = 12
    working_day_hours: int = 8
    cubic_meter_liters: int = 1000
    thousand: int = 1000
    million: int = 1_000_000


class MacroInputs(BaseModel):
    # Annual time-series (30 values, 2011-2040)
    gdp_growth: List[float] = [
        0.034, 0.047, 0.035, 0.06, 0.04, 0.004, 0.09, 0.076, 0.067, -0.024,
        0.048, 0.056, 0.02, 0.031, 0.04, 0.055, 0.05, 0.05, 0.05, 0.05,
        0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05
    ]
    gdp_nominal_usd: List[float] = [
        21.685, 21.703, 22.162, 22.722, 24.361, 24.524, 28.972, 33.112,
        34.186, 33.434, 36.927, 41.183, 40.907, 43.419, 46.08, 49.603,
        54.449, 59.728, 65.494, 71.783, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
    ]
    inflation_nepal: List[float] = [
        0.096, 0.083, 0.099, 0.09, 0.078, 0.099, 0.045, 0.041, 0.046, 0.061,
        0.036, 0.064, 0.077, 0.054, 0.049, 0.05, 0.051, 0.05, 0.05, 0.05,
        0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05
    ]
    inflation_us: List[float] = [
        0.031, 0.021, 0.015, 0.016, 0.001, 0.013, 0.021, 0.024, 0.018, 0.013,
        0.047, 0.08, 0.041, 0.03, 0.03, 0.025, 0.021, 0.022, 0.022, 0.022,
        0.022, 0.022, 0.022, 0.022, 0.022, 0.022, 0.022, 0.022, 0.022, 0.022
    ]
    exchange_rate: List[float] = [
        74.597, 85.428, 93.631, 97.624, 102.615, 107.483, 104.195, 109.413,
        112.639, 118.559, 118.267, 125.738, 132.136, 133.870, 136.339,
        139.665, 143.768, 147.707, 151.754, 155.912, 160.183, 164.572,
        169.081, 173.713, 178.472, 183.362, 188.385, 193.547, 198.849, 204.297
    ]
    real_price_year: int = 2025  # baseline year for real price deflation
    wash_budget_pct_gdp: float = 0.01125


class PopulationInputs(BaseModel):
    total_pop_start: int = 2_423_388
    total_hh_start: float = 0.608220  # millions
    total_pop_baseline: int = 3_306_160
    total_hh_baseline: float = 0.94  # millions
    pop_growth_projected: float = 0.022435168902713576
    hh_size_growth_projected: float = -0.008869176358084485


class WaterServiceLevelInputs(BaseModel):
    # Start year data
    hh_treated_piped_start: int = 320_637
    hh_no_treated_piped_start: int = 246_259
    hh_24hr_water_start: int = 0
    pct_serv1_start: float = 0.0       # Treated-piped (safely managed)
    pct_serv2_start: float = 0.5653    # Basic
    pct_serv3_start: float = 0.4341    # Limited
    pct_serv4_start: float = 0.0       # Unimproved
    pct_serv5_start: float = 0.0006    # No Service

    # Baseline year data
    hh_treated_piped_baseline: int = 388_993
    hh_no_piped_baseline: int = 368_201
    hh_24hr_water_baseline: int = 0
    pct_piped_water_baseline: float = 0.0  # % of HHs with piped water
    hh_treated_piped_conn_baseline: int = 388_993
    hist_increase_treated_piped: float = 0.02

    # KUKL breakdown
    kukl_hh_piped_treated: int = 262_212
    kukl_hh_24hr: int = 0

    # WUSCs breakdown
    wusc_hh_piped_treated: int = 126_781
    wusc_hh_24hr: int = 0

    # Non-piped
    nonpiped_hh: int = 368_201
    nonpiped_hh_treated: int = 0

    # Baseline percentages
    pct_serv1_baseline: float = 0.0       # Treated-piped (safely managed)
    pct_serv2_baseline: float = 0.4138    # Basic
    pct_serv3_baseline: float = 0.3917    # Limited
    pct_serv4_baseline: float = 0.0       # Unimproved
    pct_serv5_baseline: float = 0.1945    # No Service

    hh_kukl_baseline: int = 262_212


class SanitationServiceLevelInputs(BaseModel):
    # Start year data
    hh_sewered_start: int = 159_814
    hh_onsite_start: int = 407_082
    pct_sserv1_start: float = 0.0       # Safely managed
    pct_sserv2_start: float = 0.2817    # Basic
    pct_sserv3_start: float = 0.7177    # Limited
    pct_sserv4_start: float = 0.0       # Unimproved
    pct_sserv5_start: float = 0.0006    # No Service

    # Baseline year data
    hh_sewered_baseline: int = 454_860
    hh_onsite_baseline: int = 250_249
    hh_sewered_wwt_baseline: int = 73_000   # With wastewater treatment
    hh_onsite_with_collection: int = 125_125  # G247: HHs with on-site + collection/treatment
    hh_fs_emptied_baseline: int = 312        # G248: HHs with fecal sludge emptied
    hh_kukl_sewer_baseline: int = 180_000
    kukl_hh_wwt: int = 73_000
    wusc_hh_sewer: int = 274_860
    wusc_hh_wwt: int = 0

    pct_sserv1_baseline: float = 0.0       # Safely managed
    pct_sserv2_baseline: float = 0.4839    # Basic
    pct_sserv3_baseline: float = 0.2663    # Limited
    pct_sserv4_baseline: float = 0.0       # Unimproved
    pct_sserv5_baseline: float = 0.2498    # No Service


class WaterTargetInputs(BaseModel):
    # Dynamic providers list (replaces kukl_pct/wusc_pct/non_piped_pct)
    providers: List[WaterProviderConfig] = [
        WaterProviderConfig(name="KUKL", share_pct=0.4192, current_hh=262_212,
            network_cost_per_hh=96_877.93, cost_per_mld_treatment=0.0, existing_capacity_mld=117.0),
        WaterProviderConfig(name="WUSCs", share_pct=0.5808, current_hh=220_694,
            network_cost_per_hh=88_021.23, cost_per_mld_treatment=0.0, existing_capacity_mld=0.0),
    ]
    planned_treatment_capacity_mld: float = 510.0

    target1_serv1: float = 0.66
    target1_serv2: float = 0.34
    target1_serv3: float = 0.0
    target1_serv4: float = 0.0
    target1_serv5: float = 0.0

    target2_serv1: float = 1.0
    target2_serv2: float = 0.0
    target2_serv3: float = 0.0
    target2_serv4: float = 0.0
    target2_serv5: float = 0.0


class SanitationTargetInputs(BaseModel):
    # Dynamic providers list (replaces sewered_kukl_pct/sewered_wusc_pct)
    providers: List[SanitationProviderConfig] = [
        SanitationProviderConfig(name="KUKL", share_pct=0.4192, current_hh_sewer=180_000,
            current_hh_wwt=73_000, sewer_cost_per_hh=117_290.77, wwt_cost_per_mld=0.0, existing_wwt_capacity_mld=19.0),
        SanitationProviderConfig(name="WUSCs", share_pct=0.4608, current_hh_sewer=426_386,
            current_hh_wwt=0, sewer_cost_per_hh=106_567.90, wwt_cost_per_mld=0.0, existing_wwt_capacity_mld=0.0),
    ]
    onsite_collection_treatment_pct: float = 0.12

    target1_sserv1: float = 0.66
    target1_sserv2: float = 0.34
    target1_sserv3: float = 0.0
    target1_sserv4: float = 0.0
    target1_sserv5: float = 0.0

    target2_sserv1: float = 1.0
    target2_sserv2: float = 0.0
    target2_sserv3: float = 0.0
    target2_sserv4: float = 0.0
    target2_sserv5: float = 0.0


class WaterUnitCosts(BaseModel):
    # Distribution network cost per service level
    network_cost_per_hh_serv1: float = 96_877.93   # Treated-piped
    network_cost_per_hh_serv2: float = 96_877.93   # Basic
    network_cost_per_hh_serv3: float = 0.0         # Limited
    network_cost_per_hh_serv4: float = 0.0         # Unimproved
    network_cost_per_hh_serv5: float = 0.0         # No Service

    # KUKL
    kukl_network_cost_per_hh: float = 96_877.93
    kukl_cost_per_mld_treatment: float = 0.0

    # WUSCs
    wusc_cost_per_capita: float = 25_026.0
    wusc_network_cost_per_hh: float = 0.0
    wusc_cost_per_mld_treatment: float = 0.0

    # Non-piped
    dug_well_cost: float = 52_713.0
    borehole_cost: float = 400_000.0
    hh_treatment_system_cost: float = 8_000.0


class SanitationUnitCosts(BaseModel):
    # Sewerage cost per service level
    sewer_cost_per_hh_sserv1: float = 117_290.77   # Safely managed
    sewer_cost_per_hh_sserv2: float = 117_290.77   # Basic
    sewer_cost_per_hh_sserv3: float = 0.0          # Limited
    sewer_cost_per_hh_sserv4: float = 0.0          # Unimproved
    sewer_cost_per_hh_sserv5: float = 0.0          # No Service

    cost_ratio_wusc_kukl: float = 1.0

    # KUKL sewered
    kukl_sewer_cost_per_hh: float = 117_290.77
    kukl_wwt_cost_per_mld: float = 0.0

    # WUSCs sewered
    wusc_sewer_cost_per_hh: float = 117_290.77
    wusc_wwt_cost_per_mld: float = 0.0

    sewer_network_cost_per_hh: float = 117_290.77

    # On-site facility
    onsite_facility_capex: float = 81_604.08  # G405: weighted avg from adoption rates × costs

    # Adoption rates (whole urban population)
    adopt_septic_tank: float = 0.336
    adopt_pit_latrine: float = 0.006
    adopt_vip_latrine: float = 0.0
    adopt_pit_with_slab: float = 0.0
    adopt_composting_toilet: float = 0.0

    # Costs per type
    cost_septic_tank: float = 83_000.0
    cost_pit_latrine: float = 14_600.0
    cost_vip_latrine: float = 16_500.0
    cost_pit_with_slab: float = 14_600.0
    cost_composting_toilet: float = 22_000.0

    # Adoption rates among on-site HHs
    onsite_adopt_septic_tank: float = 0.0
    onsite_adopt_pit_latrine: float = 0.0
    onsite_adopt_vip_latrine: float = 0.0
    onsite_adopt_pit_with_slab: float = 0.0
    onsite_adopt_composting_toilet: float = 0.0

    weighted_onsite_cost: float = 14_600.0

    # Collection capex
    fs_truck_cost_mill: float = 12.45
    truck_size_m3: float = 6.0
    fs_per_person_per_day_liters: float = 0.7
    emptying_frequency_years: float = 3.2  # G411
    trips_per_truck_year: int = 1680  # G412
    cost_collection_per_hh: float = 2_000.0

    # Treatment
    cost_per_mld_fst: float = 395.0


class BAUInvestmentInputs(BaseModel):
    # Investment period boundaries
    period1_start: int = 2026
    period1_end: int = 2030
    period2_start: int = 2031
    period2_end: int = 2035
    period3_start: int = 2036
    period3_end: int = 2040
    bau_inflation_rate: float = 0.05  # inflation applied to BAU investment

    # KV spending shares by region
    kv_share_2021: float = 0.31
    kv_share_2022: float = 0.39
    kv_share_2023: float = 0.29
    kv_share_avg: float = 0.33

    # Spending by sector
    water_share_2021: float = 0.80
    water_share_2022: float = 0.54
    water_share_2023: float = 0.45
    water_share_avg: float = 0.5967  # exact average from Excel G468
    sanitation_share_2021: float = 0.0
    sanitation_share_2022: float = 0.0
    sanitation_share_2023: float = 0.0
    sanitation_share_avg: float = 0.12
    wss_combined_share_avg: float = 0.2667  # water+sanitation combined share (G470)

    large_urban_pct: float = 0.6087
    capex_pct_budget: float = 0.21

    # WASH budget % GDP by year
    wash_gdp_2020_21: float = 0.013
    wash_gdp_2021_22: float = 0.014
    wash_gdp_2022_23: float = 0.010
    wash_gdp_2023_24: float = 0.008
    wash_gdp_avg: float = 0.01125

    # Water supply investment
    ws_total_inv_hist: float = 14_832.0
    ws_planned_2026_2030: float = 16_224.0
    ws_planned_2031_2035: float = 14_005.0
    ws_planned_2036_2040: float = 9_306.0
    ws_planned_2041_2045: float = 0.0
    ws_planned_2046_2050: float = 0.0

    # Distribution network investment
    ws_network_pct_of_ws: float = 0.5893  # network investment as % of total WS investment
    ws_dist_network_hist: float = 2_996.0
    ws_dist_network_2026_2030: float = 0.0
    ws_dist_network_2031_2035: float = 0.0
    ws_dist_network_2036_2040: float = 0.0

    # Water treatment
    ws_production_inv_hist: float = 0.0
    ws_treatment_capacity_increased: float = 148.3
    ws_avg_capex_per_mld: float = 0.0
    melamchi_phase1_mld: float = 47.0
    melamchi_phase2_mld: float = 100.0

    # Sanitation investment
    san_total_inv_hist: float = 12_986.0
    san_planned_2026_2030: float = 0.0
    san_planned_2031_2035: float = 0.0
    san_planned_2036_2040: float = 0.0

    san_wwt_inv_hist: float = 2_113.0
    san_wwt_2026_2030: float = 0.0
    san_wwt_2031_2035: float = 0.0
    san_wwt_2036_2040: float = 0.0

    san_sewer_inv_hist: float = 5_383.0
    san_sewer_2026_2030: float = 0.0
    san_sewer_2031_2035: float = 0.0
    san_sewer_2036_2040: float = 0.0

    san_fsm_inv_hist: float = 453.0
    san_fsm_2026_2030: float = 2_533.3  # planned FSM investment (separate from WASH budget)
    san_fsm_2031_2035: float = 2_113.3
    san_fsm_2036_2040: float = 1_273.2

    # Sub-sector shares of sanitation capex budget (from planned investment ratios)
    san_wwt_share_of_capex: float = 0.2971  # WWT as % of san capex
    san_sewer_share_of_capex: float = 0.5865  # Sewer as % of san capex


class TechnicalInputs(BaseModel):
    # Water supply
    ws_pct_domestic: float = 0.9
    ws_non_hh_pct_of_hh: float = 0.11111111  # non-HH as % of HH = (1-domestic)/domestic
    ws_non_hh_capex_pct: float = 0.10  # non-HH / (non-HH + HH)
    ws_asset_life: int = 30
    ws_depreciation_rate: float = 0.03333333  # 1/asset_life
    ws_replacement_rate: float = 0.03333333  # same as depreciation
    ws_existing_treatment_mld: float = 117.0
    ws_num_treatment_plants: int = 26
    ws_water_req_who_lpcd: float = 75.0

    # Sanitation
    san_pct_domestic: float = 0.9
    san_non_hh_pct_of_hh: float = 0.11111111
    san_non_hh_capex_pct: float = 0.10
    san_asset_life: int = 30
    san_depreciation_rate: float = 0.03333333
    san_replacement_rate: float = 0.03333333

    # Existing WWTPs
    wwtp_hanumanghat_mld: float = 0.5
    wwtp_sallaghari_mld: float = 2.0
    wwtp_kodku_mld: float = 1.1
    wwtp_dhobighat_mld: float = 15.4
    san_existing_wwtp_mld: float = 19.0  # sum of above

    # Proposed WWTPs
    proposed_guheshwori_mld: float = 32.4
    proposed_sallaghari_mld: float = 14.2
    proposed_kodku_mld: float = 17.5
    proposed_dhobighat_mld: float = 74.0
    wwtp_capex: float = 0.0

    san_avg_capex_per_mld_wwt: float = 0.0
    san_avg_capex_per_mld_fst: float = 395.0
    san_existing_wusc_wwt_mld: float = 0.0
    san_existing_fst_mld: float = 0.000857
    san_fs_per_person_per_day: float = 0.7
    san_wastewater_factor: float = 0.8


class WaterInterventionInputs(BaseModel):
    # Collection efficiency
    ce_start_year: int = 2028
    ce_target_year: int = 2031
    ce_current_ratio: float = 0.83
    ce_target_ratio: float = 0.98
    ce_water_sold_mld: float = 240.0
    ce_water_sold_m3_yr: float = 0.0
    ce_current_tariff: float = 32.0

    # NRW reduction
    nrw_start_year: int = 2028
    nrw_target_year: int = 2034
    nrw_current_pct: float = 0.40
    nrw_target_pct: float = 0.15
    nrw_commercial_loss_pct: float = 0.50
    nrw_lag_years: int = 1
    nrw_capex_unit_cost_usd: float = 510.29
    nrw_capex_unit_cost_npr: float = 73_809.07  # G673: USD × inflation-adj × exchange_rate
    nrw_avg_consumption_per_hh: float = 0.0
    nrw_dist_cost_pct_serv1: float = 0.0
    nrw_dist_cost_pct_serv2: float = 0.0

    # Capital efficiency
    capeff_start_year: int = 2027
    capeff_gains_pct: float = 0.20

    # Tariff increase
    tariff_start_year: int = 2028
    tariff_target_year: int = 2033
    tariff_monthly_income_bottom20: float = 10_904.0
    tariff_max_pct_income_water: float = 0.05
    tariff_kukl_op_revenue: float = 1_169_262_000.0
    tariff_kukl_op_expenditure: float = 954_612_000.0
    tariff_current_om_recovery: float = 0.0  # computed = revenue/expenditure
    tariff_om_recovery_target: float = 1.5

    # Borrowing
    loan_start_year: int = 2036
    loan_end_year: int = 2040
    loan_avg_cost_per_water: float = 0.0
    loan_dscr: float = 1.2
    loan_grace_years: int = 4
    loan_tenor: int = 12
    loan_interest_rate: float = 0.067
    loan_investment_years: int = 4
    loan_cap: float = 12_500.0


class SanitationInterventionInputs(BaseModel):
    # Collection efficiency
    ce_start_year: int = 2027
    ce_target_year: int = 2030
    ce_current_ratio: float = 0.83
    ce_target_ratio: float = 0.98
    ce_wastewater_collected_pct: float = 0.80
    ce_ww_volume_billed: float = 70.08  # m3/yr millions = water_sold × ww_collected%
    ce_sewer_tariff_pct_water: float = 0.50
    ce_current_sewer_tariff: float = 16.0  # = water tariff × sewer%

    # Capital efficiency
    capeff_start_year: int = 2027
    capeff_gains_pct: float = 0.20

    # Tariff increase
    tariff_start_year: int = 2028
    tariff_target_year: int = 2033
    tariff_max_pct_income_san: float = 0.05
    tariff_current_om_recovery: float = 1.2249
    tariff_om_recovery_target: float = 1.5
    san_tariff_growth_rate: float = 0.0  # computed from O&M recovery ratio

    # Borrowing
    loan_start_year: int = 2036
    loan_end_year: int = 2040
    loan_avg_cost_per_ww_billed: float = 0.0
    loan_dscr: float = 1.2
    loan_grace_years: int = 4
    loan_tenor: int = 12
    loan_interest_rate: float = 0.067
    loan_investment_years: int = 3
    loan_cap: float = 12_500.0

    # Microfinance
    mf_start_year: int = 2028
    mf_end_year: int = 2040
    mf_onsite_cost: float = 14_600.0
    mf_interest_rate: float = 0.067
    mf_tenor: int = 12
    mf_collection_cost: float = 6_000.0
    mf_emptying_frequency: float = 3.0
    mf_max_pct_income: float = 0.05
    mf_low_percentile: float = 0.05
    mf_high_percentile: float = 0.20
    mf_adoption_rate: float = 0.5  # share of on-site HH change adopted via microfinance


class CustomIntervention(BaseModel):
    name: str = "Custom Intervention"
    enabled: bool = True
    sector: str = "water"  # "water", "sanitation", "both"
    intervention_type: str = "fixed_annual"  # "fixed_annual", "revenue_stream", "per_hh_subsidy"
    start_year: int = 2028
    end_year: int = 2035
    annual_amount: float = 0.0       # For fixed_annual: currency millions per year
    starting_amount: float = 0.0     # For revenue_stream: starting currency millions
    growth_rate: float = 0.05        # For revenue_stream: annual growth rate
    subsidy_per_hh: float = 0.0      # For per_hh_subsidy: currency per HH
    color: str = "#9333ea"


class InterventionToggles(BaseModel):
    # Water supply
    ws_collection_nrw_enabled: bool = True
    ws_capital_efficiency_enabled: bool = True
    ws_tariff_enabled: bool = True
    ws_borrowing_enabled: bool = True

    # Sanitation
    san_collection_enabled: bool = True
    san_capital_efficiency_enabled: bool = True
    san_tariff_enabled: bool = True
    san_borrowing_enabled: bool = True
    san_microfinance_enabled: bool = True


class ModelInputs(BaseModel):
    country_config: CountryConfig = CountryConfig()
    period: PeriodInputs = PeriodInputs()
    constants: Constants = Constants()
    macro: MacroInputs = MacroInputs()
    population: PopulationInputs = PopulationInputs()
    water_service: WaterServiceLevelInputs = WaterServiceLevelInputs()
    sanitation_service: SanitationServiceLevelInputs = SanitationServiceLevelInputs()
    water_targets: WaterTargetInputs = WaterTargetInputs()
    sanitation_targets: SanitationTargetInputs = SanitationTargetInputs()
    water_costs: WaterUnitCosts = WaterUnitCosts()
    sanitation_costs: SanitationUnitCosts = SanitationUnitCosts()
    bau: BAUInvestmentInputs = BAUInvestmentInputs()
    technical: TechnicalInputs = TechnicalInputs()
    water_interventions: WaterInterventionInputs = WaterInterventionInputs()
    sanitation_interventions: SanitationInterventionInputs = SanitationInterventionInputs()
    toggles: InterventionToggles = InterventionToggles()
    custom_interventions: List[CustomIntervention] = []
