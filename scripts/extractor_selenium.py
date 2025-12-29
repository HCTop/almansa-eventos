#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
EXTRACTOR DE EVENTOS TOMATICKET - v4.0
=======================================
Extrae eventos de TomaTicket para los teatros de Almansa.
CORREGIDO: Parsea correctamente las fechas (día, número, mes).
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

# Mapeo de meses en español a número
MESES_ES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
    'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
    'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

# Categorías por palabras clave
CATEGORIAS = {
    'MUSICA': ['concierto', 'música', 'recital', 'banda', 'orquesta', 'canto', 'coral'],
    'TEATRO': ['teatro', 'obra', 'monólogo', 'comedia', 'drama'],
    'INFANTIL': ['infantil', 'niños', 'familia', 'cuentacuentos', 'kids'],
    'DANZA': ['danza', 'ballet', 'flamenco', 'baile', 'durmiente'],
    'HUMOR': ['humor', 'monólogo', 'cómico', 'stand up', 'risa', 'cura'],
    'CINE': ['cine', 'película', 'film'],
    'CULTURA': ['conferencia', 'charla', 'presentación', 'festival', 'gala']
}

# ======================================================================
# FILTRO DE UBICACIÓN - Solo eventos de Almansa
# ======================================================================

# Ciudades que NO son Almansa (descartamos eventos de estas)
CIUDADES_EXCLUIDAS = [
    'jaén', 'jaen', 'murcia', 'valencia', 'madrid', 'barcelona',
    'alicante', 'cuenca', 'toledo', 'ciudad real', 'guadalajara',
    'villanueva', 'hellín', 'hellin', 'la roda', 'villarrobledo'
]

def es_evento_almansa(titulo, teatro_nombre):
    """
    Verifica si el evento es realmente de Almansa.
    
    IMPORTANTE: Los teatros de Almansa (Teatro Regio y Teatro Principal)
    están en la PROVINCIA de Albacete, por eso TomaTicket pone "en ALBACETE"
    en muchos títulos. Pero SI el teatro es de Almansa, el evento ES de Almansa.
    """
    titulo_lower = titulo.lower()
    
    # Si menciona explícitamente otra ciudad (no Albacete), descartar
    for ciudad in CIUDADES_EXCLUIDAS:
        if ciudad in titulo_lower:
            print(f"      🔍 Detectada ciudad excluida: {ciudad}")
            return False
    
    # Si el título dice "en JAÉN", "en MURCIA", etc. (mayúsculas = nombre de ciudad)
    match = re.search(r'\ben\s+([A-ZÁÉÍÓÚÑ]{3,})\b', titulo)
    if match:
        ciudad_mencionada = match.group(1).lower()
        # Lista de ciudades a excluir cuando aparecen así
        ciudades_patron = ['jaen', 'jaén', 'murcia', 'valencia', 'madrid', 
                          'toledo', 'cuenca', 'alicante', 'barcelona']
        if ciudad_mencionada in ciudades_patron:
            print(f"      🔍 Detectado patrón 'en {ciudad_mencionada.upper()}'")
            return False
    
    # "en ALBACETE" está OK porque los teatros de Almansa están en provincia de Albacete
    # El evento es válido si llegó hasta aquí
    return True

# ======================================================================
# UTILIDADES
# ======================================================================

def generar_id(titulo, fecha, lugar):
    """Genera un ID único para el evento."""
    texto = f"{titulo}{fecha}{lugar}".lower().strip()
    return "evt_" + hashlib.md5(texto.encode()).hexdigest()[:12]

def limpiar_titulo(titulo):
    """
    Limpia el título quitando basura como 'en 21', 'en 22', etc.
    que TomaTicket añade al final de algunos títulos.
    """
    # Quitar patrones como "en 21", "en 22", "en ALBACETE" del final
    titulo_limpio = re.sub(r'\s+en\s+\d+\s*$', '', titulo, flags=re.IGNORECASE)
    titulo_limpio = re.sub(r'\s+en\s+21\s*$', '', titulo_limpio, flags=re.IGNORECASE)
    
    # Limpiar espacios extra
    titulo_limpio = ' '.join(titulo_limpio.split())
    
    return titulo_limpio.strip()

def determinar_categoria(titulo):
    """Determina la categoría basándose en el título."""
    texto = titulo.lower()
    for categoria, keywords in CATEGORIAS.items():
        if any(kw in texto for kw in keywords):
            return categoria
    return "CULTURA"

