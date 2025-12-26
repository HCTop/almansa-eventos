#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EXTRACTOR DE EVENTOS - VERSIÓN LOCAL
=====================================

Versión optimizada para ejecutar desde tu ordenador (no GitHub Actions).
Solo extrae de TomaTicket (única fuente válida con eventos estructurados).

Ejecutar: python extractor_eventos_LOCAL.py
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re
import hashlib
from typing import List, Dict, Optional

# ======================================================================
# CONFIGURACIÓN
# ======================================================================

TOMATICKET_REGIO = "https://www.tomaticket.es/es-es/recintos/teatro-regio-almansa"
TOMATICKET_PRINCIPAL = "https://www.tomaticket.es/es-es/recintos/teatro-principal-almansa"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9',
    'Referer': 'https://www.tomaticket.es/',
    'Connection': 'keep-alive'
}

# Categorías
CATEGORIAS = {
    'MUSICA': ['concierto', 'música', 'recital', 'banda', 'orquesta'],
    'TEATRO': ['teatro', 'obra', 'monólogo', 'comedia'],
    'INFANTIL': ['infantil', 'niños', 'familia', 'cuentacuentos'],
    'DANZA': ['danza', 'ballet', 'flamenco'],
    'HUMOR': ['humor', 'monólogo', 'cómico', 'stand up'],
    'CULTURA': ['conferencia', 'charla', 'presentación']
}

# ======================================================================
# UTILIDADES
# ======================================================================

def generar_id(titulo: str, fecha: str, lugar: str) -> str:
    """Genera ID único"""
    texto = f"{titulo}{fecha}{lugar}".lower().strip()
    return "evt_" + hashlib.md5(texto.encode()).hexdigest()[:12]

def determinar_categoria(titulo: str) -> str:
    """Determina categoría del evento"""
    texto = titulo.lower()
    for categoria, keywords in CATEGORIAS.items():
        if any(kw in texto for kw in keywords):
            return categoria
    return "CULTURA"

def parsear_fecha_es(texto_fecha: str) -> Optional[str]:
    """Parsea fechas en español"""
    meses_es = {
        'ene': 1, 'enero': 1, 'feb': 2, 'febrero': 2, 
        'mar': 3, 'marzo': 3, 'abr': 4, 'abril': 4,
        'may': 5, 'mayo': 5, 'jun': 6, 'junio': 6,
        'jul': 7, 'julio': 7, 'ago': 8, 'agosto': 8,
        'sep': 9, 'septiembre': 9, 'oct': 10, 'octubre': 10,
        'nov': 11, 'noviembre': 11, 'dic': 12, 'diciembre': 12
    }
    
    # Patrón: "25 dic", "25 diciembre", "25/12"
    patron = r'(\d{1,2})[/\s-]+(?:de\s+)?(\w+)'
    match = re.search(patron, texto_fecha.lower())
    
    if match:
        dia = int(match.group(1))
        mes_texto = match.group(2)
        
        # Buscar mes
        mes = None
        for clave, valor in meses_es.items():
            if clave in mes_texto:
                mes = valor
                break
        
        if mes:
            # Año actual o siguiente
            anio = datetime.now().year
            try:
                fecha = datetime(anio, mes, dia)
                # Si la fecha ya pasó, asumir año siguiente
                if fecha < datetime.now():
                    fecha = datetime(anio + 1, mes, dia)
                return fecha.strftime('%Y-%m-%d')
            except ValueError:
                pass
    
    return None

# ======================================================================
# EXTRACTOR TOMATICKET
# ======================================================================

