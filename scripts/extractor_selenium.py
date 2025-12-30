#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EXTRACTOR DE EVENTOS → GOOGLE SHEETS
=====================================
Extrae eventos de TomaTicket y los escribe directamente en Google Sheets.
La app Android lee el CSV público de ese Sheet.
"""

import gspread
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime
import re
import hashlib
import time
import json
import os

# ======================================================================
# CONFIGURACIÓN
# ======================================================================

# ID del Google Sheet (de la URL)
SHEET_ID = "1Rp5I6vuVnRCcyv3fEfvhAz_dMheQ6-tMlobpSLKNEcE"

# Nombre de la hoja dentro del Sheet
NOMBRE_HOJA = "Hoja 1"  # Cambia si tu hoja se llama diferente

# URLs de TomaTicket
TOMATICKET_URLS = {
    "Teatro Regio": "https://www.tomaticket.es/es-es/recintos/teatro-regio-almansa",
    "Teatro Principal": "https://www.tomaticket.es/es-es/recintos/teatro-principal-almansa"
}

# Categorías
CATEGORIAS = {
    'MUSICA': ['concierto', 'música', 'recital', 'banda', 'orquesta', 'coral'],
    'TEATRO': ['teatro', 'obra', 'comedia', 'drama'],
    'INFANTIL': ['infantil', 'niños', 'familia', 'cuentacuentos', 'animación'],
    'DANZA': ['danza', 'ballet', 'flamenco', 'baile'],
    'HUMOR': ['humor', 'monólogo', 'cómico', 'stand up', 'comedia'],
    'CINE': ['cine', 'película', 'proyección'],
    'CULTURA': ['conferencia', 'charla', 'presentación', 'exposición']
}

# Columnas del Sheet
COLUMNAS = ['id', 'titulo', 'descripcion', 'fecha', 'hora', 'lugar', 'categoria', 'precio', 'urlCompra', 'esGratuito', 'fuente', 'activo']

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

def limpiar_titulo(titulo):
    """Limpia títulos quitando sufijos de ciudad"""
    patrones = [
        r'\s+en\s+(ALBACETE|JAÉN|MURCIA|VALENCIA|ALICANTE|MADRID).*$',
        r'\s+en\s+\d+$',
        r'\s+-\s+[A-Z][a-z]+\s+de\s+[A-Z].*$'
    ]
    resultado = titulo
    for patron in patrones:
        resultado = re.sub(patron, '', resultado, flags=re.IGNORECASE)
    return resultado.strip()

def parsear_fecha_es(texto_fecha):
    """Parsea fechas en español"""
    meses_es = {
        'ene': 1, 'enero': 1, 'feb': 2, 'febrero': 2,
        'mar': 3, 'marzo': 3, 'abr': 4, 'abril': 4,
        'may': 5, 'mayo': 5, 'jun': 6, 'junio': 6,
        'jul': 7, 'julio': 7, 'ago': 8, 'agosto': 8,
        'sep': 9, 'septiembre': 9, 'sept': 9,
        'oct': 10, 'octubre': 10, 'nov': 11, 'noviembre': 11,
        'dic': 12, 'diciembre': 12
    }

    texto = texto_fecha.lower().strip()

    # Patrón: "26 dic", "26 de diciembre", "26/12"
    patron = r'(\d{1,2})[/\s\-]+(?:de\s+)?(\w+)'
    match = re.search(patron, texto)

    if match:
        dia = int(match.group(1))
        mes_texto = match.group(2)

        # Buscar mes
        mes = None
        for clave, valor in meses_es.items():
            if clave in mes_texto or mes_texto.startswith(clave):
                mes = valor
                break

        # Si es número
        if mes is None and mes_texto.isdigit():
            mes = int(mes_texto)

        if mes and 1 <= dia <= 31:
            anio = datetime.now().year
            try:
                fecha = datetime(anio, mes, dia)
                # Si la fecha ya pasó, es del año siguiente
                if fecha < datetime.now():
                    fecha = datetime(anio + 1, mes, dia)
                return fecha.strftime('%Y-%m-%d')
            except ValueError:
                pass

    return None

# ======================================================================
# GOOGLE SHEETS
# ======================================================================

def conectar_sheets():
    """Conecta con Google Sheets usando credenciales"""
    print("📊 Conectando con Google Sheets...")

    # Scopes necesarios
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    # Cargar credenciales desde variable de entorno o archivo
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')

    if creds_json:
        # Desde variable de entorno (GitHub Actions)
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        # Desde archivo local (para pruebas)
        creds = Credentials.from_service_account_file('credenciales.json', scopes=scopes)

    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID)
    hoja = sheet.worksheet(NOMBRE_HOJA)

    print("✅ Conectado a Google Sheets")
    return hoja

def obtener_eventos_existentes(hoja):
    """Obtiene los eventos que ya están en el Sheet"""
    try:
        registros = hoja.get_all_records()
        return {r['id']: r for r in registros if r.get('id')}
    except:
        return {}

def escribir_eventos(hoja, eventos_nuevos, eventos_existentes):
    """Escribe eventos en el Sheet, respetando los manuales"""
    print(f"📝 Procesando {len(eventos_nuevos)} eventos...")

    # IDs de eventos que el usuario marcó como activo=FALSE (no tocar)
    ids_desactivados = {id for id, e in eventos_existentes.items() 
                        if str(e.get('activo', 'TRUE')).upper() == 'FALSE'}

    # Preparar datos finales
    eventos_finales = []

    # 1. Mantener eventos existentes modificados manualmente
    for id_evento, evento in eventos_existentes.items():
        if id_evento in ids_desactivados:
            # Mantener desactivados tal cual
            eventos_finales.append(evento)

    # 2. Añadir/actualizar eventos nuevos
    for evento in eventos_nuevos:
        if evento['id'] not in ids_desactivados:
            eventos_finales.append(evento)

    # Ordenar por fecha
    eventos_finales.sort(key=lambda x: x.get('fecha', '9999-99-99'))

    # Limpiar y escribir
    print(f"📤 Escribiendo {len(eventos_finales)} eventos en el Sheet...")

    # Cabeceras
    hoja.clear()
    hoja.append_row(COLUMNAS)

    # Datos
    for evento in eventos_finales:
        fila = [
            evento.get('id', ''),
            evento.get('titulo', ''),
            evento.get('descripcion', ''),
            evento.get('fecha', ''),
            evento.get('hora', ''),
            evento.get('lugar', ''),
            evento.get('categoria', ''),
            evento.get('precio', ''),
            evento.get('urlCompra', ''),
            str(evento.get('esGratuito', False)).upper(),
            evento.get('fuente', ''),
            str(evento.get('activo', True)).upper()
        ]
        hoja.append_row(fila)

    print(f"✅ {len(eventos_finales)} eventos escritos")

# ======================================================================
# SELENIUM - EXTRACCIÓN
# ======================================================================

def crear_driver():
    """Crea instancia de Chrome con Selenium"""
    chrome_options = Options()
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    chrome_options.add_argument('--window-size=1920,1080')

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def extraer_eventos_tomaticket(url, teatro_nombre):
    """Extrae eventos de una página de TomaTicket"""
    print(f"\n🎭 Extrayendo {teatro_nombre}...")
    eventos = []
    driver = None

    try:
        driver = crear_driver()
        driver.get(url)
        time.sleep(5)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )
        except:
            pass

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # Buscar tarjetas de eventos
        cards = soup.find_all(['article', 'div'], class_=re.compile(r'event|card', re.I))

        for card in cards:
            # Título
            titulo_elem = card.find(['h1', 'h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|titulo|name', re.I))
            if not titulo_elem:
                titulo_elem = card.find(['h1', 'h2', 'h3', 'h4', 'a'])

            if not titulo_elem:
                continue

            titulo_raw = titulo_elem.get_text(strip=True)
            if len(titulo_raw) < 5:
                continue

            titulo = limpiar_titulo(titulo_raw)

            # Fecha
            fecha_elem = card.find('time') or card.find(class_=re.compile(r'fecha|date', re.I))
            fecha_iso = None

            if fecha_elem:
                fecha_texto = fecha_elem.get('datetime', fecha_elem.get_text(strip=True))
                fecha_iso = parsear_fecha_es(fecha_texto)

            if not fecha_iso:
                fecha_iso = parsear_fecha_es(card.get_text())

            if not fecha_iso:
                continue  # Sin fecha válida, saltar

            # Hora
            hora = "20:00"
            hora_elem = card.find(class_=re.compile(r'hora|time', re.I))
            if hora_elem:
                match_hora = re.search(r'(\d{1,2}):(\d{2})', hora_elem.get_text())
                if match_hora:
                    hora = match_hora.group(0)

            # URL
            link_elem = card.find('a', href=True)
            link = url
            if link_elem and link_elem.get('href'):
                href = link_elem['href']
                if href.startswith('http'):
                    link = href
                elif href.startswith('/'):
                    link = 'https://www.tomaticket.es' + href

            # Descripción
            desc_elem = card.find('p')
            descripcion = desc_elem.get_text(strip=True)[:200] if desc_elem else ""

            evento = {
                'id': generar_id(titulo, fecha_iso, teatro_nombre),
                'titulo': titulo,
                'descripcion': descripcion,
                'fecha': fecha_iso,
                'hora': hora,
                'lugar': teatro_nombre,
                'categoria': determinar_categoria(titulo),
                'precio': "Ver en taquilla",
                'urlCompra': link,
                'esGratuito': False,
                'fuente': "TomaTicket",
                'activo': True
            }

            eventos.append(evento)
            print(f"   ✅ {titulo[:50]}... ({fecha_iso})")

    except Exception as e:
        print(f"   ❌ Error: {e}")

    finally:
        if driver:
            driver.quit()

    return eventos

# ======================================================================
# MAIN
# ======================================================================

def main():
    print("=" * 60)
    print("🎭 EXTRACTOR DE EVENTOS → GOOGLE SHEETS")
    print("=" * 60)

    # 1. Conectar con Sheets
    hoja = conectar_sheets()

    # 2. Obtener eventos existentes (para respetar cambios manuales)
    eventos_existentes = obtener_eventos_existentes(hoja)
    print(f"📋 Eventos existentes en Sheet: {len(eventos_existentes)}")

    # 3. Extraer eventos nuevos de TomaTicket
    eventos_nuevos = []
    for teatro, url in TOMATICKET_URLS.items():
        eventos = extraer_eventos_tomaticket(url, teatro)
        eventos_nuevos.extend(eventos)

    print(f"\n📦 Total extraídos: {len(eventos_nuevos)}")

    # 4. Escribir en Sheets
    escribir_eventos(hoja, eventos_nuevos, eventos_existentes)

    # 5. Resumen
    print("\n" + "=" * 60)
    print("✅ COMPLETADO")
    print(f"📊 Eventos en Google Sheets: {len(eventos_nuevos)}")
    print("=" * 60)

if __name__ == "__main__":
    main()
