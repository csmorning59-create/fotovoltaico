"""
Modulo per il calcolo geometrico del layout fotovoltaico
Supporta orientamenti Sud ed Est-Ovest
"""

import math
import numpy as np
from typing import Dict, List, Tuple, Optional

class GeometryCalculator:
    """Calcolatore per il layout geometrico degli impianti fotovoltaici"""
    
    def __init__(self):
        # Parametri di default per moduli fotovoltaici
        self.default_module = {
            'potenza_wp': 495,  # LONGI LR7-54HVH-495M Hi-MO X10 Scientist
            'lunghezza_mm': 2278,
            'larghezza_mm': 1134,
            'nome': 'LONGI LR7-54HVH-495M Hi-MO X10 Scientist'
        }
        
        # Fattore di riduzione minima distanza (configurabile)
        self.min_distance_reduction_factor = 0.1  # 10% di riduzione massima
    
    def calculate_south_layout(self, 
                             superficie_mq: float,
                             tilt_degrees: float,
                             margine_metri: float = 1.0,
                             modulo_params: Optional[Dict] = None,
                             angolo_solare_delta: float = 23.5) -> Dict:
        """
        Calcola il layout per orientamento Sud
        
        Args:
            superficie_mq: Superficie disponibile in m²
            tilt_degrees: Inclinazione moduli in gradi
            margine_metri: Margine dai bordi in metri
            modulo_params: Parametri del modulo (se None usa default)
            angolo_solare_delta: Angolo solare per calcolo ombreggiamento
            
        Returns:
            Dict con risultati del calcolo
        """
        if modulo_params is None:
            modulo_params = self.default_module
        
        # Conversioni
        modulo_lunghezza_m = modulo_params['lunghezza_mm'] / 1000
        modulo_larghezza_m = modulo_params['larghezza_mm'] / 1000
        tilt_rad = math.radians(tilt_degrees)
        delta_rad = math.radians(angolo_solare_delta)
        
        # Calcolo distanza minima tra file per evitare ombreggiamento
        # Formula: d = (L * sin(tilt)) / tan(δ)
        d_min_teorica = (modulo_lunghezza_m * math.sin(tilt_rad)) / math.tan(delta_rad)
        
        # Applica fattore di riduzione per massimizzare potenza installabile
        d_min_effettiva = d_min_teorica * (1 - self.min_distance_reduction_factor)
        
        # Dimensioni area utilizzabile (sottraendo margini)
        lato_lungo = math.sqrt(superficie_mq)  # Approssimazione area quadrata
        lato_corto = superficie_mq / lato_lungo
        
        area_utile_lunghezza = lato_lungo - (2 * margine_metri)
        area_utile_larghezza = lato_corto - (2 * margine_metri)
        
        if area_utile_lunghezza <= 0 or area_utile_larghezza <= 0:
            return {
                'errore': 'Superficie insufficiente considerando i margini',
                'potenza_installabile_kwp': 0,
                'numero_moduli': 0
            }
        
        # Calcolo numero di file e moduli per fila
        # Spazio occupato da ogni fila (modulo + distanza)
        spazio_per_fila = modulo_lunghezza_m * math.cos(tilt_rad) + d_min_effettiva
        
        numero_file = int(area_utile_lunghezza / spazio_per_fila)
        moduli_per_fila = int(area_utile_larghezza / modulo_larghezza_m)
        
        numero_moduli_totale = numero_file * moduli_per_fila
        potenza_installabile_kwp = (numero_moduli_totale * modulo_params['potenza_wp']) / 1000
        
        # Calcolo superficie effettivamente occupata
        superficie_occupata = numero_file * spazio_per_fila * area_utile_larghezza
        fattore_riempimento = superficie_occupata / superficie_mq
        
        return {
            'orientamento': 'sud',
            'potenza_installabile_kwp': round(potenza_installabile_kwp, 2),
            'numero_moduli': numero_moduli_totale,
            'numero_file': numero_file,
            'moduli_per_fila': moduli_per_fila,
            'distanza_tra_file_m': round(d_min_effettiva, 2),
            'distanza_teorica_m': round(d_min_teorica, 2),
            'fattore_riduzione_applicato': self.min_distance_reduction_factor,
            'superficie_occupata_mq': round(superficie_occupata, 2),
            'fattore_riempimento': round(fattore_riempimento, 3),
            'modulo_utilizzato': modulo_params['nome'],
            'tilt_degrees': tilt_degrees,
            'azimuth_degrees': 180,  # Sud
            'margine_metri': margine_metri,
            'angolo_solare_delta': angolo_solare_delta
        }
    
    def calculate_east_west_layout(self,
                                 superficie_mq: float,
                                 tilt_degrees: float,
                                 margine_metri: float = 1.0,
                                 modulo_params: Optional[Dict] = None) -> Dict:
        """
        Calcola il layout per orientamento Est-Ovest (tetto a farfalla)
        
        Args:
            superficie_mq: Superficie disponibile in m²
            tilt_degrees: Inclinazione moduli in gradi
            margine_metri: Margine dai bordi in metri
            modulo_params: Parametri del modulo (se None usa default)
            
        Returns:
            Dict con risultati del calcolo
        """
        if modulo_params is None:
            modulo_params = self.default_module
        
        # Conversioni
        modulo_lunghezza_m = modulo_params['lunghezza_mm'] / 1000
        modulo_larghezza_m = modulo_params['larghezza_mm'] / 1000
        tilt_rad = math.radians(tilt_degrees)
        
        # Per layout Est-Ovest, la distanza tra le "V" è minima
        # perché non c'è ombreggiamento reciproco significativo
        altezza_v = modulo_lunghezza_m * math.sin(tilt_rad)
        larghezza_v = 2 * modulo_lunghezza_m * math.cos(tilt_rad)
        
        # Distanza minima tra le "V" (solo per manutenzione)
        distanza_manutenzione = 0.8  # 80cm per passaggio
        
        # Dimensioni area utilizzabile
        lato_lungo = math.sqrt(superficie_mq)
        lato_corto = superficie_mq / lato_lungo
        
        area_utile_lunghezza = lato_lungo - (2 * margine_metri)
        area_utile_larghezza = lato_corto - (2 * margine_metri)
        
        if area_utile_lunghezza <= 0 or area_utile_larghezza <= 0:
            return {
                'errore': 'Superficie insufficiente considerando i margini',
                'potenza_installabile_kwp': 0,
                'numero_moduli': 0
            }
        
        # Calcolo numero di "V" e moduli per "V"
        spazio_per_v = larghezza_v + distanza_manutenzione
        numero_v = int(area_utile_lunghezza / spazio_per_v)
        moduli_per_lato_v = int(area_utile_larghezza / modulo_larghezza_m)
        
        # Ogni "V" ha moduli su entrambi i lati (Est e Ovest)
        moduli_per_v = moduli_per_lato_v * 2
        numero_moduli_totale = numero_v * moduli_per_v
        potenza_installabile_kwp = (numero_moduli_totale * modulo_params['potenza_wp']) / 1000
        
        # Calcolo superficie occupata
        superficie_occupata = numero_v * spazio_per_v * area_utile_larghezza
        fattore_riempimento = superficie_occupata / superficie_mq
        
        return {
            'orientamento': 'est_ovest',
            'potenza_installabile_kwp': round(potenza_installabile_kwp, 2),
            'numero_moduli': numero_moduli_totale,
            'numero_moduli_est': numero_moduli_totale // 2,
            'numero_moduli_ovest': numero_moduli_totale // 2,
            'numero_v': numero_v,
            'moduli_per_v': moduli_per_v,
            'moduli_per_lato_v': moduli_per_lato_v,
            'larghezza_v_m': round(larghezza_v, 2),
            'altezza_v_m': round(altezza_v, 2),
            'distanza_tra_v_m': round(distanza_manutenzione, 2),
            'superficie_occupata_mq': round(superficie_occupata, 2),
            'fattore_riempimento': round(fattore_riempimento, 3),
            'modulo_utilizzato': modulo_params['nome'],
            'tilt_degrees': tilt_degrees,
            'azimuth_est_degrees': 90,
            'azimuth_ovest_degrees': 270,
            'margine_metri': margine_metri
        }
    
    def calculate_optimal_layout(self,
                               superficie_mq: float,
                               tilt_degrees: float,
                               margine_metri: float = 1.0,
                               modulo_params: Optional[Dict] = None) -> Dict:
        """
        Calcola entrambi i layout e restituisce quello con maggiore potenza installabile
        
        Returns:
            Dict con il layout ottimale e confronto
        """
        layout_sud = self.calculate_south_layout(
            superficie_mq, tilt_degrees, margine_metri, modulo_params
        )
        
        layout_est_ovest = self.calculate_east_west_layout(
            superficie_mq, tilt_degrees, margine_metri, modulo_params
        )
        
        # Confronto potenze
        potenza_sud = layout_sud.get('potenza_installabile_kwp', 0)
        potenza_est_ovest = layout_est_ovest.get('potenza_installabile_kwp', 0)
        
        if potenza_sud >= potenza_est_ovest:
            layout_ottimale = layout_sud
            layout_alternativo = layout_est_ovest
        else:
            layout_ottimale = layout_est_ovest
            layout_alternativo = layout_sud
        
        return {
            'layout_ottimale': layout_ottimale,
            'layout_alternativo': layout_alternativo,
            'confronto': {
                'potenza_sud_kwp': potenza_sud,
                'potenza_est_ovest_kwp': potenza_est_ovest,
                'differenza_kwp': abs(potenza_sud - potenza_est_ovest),
                'migliore': layout_ottimale['orientamento']
            }
        }
    
    def get_module_suggestions(self) -> List[Dict]:
        """
        Restituisce una lista di moduli fotovoltaici suggeriti
        """
        return [
            {
                'nome': 'LONGI LR7-54HVH-495M Hi-MO X10 Scientist',
                'potenza_wp': 495,
                'lunghezza_mm': 2278,
                'larghezza_mm': 1134,
                'efficienza': 22.8,
                'tipo': 'Monocristallino'
            },
            {
                'nome': 'JinkoSolar Tiger Neo N-type 78HL4-BDV 620W',
                'potenza_wp': 620,
                'lunghezza_mm': 2465,
                'larghezza_mm': 1134,
                'efficienza': 22.3,
                'tipo': 'Monocristallino N-type'
            },
            {
                'nome': 'Canadian Solar HiKu7 Mono PERC CS7N-MS 540W',
                'potenza_wp': 540,
                'lunghezza_mm': 2384,
                'larghezza_mm': 1303,
                'efficienza': 21.2,
                'tipo': 'Monocristallino PERC'
            }
        ]
    
    def validate_parameters(self, 
                          superficie_mq: float,
                          tilt_degrees: float,
                          margine_metri: float) -> Dict:
        """
        Valida i parametri di input
        
        Returns:
            Dict con risultato validazione
        """
        errors = []
        warnings = []
        
        if superficie_mq <= 0:
            errors.append("La superficie deve essere maggiore di 0")
        elif superficie_mq < 100:
            warnings.append("Superficie molto piccola, potrebbe non essere economicamente conveniente")
        
        if tilt_degrees < 0 or tilt_degrees > 90:
            errors.append("L'inclinazione deve essere tra 0 e 90 gradi")
        elif tilt_degrees < 10:
            warnings.append("Inclinazione molto bassa, potrebbe ridurre l'efficienza")
        elif tilt_degrees > 60:
            warnings.append("Inclinazione molto alta, potrebbe ridurre la potenza installabile")
        
        if margine_metri < 0:
            errors.append("Il margine non può essere negativo")
        elif margine_metri > 5:
            warnings.append("Margine molto ampio, potrebbe ridurre significativamente la potenza installabile")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

