"""
Modulo per il calcolo e dimensionamento dei sistemi BESS (Battery Energy Storage System)
Gestisce l'ottimizzazione dell'autoconsumo e l'analisi economica delle batterie
"""

import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

@dataclass
class BESSParameters:
    """Parametri tecnici del sistema BESS"""
    dod: float = 0.8  # Depth of Discharge (80%)
    c_rate: float = 0.5  # C-Rate per carica/scarica
    efficiency: float = 0.95  # Efficienza round-trip (95%)
    cycle_life: int = 6000  # Cicli di vita
    capex_per_kwh: float = 500.0  # €/kWh
    opex_annual_percent: float = 1.0  # % annuale del CAPEX
    degradation_annual: float = 0.02  # Degradazione annuale (2%)

@dataclass
class ConsumptionProfile:
    """Profilo di consumo energetico"""
    monthly_kwh: List[float]  # Consumi mensili in kWh
    f1_percent: float = 0.33  # Percentuale fascia F1 (picco)
    f2_percent: float = 0.33  # Percentuale fascia F2 (intermedia)
    f3_percent: float = 0.34  # Percentuale fascia F3 (base)
    granularity: str = "monthly"  # monthly, daily, hourly, quarterly

@dataclass
class BESSResults:
    """Risultati del calcolo BESS (solo aspetti tecnici)"""
    optimal_capacity_kwh: float
    optimal_power_kw: float
    annual_self_consumption_increase: float  # kWh
    annual_grid_reduction: float  # kWh
    annual_grid_export_increase: float  # kWh (energia aggiuntiva immessa)
    
    # Dettagli tecnici
    daily_cycles: float
    total_cycles_20_years: float
    capacity_retention_20_years: float
    average_soc: float  # State of Charge medio
    energy_throughput_annual: float  # kWh/anno attraverso le batterie
    
    # Profili energetici
    monthly_battery_usage: List[float]  # kWh mensili utilizzati dalle batterie
    self_consumption_rate_improvement: float  # Miglioramento % autoconsumo

