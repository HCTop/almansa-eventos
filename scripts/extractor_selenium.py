#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EXTRACTOR EVENTOS TOMATICKET - VERSIÓN CORREGIDA
=================================================
Extrae eventos de TomaTicket para Teatro Regio y Teatro Principal de Almansa.
Corregido el parseo de fechas según la estructura real de la web.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re
import hashlib
import time

# ======================================================================
# CONFIGURACIÓN
# ======================================================================

TOMATICKET_URLS = {
    "Teatro Regio": "https://www.tomaticket.es/es-es/recintos/teatro-regio-almansa",
    "Teatro Principal": "https://www.tomaticket.es/es-es/recintos/teatro-principal-almansa"
}

# Mapeo de meses en español
MESES_ES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
    'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
    'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

CATEGORIAS_KEYWORDS = {
    'MUSICA': ['concierto', 'música', 'recital', 'banda', 'orquesta', 'coral', 'sinfónic'],
    'TEATRO': ['teatro', 'obra', 'comedia', 'drama', 'tragedia'],
    'INFANTIL': ['infantil', 'niños', 'familia', 'cuentacuentos', 'disney'],
    'DANZA': ['danza', 'ballet', 'flamenco', 'flamencas'],
    'HUMOR': ['humor', 'monólogo', 'monólogos', 'cómico', 'stand up', 'cura'],
    'MUSICAL': ['musical'],
}

# ======================================================================
# UTILIDADES
# ======================================================================

def generar_id(titulo, fecha, lugar):
    """Genera ID único basado en título, fecha y lugar"""
    texto = f"{titulo}{fecha}{lugar}".lower().strip()
    return "evt_" + hashlib.md5(texto.encode()).hexdigest()[:12]


def determinar_categoria(titulo):
    """Determina la categoría basándose en palabras clave del título"""
    texto = titulo.lower()
    for categoria, keywords in CATEGORIAS_KEYWORDS.items():
        if any(kw in texto for kw in keywords):
            return categoria
    return "CULTURA"


def parsear_fecha_tomaticket(dia_num, mes_texto):
    """
    Parsea fecha desde los elementos de TomaTicket.
    
    Args:
        dia_num: Número del día (ej: "28")
        mes_texto: Nombre del mes en español (ej: "Diciembre")
    
    Returns:
        Fecha en formato ISO (YYYY-MM-DD) o None si falla
    """
    try:
        dia = int(dia_num)
        mes_lower = mes_texto.lower().strip()
        
        # Buscar el número del mes
        mes = None
        for nombre, num in MESES_ES.items():
            if nombre in mes_lower or mes_lower in nombre:
                mes = num
                break
        
        if mes is None:
            print(f"   ⚠️ Mes no reconocido: {mes_texto}")
            return None
        
        # Determinar el año
        hoy = datetime.now()
        anio = hoy.year
        
        # Si el mes ya pasó este año, asumimos que es el próximo año
        fecha_tentativa = datetime(anio, mes, dia)
        if fecha_tentativa < hoy:
            anio += 1
        
        fecha_final = datetime(anio, mes, dia)
        return fecha_final.strftime('%Y-%m-%d')
        
    except Exception as e:
        print(f"   ❌ Error parseando fecha ({dia_num}, {mes_texto}): {e}")
        return None


def extraer_precio(texto):
    """Extrae el precio del texto"""
    match = re.search(r'(\d+)\s*€', texto)
    if match:
        return f"{match.group(1)} €"
    return "Ver en taquilla"


# ======================================================================
# SELENIUM DRIVER
# ======================================================================

def crear_driver():
    """Crea instancia de Chrome con Selenium"""
    print("🔧 Configurando Chrome Selenium...")
    
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver


# ======================================================================
# EXTRACCIÓN PRINCIPAL
# ======================================================================

