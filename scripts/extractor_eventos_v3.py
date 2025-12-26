#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EXTRACTOR MULTI-FUENTE v3.0 - ALMANSA INFORMA
==============================================

Extrae eventos de múltiples fuentes web y genera un JSON unificado.

FUENTES ACTIVAS:
1. La Tinta de Almansa - Programaciones
2. Ayuntamiento de Almansa - RSS (Actualidad + Cultura)
3. TomaTicket (Teatro Regio + Teatro Principal)
4. DeAlmansa.com
5. La Tinta RSS (backup)

DESACTIVADO:
- Almansa Cultura (bloqueado por firewall anti-bot)

Autor: HCTop
Fecha: 2025-12-26
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re
import hashlib
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
import time

# ======================================================================
# CONFIGURACIÓN
# ======================================================================

# URLs de las fuentes
LA_TINTA_RSS = "https://latintadealmansa.com/feed/"
LA_TINTA_PROGRAMACION = "https://latintadealmansa.com/cultura/"
ALMANSA_CULTURA_EVENTOS = "https://www.almansacultura.es/index.php/eventos"  # DESACTIVADO
AYUNTAMIENTO_RSS = "https://almansa.es/category/actualidad/feed/"
AYUNTAMIENTO_CULTURA = "https://almansa.es/category/cultura/feed/"
TOMATICKET_REGIO = "https://www.tomaticket.es/es-es/recintos/teatro-regio-almansa"
TOMATICKET_PRINCIPAL = "https://www.tomaticket.es/es-es/recintos/teatro-principal-almansa"
DEALMANSA_AGENDA = "https://dealmansa.com/agenda/"

# Headers comunes para todas las peticiones (anti-bot mejorado)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://www.google.com/'
}

# Categorías de eventos
CATEGORIAS = {
    'MUSICA': ['concierto', 'música', 'recital', 'banda', 'orquesta', 'coro'],
    'TEATRO': ['teatro', 'obra', 'monólogo', 'comedia', 'drama'],
    'INFANTIL': ['infantil', 'niños', 'familia', 'cuentacuentos'],
    'DEPORTE': ['deport', 'partido', 'carrera', 'torneo', 'liga', 'campeonato'],
    'FIESTA': ['fiesta', 'feria', 'verbena', 'carnaval'],
    'EXPOSICION': ['exposición', 'muestra', 'galería'],
    'CINE': ['cine', 'película', 'proyección', 'film'],
    'CULTURA': ['charla', 'conferencia', 'presentación', 'taller', 'jornada']
}

# ======================================================================
# FUNCIONES DE UTILIDAD
# ======================================================================

def generar_id(titulo: str, fecha: str, lugar: str) -> str:
    """Genera un ID único basado en título, fecha y lugar"""
    texto = f"{titulo}{fecha}{lugar}".lower().strip()
    return "evt_" + hashlib.md5(texto.encode()).hexdigest()[:12]

def determinar_categoria(titulo: str, descripcion: str) -> str:
    """Determina la categoría del evento basándose en palabras clave"""
    texto = (titulo + " " + descripcion).lower()
    
    for categoria, keywords in CATEGORIAS.items():
        if any(kw in texto for kw in keywords):
            return categoria
    
    return "CULTURA"

def es_evento(titulo: str, descripcion: str) -> bool:
    """Determina si la noticia es sobre un evento - VERSIÓN AMPLIADA"""
    
    keywords = [
        # Tipos de eventos
        'programa', 'eventos', 'concierto', 'teatro', 'festival',
        'feria', 'fiestas', 'actuación', 'espectáculo', 'exposición',
        'taller', 'charla', 'jornada', 'encuentro', 'celebra',
        'presentación', 'inauguración', 'estreno', 'gala', 'función',
        'proyección', 'recital', 'tributo', 'homenaje', 'muestra',
        'certamen', 'competición', 'carrera', 'maratón', 'torneo',
        'campeonato', 'semifinal', 'final', 'partido',
        
        # Palabras relacionadas con eventos
        'entradas', 'inscripc', 'asistir', 'participar', 'acudir',
        'agenda', 'actividad', 'programación', 'calendario',
        
        # Lugares típicos de eventos
        'teatro regio', 'teatro principal', 'auditorio', 'castillo',
        'pabellón', 'estadio', 'plaza mayor', 'sala', 'polideportivo',
        
        # Indicadores temporales
        'próximo', 'este sábado', 'este domingo', 'el día',
        'horario', 'hora:', 'a las', 'desde las', 'hasta el',
        
        # Deportes y ocio
        'torneo', 'liga', 'clasificación', 'campeonato', 'exhibición'
    ]
    
    texto = (titulo + " " + descripcion).lower()
    
    # REGLA 1: Indicadores de precio = casi seguro es evento
    if any(p in texto for p in ['€', 'euros', 'precio:', 'gratuito', 'gratis', 'entrada libre', 'entrada gratuita']):
        return True
    
    # REGLA 2: Patrón de fecha explícita
    if re.search(r'\d{1,2}\s+de\s+\w+', texto):
        return True
    
    # REGLA 3: Horario explícito
    if re.search(r'a las \d{1,2}[:\d]*', texto):
        return True
    
    # REGLA 4: Keywords normales
    return any(kw in texto for kw in keywords)

