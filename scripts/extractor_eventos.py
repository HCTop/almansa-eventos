#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para extraer eventos de Almansa desde múltiples fuentes.
Genera un archivo JSON listo para consumir desde GitHub Pages.

ESTRATEGIA ANTI-BLOQUEO:
1. Intentar con requests + BeautifulSoup (más rápido, menos detectable)
2. Si falla, usar Selenium con configuración anti-detección
"""

import json
import time
import sys
import random
from datetime import datetime
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================

URL_GIGLON = "https://www.giglon.com/todos?city=Almansa"
URL_LA_TINTA_RSS = "https://latintadealmansa.com/feed/"
ARCHIVO_SALIDA = "eventos_agenda.json"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

CATEGORIAS = {
    "teatro": "CULTURA",
    "concierto": "MUSICA",
    "música": "MUSICA",
    "musical": "MUSICA",
    "deporte": "DEPORTE",
    "fútbol": "DEPORTE",
    "baloncesto": "DEPORTE",
    "infantil": "INFANTIL",
    "niños": "INFANTIL",
    "misa": "RELIGIOSO",
    "procesión": "RELIGIOSO",
    "fiesta": "FIESTA",
    "verbena": "FIESTA",
}

# ==============================================================================
# UTILIDADES
# ==============================================================================

def limpiar_texto(texto: str) -> str:
    """Limpia espacios en blanco y saltos de línea."""
    if not texto:
        return ""
    return " ".join(texto.strip().split())

def categorizar_evento(titulo: str, descripcion: str) -> str:
    """Determina la categoría del evento basándose en palabras clave."""
    texto_busqueda = f"{titulo} {descripcion}".lower()
    
    for palabra_clave, categoria in CATEGORIAS.items():
        if palabra_clave in texto_busqueda:
            return categoria
    
    return "CULTURA"  # Categoría por defecto

def parsear_fecha_giglon(texto_fecha: str) -> Optional[tuple]:
    """
    Convierte 'desde 26/12/2025 - Lugar' a ('2025-12-26', '26 Diciembre')
    """
    try:
        # Extraer solo la parte de la fecha
        if " - " in texto_fecha:
            fecha_parte = texto_fecha.split(" - ")[0].strip()
        else:
            fecha_parte = texto_fecha.strip()
        
        # Remover "desde" si existe
        fecha_parte = fecha_parte.replace("desde", "").strip()
        
        # Parsear formato DD/MM/YYYY
        fecha_obj = datetime.strptime(fecha_parte, "%d/%m/%Y")
        
        # Formato para JSON (YYYY-MM-DD)
        fecha_iso = fecha_obj.strftime("%Y-%m-%d")
        
        # Formato para mostrar (DD Mes)
        meses = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        fecha_mostrar = f"{fecha_obj.day} {meses[fecha_obj.month]}"
        
        return (fecha_iso, fecha_mostrar)
    except Exception as e:
        print(f"⚠️ Error parseando fecha '{texto_fecha}': {e}")
        return None

def extraer_lugar_giglon(descripcion: str) -> str:
    """
    Extrae el lugar de 'desde 26/12/2025 - Teatro Regio Almansa - Almansa(ALBACETE)'
    """
    try:
        if " - " in descripcion:
            partes = descripcion.split(" - ")
            if len(partes) >= 2:
                # Segunda parte es el lugar
                lugar = partes[1].strip()
                # Remover la parte de "(ALBACETE)" si existe
                if " - " in lugar:
                    lugar = lugar.split(" - ")[0].strip()
                return lugar
    except:
        pass
    return "Por confirmar"

# ==============================================================================
# MÉTODO 1: EXTRACTOR CON REQUESTS (MÁS RÁPIDO Y MENOS DETECTABLE)
# ==============================================================================

def extraer_eventos_giglon_requests() -> List[Dict]:
    """Extrae eventos de Giglon usando requests + BeautifulSoup."""
    print("\n🔍 Método 1: Extrayendo de GIGLON con requests...")
    eventos = []
    
    try:
        # Hacer petición con headers realistas
        print("📡 Conectando a Giglon...")
        response = requests.get(URL_GIGLON, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        print(f"✅ Respuesta recibida (código {response.status_code})")
        
        # Parsear HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Buscar tarjetas de eventos
        tarjetas = soup.select('a.event-grid')
        print(f"🎯 Encontradas {len(tarjetas)} tarjetas de eventos")
        
        if len(tarjetas) == 0:
            print("⚠️ No se encontraron eventos con el selector 'a.event-grid'")
            return []
        
        for idx, tarjeta in enumerate(tarjetas, 1):
            try:
                # Extraer datos
                titulo_elem = tarjeta.select_one('span.name-list')
                descripcion_elem = tarjeta.select_one('span.description-list')
                precio_elem = tarjeta.select_one('span.price-list')
                imagen_elem = tarjeta.select_one('img')
                
                if not titulo_elem or not descripcion_elem:
                    print(f"⚠️ Evento {idx}: Faltan datos básicos")
                    continue
                
                # Limpiar datos
                titulo = limpiar_texto(titulo_elem.get_text())
                descripcion_completa = limpiar_texto(descripcion_elem.get_text())
                precio = limpiar_texto(precio_elem.get_text()) if precio_elem else "Consultar precio"
                
                # Parsear fecha
                fecha_datos = parsear_fecha_giglon(descripcion_completa)
                if not fecha_datos:
                    print(f"⚠️ Evento {idx} '{titulo}': Fecha inválida")
                    continue
                
                fecha_iso, fecha_mostrar = fecha_datos
                
                # Extraer lugar
                lugar = extraer_lugar_giglon(descripcion_completa)
                
                # URL del evento
                href = tarjeta.get('href', '')
                url_evento = f"https://www.giglon.com{href}" if href.startswith('/') else href
                
                # Imagen
                url_imagen = ""
                if imagen_elem:
                    src = imagen_elem.get('src', '')
                    if src:
                        url_imagen = f"https://www.giglon.com{src}" if src.startswith('/') else src
                
                # Crear evento
                evento = {
                    "id": f"giglon_{idx}_{int(time.time())}",
                    "titulo": titulo,
                    "descripcion": titulo,
                    "fecha": fecha_iso,
                    "hora": "Por confirmar",
                    "lugar": lugar,
                    "precio": precio,
                    "categoria": categorizar_evento(titulo, titulo),
                    "urlEvento": url_evento,
                    "urlImagen": url_imagen
                }
                
                eventos.append(evento)
                print(f"✅ Evento {idx}: {titulo} ({fecha_mostrar})")
                
            except Exception as e:
                print(f"❌ Error procesando evento {idx}: {e}")
                continue
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
        return []
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return []
    
    print(f"\n📊 Giglon (requests): {len(eventos)} eventos extraídos")
    return eventos

# ==============================================================================
# MÉTODO 2: EXTRACTOR CON SELENIUM (FALLBACK)
# ==============================================================================

def extraer_eventos_giglon_selenium() -> List[Dict]:
    """Extrae eventos de Giglon usando Selenium (fallback)."""
    print("\n🔍 Método 2 (fallback): Extrayendo de GIGLON con Selenium...")
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError:
        print("❌ Selenium no disponible")
        return []
    
    eventos = []
    driver = None
    
    try:
        # Configurar Chrome con anti-detección
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Ocultar que somos un bot
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print("🌐 Cargando Giglon...")
        driver.get(URL_GIGLON)
        
        # Esperar más tiempo
        print("⏳ Esperando carga de eventos (20s)...")
        time.sleep(5)  # Espera inicial
        
        # Intentar esperar por los elementos
        try:
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.event-grid"))
            )
        except:
            print("⚠️ Timeout esperando eventos")
        
        # Scroll gradual (simular humano)
        print("📜 Simulando scroll...")
        for _ in range(3):
            driver.execute_script("window.scrollBy(0, 300);")
            time.sleep(random.uniform(0.5, 1.5))
        
        time.sleep(3)
        
        # Parsear con BeautifulSoup
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        tarjetas = soup.select('a.event-grid')
        
        print(f"🎯 Encontradas {len(tarjetas)} tarjetas")
        
        # Procesar eventos (mismo código que método 1)
        for idx, tarjeta in enumerate(tarjetas, 1):
            try:
                titulo_elem = tarjeta.select_one('span.name-list')
                descripcion_elem = tarjeta.select_one('span.description-list')
                precio_elem = tarjeta.select_one('span.price-list')
                imagen_elem = tarjeta.select_one('img')
                
                if not titulo_elem or not descripcion_elem:
                    continue
                
                titulo = limpiar_texto(titulo_elem.get_text())
                descripcion_completa = limpiar_texto(descripcion_elem.get_text())
                precio = limpiar_texto(precio_elem.get_text()) if precio_elem else "Consultar precio"
                
                fecha_datos = parsear_fecha_giglon(descripcion_completa)
                if not fecha_datos:
                    continue
                
                fecha_iso, fecha_mostrar = fecha_datos
                lugar = extraer_lugar_giglon(descripcion_completa)
                
                href = tarjeta.get('href', '')
                url_evento = f"https://www.giglon.com{href}" if href.startswith('/') else href
                
                url_imagen = ""
                if imagen_elem:
                    src = imagen_elem.get('src', '')
                    if src:
                        url_imagen = f"https://www.giglon.com{src}" if src.startswith('/') else src
                
                evento = {
                    "id": f"giglon_{idx}_{int(time.time())}",
                    "titulo": titulo,
                    "descripcion": titulo,
                    "fecha": fecha_iso,
                    "hora": "Por confirmar",
                    "lugar": lugar,
                    "precio": precio,
                    "categoria": categorizar_evento(titulo, titulo),
                    "urlEvento": url_evento,
                    "urlImagen": url_imagen
                }
                
                eventos.append(evento)
                print(f"✅ Evento {idx}: {titulo}")
                
            except Exception as e:
                print(f"❌ Error en evento {idx}: {e}")
                continue
        
    except Exception as e:
        print(f"❌ Error en Selenium: {e}")
    
    finally:
        if driver:
            driver.quit()
    
    print(f"\n📊 Giglon (Selenium): {len(eventos)} eventos extraídos")
    return eventos

# ==============================================================================
# FUNCIÓN PRINCIPAL DE EXTRACCIÓN DE GIGLON
# ==============================================================================

def extraer_eventos_giglon() -> List[Dict]:
    """Intenta extraer eventos con requests primero, luego Selenium."""
    
    # Método 1: Requests (más rápido)
    eventos = extraer_eventos_giglon_requests()
    
    if len(eventos) > 0:
        print("✅ Método 1 (requests) exitoso")
        return eventos
    
    # Método 2: Selenium (fallback)
    print("\n⚠️ Método 1 no encontró eventos, intentando con Selenium...")
    eventos = extraer_eventos_giglon_selenium()
    
    if len(eventos) > 0:
        print("✅ Método 2 (Selenium) exitoso")
        return eventos
    
    print("❌ Ambos métodos fallaron")
    return []

# ==============================================================================
# EXTRACTOR DE LA TINTA DE ALMANSA (RSS)
# ==============================================================================

def extraer_eventos_la_tinta() -> List[Dict]:
    """Extrae eventos del RSS de La Tinta de Almansa."""
    print("\n🔍 Extrayendo eventos de LA TINTA...")
    eventos = []
    
    try:
        response = requests.get(URL_LA_TINTA_RSS, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        print(f"✅ Encontrados {len(items)} artículos en RSS")
        
        for idx, item in enumerate(items, 1):
            try:
                titulo = item.find('title').get_text() if item.find('title') else ""
                descripcion = item.find('description').get_text() if item.find('description') else ""
                link = item.find('link').get_text() if item.find('link') else ""
                fecha_pub = item.find('pubDate').get_text() if item.find('pubDate') else ""
                
                # Filtrar solo artículos sobre eventos
                keywords_evento = ['evento', 'concierto', 'teatro', 'exposición', 'feria', 'festival']
                titulo_lower = titulo.lower()
                
                if not any(kw in titulo_lower for kw in keywords_evento):
                    continue
                
                # Parsear fecha RSS
                try:
                    fecha_obj = datetime.strptime(fecha_pub, "%a, %d %b %Y %H:%M:%S %z")
                    fecha_iso = fecha_obj.strftime("%Y-%m-%d")
                    
                    meses = {
                        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
                        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
                        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
                    }
                    fecha_mostrar = f"{fecha_obj.day} {meses[fecha_obj.month]}"
                except:
                    fecha_iso = datetime.now().strftime("%Y-%m-%d")
                    fecha_mostrar = "Por confirmar"
                
                # Limpiar descripción
                descripcion_limpia = BeautifulSoup(descripcion, 'html.parser').get_text()
                descripcion_corta = descripcion_limpia[:200] + "..." if len(descripcion_limpia) > 200 else descripcion_limpia
                
                evento = {
                    "id": f"latinta_{idx}_{int(time.time())}",
                    "titulo": limpiar_texto(titulo),
                    "descripcion": limpiar_texto(descripcion_corta),
                    "fecha": fecha_iso,
                    "hora": "Por confirmar",
                    "lugar": "Almansa",
                    "precio": "Consultar",
                    "categoria": categorizar_evento(titulo, descripcion_limpia),
                    "urlEvento": link,
                    "urlImagen": ""
                }
                
                eventos.append(evento)
                print(f"✅ Evento {idx}: {titulo}")
                
            except Exception as e:
                print(f"❌ Error procesando item {idx}: {e}")
                continue
        
    except Exception as e:
        print(f"❌ Error en La Tinta: {e}")
    
    print(f"\n📊 La Tinta: {len(eventos)} eventos extraídos")
    return eventos

# ==============================================================================
# CONSOLIDACIÓN Y GUARDADO
# ==============================================================================

def consolidar_eventos(eventos_giglon: List[Dict], eventos_la_tinta: List[Dict]) -> List[Dict]:
    """Consolida eventos de múltiples fuentes eliminando duplicados."""
    print("\n🔄 Consolidando eventos...")
    
    todos_eventos = eventos_giglon + eventos_la_tinta
    
    # Eliminar duplicados por título similar
    eventos_unicos = []
    titulos_vistos = set()
    
    for evento in todos_eventos:
        titulo_normalizado = evento['titulo'].lower().strip()
        
        if titulo_normalizado not in titulos_vistos:
            titulos_vistos.add(titulo_normalizado)
            eventos_unicos.append(evento)
    
    # Ordenar por fecha
    eventos_unicos.sort(key=lambda x: x['fecha'])
    
    print(f"✅ Total eventos únicos: {len(eventos_unicos)}")
    return eventos_unicos

def guardar_json(eventos: List[Dict], archivo: str):
    """Guarda los eventos en formato JSON."""
    try:
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(eventos, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Archivo guardado: {archivo}")
    except Exception as e:
        print(f"❌ Error guardando JSON: {e}")
        sys.exit(1)

# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("="*70)
    print("🎭 EXTRACTOR DE EVENTOS DE ALMANSA v2.0")
    print("="*70)
    
    # Extraer de Giglon
    eventos_giglon = extraer_eventos_giglon()
    
    # Extraer de La Tinta
    eventos_la_tinta = extraer_eventos_la_tinta()
    
    # Consolidar
    eventos_unicos = consolidar_eventos(eventos_giglon, eventos_la_tinta)
    
    # Guardar
    guardar_json(eventos_unicos, ARCHIVO_SALIDA)
    
    print("\n" + "="*70)
    print(f"✅ COMPLETADO: {len(eventos_unicos)} eventos en {ARCHIVO_SALIDA}")
    print("="*70)
    
    # Siempre salir con código 0 (éxito)
    sys.exit(0)

if __name__ == "__main__":
    main()

