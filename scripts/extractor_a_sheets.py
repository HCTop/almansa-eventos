#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EXTRACTOR DE EVENTOS → GOOGLE SHEETS
=====================================
Extrae eventos de TomaTicket y los escribe en Google Sheets.
VERSIÓN CORREGIDA: Escritura fiable, fechas correctas, sin eventos pasados.
"""

import gspread
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import hashlib
import time
import json
import os

# ======================================================================
# CONFIGURACIÓN
# ======================================================================

SHEET_ID = "1Rp5I6vuVnRCcyv3fEfvhAz_dMheQ6-tMlobpSLKNEcE"
NOMBRE_HOJA = "Eventos"

TOMATICKET_URLS = {
    "Teatro Regio": "https://www.tomaticket.es/es-es/recintos/teatro-regio-almansa",
    "Teatro Principal": "https://www.tomaticket.es/es-es/recintos/teatro-principal-almansa"
}

CATEGORIAS = {
    'MUSICA': ['concierto', 'música', 'recital', 'banda', 'orquesta', 'coral'],
    'TEATRO': ['teatro', 'obra', 'comedia', 'drama'],
    'INFANTIL': ['infantil', 'niños', 'familia', 'cuentacuentos', 'animación', 'futbolísimos'],
    'DANZA': ['danza', 'ballet', 'flamenco', 'baile'],
    'HUMOR': ['humor', 'monólogo', 'cómico', 'stand up', 'monólogos'],
    'CINE': ['cine', 'película', 'proyección'],
}

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
    """Limpia títulos quitando sufijos de ciudad y 'en 21'"""
    patrones = [
        r'\s+en\s+21\s*$',
        r'\s+en\s+(ALBACETE|JAÉN|MURCIA|VALENCIA|ALICANTE|MADRID).*$',
        r'\s+-\s+[A-Z][a-z]+\s+(de|del)\s+.*$',
    ]
    resultado = titulo
    for patron in patrones:
        resultado = re.sub(patron, '', resultado, flags=re.IGNORECASE)
    return resultado.strip()

def parsear_fecha_tomaticket(dia_texto, mes_texto):
    """
    Parsea fecha de TomaTicket que viene como "03" y "Enero" por separado.
    LÓGICA: Si el mes es anterior al actual, es del año siguiente.
    """
    meses_es = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    
    try:
        dia = int(dia_texto.strip())
        mes_lower = mes_texto.lower().strip()
        mes = meses_es.get(mes_lower)
        
        if not mes:
            return None
        
        hoy = datetime.now()
        anio = hoy.year
        
        # Si el mes del evento es anterior al mes actual, es del año siguiente
        if mes < hoy.month:
            anio = hoy.year + 1
        elif mes == hoy.month and dia < hoy.day:
            anio = hoy.year + 1
            
        fecha = datetime(anio, mes, dia)
        return fecha.strftime('%Y-%m-%d')
        
    except Exception as e:
        print(f"      ⚠️ Error parseando fecha '{dia_texto} {mes_texto}': {e}")
        return None

# ======================================================================
# GOOGLE SHEETS
# ======================================================================

def conectar_sheets():
    """Conecta con Google Sheets"""
    print("📊 Conectando con Google Sheets...")
    
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    creds_json = os.environ.get('GOOGLE_CREDENTIALS')
    
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    else:
        creds = Credentials.from_service_account_file('credenciales.json', scopes=scopes)
    
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID)
    hoja = sheet.worksheet(NOMBRE_HOJA)
    
    print("✅ Conectado a Google Sheets")
    return hoja

def obtener_eventos_existentes(hoja):
    """Obtiene los eventos que ya están en el Sheet como diccionario {id: evento}"""
    try:
        todas_las_filas = hoja.get_all_values()
        
        if len(todas_las_filas) <= 1:
            return {}
        
        # Buscar la fila de cabeceras (debe tener 'id' en columna A)
        cabecera_idx = -1
        for i, fila in enumerate(todas_las_filas):
            if fila and len(fila) > 0 and fila[0] == 'id':
                cabecera_idx = i
                break
        
        if cabecera_idx == -1:
            return {}
        
        # Crear diccionario de eventos existentes
        eventos = {}
        for fila in todas_las_filas[cabecera_idx + 1:]:
            if fila and len(fila) > 0 and fila[0] and fila[0].startswith('evt_'):
                evento_id = fila[0]
                eventos[evento_id] = {
                    'id': fila[0] if len(fila) > 0 else '',
                    'titulo': fila[1] if len(fila) > 1 else '',
                    'descripcion': fila[2] if len(fila) > 2 else '',
                    'fecha': fila[3] if len(fila) > 3 else '',
                    'hora': fila[4] if len(fila) > 4 else '',
                    'lugar': fila[5] if len(fila) > 5 else '',
                    'categoria': fila[6] if len(fila) > 6 else '',
                    'precio': fila[7] if len(fila) > 7 else '',
                    'urlCompra': fila[8] if len(fila) > 8 else '',
                    'esGratuito': fila[9] if len(fila) > 9 else 'FALSE',
                    'fuente': fila[10] if len(fila) > 10 else '',
                    'activo': fila[11] if len(fila) > 11 else 'TRUE',
                }
        
        return eventos
    except Exception as e:
        print(f"⚠️ Error leyendo eventos existentes: {e}")
        return {}

def limpiar_eventos_pasados(eventos_existentes, dias_gracia=365):
    """
    Elimina eventos que ya pasaron hace más de X días.
    Mantiene eventos recientes por si alguien quiere verlos.
    
    Args:
        eventos_existentes: diccionario {id: evento}
        dias_gracia: días después del evento antes de borrarlo (default: 365)
    
    Returns:
        diccionario con solo eventos vigentes
    """
    hoy = datetime.now()
    fecha_limite = hoy - timedelta(days=dias_gracia)
    
    eventos_vigentes = {}
    eventos_eliminados = 0
    
    for evento_id, evento in eventos_existentes.items():
        fecha_str = evento.get('fecha', '')
        
        try:
            fecha_evento = datetime.strptime(fecha_str, '%Y-%m-%d')
            
            if fecha_evento < fecha_limite:
                # Evento pasado - no lo incluimos
                eventos_eliminados += 1
                print(f"   🗑️  Eliminando pasado: {evento.get('titulo', '')[:40]}... ({fecha_str})")
            else:
                # Evento vigente - lo mantenemos
                eventos_vigentes[evento_id] = evento
        except:
            # Si no puede parsear fecha, lo mantiene por seguridad
            eventos_vigentes[evento_id] = evento
    
    if eventos_eliminados > 0:
        print(f"   📋 Eliminados {eventos_eliminados} eventos pasados")
    
    return eventos_vigentes

def escribir_eventos(hoja, eventos_nuevos, eventos_existentes):
    """
    Escribe eventos en el Sheet:
    - PRIMERO limpia eventos pasados (más de 3 días)
    - Mantiene eventos existentes (incluyendo ediciones manuales)
    - Añade solo los nuevos
    - Ordena TODO por fecha
    - Cabeceras siempre en fila 1, columna A
    """
    print(f"\n📝 Procesando {len(eventos_nuevos)} eventos extraídos...")
    print(f"📊 Eventos ya en Sheet: {len(eventos_existentes)}")
    
    # PASO 1: Limpiar eventos pasados de los existentes
    #print("\n🧹 Limpiando eventos pasados...")
    #eventos_existentes = limpiar_eventos_pasados(eventos_existentes, dias_gracia=3)
    
    # Combinar: existentes + nuevos (sin duplicados)
    todos_los_eventos = dict(eventos_existentes)  # Copiar existentes
    
    nuevos_añadidos = 0
    for evento in eventos_nuevos:
        if evento['id'] not in todos_los_eventos:
            todos_los_eventos[evento['id']] = evento
            nuevos_añadidos += 1
            print(f"   ➕ Nuevo: {evento['titulo'][:45]}... ({evento['fecha']})")
        else:
            print(f"   ⏭️  Ya existe: {evento['titulo'][:40]}...")
    
    if nuevos_añadidos == 0:
        print("✅ No hay eventos nuevos que añadir")
        return
    
    # Convertir a lista y ordenar por fecha
    lista_eventos = list(todos_los_eventos.values())
    lista_eventos.sort(key=lambda x: x.get('fecha', '9999-99-99'))
    
    print(f"\n📤 Escribiendo {len(lista_eventos)} eventos ordenados por fecha...")
    
    # Preparar datos para escritura (cabeceras + eventos)
    datos = [COLUMNAS]  # Fila 1: cabeceras
    
    for evento in lista_eventos:
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
            str(evento.get('esGratuito', 'FALSE')).upper(),
            evento.get('fuente', ''),
            str(evento.get('activo', 'TRUE')).upper()
        ]
        datos.append(fila)
    
    # ESCRIBIR TODO DE UNA VEZ (batch) - Limpia y reescribe
    try:
        hoja.clear()
        hoja.update('A1', datos, value_input_option='RAW')
        print(f"✅ {nuevos_añadidos} eventos nuevos añadidos")
        print(f"📊 Total en Sheet: {len(lista_eventos)}")
    except Exception as e:
        print(f"❌ Error escribiendo: {e}")

# ======================================================================
# SELENIUM - EXTRACCIÓN
# ======================================================================

def crear_driver():
    """Crea instancia de Chrome headless"""
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
    """Extrae eventos de TomaTicket - SOLO próximos eventos, ignora los pasados"""
    print(f"\n🎭 Extrayendo {teatro_nombre}...")
    eventos = []
    driver = None
    
    try:
        driver = crear_driver()
        driver.get(url)
        time.sleep(5)
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # IMPORTANTE: Buscar SOLO la sección de "Próximos eventos"
        # y EXCLUIR "Eventos anteriormente celebrados"
        
        seccion_proximos = None
        seccion_pasados = None
        
        # Buscar todos los encabezados de sección
        for elemento in soup.find_all(['h2', 'h3']):
            texto = elemento.get_text().lower()
            
            if 'próximos' in texto or 'proximos' in texto:
                # Encontrar el contenedor padre de esta sección
                padre = elemento.find_parent(['section', 'div'])
                if padre:
                    seccion_proximos = padre
                    
            elif 'anteriormente' in texto or 'pasados' in texto or 'celebrados' in texto:
                # Marcar sección de pasados para excluirla
                padre = elemento.find_parent(['section', 'div'])
                if padre:
                    seccion_pasados = padre
        
        # Si encontramos sección de próximos, usar solo esa
        if seccion_proximos:
            contenedor = seccion_proximos
            print(f"   📍 Encontrada sección 'Próximos eventos'")
        else:
            # Si no, usar todo pero filtrar más estrictamente
            contenedor = soup
            print(f"   ⚠️  No se encontró sección específica, usando filtro por fecha")
        
        # Buscar tarjetas de eventos
        cards = contenedor.find_all(['article', 'div'], class_=re.compile(r'event|card', re.I))
        
        hoy = datetime.now()
        
        for card in cards:
            try:
                # VERIFICAR que la tarjeta NO está en sección de pasados
                if seccion_pasados:
                    # Comprobar si esta tarjeta es descendiente de la sección de pasados
                    es_pasado = False
                    for parent in card.parents:
                        if parent == seccion_pasados:
                            es_pasado = True
                            break
                    if es_pasado:
                        continue  # Saltar este evento
                
                # TÍTULO
                titulo_elem = card.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|titulo|name', re.I))
                if not titulo_elem:
                    titulo_elem = card.find(['h2', 'h3', 'h4'])
                
                if not titulo_elem:
                    continue
                
                titulo_raw = titulo_elem.get_text(strip=True)
                if len(titulo_raw) < 5:
                    continue
                
                titulo = limpiar_titulo(titulo_raw)
                
                # FECHA - Buscar día y mes
                fecha_iso = None
                texto_card = card.get_text()
                
                # Patrón: número + mes en español
                match = re.search(r'(\d{1,2})\s*(Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre)', texto_card, re.IGNORECASE)
                if match:
                    fecha_iso = parsear_fecha_tomaticket(match.group(1), match.group(2))
                
                if not fecha_iso:
                    continue
                
                # FILTRO ADICIONAL: Si la fecha calculada está en el pasado, ignorar
                try:
                    fecha_evento = datetime.strptime(fecha_iso, '%Y-%m-%d')
                    if fecha_evento < hoy - timedelta(days=1):
                        # Este evento ya pasó - ignorar
                        continue
                except:
                    pass
                
                # PRECIO
                precio = "Ver en taquilla"
                match_precio = re.search(r'[Dd]esde\s*(\d+)\s*€', texto_card)
                if match_precio:
                    precio = f"Desde {match_precio.group(1)} €"
                
                # HORA (por defecto 20:00)
                hora = "20:00"
                
                # URL
                link_elem = card.find('a', href=True)
                link = url
                if link_elem and link_elem.get('href'):
                    href = link_elem['href']
                    if href.startswith('http'):
                        link = href
                    elif href.startswith('/'):
                        link = 'https://www.tomaticket.es' + href
                
                # Crear evento
                evento = {
                    'id': generar_id(titulo, fecha_iso, teatro_nombre),
                    'titulo': titulo,
                    'descripcion': '',
                    'fecha': fecha_iso,
                    'hora': hora,
                    'lugar': teatro_nombre,
                    'categoria': determinar_categoria(titulo),
                    'precio': precio,
                    'urlCompra': link,
                    'esGratuito': 'FALSE',
                    'fuente': 'TomaTicket',
                    'activo': 'TRUE'
                }
                
                # Evitar duplicados en la misma extracción
                if not any(e['id'] == evento['id'] for e in eventos):
                    eventos.append(evento)
                    print(f"   ✅ {titulo[:50]}... ({fecha_iso})")
                
            except Exception as e:
                continue
        
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
    
    # Conectar a Sheets
    hoja = conectar_sheets()
    
    # Obtener eventos existentes
    eventos_existentes = obtener_eventos_existentes(hoja)
    print(f"📋 Eventos existentes en Sheet: {len(eventos_existentes)}")
    
    # Extraer eventos de TomaTicket
    todos_eventos = []
    for teatro, url in TOMATICKET_URLS.items():
        eventos = extraer_eventos_tomaticket(url, teatro)
        todos_eventos.extend(eventos)
    
    print(f"\n📦 Total extraídos: {len(todos_eventos)}")
    
    # Escribir en Sheets
    if todos_eventos:
        escribir_eventos(hoja, todos_eventos, eventos_existentes)
    else:
        print("⚠️ No se encontraron eventos")
    
    print("\n" + "=" * 60)
    print("✅ COMPLETADO")
    print("=" * 60)

if __name__ == "__main__":
    main()