def extraer_tomaticket() -> List[Dict]:
    """Extrae eventos de TomaTicket"""
    print("🎭 Extrayendo eventos de TomaTicket...")
    eventos = []
    
    for teatro, url in [("Teatro Regio", TOMATICKET_REGIO), 
                        ("Teatro Principal", TOMATICKET_PRINCIPAL)]:
        try:
            print(f"\n  🔍 Buscando en {teatro}...")
            response = requests.get(url, headers=HEADERS, timeout=15)
            
            if response.status_code != 200:
                print(f"  ⚠️ Error HTTP {response.status_code}")
                continue
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar múltiples posibles estructuras
            selectores = [
                {'class': ['event-card', 'evento', 'card-event']},
                {'class': ['card']},
                {'class': ['item', 'item-event']},
                {'attrs': {'data-event': True}},
                {'name': 'article'}
            ]
            
            eventos_cards = []
            for selector in selectores:
                if 'class' in selector:
                    eventos_cards.extend(soup.find_all(['div', 'article'], class_=selector['class']))
                elif 'attrs' in selector:
                    eventos_cards.extend(soup.find_all(['div', 'article'], attrs=selector['attrs']))
                elif 'name' in selector:
                    eventos_cards.extend(soup.find_all(selector['name']))
            
            # Eliminar duplicados
            eventos_cards = list({str(card): card for card in eventos_cards}.values())
            
            print(f"  📋 Encontradas {len(eventos_cards)} posibles tarjetas")
            
            for card in eventos_cards:
                # Buscar título
                titulo_elem = card.find(['h2', 'h3', 'h4', 'h5', 'a', 'span'], class_=re.compile(r'title|titulo|name|nombre', re.I))
                if not titulo_elem:
                    titulo_elem = card.find(['h2', 'h3', 'h4', 'a'])
                
                if not titulo_elem:
                    continue
                
                titulo = titulo_elem.get_text(strip=True)
                
                # Filtrar títulos muy cortos o genéricos
                if len(titulo) < 5 or titulo.lower() in ['ver más', 'más info', 'comprar']:
                    continue
                
                # Buscar fecha
                fecha_elem = card.find('time') or card.find(class_=re.compile(r'fecha|date', re.I))
                fecha_iso = None
                
                if fecha_elem:
                    fecha_texto = fecha_elem.get('datetime', fecha_elem.get_text(strip=True))
                    fecha_iso = parsear_fecha_es(fecha_texto)
                
                # Si no hay fecha, intentar buscar en todo el texto
                if not fecha_iso:
                    texto_completo = card.get_text()
                    fecha_iso = parsear_fecha_es(texto_completo)
                
                # Si aún no hay fecha, usar fecha aproximada futura
                if not fecha_iso:
                    fecha_iso = (datetime.now()).strftime('%Y-%m-%d')
                
                # Buscar hora
                hora = ""
                hora_elem = card.find(class_=re.compile(r'hora|time', re.I))
                if hora_elem:
                    hora_texto = hora_elem.get_text(strip=True)
                    match_hora = re.search(r'(\d{1,2}):(\d{2})', hora_texto)
                    if match_hora:
                        hora = match_hora.group(0)
                
                # Si no hay hora, usar horario típico de teatro
                if not hora:
                    hora = "20:00"
                
                # Buscar enlace
                link_elem = card.find('a', href=True)
                link = ""
                if link_elem:
                    link = link_elem.get('href', '')
                    if link and not link.startswith('http'):
                        link = 'https://www.tomaticket.es' + link
                
                print(f"  ✅ {titulo[:60]}")
                print(f"     📅 {fecha_iso} | ⏰ {hora} | 📍 {teatro}")
                
                eventos.append({
                    'id': generar_id(titulo, fecha_iso, teatro),
                    'titulo': titulo,
                    'descripcion': card.get_text(strip=True)[:200],
                    'fecha': fecha_iso,
                    'hora': hora,
                    'lugar': teatro,
                    'categoria': determinar_categoria(titulo),
                    'precio': "Ver en taquilla",
                    'urlCompra': link or url,
                    'esGratuito': False,
                    'fuente': "TomaTicket"
                })
        
        except Exception as e:
            print(f"  ❌ Error en {teatro}: {str(e)}")
    
    return eventos

# ======================================================================
# MAIN
# ======================================================================

def main():
    print("="*70)
    print("EXTRACTOR DE EVENTOS - VERSIÓN LOCAL")
    print("="*70)
    print()
    
    # Extraer eventos
    eventos = extraer_tomaticket()
    
    # Ordenar por fecha
    eventos_ordenados = sorted(eventos, key=lambda x: x['fecha'])
    
    # Guardar JSON
    with open('eventos_agenda.json', 'w', encoding='utf-8') as f:
        json.dump(eventos_ordenados, f, ensure_ascii=False, indent=2)
    
    # Estadísticas
    print()
    print("="*70)
    print("✅ COMPLETADO")
    print(f"📊 Eventos encontrados: {len(eventos_ordenados)}")
    print(f"📁 Archivo: eventos_agenda.json")
    
    if eventos_ordenados:
        print(f"📅 Próximo evento: {eventos_ordenados[0]['fecha']}")
        print()
        print("📋 EVENTOS CAPTURADOS:")
        for i, e in enumerate(eventos_ordenados[:10], 1):
            print(f"  {i}. {e['titulo'][:50]}")
            print(f"     {e['fecha']} {e['hora']} - {e['lugar']}")
    else:
        print()
        print("⚠️ No se encontraron eventos")
        print("   Posibles causas:")
        print("   - Temporada baja (enero/agosto)")
        print("   - Teatros cerrados")
        print("   - Cambio en estructura web de TomaTicket")
    
    print("="*70)

if __name__ == "__main__":
    main()
