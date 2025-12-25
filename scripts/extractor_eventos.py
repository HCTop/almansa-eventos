#!/usr/bin/env python3
"""
Extractor Automático de Eventos - Almansa Informa
Optimizado para GitHub Actions
"""

import json
import re
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import requests
import time
import sys

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

OUTPUT_FILE = "eventos_agenda.json"
GIGLON_ALMANSA = "https://www.giglon.com/todos?city=Almansa"
LA_TINTA_RSS = "https://latintadealmansa.com/feed/"

# ============================================================================
# EXTRACTOR GIGLON
# ============================================================================

def extraer_giglon():
    """Extrae eventos de Giglon usando Selenium headless"""
    print("🔍 Extrayendo eventos de Giglon...")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    eventos = []
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(GIGLON_ALMANSA)
        
        print("⏳ Esperando carga de eventos...")
        time.sleep(8)
        
        html = driver.page_source
        driver.quit()
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Intentar múltiples selectores
        tarjetas = (
            soup.find_all('div', class_=re.compile(r'event|evento', re.I)) or
            soup.find_all('article', class_=re.compile(r'event|evento', re.I)) or
            soup.find_all('a', href=re.compile(r'/evento/'))
        )
        
        print(f"📋 Encontradas {len(tarjetas)} posibles tarjetas")
        
        for idx, tarjeta in enumerate(tarjetas):
            try:
                # Buscar título
                titulo_elem = (
                    tarjeta.find('h1') or tarjeta.find('h2') or 
                    tarjeta.find('h3') or tarjeta.find('h4') or
                    tarjeta.find(class_=re.compile(r'title|titulo', re.I))
                )
                if not titulo_elem:
                    continue
                    
                titulo = titulo_elem.get_text(strip=True)
                
                # Filtrar elementos no deseados
                if len(titulo) < 5 or 'cookie' in titulo.lower():
                    continue
                
                # Fecha
                fecha_elem = tarjeta.find('time') or tarjeta.find(class_=re.compile(r'date|fecha', re.I))
                fecha_texto = ''
                if fecha_elem:
                    fecha_texto = fecha_elem.get('datetime', '') or fecha_elem.get_text(strip=True)
                
                fecha = parsear_fecha(fecha_texto)
                if not fecha:
                    continue
                
                # Solo eventos futuros
                if datetime.strptime(fecha, '%Y-%m-%d') < datetime.now():
                    continue
                
                # Lugar
                lugar_elem = tarjeta.find(class_=re.compile(r'venue|lugar|location', re.I))
                lugar = lugar_elem.get_text(strip=True) if lugar_elem else "Teatro Regio Almansa"
                
                # Precio
                precio_elem = tarjeta.find(class_=re.compile(r'price|precio', re.I))
                precio = precio_elem.get_text(strip=True) if precio_elem else "Consultar"
                
                # URL
                link_elem = tarjeta.find('a', href=True)
                url = link_elem['href'] if link_elem else ""
                if url and not url.startswith('http'):
                    url = f"https://www.giglon.com{url}"
                
                # Descripción
                desc_elem = tarjeta.find('p') or tarjeta.find(class_=re.compile(r'desc|description', re.I))
                descripcion = desc_elem.get_text(strip=True) if desc_elem else titulo
                descripcion = descripcion[:250]
                
                # Categoría
                categoria = detectar_categoria(titulo + " " + descripcion)
                
                # Hora
                hora = extraer_hora(fecha_texto)
                
                evento = {
                    "id": f"evt_giglon_{hash(titulo + fecha)}",
                    "titulo": titulo,
                    "descripcion": descripcion,
                    "fecha": fecha,
                    "hora": hora,
                    "lugar": lugar,
                    "categoria": categoria,
                    "precio": precio,
                    "urlCompra": url,
                    "esGratuito": 'gratis' in precio.lower() or 'gratuito' in precio.lower()
                }
                
                eventos.append(evento)
                print(f"  ✅ {titulo} - {fecha}")
                
            except Exception as e:
                print(f"  ⚠️ Error en evento {idx}: {e}")
                continue
        
    except Exception as e:
        print(f"❌ Error en Giglon: {e}")
    
    print(f"✅ Giglon: {len(eventos)} eventos\n")
    return eventos


# ============================================================================
# EXTRACTOR LA TINTA
# ============================================================================

