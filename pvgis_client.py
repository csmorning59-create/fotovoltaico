"""
Client per l'integrazione con l'API PVGIS (Photovoltaic Geographical Information System)
Fornisce dati di irraggiamento solare e produzione fotovoltaica per l'Europa
"""

import requests
import json
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime

class PVGISClient:
    """Client per l'API PVGIS del Joint Research Centre (JRC) della Commissione Europea"""
    
    def __init__(self):
        self.base_url = "https://re.jrc.ec.europa.eu/api/v5_2"
        self.timeout = 30
        
    def get_pv_production(self, 
                         latitude: float, 
                         longitude: float,
                         peak_power_kwp: float,
                         tilt: float,
                         azimuth: float,
                         mounting_type: str = "free",
                         pvtech: str = "crystSi",
                         loss: float = 14.0) -> Dict:
        """
        Ottiene i dati di produzione fotovoltaica da PVGIS
        
        Args:
            latitude: Latitudine in gradi decimali
            longitude: Longitudine in gradi decimali
            peak_power_kwp: Potenza di picco in kWp
            tilt: Inclinazione dei moduli in gradi (0-90)
            azimuth: Azimuth in gradi (0=Nord, 90=Est, 180=Sud, 270=Ovest)
            mounting_type: Tipo di montaggio ('free', 'building')
            pvtech: Tecnologia PV ('crystSi', 'CIS', 'CdTe', 'Unknown')
            loss: Perdite del sistema in % (default 14%)
            
        Returns:
            Dict con i dati di produzione PVGIS
        """
        try:
            params = {
                'lat': latitude,
                'lon': longitude,
                'peakpower': peak_power_kwp,
                'angle': tilt,
                'aspect': azimuth,
                'mountingplace': mounting_type,
                'pvtechchoice': pvtech,
                'loss': loss,
                'outputformat': 'json'
            }
            
            print(f"Chiamata PVGIS con parametri: {params}")
            
            response = requests.get(
                f"{self.base_url}/PVcalc",
                params=params,
                timeout=self.timeout
            )
            
            print(f"Status code: {response.status_code}")
            print(f"Response text (primi 500 char): {response.text[:500]}")
            
            response.raise_for_status()
            
            # Prova a fare il parsing JSON
            try:
                data = response.json()
            except json.JSONDecodeError:
                # Se non è JSON, potrebbe essere un errore HTML
                if response.text.startswith('<!'):
                    raise Exception("PVGIS ha restituito una pagina HTML invece di JSON. Parametri non validi.")
                else:
                    raise Exception(f"Risposta non JSON: {response.text[:200]}")
            
            print(f"Dati ricevuti: {json.dumps(data, indent=2)[:1000]}")
            
            # Estrae i dati principali
            if 'outputs' in data:
                return self._process_pv_data(data)
            else:
                raise ValueError(f"Formato risposta PVGIS non valido: {data}")
                
        except requests.exceptions.RequestException as e:
            logging.error(f"Errore chiamata PVGIS: {e}")
            raise Exception(f"Errore connessione PVGIS: {str(e)}")
        except json.JSONDecodeError as e:
            logging.error(f"Errore parsing JSON PVGIS: {e}")
            raise Exception("Errore parsing risposta PVGIS")
        except Exception as e:
            logging.error(f"Errore generico PVGIS: {e}")
            raise Exception(f"Errore PVGIS: {str(e)}")
    
    def get_dual_axis_production(self,
                               latitude: float,
                               longitude: float,
                               peak_power_kwp: float,
                               tilt: float,
                               azimuth_east: float = 90,
                               azimuth_west: float = -90,  # Corretto: -90 invece di 270
                               split_ratio: float = 0.5) -> Dict:
        """
        Calcola la produzione per un sistema Est-Ovest
        
        Args:
            latitude: Latitudine
            longitude: Longitudine
            peak_power_kwp: Potenza totale in kWp
            tilt: Inclinazione moduli
            azimuth_east: Azimuth lato Est (default 90°)
            azimuth_west: Azimuth lato Ovest (default 270°)
            split_ratio: Rapporto di divisione potenza (0.5 = 50% per lato)
            
        Returns:
            Dict con produzione combinata Est-Ovest
        """
        try:
            # Calcola potenza per ogni lato
            power_east = peak_power_kwp * split_ratio
            power_west = peak_power_kwp * (1 - split_ratio)
            
            # Ottiene dati per lato Est
            data_east = self.get_pv_production(
                latitude, longitude, power_east, tilt, azimuth_east
            )
            
            # Ottiene dati per lato Ovest
            data_west = self.get_pv_production(
                latitude, longitude, power_west, tilt, azimuth_west
            )
            
            # Combina i risultati
            return self._combine_dual_axis_data(data_east, data_west, split_ratio)
            
        except Exception as e:
            logging.error(f"Errore calcolo dual-axis: {e}")
            raise Exception(f"Errore calcolo Est-Ovest: {str(e)}")
    
    def get_irradiation_data(self,
                           latitude: float,
                           longitude: float) -> Dict:
        """
        Ottiene dati di irraggiamento solare per la posizione
        
        Args:
            latitude: Latitudine
            longitude: Longitudine
            
        Returns:
            Dict con dati di irraggiamento
        """
        try:
            params = {
                'lat': latitude,
                'lon': longitude,
                'outputformat': 'json',
                'startyear': 2016,
                'endyear': 2020,
                'components': 1
            }
            
            response = requests.get(
                f"{self.base_url}/seriescalc",
                params=params,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            return self._process_irradiation_data(data)
            
        except Exception as e:
            logging.error(f"Errore dati irraggiamento: {e}")
            raise Exception(f"Errore dati irraggiamento: {str(e)}")
    
    def _process_pv_data(self, raw_data: Dict) -> Dict:
        """Processa i dati grezzi di PVGIS in formato standardizzato"""
        try:
            outputs = raw_data['outputs']
            
            # Dati mensili - la struttura corretta è outputs.monthly.fixed
            monthly_data = []
            totals_data = {}
            
            if 'monthly' in outputs and 'fixed' in outputs['monthly']:
                monthly_fixed = outputs['monthly']['fixed']
                
                # Calcola totali annuali
                annual_production = sum(month.get('E_m', 0) for month in monthly_fixed)
                annual_irradiation = sum(month.get('H(i)_m', 0) for month in monthly_fixed)
                
                # Processa dati mensili
                for month_data in monthly_fixed:
                    monthly_data.append({
                        'month': month_data['month'],
                        'production_kwh': month_data.get('E_m', 0),
                        'production_daily_avg_kwh': month_data.get('E_d', 0),
                        'irradiation_kwh_m2': month_data.get('H(i)_m', 0),
                        'irradiation_daily_avg_kwh_m2': month_data.get('H(i)_d', 0),
                        'standard_deviation': month_data.get('SD_m', 0)
                    })
                
                totals_data = {
                    'E_y': annual_production,
                    'H(i)_y': annual_irradiation
                }
            
            # Calcola performance ratio e produzione specifica
            peak_power = raw_data.get('inputs', {}).get('pv_module', {}).get('peak_power', 1)
            specific_production = totals_data.get('E_y', 0) / max(1, peak_power)
            
            # Performance ratio approssimativo (produzione / irraggiamento * efficienza teorica)
            # Formula semplificata: PR = Produzione_reale / (Irraggiamento * Potenza_nominale * 0.2)
            # dove 0.2 è l'efficienza teorica del modulo (20%)
            irradiation_total = totals_data.get('H(i)_y', 0)
            if irradiation_total > 0 and peak_power > 0:
                performance_ratio = totals_data.get('E_y', 0) / (irradiation_total * peak_power * 0.2)
            else:
                performance_ratio = 0
            
            return {
                'success': True,
                'annual_production_kwh': totals_data.get('E_y', 0),
                'annual_irradiation_kwh_m2': totals_data.get('H(i)_y', 0),
                'specific_production_kwh_kwp': specific_production,
                'performance_ratio': min(1.0, performance_ratio),  # Cap a 1.0
                'monthly_data': monthly_data,
                'hourly_data': [],  # Non disponibile in questa versione
                'metadata': {
                    'latitude': raw_data.get('inputs', {}).get('location', {}).get('latitude', 0),
                    'longitude': raw_data.get('inputs', {}).get('location', {}).get('longitude', 0),
                    'elevation': raw_data.get('inputs', {}).get('location', {}).get('elevation', 0),
                    'peak_power_kwp': peak_power,
                    'tilt': raw_data.get('inputs', {}).get('mounting_system', {}).get('fixed', {}).get('slope', {}).get('value', 0),
                    'azimuth': raw_data.get('inputs', {}).get('mounting_system', {}).get('fixed', {}).get('azimuth', {}).get('value', 0),
                    'pvtech': raw_data.get('inputs', {}).get('pv_module', {}).get('technology', ''),
                    'loss_percent': raw_data.get('inputs', {}).get('pv_module', {}).get('system_loss', 0),
                    'radiation_db': raw_data.get('inputs', {}).get('meteo_data', {}).get('radiation_db', ''),
                    'meteo_db': raw_data.get('inputs', {}).get('meteo_data', {}).get('meteo_db', ''),
                    'year_min': raw_data.get('inputs', {}).get('meteo_data', {}).get('year_min', 0),
                    'year_max': raw_data.get('inputs', {}).get('meteo_data', {}).get('year_max', 0),
                    'data_source': 'PVGIS JRC',
                    'calculation_date': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logging.error(f"Errore processing dati PVGIS: {e}")
            print(f"Struttura dati ricevuta: {json.dumps(raw_data, indent=2)[:2000]}")
            return {
                'success': False,
                'error': f"Errore elaborazione dati: {str(e)}"
            }
    
    def _combine_dual_axis_data(self, data_east: Dict, data_west: Dict, split_ratio: float) -> Dict:
        """Combina i dati di produzione Est e Ovest"""
        try:
            if not (data_east.get('success') and data_west.get('success')):
                raise ValueError("Dati Est o Ovest non validi")
            
            # Combina produzione annuale
            annual_production = data_east['annual_production_kwh'] + data_west['annual_production_kwh']
            
            # Combina dati mensili
            monthly_combined = []
            for i in range(min(len(data_east['monthly_data']), len(data_west['monthly_data']))):
                month_east = data_east['monthly_data'][i]
                month_west = data_west['monthly_data'][i]
                
                monthly_combined.append({
                    'month': month_east['month'],
                    'production_kwh': month_east['production_kwh'] + month_west['production_kwh'],
                    'production_east_kwh': month_east['production_kwh'],
                    'production_west_kwh': month_west['production_kwh'],
                    'irradiation_east_kwh_m2': month_east['irradiation_kwh_m2'],
                    'irradiation_west_kwh_m2': month_west['irradiation_kwh_m2']
                })
            
            return {
                'success': True,
                'orientation': 'est_ovest',
                'annual_production_kwh': annual_production,
                'annual_production_east_kwh': data_east['annual_production_kwh'],
                'annual_production_west_kwh': data_west['annual_production_kwh'],
                'specific_production_kwh_kwp': annual_production / max(1, 
                    data_east['metadata']['peak_power_kwp'] + data_west['metadata']['peak_power_kwp']),
                'monthly_data': monthly_combined,
                'split_ratio': split_ratio,
                'metadata': {
                    'orientation': 'est_ovest',
                    'peak_power_total_kwp': data_east['metadata']['peak_power_kwp'] + data_west['metadata']['peak_power_kwp'],
                    'peak_power_east_kwp': data_east['metadata']['peak_power_kwp'],
                    'peak_power_west_kwp': data_west['metadata']['peak_power_kwp'],
                    'tilt': data_east['metadata']['tilt'],
                    'azimuth_east': data_east['metadata']['azimuth'],
                    'azimuth_west': data_west['metadata']['azimuth'],
                    'data_source': 'PVGIS JRC (Est-Ovest)',
                    'calculation_date': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logging.error(f"Errore combinazione dati Est-Ovest: {e}")
            return {
                'success': False,
                'error': f"Errore combinazione dati: {str(e)}"
            }
    
    def _process_irradiation_data(self, raw_data: Dict) -> Dict:
        """Processa i dati di irraggiamento"""
        # Implementazione semplificata per ora
        return {
            'success': True,
            'data': raw_data
        }
    
    def validate_coordinates(self, latitude: float, longitude: float) -> bool:
        """
        Valida se le coordinate sono supportate da PVGIS
        PVGIS copre Europa, Africa, Asia e parte delle Americhe
        """
        # Controlli di base
        if not (-90 <= latitude <= 90):
            return False
        if not (-180 <= longitude <= 180):
            return False
        
        # PVGIS ha copertura principalmente per:
        # Europa: lat 30-75, lon -25-65
        # Africa: lat -35-40, lon -20-55
        # Asia: lat -15-60, lon 60-150
        # Americhe: lat -60-75, lon -170 to -30
        
        # Per semplicità, accettiamo tutte le coordinate valide
        # In produzione si potrebbe fare un controllo più specifico
        return True

def test_pvgis_client():
    """Funzione di test per il client PVGIS"""
    client = PVGISClient()
    
    # Test con coordinate Milano
    latitude = 45.4642
    longitude = 9.1900
    peak_power = 100  # kWp
    tilt = 30
    azimuth = 180  # Sud
    
    print("=== TEST PVGIS CLIENT ===")
    print(f"Coordinate: {latitude}, {longitude}")
    print(f"Potenza: {peak_power} kWp")
    print(f"Inclinazione: {tilt}°")
    print(f"Azimuth: {azimuth}° (Sud)")
    print()
    
    try:
        # Test produzione Sud
        print("Test produzione orientamento Sud...")
        data_sud = client.get_pv_production(latitude, longitude, peak_power, tilt, azimuth)
        
        if data_sud['success']:
            print(f"✅ Produzione annuale: {data_sud['annual_production_kwh']:.0f} kWh")
            print(f"✅ Produzione specifica: {data_sud['specific_production_kwh_kwp']:.0f} kWh/kWp")
            print(f"✅ Performance Ratio: {data_sud['performance_ratio']:.2f}")
            print(f"✅ Dati mensili: {len(data_sud['monthly_data'])} mesi")
        else:
            print(f"❌ Errore: {data_sud.get('error')}")
        
        print()
        
        # Test produzione Est-Ovest
        print("Test produzione orientamento Est-Ovest...")
        data_eo = client.get_dual_axis_production(latitude, longitude, peak_power, tilt)
        
        if data_eo['success']:
            print(f"✅ Produzione annuale totale: {data_eo['annual_production_kwh']:.0f} kWh")
            print(f"✅ Produzione Est: {data_eo['annual_production_east_kwh']:.0f} kWh")
            print(f"✅ Produzione Ovest: {data_eo['annual_production_west_kwh']:.0f} kWh")
            print(f"✅ Produzione specifica: {data_eo['specific_production_kwh_kwp']:.0f} kWh/kWp")
        else:
            print(f"❌ Errore: {data_eo.get('error')}")
            
    except Exception as e:
        print(f"❌ Errore test: {e}")

if __name__ == "__main__":
    test_pvgis_client()