def parsear_fecha_tomaticket(dia_semana, dia_num, mes_texto):
    """
    Parsea la fecha desde los elementos de TomaTicket.
    
    Args:
        dia_semana: "Domingo", "Sábado", etc.
        dia_num: "28", "03", etc.
        mes_texto: "Diciembre", "Enero", etc.
    
    Returns:
        Fecha en formato "YYYY-MM-DD" o None si falla.
    """
    try:
        # Limpiar y convertir
        dia = int(dia_num.strip())
        mes_lower = mes_texto.strip().lower()
        
        if mes_lower not in MESES_ES:
            print(f"      ⚠️ Mes no reconocido: {mes_texto}")
            return None
        
        mes = MESES_ES[mes_lower]
        
        # Determinar el año
        hoy = datetime.now()
        anio_actual = hoy.year
        
        # Crear fecha candidata con año actual
        try:
            fecha_candidata = datetime(anio_actual, mes, dia)
        except ValueError:
            # Día inválido para ese mes
            return None
        
        # Si la fecha es más de 2 meses en el pasado, probablemente es del año siguiente
        diferencia_dias = (fecha_candidata - hoy).days
        
        if diferencia_dias < -60:
            # Más de 2 meses en el pasado -> año siguiente
            fecha_candidata = datetime(anio_actual + 1, mes, dia)
        
        return fecha_candidata.strftime('%Y-%m-%d')
        
    except Exception as e:
        print(f"      ❌ Error parseando fecha: {e}")
        return None

def extraer_precio(card):
    """Extrae el precio del evento."""
    # Buscar "Desde X €"
    texto = card.get_text()
    match = re.search(r'Desde\s*(\d+)\s*€', texto)
    if match:
        return f"Desde {match.group(1)} €"
    
    # Buscar solo "X €"
    match = re.search(r'(\d+)\s*€', texto)
    if match:
        return f"{match.group(1)} €"
    
    return "Ver en taquilla"

# ======================================================================
# SELENIUM
# ======================================================================