class BESSCalculator:
    """Calcolatore per sistemi BESS"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_optimal_bess(
        self,
        pv_production_monthly: List[float],  # kWh mensili da PVGIS
        consumption_profile: ConsumptionProfile,
        bess_params: BESSParameters
    ) -> BESSResults:
        """
        Calcola il dimensionamento ottimale del sistema BESS (solo aspetti tecnici)
        
        Args:
            pv_production_monthly: Produzione FV mensile da PVGIS
            consumption_profile: Profilo di consumo del cliente
            bess_params: Parametri tecnici BESS
        
        Returns:
            BESSResults con tutti i calcoli tecnici
        """
        try:
            # 1. Analisi baseline senza BESS
            baseline = self._calculate_baseline_scenario(
                pv_production_monthly, 
                consumption_profile.monthly_kwh
            )
            
            # 2. Ottimizzazione capacità BESS (basata su criteri tecnici)
            optimal_capacity = self._optimize_bess_capacity_technical(
                pv_production_monthly,
                consumption_profile,
                bess_params
            )
            
            # 3. Calcolo performance con BESS ottimale
            bess_scenario = self._calculate_bess_scenario(
                pv_production_monthly,
                consumption_profile.monthly_kwh,
                optimal_capacity,
                bess_params
            )
            
            # 4. Calcoli tecnici avanzati
            technical_results = self._calculate_technical_metrics(
                optimal_capacity,
                bess_scenario['daily_energy_throughput'],
                bess_params
            )
            
            # 5. Calcolo miglioramento autoconsumo
            self_consumption_improvement = self._calculate_self_consumption_improvement(
                baseline, bess_scenario
            )
            
            return BESSResults(
                optimal_capacity_kwh=optimal_capacity,
                optimal_power_kw=optimal_capacity * bess_params.c_rate,
                annual_self_consumption_increase=bess_scenario['annual_self_consumption'] - baseline['annual_self_consumption'],
                annual_grid_reduction=baseline['annual_grid_import'] - bess_scenario['annual_grid_import'],
                annual_grid_export_increase=bess_scenario['annual_grid_export'] - baseline['annual_grid_export'],
                daily_cycles=technical_results['daily_cycles'],
                total_cycles_20_years=technical_results['total_cycles_20_years'],
                capacity_retention_20_years=technical_results['capacity_retention_20_years'],
                average_soc=technical_results['average_soc'],
                energy_throughput_annual=technical_results['energy_throughput_annual'],
                monthly_battery_usage=bess_scenario['monthly_battery_usage'],
                self_consumption_rate_improvement=self_consumption_improvement
            )
            
        except Exception as e:
            self.logger.error(f"Errore calcolo BESS: {e}")
            raise
    
    def _calculate_baseline_scenario(
        self,
        pv_production: List[float],
        consumption: List[float],
        electricity_price: float,
        feed_in_tariff: float
    ) -> Dict:
        """Calcola scenario baseline senza BESS"""
        
        annual_pv_production = sum(pv_production)
        annual_consumption = sum(consumption)
        
        # Autoconsumo diretto (semplificato mensile)
        monthly_self_consumption = []
        monthly_grid_import = []
        monthly_grid_export = []
        
        for i in range(12):
            # Autoconsumo = minimo tra produzione e consumo mensile
            self_consumption = min(pv_production[i], consumption[i])
            monthly_self_consumption.append(self_consumption)
            
            # Importazione dalla rete
            grid_import = max(0, consumption[i] - pv_production[i])
            monthly_grid_import.append(grid_import)
            
            # Esportazione in rete
            grid_export = max(0, pv_production[i] - consumption[i])
            monthly_grid_export.append(grid_export)
        
        annual_self_consumption = sum(monthly_self_consumption)
        annual_grid_import = sum(monthly_grid_import)
        annual_grid_export = sum(monthly_grid_export)
        
        # Costi/ricavi
        annual_electricity_cost = annual_grid_import * electricity_price
        annual_feed_in_revenue = annual_grid_export * feed_in_tariff
        annual_net_cost = annual_electricity_cost - annual_feed_in_revenue
        
        return {
            'annual_pv_production': annual_pv_production,
            'annual_consumption': annual_consumption,
            'annual_self_consumption': annual_self_consumption,
            'annual_grid_import': annual_grid_import,
            'annual_grid_export': annual_grid_export,
            'annual_electricity_cost': annual_electricity_cost,
            'annual_feed_in_revenue': annual_feed_in_revenue,
            'annual_net_cost': annual_net_cost,
            'self_consumption_rate': annual_self_consumption / annual_pv_production if annual_pv_production > 0 else 0
        }
    
    def _optimize_bess_capacity(
        self,
        pv_production: List[float],
        consumption_profile: ConsumptionProfile,
        bess_params: BESSParameters,
        electricity_price: float,
        feed_in_tariff: float
    ) -> float:
        """Ottimizza la capacità BESS per massimizzare il NPV"""
        
        # Range di capacità da testare (da 10% a 200% del consumo mensile medio)
        monthly_avg_consumption = sum(consumption_profile.monthly_kwh) / 12
        min_capacity = monthly_avg_consumption * 0.1
        max_capacity = monthly_avg_consumption * 2.0
        
        # Test incrementale
        best_npv = float('-inf')
        optimal_capacity = min_capacity
        
        # Test con step del 10% della capacità minima
        step = min_capacity * 0.1
        current_capacity = min_capacity
        
        while current_capacity <= max_capacity:
            # Calcola NPV per questa capacità
            bess_scenario = self._calculate_bess_scenario(
                pv_production,
                consumption_profile.monthly_kwh,
                current_capacity,
                bess_params,
                electricity_price,
                feed_in_tariff
            )
            
            # Calcolo NPV semplificato
            annual_savings = bess_scenario['annual_savings']
            capex = current_capacity * bess_params.capex_per_kwh
            opex_annual = capex * bess_params.opex_annual_percent / 100
            
            # NPV a 20 anni con WACC 5%
            npv = self._calculate_npv_simple(annual_savings - opex_annual, capex, 0.05, 20)
            
            if npv > best_npv:
                best_npv = npv
                optimal_capacity = current_capacity
            
            current_capacity += step
        
        return optimal_capacity
    
    def _calculate_bess_scenario(
        self,
        pv_production: List[float],
        consumption: List[float],
        bess_capacity: float,
        bess_params: BESSParameters,
        electricity_price: float,
        feed_in_tariff: float
    ) -> Dict:
        """Calcola scenario con BESS di capacità specificata"""
        
        # Capacità utilizzabile considerando DoD
        usable_capacity = bess_capacity * bess_params.dod
        
        monthly_results = []
        total_energy_throughput = 0
        
        for i in range(12):
            month_pv = pv_production[i]
            month_consumption = consumption[i]
            
            # Simulazione semplificata giornaliera
            days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][i]
            daily_pv = month_pv / days_in_month
            daily_consumption = month_consumption / days_in_month
            
            # Logica BESS semplificata
            if daily_pv > daily_consumption:
                # Eccesso di produzione - carica batteria
                excess = daily_pv - daily_consumption
                battery_charge = min(excess, usable_capacity) * bess_params.efficiency
                remaining_excess = max(0, excess - usable_capacity / bess_params.efficiency)
                
                # Autoconsumo diretto + carica batteria
                daily_self_consumption = daily_consumption + (excess - remaining_excess)
                daily_grid_export = remaining_excess
                daily_grid_import = 0
                
            else:
                # Deficit di produzione - scarica batteria
                deficit = daily_consumption - daily_pv
                battery_discharge = min(deficit, usable_capacity)
                remaining_deficit = max(0, deficit - battery_discharge)
                
                # Autoconsumo diretto + scarica batteria
                daily_self_consumption = daily_pv + battery_discharge
                daily_grid_import = remaining_deficit
                daily_grid_export = 0
                battery_charge = 0
            
            # Accumula per il mese
            month_self_consumption = daily_self_consumption * days_in_month
            month_grid_import = daily_grid_import * days_in_month
            month_grid_export = daily_grid_export * days_in_month
            
            # Energy throughput per calcoli di usura
            monthly_throughput = (battery_charge + battery_discharge) * days_in_month
            total_energy_throughput += monthly_throughput
            
            monthly_results.append({
                'self_consumption': month_self_consumption,
                'grid_import': month_grid_import,
                'grid_export': month_grid_export,
                'throughput': monthly_throughput
            })
        
        # Totali annuali
        annual_self_consumption = sum(r['self_consumption'] for r in monthly_results)
        annual_grid_import = sum(r['grid_import'] for r in monthly_results)
        annual_grid_export = sum(r['grid_export'] for r in monthly_results)
        
        # Costi/ricavi
        annual_electricity_cost = annual_grid_import * electricity_price
        annual_feed_in_revenue = annual_grid_export * feed_in_tariff
        annual_net_cost = annual_electricity_cost - annual_feed_in_revenue
        
        # Risparmio rispetto al baseline (da calcolare esternamente)
        annual_savings = 0  # Sarà calcolato nel confronto
        
        return {
            'annual_self_consumption': annual_self_consumption,
            'annual_grid_import': annual_grid_import,
            'annual_grid_export': annual_grid_export,
            'annual_electricity_cost': annual_electricity_cost,
            'annual_feed_in_revenue': annual_feed_in_revenue,
            'annual_net_cost': annual_net_cost,
            'annual_savings': annual_savings,
            'daily_energy_throughput': total_energy_throughput / 365,
            'monthly_results': monthly_results
        }
    
    def _calculate_economics(
        self,
        baseline: Dict,
        bess_scenario: Dict,
        bess_capacity: float,
        bess_params: BESSParameters,
        wacc: float
    ) -> Dict:
        """Calcola l'analisi economica del BESS"""
        
        # Investimento iniziale
        capex_total = bess_capacity * bess_params.capex_per_kwh
        opex_annual = capex_total * bess_params.opex_annual_percent / 100
        
        # Risparmi annuali
        annual_savings = baseline['annual_net_cost'] - bess_scenario['annual_net_cost']
        bess_scenario['annual_savings'] = annual_savings
        
        # Breakdown risparmi
        avoided_grid_cost = (baseline['annual_grid_import'] - bess_scenario['annual_grid_import']) * 0.25  # €/kWh
        additional_feed_in = (bess_scenario['annual_grid_export'] - baseline['annual_grid_export']) * 0.05  # €/kWh
        
        # Payback semplice
        net_annual_savings = annual_savings - opex_annual
        payback_years = capex_total / net_annual_savings if net_annual_savings > 0 else float('inf')
        
        # NPV a 20 anni
        npv_20_years = self._calculate_npv_simple(net_annual_savings, capex_total, wacc, 20)
        
        # IRR (approssimazione)
        irr_percent = self._calculate_irr_approximation(capex_total, net_annual_savings, 20)
        
        # LCOE reduction (semplificato)
        lcoe_reduction = annual_savings / sum([baseline['annual_pv_production']]) * 1000  # €/MWh
        
        return {
            'capex_total': capex_total,
            'opex_annual': opex_annual,
            'savings_annual': annual_savings,
            'avoided_grid_cost': avoided_grid_cost,
            'incentives_annual': additional_feed_in,
            'payback_years': payback_years,
            'npv_20_years': npv_20_years,
            'irr_percent': irr_percent,
            'lcoe_reduction': lcoe_reduction
        }
    
    def _calculate_technical_metrics(
        self,
        bess_capacity: float,
        daily_throughput: float,
        bess_params: BESSParameters
    ) -> Dict:
        """Calcola metriche tecniche del BESS"""
        
        # Cicli giornalieri
        usable_capacity = bess_capacity * bess_params.dod
        daily_cycles = daily_throughput / (2 * usable_capacity) if usable_capacity > 0 else 0
        
        # Cicli totali in 20 anni
        total_cycles_20_years = daily_cycles * 365 * 20
        
        # Ritenzione capacità dopo 20 anni
        degradation_total = min(0.8, bess_params.degradation_annual * 20)  # Max 80% degradazione
        capacity_retention_20_years = 1 - degradation_total
        
        return {
            'daily_cycles': daily_cycles,
            'total_cycles_20_years': total_cycles_20_years,
            'capacity_retention_20_years': capacity_retention_20_years
        }
    
    def _calculate_npv_simple(self, annual_cashflow: float, initial_investment: float, discount_rate: float, years: int) -> float:
        """Calcola NPV semplificato"""
        npv = -initial_investment
        for year in range(1, years + 1):
            npv += annual_cashflow / ((1 + discount_rate) ** year)
        return npv
    
    def _calculate_irr_approximation(self, initial_investment: float, annual_cashflow: float, years: int) -> float:
        """Calcola IRR approssimato"""
        if annual_cashflow <= 0:
            return 0
        
        # Approssimazione semplice: IRR ≈ (Annual Cashflow / Initial Investment) - depreciation
        simple_return = annual_cashflow / initial_investment
        depreciation_rate = 1 / years
        irr_approx = (simple_return - depreciation_rate) * 100
        
        return max(0, min(100, irr_approx))  # Limita tra 0% e 100%

