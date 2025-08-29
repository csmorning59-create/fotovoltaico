"""
Modulo per l'analisi economica completa di progetti fotovoltaici con BESS
"""

import logging
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

@dataclass
class EconomicParameters:
    """Parametri economici per l'analisi finanziaria"""
    # Prezzi energia
    electricity_price_f1: float = 0.28  # €/kWh fascia F1 (punta)
    electricity_price_f2: float = 0.25  # €/kWh fascia F2 (intermedia)
    electricity_price_f3: float = 0.22  # €/kWh fascia F3 (base)
    feed_in_tariff: float = 0.05  # €/kWh tariffa immissione
    
    # Costi impianto FV
    pv_capex_per_kwp: float = 1200  # €/kWp
    pv_opex_annual_percent: float = 0.015  # 1.5% del CAPEX all'anno
    
    # Costi BESS
    bess_capex_per_kwh: float = 500  # €/kWh
    bess_opex_annual_percent: float = 0.01  # 1% del CAPEX all'anno
    
    # Parametri finanziari
    wacc: float = 0.05  # Weighted Average Cost of Capital (5%)
    analysis_years: int = 20  # Anni di analisi
    
    # Escalation rates
    electricity_price_escalation: float = 0.02  # 2% annuo
    opex_escalation: float = 0.02  # 2% annuo
    
    # Incentivi e detrazioni
    tax_deduction_percent: float = 0.0  # Detrazione fiscale (es. 50%)
    green_certificates: float = 0.0  # €/MWh certificati verdi

@dataclass
class EconomicResults:
    """Risultati dell'analisi economica"""
    # Scenario FV solo
    pv_only_npv: float
    pv_only_irr: float
    pv_only_payback: float
    pv_only_capex: float
    pv_only_annual_savings: float
    
    # Scenario FV + BESS
    pv_bess_npv: float
    pv_bess_irr: float
    pv_bess_payback: float
    pv_bess_capex: float
    pv_bess_annual_savings: float
    
    # Confronto
    bess_incremental_npv: float  # NPV incrementale del BESS
    bess_incremental_irr: float  # IRR incrementale del BESS
    bess_incremental_payback: float  # Payback incrementale del BESS
    
    # Breakdown dettagliato
    annual_cash_flows_pv: List[float]  # Flussi di cassa FV solo
    annual_cash_flows_pv_bess: List[float]  # Flussi di cassa FV+BESS
    
    # Analisi di sensibilità
    sensitivity_analysis: Dict[str, Dict[str, float]]
    
    # KPI riassuntivi
    total_investment: float
    total_annual_production: float
    total_annual_savings: float
    lcoe: float  # Levelized Cost of Energy