def parsear_fecha_es(texto_fecha: str) -> Optional[str]:
    """Parsea fechas en español y las convierte a formato ISO"""
    meses_es = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    
    # Patrón: "25 de diciembre de 2025"
    patron = r'(\d{1,2})\s+de\s+(\w+)(?:\s+de\s+(\d{4}))?'
    match = re.search(patron, texto_fecha.lower())
    
    if match:
        dia = int(match.group(1))
        mes_texto = match.group(2)
        anio = int(match.group(3)) if match.group(3) else datetime.now().year
        
        if mes_texto in meses_es:
            mes = meses_es[mes_texto]
            try:
                fecha = datetime(anio, mes, dia)
                return fecha.strftime('%Y-%m-%d')
            except ValueError:
                pass
    
    return None

# ======================================================================
# EXTRACTORES POR FUENTE
# ======================================================================

def extraer_la_tinta_programaciones() -> List[Dict]:
    """Extrae programaciones trimestrales de La Tinta"""
    print("🔍 Extrayendo programaciones de La Tinta...")
    eventos = []
    
    try:
        response = requests.get(LA_TINTA_PROGRAMACION, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"  ⚠️ Error HTTP {response.status_code}")
            return eventos
        
        soup = BeautifulSoup(response.content, 'html.parser')
        articulos = soup.find_all('article', class_='post')
        
        for articulo in articulos:
            titulo_elem = articulo.find(['h2', 'h3'])
            if not titulo_elem:
                continue
            
            titulo = titulo_elem.get_text(strip=True)
            
            if 'programación' in titulo.lower():
                link_elem = titulo_elem.find('a')
                if link_elem:
                    eventos.append({
                        'id': generar_id(titulo, "", "La Tinta"),
                        'titulo': titulo,
                        'descripcion': "Programación cultural trimestral",
                        'fecha': datetime.now().strftime('%Y-%m-%d'),
                        'hora': "",
                        'lugar': "Varios",
                        'categoria': "CULTURA",
                        'precio': "",
                        'urlCompra': link_elem.get('href', ''),
                        'esGratuito': False,
                        'fuente': "La Tinta de Almansa"
                    })
        
        print(f"✅ La Tinta Programaciones: {len(eventos)} eventos")
        
    except Exception as e:
        print(f"  ⚠️ Error: {str(e)}")
    
    return eventos

def extraer_ayuntamiento_almansa() -> List[Dict]:
    """Extrae eventos del RSS del Ayuntamiento (Actualidad + Cultura)"""
    print("🔍 Extrayendo eventos del Ayuntamiento de Almansa...")
    eventos = []
    
    for nombre, url in [("Actualidad", AYUNTAMIENTO_RSS), ("Cultura", AYUNTAMIENTO_CULTURA)]:
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            if response.status_code != 200:
                continue
            
            root = ET.fromstring(response.content)
            items = root.findall('.//item')
            print(f"  📋 {nombre}: {len(items)} artículos encontrados")
            
            for item in items:
                titulo = item.find('title').text if item.find('title') is not None else ""
                descripcion = item.find('description').text if item.find('description') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                
                if not es_evento(titulo, descripcion):
                    continue
                
                fecha_pub = item.find('pubDate').text if item.find('pubDate') is not None else ""
                
                eventos.append({
                    'id': generar_id(titulo, fecha_pub, "Ayuntamiento"),
                    'titulo': titulo,
                    'descripcion': descripcion[:200],
                    'fecha': datetime.now().strftime('%Y-%m-%d'),
                    'hora': "",
                    'lugar': "Almansa",
                    'categoria': determinar_categoria(titulo, descripcion),
                    'precio': "",
                    'urlCompra': link,
                    'esGratuito': True,
                    'fuente': "Ayuntamiento de Almansa"
                })
        
        except Exception as e:
            print(f"  ⚠️ Error en {nombre}: {str(e)}")
    
    print(f"✅ Ayuntamiento: {len(eventos)} eventos")
    return eventos