def extraer_eventos_tomaticket(url, teatro_nombre):
    """
    Extrae eventos de TomaTicket usando Selenium.
    
    La estructura de TomaTicket es:
    - Cada evento está en un <a> con href que contiene "/es-es/entradas-"
    - Dentro hay: <h4> con título, y textos separados para día de semana, día, mes, precio
    """
    print(f"\n🎭 Extrayendo {teatro_nombre}...")
    print(f"   URL: {url}")
    
    eventos = []
    driver = None
    
    try:
        driver = crear_driver()
        
        print("   📥 Cargando página...")
        driver.get(url)
        time.sleep(3)  # Espera para JavaScript
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar todos los enlaces a eventos
        # Los eventos tienen href con "/es-es/entradas-"
        enlaces_eventos = soup.find_all('a', href=re.compile(r'/es-es/entradas-'))
        
        print(f"   📋 Encontrados {len(enlaces_eventos)} enlaces de eventos")
        
        eventos_procesados = set()  # Para evitar duplicados
        
        for enlace in enlaces_eventos:
            try:
                href = enlace.get('href', '')
                
                # Evitar duplicados
                if href in eventos_procesados:
                    continue
                eventos_procesados.add(href)
                
                # Obtener el texto completo del bloque
                texto_completo = enlace.get_text(separator='\n', strip=True)
                lineas = [l.strip() for l in texto_completo.split('\n') if l.strip()]
                
                if len(lineas) < 3:
                    continue
                
                # Buscar título (en h4 o primera línea significativa)
                titulo_elem = enlace.find(['h4', 'h3', 'h5'])
                if titulo_elem:
                    titulo = titulo_elem.get_text(strip=True)
                else:
                    # Primera línea que no sea día de semana ni número
                    titulo = None
                    for linea in lineas:
                        if not re.match(r'^(lunes|martes|miércoles|jueves|viernes|sábado|domingo|\d{1,2}|enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|desde|\d+\s*€)$', linea.lower()):
                            titulo = linea
                            break
                    if not titulo:
                        continue
                
                # Filtrar títulos no válidos
                if len(titulo) < 5 or titulo.lower() in ['ver más', 'comprar', 'entradas']:
                    continue
                
                # Buscar fecha: día (número) y mes
                dia_num = None
                mes_texto = None
                
                for i, linea in enumerate(lineas):
                    # Buscar número de día (1-31)
                    if re.match(r'^\d{1,2}$', linea):
                        num = int(linea)
                        if 1 <= num <= 31:
                            dia_num = linea
                            # El mes suele estar justo después
                            if i + 1 < len(lineas):
                                siguiente = lineas[i + 1].lower()
                                if any(m in siguiente for m in MESES_ES.keys()):
                                    mes_texto = lineas[i + 1]
                                    break
                
                # Si no encontramos fecha, buscar con otro patrón
                if not dia_num or not mes_texto:
                    for linea in lineas:
                        linea_lower = linea.lower()
                        for mes_nombre in MESES_ES.keys():
                            if mes_nombre in linea_lower:
                                mes_texto = linea
                                break
                
                # Parsear la fecha
                fecha_iso = None
                if dia_num and mes_texto:
                    fecha_iso = parsear_fecha_tomaticket(dia_num, mes_texto)
                
                # Si aún no tenemos fecha, SALTAR este evento (no usar fecha actual)
                if not fecha_iso:
                    print(f"   ⚠️ Sin fecha válida: {titulo[:40]}...")
                    continue
                
                # Extraer precio
                precio = extraer_precio(texto_completo)
                
                # Construir URL completa
                url_evento = href
                if not url_evento.startswith('http'):
                    url_evento = 'https://www.tomaticket.es' + url_evento
                
                print(f"   ✅ {titulo[:50]}...")
                print(f"      📅 {fecha_iso} | 💰 {precio}")
                
                evento = {
                    'id': generar_id(titulo, fecha_iso, teatro_nombre),
                    'titulo': titulo,
                    'descripcion': f"Evento en {teatro_nombre}",
                    'fecha': fecha_iso,
                    'hora': '20:00',  # Hora por defecto
                    'lugar': teatro_nombre,
                    'categoria': determinar_categoria(titulo),
                    'precio': precio,
                    'urlCompra': url_evento,
                    'esGratuito': False,
                    'fuente': 'TomaTicket'
                }
                
                eventos.append(evento)
                
            except Exception as e:
                print(f"   ❌ Error procesando evento: {e}")
                continue
        
    except Exception as e:
        print(f"   ❌ Error general: {e}")
    
    finally:
        if driver:
            driver.quit()
    
    return eventos


def eliminar_duplicados(eventos):
    """Elimina eventos duplicados basándose en título + fecha + lugar"""
    vistos = set()
    unicos = []
    
    for evento in eventos:
        clave = (evento['titulo'].lower(), evento['fecha'], evento['lugar'])
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(evento)
    
    return unicos


def filtrar_eventos_pasados(eventos):
    """Elimina eventos con fecha anterior a hoy"""
    hoy = datetime.now().strftime('%Y-%m-%d')
    return [e for e in eventos if e['fecha'] >= hoy]


# ======================================================================
# MAIN
# ======================================================================

def main():
    print("=" * 70)
    print("EXTRACTOR EVENTOS TOMATICKET - ALMANSA")
    print("=" * 70)
    print(f"Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    
    todos_eventos = []
    
    # Extraer de cada teatro
    for teatro, url in TOMATICKET_URLS.items():
        eventos = extraer_eventos_tomaticket(url, teatro)
        todos_eventos.extend(eventos)
        print(f"   📊 {len(eventos)} eventos de {teatro}")
    
    # Post-procesado
    print("\n🔄 Post-procesado...")
    eventos_unicos = eliminar_duplicados(todos_eventos)
    print(f"   Después de deduplicar: {len(eventos_unicos)}")
    
    eventos_futuros = filtrar_eventos_pasados(eventos_unicos)
    print(f"   Eventos futuros: {len(eventos_futuros)}")
    
    # Ordenar por fecha
    eventos_ordenados = sorted(eventos_futuros, key=lambda x: x['fecha'])
    
    # Guardar JSON
    with open('eventos_agenda.json', 'w', encoding='utf-8') as f:
        json.dump(eventos_ordenados, f, ensure_ascii=False, indent=2)
    
    # Estadísticas finales
    print()
    print("=" * 70)
    print("✅ COMPLETADO")
    print(f"📊 Total eventos: {len(eventos_ordenados)}")
    print(f"📁 Archivo: eventos_agenda.json")
    
    if eventos_ordenados:
        print()
        print("📋 PRÓXIMOS EVENTOS:")
        for i, e in enumerate(eventos_ordenados[:10], 1):
            print(f"  {i}. [{e['fecha']}] {e['titulo'][:45]}")
            print(f"      {e['lugar']} | {e['precio']}")
    else:
        print()
        print("⚠️ No se encontraron eventos futuros")
    
    print("=" * 70)
    
    return eventos_ordenados


if __name__ == "__main__":
    main()