class EconomicCalculator:
    """Calcolatore per analisi economica completa"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_complete_economic_analysis(
        self,
        pv_power_kwp: float,
        pv_production_annual: float,  # kWh/anno
        pv_production_monthly: List[float],  # kWh mensili
        consumption_annual: float,  # kWh/anno
        consumption_monthly: List[float],  # kWh mensili
        bess_capacity_kwh: Optional[float] = None,
        bess_annual_throughput: Optional[float] = None,
        bess_self_consumption_increase: Optional[float] = None,
        economic_params: Optional[EconomicParameters] = None
    ) -> EconomicResults:
        """
        Calcola l'analisi economica completa per FV e FV+BESS
        
        Args:
            pv_power_kwp: Potenza FV installata
            pv_production_annual: Produzione FV annuale
            pv_production_monthly: Produzione FV mensile
            consumption_annual: Consumo annuale
            consumption_monthly: Consumo mensile
            bess_capacity_kwh: Capacità BESS (opzionale)
            bess_annual_throughput: Energia annuale attraverso BESS
            bess_self_consumption_increase: Aumento autoconsumo con BESS
            economic_params: Parametri economici
        
        Returns:
            EconomicResults con analisi completa
        """
        if economic_params is None:
            economic_params = EconomicParameters()
        
        try:
            # 1. Analisi scenario FV solo
            pv_only_results = self._calculate_pv_only_scenario(
                pv_power_kwp,
                pv_production_annual,
                pv_production_monthly,
                consumption_monthly,
                economic_params
            )
            
            # 2. Analisi scenario FV + BESS (se presente)
            if bess_capacity_kwh and bess_self_consumption_increase:
                pv_bess_results = self._calculate_pv_bess_scenario(
                    pv_power_kwp,
                    pv_production_annual,
                    pv_production_monthly,
                    consumption_monthly,
                    bess_capacity_kwh,
                    bess_self_consumption_increase,
                    economic_params
                )
                
                # 3. Calcolo incrementale BESS
                incremental_results = self._calculate_incremental_bess_economics(
                    pv_only_results,
                    pv_bess_results,
                    bess_capacity_kwh,
                    economic_params
                )
            else:
                # Scenario senza BESS
                pv_bess_results = pv_only_results.copy()
                incremental_results = {
                    'npv': 0,
                    'irr': 0,
                    'payback': float('inf')
                }
            
            # 4. Analisi di sensibilità
            sensitivity_results = self._calculate_sensitivity_analysis(
                pv_power_kwp,
                pv_production_annual,
                consumption_annual,
                bess_capacity_kwh or 0,
                economic_params
            )
            
            # 5. Calcolo LCOE
            lcoe = self._calculate_lcoe(
                pv_only_results['capex'],
                pv_only_results['annual_opex'],
                pv_production_annual,
                economic_params
            )
            
            return EconomicResults(
                # Scenario FV solo
                pv_only_npv=pv_only_results['npv'],
                pv_only_irr=pv_only_results['irr'],
                pv_only_payback=pv_only_results['payback'],
                pv_only_capex=pv_only_results['capex'],
                pv_only_annual_savings=pv_only_results['annual_savings'],
                
                # Scenario FV + BESS
                pv_bess_npv=pv_bess_results['npv'],
                pv_bess_irr=pv_bess_results['irr'],
                pv_bess_payback=pv_bess_results['payback'],
                pv_bess_capex=pv_bess_results['capex'],
                pv_bess_annual_savings=pv_bess_results['annual_savings'],
                
                # Incrementale BESS
                bess_incremental_npv=incremental_results['npv'],
                bess_incremental_irr=incremental_results['irr'],
                bess_incremental_payback=incremental_results['payback'],
                
                # Flussi di cassa
                annual_cash_flows_pv=pv_only_results['cash_flows'],
                annual_cash_flows_pv_bess=pv_bess_results['cash_flows'],
                
                # Altri risultati
                sensitivity_analysis=sensitivity_results,
                total_investment=pv_bess_results['capex'],
                total_annual_production=pv_production_annual,
                total_annual_savings=pv_bess_results['annual_savings'],
                lcoe=lcoe
            )
            
        except Exception as e:
            self.logger.error(f"Errore analisi economica: {e}")
            raise
    
    def _calculate_pv_only_scenario(
        self,
        pv_power_kwp: float,
        pv_production_annual: float,
        pv_production_monthly: List[float],
        consumption_monthly: List[float],
        economic_params: EconomicParameters
    ) -> Dict:
        """Calcola scenario FV solo"""
        
        # CAPEX e OPEX FV
        pv_capex = pv_power_kwp * economic_params.pv_capex_per_kwp
        pv_opex_annual = pv_capex * economic_params.pv_opex_annual_percent
        
        # Calcolo autoconsumo e immissione mensile
        monthly_self_consumption = []
        monthly_grid_export = []
        monthly_grid_import = []
        
        for i in range(12):
            production = pv_production_monthly[i]
            consumption = consumption_monthly[i]
            
            self_consumption = min(production, consumption)
            grid_export = max(0, production - consumption)
            grid_import = max(0, consumption - production)
            
            monthly_self_consumption.append(self_consumption)
            monthly_grid_export.append(grid_export)
            monthly_grid_import.append(grid_import)
        
        # Totali annuali
        annual_self_consumption = sum(monthly_self_consumption)
        annual_grid_export = sum(monthly_grid_export)
        annual_grid_import = sum(monthly_grid_import)
        
        # Calcolo risparmi annuali (semplificato con prezzo medio)
        avg_electricity_price = (
            economic_params.electricity_price_f1 * 0.33 +
            economic_params.electricity_price_f2 * 0.33 +
            economic_params.electricity_price_f3 * 0.34
        )
        
        annual_savings = (
            annual_self_consumption * avg_electricity_price +  # Energia non acquistata
            annual_grid_export * economic_params.feed_in_tariff  # Energia venduta
        )
        
        # Calcolo flussi di cassa
        cash_flows = []
        for year in range(economic_params.analysis_years):
            # Escalation prezzi
            escalated_savings = annual_savings * (1 + economic_params.electricity_price_escalation) ** year
            escalated_opex = pv_opex_annual * (1 + economic_params.opex_escalation) ** year
            
            net_cash_flow = escalated_savings - escalated_opex
            cash_flows.append(net_cash_flow)
        
        # Calcolo NPV, IRR, Payback
        npv = self._calculate_npv([-pv_capex] + cash_flows, economic_params.wacc)
        irr = self._calculate_irr([-pv_capex] + cash_flows)
        payback = self._calculate_payback(pv_capex, cash_flows)
        
        return {
            'npv': npv,
            'irr': irr,
            'payback': payback,
            'capex': pv_capex,
            'annual_opex': pv_opex_annual,
            'annual_savings': annual_savings,
            'cash_flows': cash_flows,
            'annual_self_consumption': annual_self_consumption,
            'annual_grid_export': annual_grid_export,
            'annual_grid_import': annual_grid_import
        }
    
    def _calculate_pv_bess_scenario(
        self,
        pv_power_kwp: float,
        pv_production_annual: float,
        pv_production_monthly: List[float],
        consumption_monthly: List[float],
        bess_capacity_kwh: float,
        bess_self_consumption_increase: float,
        economic_params: EconomicParameters
    ) -> Dict:
        """Calcola scenario FV + BESS"""
        
        # CAPEX totale
        pv_capex = pv_power_kwp * economic_params.pv_capex_per_kwp
        bess_capex = bess_capacity_kwh * economic_params.bess_capex_per_kwh
        total_capex = pv_capex + bess_capex
        
        # OPEX totale
        pv_opex_annual = pv_capex * economic_params.pv_opex_annual_percent
        bess_opex_annual = bess_capex * economic_params.bess_opex_annual_percent
        total_opex_annual = pv_opex_annual + bess_opex_annual
        
        # Calcolo autoconsumo migliorato con BESS
        # Semplificazione: aggiungiamo l'aumento di autoconsumo del BESS
        annual_self_consumption_base = min(pv_production_annual, sum(consumption_monthly))
        annual_self_consumption_with_bess = annual_self_consumption_base + bess_self_consumption_increase
        
        # Ricalcolo immissione e prelievo
        annual_grid_export = max(0, pv_production_annual - annual_self_consumption_with_bess)
        annual_grid_import = max(0, sum(consumption_monthly) - annual_self_consumption_with_bess)
        
        # Calcolo risparmi annuali
        avg_electricity_price = (
            economic_params.electricity_price_f1 * 0.33 +
            economic_params.electricity_price_f2 * 0.33 +
            economic_params.electricity_price_f3 * 0.34
        )
        
        annual_savings = (
            annual_self_consumption_with_bess * avg_electricity_price +
            annual_grid_export * economic_params.feed_in_tariff
        )
        
        # Calcolo flussi di cassa
        cash_flows = []
        for year in range(economic_params.analysis_years):
            escalated_savings = annual_savings * (1 + economic_params.electricity_price_escalation) ** year
            escalated_opex = total_opex_annual * (1 + economic_params.opex_escalation) ** year
            
            net_cash_flow = escalated_savings - escalated_opex
            cash_flows.append(net_cash_flow)
        
        # Calcolo NPV, IRR, Payback
        npv = self._calculate_npv([-total_capex] + cash_flows, economic_params.wacc)
        irr = self._calculate_irr([-total_capex] + cash_flows)
        payback = self._calculate_payback(total_capex, cash_flows)
        
        return {
            'npv': npv,
            'irr': irr,
            'payback': payback,
            'capex': total_capex,
            'annual_opex': total_opex_annual,
            'annual_savings': annual_savings,
            'cash_flows': cash_flows,
            'annual_self_consumption': annual_self_consumption_with_bess,
            'annual_grid_export': annual_grid_export,
            'annual_grid_import': annual_grid_import
        }
    
    def _calculate_incremental_bess_economics(
        self,
        pv_only_results: Dict,
        pv_bess_results: Dict,
        bess_capacity_kwh: float,
        economic_params: EconomicParameters
    ) -> Dict:
        """Calcola l'economia incrementale del BESS"""
        
        # Investimento incrementale
        bess_capex = bess_capacity_kwh * economic_params.bess_capex_per_kwh
        
        # Flussi di cassa incrementali
        incremental_cash_flows = [
            pv_bess_results['cash_flows'][i] - pv_only_results['cash_flows'][i]
            for i in range(len(pv_only_results['cash_flows']))
        ]
        
        # NPV, IRR, Payback incrementali
        incremental_npv = self._calculate_npv([-bess_capex] + incremental_cash_flows, economic_params.wacc)
        incremental_irr = self._calculate_irr([-bess_capex] + incremental_cash_flows)
        incremental_payback = self._calculate_payback(bess_capex, incremental_cash_flows)
        
        return {
            'npv': incremental_npv,
            'irr': incremental_irr,
            'payback': incremental_payback
        }
    
    def _calculate_sensitivity_analysis(
        self,
        pv_power_kwp: float,
        pv_production_annual: float,
        consumption_annual: float,
        bess_capacity_kwh: float,
        economic_params: EconomicParameters
    ) -> Dict[str, Dict[str, float]]:
        """Calcola l'analisi di sensibilità"""
        
        base_params = economic_params
        sensitivity_results = {}
        
        # Variazioni da testare
        variations = [-20, -10, 0, 10, 20]  # Percentuali
        
        # Parametri da variare
        sensitivity_params = {
            'electricity_price': 'electricity_price_f2',
            'pv_capex': 'pv_capex_per_kwp',
            'bess_capex': 'bess_capex_per_kwh',
            'wacc': 'wacc'
        }
        
        for param_name, param_attr in sensitivity_params.items():
            sensitivity_results[param_name] = {}
            
            for variation in variations:
                # Crea parametri modificati
                modified_params = EconomicParameters(**base_params.__dict__)
                base_value = getattr(modified_params, param_attr)
                setattr(modified_params, param_attr, base_value * (1 + variation / 100))
                
                # Calcolo rapido NPV
                try:
                    # Semplificazione per analisi di sensibilità
                    pv_capex = pv_power_kwp * modified_params.pv_capex_per_kwp
                    bess_capex = bess_capacity_kwh * modified_params.bess_capex_per_kwh
                    total_capex = pv_capex + bess_capex
                    
                    annual_savings = pv_production_annual * modified_params.electricity_price_f2 * 0.7  # Stima autoconsumo 70%
                    annual_opex = total_capex * 0.015  # 1.5% OPEX
                    
                    cash_flows = [annual_savings - annual_opex] * modified_params.analysis_years
                    npv = self._calculate_npv([-total_capex] + cash_flows, modified_params.wacc)
                    
                    sensitivity_results[param_name][f"{variation:+d}%"] = npv
                    
                except Exception:
                    sensitivity_results[param_name][f"{variation:+d}%"] = 0
        
        return sensitivity_results
    
    def _calculate_lcoe(
        self,
        capex: float,
        annual_opex: float,
        annual_production: float,
        economic_params: EconomicParameters
    ) -> float:
        """Calcola il Levelized Cost of Energy"""
        
        # Flussi di cassa dei costi
        cost_cash_flows = [capex] + [annual_opex * (1 + economic_params.opex_escalation) ** year 
                                    for year in range(economic_params.analysis_years)]
        
        # Produzione attualizzata
        discounted_production = sum([
            annual_production / (1 + economic_params.wacc) ** year
            for year in range(1, economic_params.analysis_years + 1)
        ])
        
        # Costi attualizzati
        discounted_costs = sum([
            cost / (1 + economic_params.wacc) ** year
            for year, cost in enumerate(cost_cash_flows)
        ])
        
        return discounted_costs / discounted_production if discounted_production > 0 else 0
    
    def _calculate_npv(self, cash_flows: List[float], discount_rate: float) -> float:
        """Calcola il Net Present Value"""
        npv = 0
        for i, cf in enumerate(cash_flows):
            npv += cf / (1 + discount_rate) ** i
        return npv
    
    def _calculate_irr(self, cash_flows: List[float]) -> float:
        """Calcola l'Internal Rate of Return usando metodo iterativo"""
        try:
            # Metodo di Newton-Raphson semplificato
            rate = 0.1  # Stima iniziale 10%
            
            for _ in range(100):  # Max 100 iterazioni
                npv = sum(cf / (1 + rate) ** i for i, cf in enumerate(cash_flows))
                npv_derivative = sum(-i * cf / (1 + rate) ** (i + 1) for i, cf in enumerate(cash_flows) if i > 0)
                
                if abs(npv) < 1e-6:  # Convergenza
                    return rate
                
                if abs(npv_derivative) < 1e-10:  # Evita divisione per zero
                    break
                
                rate = rate - npv / npv_derivative
                
                if rate < -0.99:  # Limita il rate
                    rate = -0.99
                elif rate > 10:  # Limita il rate
                    rate = 10
            
            return rate if -1 < rate < 10 else 0
            
        except Exception:
            return 0
    
    def _calculate_payback(self, initial_investment: float, cash_flows: List[float]) -> float:
        """Calcola il Payback Period"""
        cumulative_cf = 0
        
        for year, cf in enumerate(cash_flows):
            cumulative_cf += cf
            if cumulative_cf >= initial_investment:
                # Interpolazione per il payback esatto
                if year == 0:
                    return cf / initial_investment if cf > 0 else float('inf')
                
                previous_cumulative = cumulative_cf - cf
                fraction = (initial_investment - previous_cumulative) / cf
                return year + fraction
        
        return float('inf')  # Non raggiunge mai il payback