def extraer_la_tinta():
    """Extrae eventos del RSS de La Tinta"""
    print("🔍 Extrayendo eventos de La Tinta...")
    eventos = []
    
    try:
        response = requests.get(LA_TINTA_RSS, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; AlmansaInforma/1.0)'
        })
        
        if response.status_code != 200:
            print(f"⚠️ Error HTTP {response.status_code}")
            return eventos
        
        soup = BeautifulSoup(response.content, 'xml')
        items = soup.find_all('item')
        
        for item in items[:30]:
            try:
                titulo = item.find('title').get_text(strip=True)
                descripcion = item.find('description').get_text(strip=True)
                link = item.find('link').get_text(strip=True)
                
                # Solo noticias de cultura/eventos
                if not es_evento(titulo, descripcion):
                    continue
                
                # Extraer fecha del contenido
                fecha = extraer_fecha_contenido(titulo + " " + descripcion)
                if not fecha:
                    continue
                
                # Solo futuros
                if datetime.strptime(fecha, '%Y-%m-%d') < datetime.now():
                    continue
                
                categoria = detectar_categoria(titulo + " " + descripcion)
                
                evento = {
                    "id": f"evt_latinta_{hash(titulo)}",
                    "titulo": limpiar_titulo(titulo),
                    "descripcion": limpiar_html(descripcion)[:250],
                    "fecha": fecha,
                    "hora": "Por confirmar",
                    "lugar": "Por confirmar",
                    "categoria": categoria,
                    "precio": "Consultar",
                    "urlCompra": link,
                    "esGratuito": False
                }
                
                eventos.append(evento)
                print(f"  ✅ {titulo} - {fecha}")
                
            except Exception as e:
                continue
        
    except Exception as e:
        print(f"❌ Error en La Tinta: {e}")
    
    print(f"✅ La Tinta: {len(eventos)} eventos\n")
    return eventos


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def parsear_fecha(texto):
    """Convierte texto de fecha a formato YYYY-MM-DD"""
    if not texto:
        return None
    
    # Formato DD/MM/YYYY
    match = re.search(r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})', texto)
    if match:
        dia, mes, anio = match.groups()
        return f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"
    
    # Formato YYYY-MM-DD
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', texto)
    if match:
        return match.group(0)
    
    return None


def extraer_hora(texto):
    """Extrae hora HH:MM del texto"""
    if not texto:
        return "Por confirmar"
    match = re.search(r'(\d{1,2}):(\d{2})', texto)
    return match.group(0) if match else "Por confirmar"


def extraer_fecha_contenido(texto):
    """Extrae fecha de texto en lenguaje natural"""
    meses = {
        'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
        'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
        'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
    }
    
    texto_lower = texto.lower()
    
    # Patrón: "19 de diciembre"
    for mes_nombre, mes_num in meses.items():
        pattern = rf'(\d{1,2})\s+de\s+{mes_nombre}'
        match = re.search(pattern, texto_lower)
        if match:
            dia = match.group(1).zfill(2)
            anio = datetime.now().year
            fecha = f"{anio}-{mes_num}-{dia}"
            
            # Si ya pasó, usar año siguiente
            if datetime.strptime(fecha, '%Y-%m-%d') < datetime.now():
                anio += 1
                fecha = f"{anio}-{mes_num}-{dia}"
            
            return fecha
    
    return None


def es_evento(titulo, descripcion):
    """Determina si la noticia es sobre un evento"""
    keywords = [
        'programa', 'eventos', 'concierto', 'teatro', 'festival',
        'feria', 'fiestas', 'actuación', 'espectáculo', 'exposición',
        'taller', 'charla', 'jornada', 'encuentro', 'celebra'
    ]
    texto = (titulo + " " + descripcion).lower()
    return any(kw in texto for kw in keywords)


def detectar_categoria(texto):
    """Detecta categoría por palabras clave"""
    texto_lower = texto.lower()
    
    if any(kw in texto_lower for kw in ['concierto', 'música', 'coral', 'orquesta']):
        return 'MUSICA'
    if any(kw in texto_lower for kw in ['infantil', 'niños', 'niñas', 'familia']):
        return 'INFANTIL'
    if any(kw in texto_lower for kw in ['deporte', 'carrera', 'atletismo', 'fútbol']):
        return 'DEPORTE'
    if any(kw in texto_lower for kw in ['feria', 'fiesta', 'batalla', 'moros']):
        return 'FIESTA'
    
    return 'CULTURA'


def limpiar_html(texto):
    """Elimina etiquetas HTML"""
    return re.sub(r'<[^>]+>', '', texto).strip()


def limpiar_titulo(titulo):
    """Limpia entidades HTML del título"""
    return (titulo
        .replace('&#8211;', '-')
        .replace('&#8230;', '...')
        .replace('&nbsp;', ' ')
        .strip())


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("EXTRACTOR AUTOMÁTICO - GITHUB ACTIONS")
    print("=" * 70 + "\n")
    
    # Extraer de ambas fuentes
    eventos_giglon = extraer_giglon()
    eventos_latinta = extraer_la_tinta()
    
    # Combinar
    todos_eventos = eventos_giglon + eventos_latinta
    
    # Eliminar duplicados por título similar
    eventos_unicos = []
    titulos_vistos = set()
    
    for evento in todos_eventos:
        titulo_normalizado = evento['titulo'].lower().strip()
        if titulo_normalizado not in titulos_vistos:
            eventos_unicos.append(evento)
            titulos_vistos.add(titulo_normalizado)
    
    # Ordenar por fecha
    eventos_unicos.sort(key=lambda x: x['fecha'])
    
    # Guardar JSON
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(eventos_unicos, f, ensure_ascii=False, indent=2)
    
    print("=" * 70)
    print(f"✅ COMPLETADO: {len(eventos_unicos)} eventos únicos")
    print(f"📁 Guardado en: {OUTPUT_FILE}")
    print("=" * 70)
    
    # Retornar código de salida
    sys.exit(0) 


if __name__ == "__main__":
    main()