def test_geometry_calculator():
    """Funzione di test per il calcolatore geometrico"""
    calc = GeometryCalculator()
    
    # Test con parametri tipici
    superficie = 2500  # m²
    tilt = 30  # gradi
    margine = 1.5  # metri
    
    print("=== TEST GEOMETRY CALCULATOR ===")
    print(f"Superficie: {superficie} m²")
    print(f"Inclinazione: {tilt}°")
    print(f"Margine: {margine} m")
    print()
    
    # Test layout Sud
    layout_sud = calc.calculate_south_layout(superficie, tilt, margine)
    print("LAYOUT SUD:")
    for key, value in layout_sud.items():
        print(f"  {key}: {value}")
    print()
    
    # Test layout Est-Ovest
    layout_eo = calc.calculate_east_west_layout(superficie, tilt, margine)
    print("LAYOUT EST-OVEST:")
    for key, value in layout_eo.items():
        print(f"  {key}: {value}")
    print()
    
    # Test layout ottimale
    layout_ottimale = calc.calculate_optimal_layout(superficie, tilt, margine)
    print("CONFRONTO LAYOUT:")
    print(f"  Migliore: {layout_ottimale['confronto']['migliore']}")
    print(f"  Potenza Sud: {layout_ottimale['confronto']['potenza_sud_kwp']} kWp")
    print(f"  Potenza Est-Ovest: {layout_ottimale['confronto']['potenza_est_ovest_kwp']} kWp")
    print(f"  Differenza: {layout_ottimale['confronto']['differenza_kwp']} kWp")

if __name__ == "__main__":
    test_geometry_calculator()