# Funzioni di utilità per l'integrazione con l'applicazione Flask

def create_default_consumption_profile(annual_consumption_kwh: float) -> ConsumptionProfile:
    """Crea un profilo di consumo di default basato su consumo annuale"""
    
    # Distribuzione mensile tipica per utenza industriale italiana
    monthly_distribution = [
        0.09, 0.08, 0.085, 0.08, 0.075, 0.07,  # Gen-Giu
        0.065, 0.07, 0.075, 0.085, 0.09, 0.095  # Lug-Dic
    ]
    
    monthly_kwh = [annual_consumption_kwh * dist for dist in monthly_distribution]
    
    return ConsumptionProfile(
        monthly_kwh=monthly_kwh,
        f1_percent=0.35,  # Fascia F1 (picco)
        f2_percent=0.30,  # Fascia F2 (intermedia)  
        f3_percent=0.35,  # Fascia F3 (base)
        granularity="monthly"
    )

def estimate_consumption_from_power(installed_power_kw: float, load_factor: float = 0.3) -> float:
    """Stima consumo annuale da potenza installata e fattore di carico"""
    return installed_power_kw * load_factor * 8760  # kWh/anno

# Test del modulo
if __name__ == "__main__":
    # Test con dati di esempio
    calculator = BESSCalculator()
    
    # Dati PVGIS di esempio (Milano, 228.7 kWp)
    pv_monthly = [3132, 4101, 9481, 17650, 25538, 29065, 29809, 21846, 12391, 5654, 3395, 2767]
    
    # Profilo di consumo di esempio
    consumption_profile = create_default_consumption_profile(200000)  # 200 MWh/anno
    
    # Parametri BESS
    bess_params = BESSParameters()
    
    # Calcolo
    results = calculator.calculate_optimal_bess(
        pv_production_monthly=pv_monthly,
        consumption_profile=consumption_profile,
        bess_params=bess_params
    )
    
    print("=== RISULTATI CALCOLO BESS ===")
    print(f"Capacità ottimale: {results.optimal_capacity_kwh:.1f} kWh")
    print(f"Potenza ottimale: {results.optimal_power_kw:.1f} kW")
    print(f"Aumento autoconsumo: {results.annual_self_consumption_increase:.0f} kWh/anno")
    print(f"CAPEX totale: €{results.capex_total:,.0f}")
    print(f"Payback: {results.payback_years:.1f} anni")
    print(f"NPV 20 anni: €{results.npv_20_years:,.0f}")
    print(f"IRR: {results.irr_percent:.1f}%")

