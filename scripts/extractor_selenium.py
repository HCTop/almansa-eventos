#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EXTRACTOR CON SELENIUM - GITHUB ACTIONS
========================================
Usa Selenium para simular navegador real y evitar bloqueos 403.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
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

def generar_id(titulo, fecha, lugar):
    texto = f"{titulo}{fecha}{lugar}".lower().strip()
    return "evt_" + hashlib.md5(texto.encode()).hexdigest()[:12]

def determinar_categoria(titulo):
    texto = titulo.lower()
    for categoria, keywords in CATEGORIAS.items():
        if any(kw in texto for kw in keywords):
            return categoria
    return "CULTURA"

def parsear_fecha_es(texto_fecha):
    meses_es = {
        'ene': 1, 'enero': 1, 'feb': 2, 'febrero': 2, 
        'mar': 3, 'marzo': 3, 'abr': 4, 'abril': 4,
        'may': 5, 'mayo': 5, 'jun': 6, 'junio': 6,
        'jul': 7, 'julio': 7, 'ago': 8, 'agosto': 8,
        'sep': 9, 'septiembre': 9, 'oct': 10, 'octubre': 10,
        'nov': 11, 'noviembre': 11, 'dic': 12, 'diciembre': 12
    }
    
    patron = r'(\d{1,2})[/\s-]+(?:de\s+)?(\w+)'
    match = re.search(patron, texto_fecha.lower())
    
    if match:
        dia = int(match.group(1))
        mes_texto = match.group(2)
        
        mes = None
        for clave, valor in meses_es.items():
            if clave in mes_texto:
                mes = valor
                break
        
        if mes:
            anio = datetime.now().year
            try:
                fecha = datetime(anio, mes, dia)
                if fecha < datetime.now():
                    fecha = datetime(anio + 1, mes, dia)
                return fecha.strftime('%Y-%m-%d')
            except ValueError:
                pass
    
    return None

# ======================================================================
# SELENIUM
# ======================================================================

def crear_driver():
    """Crea instancia de Chrome con Selenium"""
    print("🔧 Configurando Chrome Selenium...")
    
    chrome_options = Options()
    
    # Modo headless (sin interfaz gráfica)
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    
    # Anti-detección
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # User agent real
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Tamaño de ventana
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Script anti-detección adicional
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def extraer_con_selenium(url, teatro_nombre):
    """Extrae eventos usando Selenium"""
    print(f"\n🎭 Extrayendo {teatro_nombre}...")
    print(f"   URL: {url}")
    
    eventos = []
    driver = None
    
    try:
        driver = crear_driver()
        
        # Cargar página
        print("   📥 Cargando página...")
        driver.get(url)
        
        # Esperar a que cargue el contenido dinámico (máximo 15 segundos)
        print("   ⏳ Esperando contenido JavaScript...")
        time.sleep(5)  # Espera fija inicial
        
        # Intentar esperar elementos específicos
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
            print("   ✅ Contenido cargado (detectado <article>)")
        except:
            print("   ⚠️ No se detectaron <article>, continuando...")
        
        # Obtener HTML renderizado
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar eventos con múltiples selectores
        selectores = [
            'article',
            {'class': ['event', 'evento', 'card-event', 'event-card']},
            {'class': ['card']},
            {'attrs': {'data-event': True}}
        ]
        
        eventos_cards = []
        for selector in selectores:
            if isinstance(selector, str):
                eventos_cards.extend(soup.find_all(selector))
            elif 'class' in selector:
                eventos_cards.extend(soup.find_all(['div', 'article'], class_=selector['class']))
            elif 'attrs' in selector:
                eventos_cards.extend(soup.find_all(['div', 'article'], attrs=selector['attrs']))
        
        # Eliminar duplicados
        eventos_cards = list({str(card): card for card in eventos_cards}.values())
        
        print(f"   📋 Encontradas {len(eventos_cards)} posibles tarjetas")
        
        for card in eventos_cards:
            # Título
            titulo_elem = card.find(['h1', 'h2', 'h3', 'h4', 'h5', 'a'], class_=re.compile(r'title|titulo|name|nombre|heading', re.I))
            if not titulo_elem:
                titulo_elem = card.find(['h1', 'h2', 'h3', 'h4', 'a'])
            
            if not titulo_elem:
                continue
            
            titulo = titulo_elem.get_text(strip=True)
            
            # Filtrar títulos muy cortos
            if len(titulo) < 5 or titulo.lower() in ['ver más', 'más info', 'comprar', 'entradas']:
                continue
            
            # Fecha
            fecha_elem = card.find('time') or card.find(class_=re.compile(r'fecha|date', re.I))
            fecha_iso = None
            
            if fecha_elem:
                fecha_texto = fecha_elem.get('datetime', fecha_elem.get_text(strip=True))
                fecha_iso = parsear_fecha_es(fecha_texto)
            
            if not fecha_iso:
                texto_completo = card.get_text()
                fecha_iso = parsear_fecha_es(texto_completo)
            
            if not fecha_iso:
                fecha_iso = datetime.now().strftime('%Y-%m-%d')
            
            # Hora
            hora = ""
            hora_elem = card.find(class_=re.compile(r'hora|time', re.I))
            if hora_elem:
                hora_texto = hora_elem.get_text(strip=True)
                match_hora = re.search(r'(\d{1,2}):(\d{2})', hora_texto)
                if match_hora:
                    hora = match_hora.group(0)
            
            if not hora:
                hora = "20:00"
            
            # URL
            link_elem = card.find('a', href=True)
            link = ""
            if link_elem:
                link = link_elem.get('href', '')
                if link and not link.startswith('http'):
                    link = 'https://www.tomaticket.es' + link
            
            # Descripción
            desc_elem = card.find('p') or card.find(class_=re.compile(r'desc|summ', re.I))
            descripcion = desc_elem.get_text(strip=True)[:200] if desc_elem else titulo
            
            print(f"   ✅ {titulo[:60]}")
            print(f"      📅 {fecha_iso} | ⏰ {hora}")
            
            eventos.append({
                'id': generar_id(titulo, fecha_iso, teatro_nombre),
                'titulo': titulo,
                'descripcion': descripcion,
                'fecha': fecha_iso,
                'hora': hora,
                'lugar': teatro_nombre,
                'categoria': determinar_categoria(titulo),
                'precio': "Ver en taquilla",
                'urlCompra': link or url,
                'esGratuito': False,
                'fuente': "TomaTicket"
            })
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    finally:
        if driver:
            driver.quit()
    
    return eventos

# ======================================================================
# MAIN
# ======================================================================

def main():
    print("="*70)
    print("EXTRACTOR CON SELENIUM - GITHUB ACTIONS")
    print("="*70)
    print()
    
    todos_eventos = []
    
    for teatro, url in TOMATICKET_URLS.items():
        eventos = extraer_con_selenium(url, teatro)
        todos_eventos.extend(eventos)
    
    # Ordenar por fecha
    eventos_ordenados = sorted(todos_eventos, key=lambda x: x['fecha'])
    
    # Guardar JSON
    with open('eventos_agenda.json', 'w', encoding='utf-8') as f:
        json.dump(eventos_ordenados, f, ensure_ascii=False, indent=2)
    
    # Estadísticas
    print()
    print("="*70)
    print("✅ COMPLETADO")
    print(f"📊 Total eventos: {len(eventos_ordenados)}")
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
        print("   - Puede ser temporada baja")
        print("   - O cambios en la web de TomaTicket")
    
    print("="*70)

if __name__ == "__main__":
    main()