def extraer_tomaticket() -> List[Dict]:
    """Extrae eventos de TomaTicket (Teatro Regio + Principal)"""
    print("🔍 Extrayendo eventos de TomaTicket...")
    eventos = []
    
    for teatro, url in [("Teatro Regio", TOMATICKET_REGIO), ("Teatro Principal", TOMATICKET_PRINCIPAL)]:
        try:
            time.sleep(1)
            response = requests.get(url, headers=HEADERS, timeout=15)
            if response.status_code != 200:
                continue
            
            soup = BeautifulSoup(response.content, 'html.parser')
            eventos_cards = soup.find_all('div', class_=['event-card', 'evento', 'card'])
            print(f"  📋 {teatro}: {len(eventos_cards)} posibles eventos")
            
            for card in eventos_cards:
                titulo_elem = card.find(['h2', 'h3', 'h4', 'a'])
                if not titulo_elem:
                    continue
                
                titulo = titulo_elem.get_text(strip=True)
                
                fecha_elem = card.find('time') or card.find(class_=re.compile(r'fecha|date'))
                fecha_iso = datetime.now().strftime('%Y-%m-%d')
                
                if fecha_elem:
                    fecha_texto = fecha_elem.get('datetime', fecha_elem.get_text(strip=True))
                    fecha_parseada = parsear_fecha_es(fecha_texto)
                    if fecha_parseada:
                        fecha_iso = fecha_parseada
                
                hora = ""
                hora_elem = card.find(class_=re.compile(r'hora|time'))
                if hora_elem:
                    hora = hora_elem.get_text(strip=True)
                
                link_elem = card.find('a')
                link = link_elem.get('href', '') if link_elem else ''
                if link and not link.startswith('http'):
                    link = 'https://www.tomaticket.es' + link
                
                print(f"  ✅ {titulo[:50]} - {fecha_iso}")
                
                eventos.append({
                    'id': generar_id(titulo, fecha_iso, teatro),
                    'titulo': titulo,
                    'descripcion': card.get_text(strip=True)[:200],
                    'fecha': fecha_iso,
                    'hora': hora or "20:00",
                    'lugar': teatro,
                    'categoria': determinar_categoria(titulo, ""),
                    'precio': "Consultar en taquilla",
                    'urlCompra': link,
                    'esGratuito': False,
                    'fuente': "TomaTicket"
                })
        
        except Exception as e:
            print(f"  ⚠️ Error en {teatro}: {str(e)}")
    
    print(f"✅ TomaTicket: {len(eventos)} eventos")
    return eventos

def extraer_dealmansa() -> List[Dict]:
    """Extrae eventos de DeAlmansa.com"""
    print("🔍 Extrayendo eventos de DeAlmansa.com...")
    eventos = []
    
    try:
        time.sleep(1)
        response = requests.get(DEALMANSA_AGENDA, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"  ⚠️ Error HTTP {response.status_code}")
            return eventos
        
        soup = BeautifulSoup(response.content, 'html.parser')
        cards = soup.find_all(['div', 'article'], class_=re.compile(r'evento|event|card|item'))
        print(f"  📋 Encontradas {len(cards)} posibles tarjetas")
        
        for card in cards:
            titulo_elem = card.find(['h2', 'h3', 'h4'])
            if not titulo_elem:
                continue
            
            titulo = titulo_elem.get_text(strip=True)
            descripcion = card.get_text(strip=True)[:200]
            
            if not es_evento(titulo, descripcion):
                continue
            
            eventos.append({
                'id': generar_id(titulo, "", "DeAlmansa"),
                'titulo': titulo,
                'descripcion': descripcion,
                'fecha': datetime.now().strftime('%Y-%m-%d'),
                'hora': "",
                'lugar': "Almansa",
                'categoria': determinar_categoria(titulo, descripcion),
                'precio': "",
                'urlCompra': DEALMANSA_AGENDA,
                'esGratuito': False,
                'fuente': "DeAlmansa"
            })
        
        print(f"✅ DeAlmansa: {len(eventos)} eventos")
        
    except Exception as e:
        print(f"  ⚠️ Error: {str(e)}")
    
    return eventos