def crear_driver():
    """Crea instancia de Chrome con Selenium."""
    print("🔧 Configurando Chrome Selenium...")
    
    chrome_options = Options()
    
    # Modo headless
    chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    
    # Anti-detección
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # User agent
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    chrome_options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def extraer_eventos_tomaticket(url, teatro_nombre):
    """
    Extrae eventos de una página de TomaTicket.
    SOLO extrae eventos de la sección "Próximos eventos".
    """
    print(f"\n🎭 Extrayendo {teatro_nombre}...")
    print(f"   URL: {url}")
    
    eventos = []
    driver = None
    
    try:
        driver = crear_driver()
        
        print("   📥 Cargando página...")
        driver.get(url)
        
        # Esperar carga
        print("   ⏳ Esperando contenido...")
        time.sleep(5)
        
        # Obtener HTML
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # =====================================================================
        # BUSCAR SECCIÓN "PRÓXIMOS EVENTOS"
        # =====================================================================
        
        # Buscar el h2 que dice "Próximos eventos"
        seccion_proximos = None
        for h2 in soup.find_all('h2'):
            if 'próximos' in h2.get_text().lower():
                seccion_proximos = h2.find_parent(['section', 'div'])
                break
        
        if not seccion_proximos:
            # Fallback: buscar todos los enlaces de eventos
            print("   ⚠️ No encontré sección 'Próximos eventos', buscando en toda la página...")
            seccion_proximos = soup
        
        # Buscar tarjetas de eventos (enlaces que contienen la info)
        # TomaTicket usa enlaces con estructura: título, día semana, día número, mes
        eventos_links = seccion_proximos.find_all('a', href=re.compile(r'/es-es/entradas-'))
        
        print(f"   📋 Encontrados {len(eventos_links)} enlaces de eventos")
        
        for link in eventos_links:
            try:
                # Extraer título (h4 dentro del enlace)
                titulo_elem = link.find(['h4', 'h3', 'h2'])
                if not titulo_elem:
                    continue
                
                titulo = titulo_elem.get_text(strip=True)
                
                # Filtrar títulos no válidos
                if len(titulo) < 5:
                    continue
                
                # =========================================================
                # EXTRAER FECHA (día semana, día número, mes)
                # =========================================================
                
                # Buscar todos los textos dentro del enlace
                textos = [t.strip() for t in link.stripped_strings]
                
                # La estructura típica es:
                # [título, día_semana, día_num, mes, "Desde", precio, "€"]
                
                dia_semana = None
                dia_num = None
                mes_texto = None
                
                dias_semana = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
                
                for i, texto in enumerate(textos):
                    texto_lower = texto.lower()
                    
                    # Buscar día de la semana
                    if texto_lower in dias_semana:
                        dia_semana = texto
                        # El siguiente debería ser el número del día
                        if i + 1 < len(textos) and textos[i + 1].isdigit():
                            dia_num = textos[i + 1]
                        # El siguiente después debería ser el mes
                        if i + 2 < len(textos) and textos[i + 2].lower() in MESES_ES:
                            mes_texto = textos[i + 2]
                        break
                
                # Si no encontró con el método anterior, buscar directamente
                if not dia_num or not mes_texto:
                    for i, texto in enumerate(textos):
                        if texto.isdigit() and 1 <= int(texto) <= 31:
                            dia_num = texto
                            # El siguiente podría ser el mes
                            if i + 1 < len(textos) and textos[i + 1].lower() in MESES_ES:
                                mes_texto = textos[i + 1]
                            break
                
                # Parsear fecha
                fecha_iso = None
                if dia_num and mes_texto:
                    fecha_iso = parsear_fecha_tomaticket(dia_semana or "", dia_num, mes_texto)
                
                if not fecha_iso:
                    print(f"   ⚠️ Sin fecha válida para: {titulo[:40]}...")
                    print(f"      Textos encontrados: {textos[:8]}")
                    continue
                
                # =========================================================
                # EXTRAER OTROS DATOS
                # =========================================================
                
                # URL del evento
                url_evento = link.get('href', '')
                if url_evento and not url_evento.startswith('http'):
                    url_evento = 'https://www.tomaticket.es' + url_evento
                
                # Precio
                precio = extraer_precio(link)
                
                # Verificar si es evento pasado (ignorar)
                hoy = datetime.now().strftime('%Y-%m-%d')
                if fecha_iso < hoy:
                    print(f"   ⏭️ Ignorando evento pasado: {titulo[:40]} ({fecha_iso})")
                    continue
                
                # Verificar si es evento de Almansa (filtrar otras ciudades)
                if not es_evento_almansa(titulo, teatro_nombre):
                    print(f"   🚫 Ignorando (no es de Almansa): {titulo[:40]}")
                    continue
                
                # Limpiar el título (quitar "en 21" y basura similar)
                titulo_limpio = limpiar_titulo(titulo)
                
                print(f"   ✅ {titulo_limpio[:50]}")
                print(f"      📅 {fecha_iso} | 💰 {precio}")
                
                eventos.append({
                    'id': generar_id(titulo_limpio, fecha_iso, teatro_nombre),
                    'titulo': titulo_limpio,
                    'descripcion': f"{dia_semana or ''} - {teatro_nombre}".strip(' -'),
                    'fecha': fecha_iso,
                    'hora': "20:00",  # Hora por defecto
                    'lugar': teatro_nombre,
                    'categoria': determinar_categoria(titulo_limpio),
                    'precio': precio,
                    'urlCompra': url_evento or url,
                    'esGratuito': False,
                    'fuente': "TomaTicket"
                })
                
            except Exception as e:
                print(f"   ❌ Error procesando evento: {e}")
                continue
        
    except Exception as e:
        print(f"   ❌ Error general: {str(e)}")
    
    finally:
        if driver:
            driver.quit()
    
    print(f"   📊 Total extraídos: {len(eventos)}")
    return eventos

# ======================================================================
# MAIN
# ======================================================================

def main():
    print("=" * 70)
    print("EXTRACTOR DE EVENTOS TOMATICKET - v4.0")
    print("=" * 70)
    print(f"Fecha de ejecución: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    
    todos_eventos = []
    
    for teatro, url in TOMATICKET_URLS.items():
        eventos = extraer_eventos_tomaticket(url, teatro)
        todos_eventos.extend(eventos)
    
    # Eliminar duplicados por ID
    eventos_unicos = {e['id']: e for e in todos_eventos}
    eventos_lista = list(eventos_unicos.values())
    
    # Ordenar por fecha
    eventos_ordenados = sorted(eventos_lista, key=lambda x: x['fecha'])
    
    # Guardar JSON
    with open('eventos_agenda.json', 'w', encoding='utf-8') as f:
        json.dump(eventos_ordenados, f, ensure_ascii=False, indent=2)
    
    # Estadísticas
    print()
    print("=" * 70)
    print("✅ COMPLETADO")
    print(f"📊 Total eventos únicos: {len(eventos_ordenados)}")
    print(f"📁 Archivo: eventos_agenda.json")
    
    if eventos_ordenados:
        print()
        print("📋 PRÓXIMOS EVENTOS:")
        for i, e in enumerate(eventos_ordenados[:10], 1):
            print(f"  {i}. {e['titulo'][:50]}")
            print(f"     📅 {e['fecha']} | 📍 {e['lugar']} | 💰 {e['precio']}")
    else:
        print()
        print("⚠️ No se encontraron eventos futuros")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
