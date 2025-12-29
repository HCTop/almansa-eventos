#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EXTRACTOR CON SELENIUM - GITHUB ACTIONS
========================================
Usa Selenium para simular navegador real y evitar bloqueos 403.

CORREGIDO: Ya no cambia el año de eventos pasados recientes.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
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
    'MUSICA': ['concierto', 'música', 'recital', 'banda', 'orquesta', 'coral', 'canto'],
    'TEATRO': ['teatro', 'obra', 'monólogo', 'comedia', 'drama'],
    'INFANTIL': ['infantil', 'niños', 'familia', 'cuentacuentos', 'futbolísimos'],
    'DANZA': ['danza', 'ballet', 'flamenco', 'durmiente'],
    'HUMOR': ['humor', 'monólogo', 'cómico', 'stand up', 'bingueros'],
    'CULTURA': ['conferencia', 'charla', 'presentación', 'navidad', 'festival']
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
    """
    Parsea una fecha en español y determina el año correcto.
    
    LÓGICA CORREGIDA:
    - Si la fecha es de los próximos 6 meses -> año actual o siguiente
    - Si la fecha ya pasó hace más de 30 días -> es del año pasado (no lo incluimos)
    - Si la fecha pasó hace menos de 30 días -> es del año actual (evento reciente)
    """
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
            hoy = datetime.now()
            anio_actual = hoy.year
            
            try:
                # Intentar con el año actual
                fecha_candidata = datetime(anio_actual, mes, dia)
                
                # Calcular diferencia en días
                diferencia_dias = (fecha_candidata - hoy).days
                
                # LÓGICA MEJORADA:
                if diferencia_dias >= -30:
                    # El evento es de hace menos de 30 días o es futuro
                    # Usar el año actual
                    return fecha_candidata.strftime('%Y-%m-%d')
                elif diferencia_dias < -30 and diferencia_dias > -180:
                    # Evento de hace más de 30 días pero menos de 6 meses
                    # Probablemente es un evento pasado, mantener año actual
                    return fecha_candidata.strftime('%Y-%m-%d')
                else:
                    # Diferencia muy grande negativa (más de 6 meses atrás)
                    # Podría ser del año siguiente
                    fecha_siguiente = datetime(anio_actual + 1, mes, dia)
                    return fecha_siguiente.strftime('%Y-%m-%d')
                    
            except ValueError:
                # Fecha inválida (ej: 31 de febrero)
                pass
    
    return None

def extraer_año_del_texto(texto):
    """
    Intenta extraer el año directamente del texto si está presente.
    Ej: "26 de diciembre de 2025" -> 2025
    """
    patron_año = r'20\d{2}'
    match = re.search(patron_año, texto)
    if match:
        return int(match.group())
    return None

def parsear_fecha_completa(texto_fecha):
    """
    Versión mejorada que primero busca el año en el texto.
    """
    # Primero intentar extraer el año directamente
    año_explicito = extraer_año_del_texto(texto_fecha)
    
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
            # Si encontramos año explícito, usarlo
            if año_explicito:
                try:
                    fecha = datetime(año_explicito, mes, dia)
                    return fecha.strftime('%Y-%m-%d')
                except ValueError:
                    pass
            
            # Si no hay año explícito, usar lógica inteligente
            return parsear_fecha_es(texto_fecha)
    
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
            
            # Fecha - USAR LA NUEVA FUNCIÓN
            fecha_elem = card.find('time') or card.find(class_=re.compile(r'fecha|date', re.I))
            fecha_iso = None
            
            if fecha_elem:
                fecha_texto = fecha_elem.get('datetime', fecha_elem.get_text(strip=True))
                fecha_iso = parsear_fecha_completa(fecha_texto)
            
            if not fecha_iso:
                texto_completo = card.get_text()
                fecha_iso = parsear_fecha_completa(texto_completo)
            
            if not fecha_iso:
                # Si no podemos parsear la fecha, usar hoy como fallback
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
# FILTRADO DE EVENTOS
# ======================================================================

def filtrar_eventos_validos(eventos):
    """
    Filtra eventos para mostrar solo los relevantes:
    - Eventos futuros (próximos 6 meses)
    - Eventos pasados de hace máximo 7 días (por si alguien quiere ver qué se perdió)
    """
    hoy = datetime.now()
    limite_pasado = hoy - timedelta(days=7)  # Hasta 7 días atrás
    limite_futuro = hoy + timedelta(days=180)  # Hasta 6 meses adelante
    
    eventos_filtrados = []
    
    for evento in eventos:
        try:
            fecha_evento = datetime.strptime(evento['fecha'], '%Y-%m-%d')
            
            if limite_pasado <= fecha_evento <= limite_futuro:
                eventos_filtrados.append(evento)
            else:
                print(f"   ⏭️ Evento filtrado (fuera de rango): {evento['titulo'][:40]} - {evento['fecha']}")
                
        except ValueError:
            # Si no podemos parsear la fecha, incluir el evento por si acaso
            eventos_filtrados.append(evento)
    
    return eventos_filtrados

# ======================================================================
# MAIN
# ======================================================================

def main():
    print("="*70)
    print("EXTRACTOR CON SELENIUM - GITHUB ACTIONS")
    print(f"Fecha actual: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)
    print()
    
    todos_eventos = []
    
    for teatro, url in TOMATICKET_URLS.items():
        eventos = extraer_con_selenium(url, teatro)
        todos_eventos.extend(eventos)
    
    # Filtrar eventos válidos (quitar los de fechas muy antiguas o muy futuras)
    print("\n🔍 Filtrando eventos por fecha...")
    eventos_validos = filtrar_eventos_validos(todos_eventos)
    
    # Ordenar por fecha
    eventos_ordenados = sorted(eventos_validos, key=lambda x: x['fecha'])
    
    # Guardar JSON
    with open('eventos_agenda.json', 'w', encoding='utf-8') as f:
        json.dump(eventos_ordenados, f, ensure_ascii=False, indent=2)
    
    # Estadísticas
    print()
    print("="*70)
    print("✅ COMPLETADO")
    print(f"📊 Total eventos extraídos: {len(todos_eventos)}")
    print(f"📊 Eventos válidos (después de filtrar): {len(eventos_ordenados)}")
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