# Test del modulo
if __name__ == "__main__":
    # Test con dati di esempio
    calc = EconomicCalculator()
    
    # Parametri di test
    pv_power = 228.7  # kWp
    pv_production_annual = 164830  # kWh
    pv_production_monthly = [3132, 4101, 9481, 17650, 25538, 29065, 29809, 21846, 12391, 5654, 3395, 2767]
    consumption_annual = 200000  # kWh
    consumption_monthly = [consumption_annual / 12] * 12  # Distribuzione uniforme
    
    bess_capacity = 1600  # kWh
    bess_self_consumption_increase = 130987  # kWh
    
    # Parametri economici personalizzati
    economic_params = EconomicParameters(
        wacc=0.06,  # 6% WACC
        electricity_price_f2=0.25,
        pv_capex_per_kwp=1200,
        bess_capex_per_kwh=500
    )
    
    results = calc.calculate_complete_economic_analysis(
        pv_power_kwp=pv_power,
        pv_production_annual=pv_production_annual,
        pv_production_monthly=pv_production_monthly,
        consumption_annual=consumption_annual,
        consumption_monthly=consumption_monthly,
        bess_capacity_kwh=bess_capacity,
        bess_self_consumption_increase=bess_self_consumption_increase,
        economic_params=economic_params
    )
    
    print("=== RISULTATI ANALISI ECONOMICA ===")
    print(f"FV Solo - NPV: €{results.pv_only_npv:,.0f}")
    print(f"FV Solo - IRR: {results.pv_only_irr:.1%}")
    print(f"FV Solo - Payback: {results.pv_only_payback:.1f} anni")
    print()
    print(f"FV+BESS - NPV: €{results.pv_bess_npv:,.0f}")
    print(f"FV+BESS - IRR: {results.pv_bess_irr:.1%}")
    print(f"FV+BESS - Payback: {results.pv_bess_payback:.1f} anni")
    print()
    print(f"BESS Incrementale - NPV: €{results.bess_incremental_npv:,.0f}")
    print(f"BESS Incrementale - IRR: {results.bess_incremental_irr:.1%}")
    print(f"BESS Incrementale - Payback: {results.bess_incremental_payback:.1f} anni")
    print()
    print(f"LCOE: €{results.lcoe:.3f}/kWh")
    print(f"Investimento Totale: €{results.total_investment:,.0f}")
    print(f"Risparmi Annuali: €{results.total_annual_savings:,.0f}")