def extraer_la_tinta_rss() -> List[Dict]:
    """Extrae eventos del RSS general de La Tinta (backup)"""
    print("🔍 Extrayendo eventos de RSS La Tinta (backup)...")
    eventos = []
    
    try:
        response = requests.get(LA_TINTA_RSS, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return eventos
        
        root = ET.fromstring(response.content)
        items = root.findall('.//item')
        
        for item in items:
            titulo = item.find('title').text if item.find('title') is not None else ""
            descripcion = item.find('description').text if item.find('description') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            
            if not es_evento(titulo, descripcion):
                continue
            
            eventos.append({
                'id': generar_id(titulo, "", "La Tinta RSS"),
                'titulo': titulo,
                'descripcion': descripcion[:200],
                'fecha': datetime.now().strftime('%Y-%m-%d'),
                'hora': "",
                'lugar': "Almansa",
                'categoria': determinar_categoria(titulo, descripcion),
                'precio': "",
                'urlCompra': link,
                'esGratuito': False,
                'fuente': "La Tinta de Almansa"
            })
        
        print(f"✅ La Tinta RSS: {len(eventos)} eventos")
        
    except Exception as e:
        print(f"  ⚠️ Error: {str(e)}")
    
    return eventos

# ======================================================================
# DEDUPLICACIÓN
# ======================================================================

def deduplicar_eventos(eventos: List[Dict]) -> List[Dict]:
    """Elimina eventos duplicados basándose en una firma única"""
    print("\n📡 FASE 2: DEDUPLICACIÓN\n")
    print("🔄 Deduplicando eventos...")
    
    eventos_unicos = {}
    
    for evento in eventos:
        # Firma: título normalizado + fecha + lugar
        firma = f"{evento['titulo'].lower().strip()}{evento['fecha']}{evento['lugar'].lower()}"
        
        if firma not in eventos_unicos:
            eventos_unicos[firma] = evento
        else:
            print(f"  ⚠️ Duplicado eliminado: {evento['titulo'][:50]}")
    
    resultado = list(eventos_unicos.values())
    print(f"✅ Deduplicación: {len(eventos)} → {len(resultado)} eventos únicos")
    
    return resultado

# ======================================================================
# MAIN
# ======================================================================

def main():
    print("="*70)
    print("EXTRACTOR MULTI-FUENTE v3.0 - ALMANSA INFORMA")
    print("="*70)
    
    print("\n📡 FASE 1: EXTRACCIÓN DE TODAS LAS FUENTES\n")
    
    # EXTRACCIÓN
    eventos_tinta_prog = extraer_la_tinta_programaciones()
    # eventos_almansa = extraer_almansa_cultura()  # DESACTIVADO (bloquea bots)
    eventos_almansa = []  # Vacío mientras esté bloqueado
    eventos_ayto = extraer_ayuntamiento_almansa()
    eventos_tomaticket = extraer_tomaticket()
    eventos_dealmansa = extraer_dealmansa()
    eventos_tinta_rss = extraer_la_tinta_rss()
    
    # CONSOLIDACIÓN
    todos_eventos = (
        eventos_tinta_prog + 
        eventos_almansa + 
        eventos_ayto + 
        eventos_tomaticket + 
        eventos_dealmansa + 
        eventos_tinta_rss
    )
    
    print(f"\n📊 Total extraído: {len(todos_eventos)} eventos")
    
    # DEDUPLICACIÓN
    eventos_finales = deduplicar_eventos(todos_eventos)
    
    # GUARDADO
    print("\n📡 FASE 3: GUARDADO\n")
    
    with open('eventos_agenda.json', 'w', encoding='utf-8') as f:
        json.dump(eventos_finales, f, ensure_ascii=False, indent=2)
    
    # ESTADÍSTICAS
    print("="*70)
    print("✅ COMPLETADO")
    print(f"📊 Eventos únicos: {len(eventos_finales)}")
    print(f"📁 Archivo: eventos_agenda.json")
    
    if eventos_finales:
        fechas = [e['fecha'] for e in eventos_finales if e['fecha']]
        if fechas:
            print(f"📅 Rango: {min(fechas)} → {max(fechas)}")
    
    print("="*70)
    
    # ESTADÍSTICAS POR FUENTE
    fuentes = {}
    for e in eventos_finales:
        fuente = e.get('fuente', 'Desconocido')
        fuentes[fuente] = fuentes.get(fuente, 0) + 1
    
    print("\n📊 ESTADÍSTICAS POR FUENTE:")
    for fuente, count in sorted(fuentes.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {fuente}: {count} eventos")
    
    # ESTADÍSTICAS POR CATEGORÍA
    categorias = {}
    for e in eventos_finales:
        cat = e.get('categoria', 'CULTURA')
        categorias[cat] = categorias.get(cat, 0) + 1
    
    print("\n📊 ESTADÍSTICAS POR CATEGORÍA:")
    for cat, count in sorted(categorias.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {cat}: {count} eventos")

if __name__ == "__main__":
    main()
