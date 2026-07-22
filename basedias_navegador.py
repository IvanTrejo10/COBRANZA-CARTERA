# -*- coding: utf-8 -*-
"""
BASE DÍAS — Proceso por PÁGINA (navegador) — el script "de movimiento".

Entra a las páginas de Rapivale, Vale Amigo, Vale Amigo Perú y Viva Vale,
descarga la cartera base días del DÍA DE HOY y mueve cada archivo de
Descargas a su carpeta de OneDrive.

Se puede correr de 2 formas:
  1) Desde la página del proyecto: pestaña BASE DÍAS -> "Descarga por navegador"
     (funciona cuando la página corre en TU computadora: streamlit run app.py).
  2) Solo, como siempre:  python basedias_navegador.py

Requisitos (solo local, NO van en requirements.txt de Streamlit Cloud):
    pip install selenium webdriver-manager
"""
import os
import time
import shutil
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ------------------ CONFIGURACIÓN DE RUTAS ------------------
DOWNLOADS_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
RUTA_BASE_DESTINOS = r'C:\Users\progr\OneDrive\Documentos\Ivan\OneDrive\Nidya\Base dias'

CARPETAS_DESTINO = {
    "RAPIVALE": os.path.join(RUTA_BASE_DESTINOS, "RAPI VALE"),
    "VALE_AMIGO": os.path.join(RUTA_BASE_DESTINOS, "VALE AMIGO"),
    "VIVA_VALE": os.path.join(RUTA_BASE_DESTINOS, "VIVA VALE"),
    "VALE_AMIGO_PERU": os.path.join(RUTA_BASE_DESTINOS, "VALE AMIGO PERU")
}

# Credenciales de las PÁGINAS (mismas del script original)
USUARIO_VALE = "jorgeitl"
PASS_VALE = "Trejo907654"
USUARIO_RAPI = "Nidyarh"
PASS_RAPI = "Nidyarh2234"
USUARIO_PERU = "Nidyarh"
PASS_PERU = "Hernandez315"

# Orden original del proceso
MARCAS_NAVEGADOR = ["RAPIVALE", "VALE AMIGO", "VALE AMIGO PERU", "VIVA VALE"]


# ------------------ FUNCIÓN PARA MOVER ARCHIVOS ------------------
def mover_archivo_descargado(prefijo, carpeta_destino, log=print):
    """Busca el archivo recién descargado y lo mueve a su carpeta correspondiente."""
    if not os.path.exists(carpeta_destino):
        os.makedirs(carpeta_destino)

    for archivo in os.listdir(DOWNLOADS_FOLDER):
        if archivo.startswith(prefijo):
            ruta_origen = os.path.join(DOWNLOADS_FOLDER, archivo)
            ruta_destino = os.path.join(carpeta_destino, archivo)
            try:
                shutil.move(ruta_origen, ruta_destino)
                log(f"    ✅ Movido a {os.path.basename(carpeta_destino)}: {archivo}")
                return archivo
            except Exception as e:
                log(f"    ⚠️ Error al mover {archivo}: {e}")

    log(f"    ⚠️ No se encontró ningún archivo con el prefijo '{prefijo}' en Descargas.")
    return None


# ------------------ NAVEGADOR ------------------
def crear_driver():
    options = Options()
    options.add_argument("--start-maximized")
    prefs = {
        "download.default_directory": DOWNLOADS_FOLDER,
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


# ------------------ PROCESOS POR MARCA (misma lógica del script original) ------------------
def proceso_rapivale(driver, wait, fecha_hoy, log=print):
    log(">>> INICIANDO RAPIVALE")
    driver.get("https://system.rapivale.mx/#/auth/login")
    wait.until(EC.visibility_of_element_located((By.XPATH, "//input[@formcontrolname='username']"))).send_keys(USUARIO_RAPI)
    driver.find_element(By.XPATH, "//input[@formcontrolname='password']").send_keys(PASS_RAPI)
    driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, "//button[@type='submit']"))
    time.sleep(10)

    driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Reportes')]"))))
    time.sleep(3)
    driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'report/wallet')]"))))
    time.sleep(3)

    btn_gen = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'float-end')]")))
    log("   📥 Descargando Rapivale...")
    driver.execute_script("arguments[0].click();", btn_gen)
    time.sleep(30)  # Tiempo de descarga

    archivo = mover_archivo_descargado(f"base_dias_{fecha_hoy}", CARPETAS_DESTINO["RAPIVALE"], log)

    # Logout Rapivale
    driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'nav-user')]"))))
    time.sleep(2)
    driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Cerrar sesión')]"))))
    time.sleep(2)
    return archivo


def _proceso_nv(driver, wait, fecha_hoy, url, usuario, contrasena, prefijo, carpeta, nombre, log=print):
    """Flujo común de Vale Amigo / Vale Amigo Perú / Viva Vale (con validación de fecha)."""
    log(f">>> INICIANDO {nombre}")
    driver.get(url)
    wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(usuario)
    driver.find_element(By.NAME, "password").send_keys(contrasena)
    driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "submit"))
    time.sleep(10)

    driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Reportes']/.."))))
    time.sleep(3)
    driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Cartera base días')]"))))
    time.sleep(3)

    archivo, en_fecha = None, False
    f_pagina = wait.until(EC.presence_of_element_located((By.ID, "date"))).get_attribute("value")
    if f_pagina == fecha_hoy:
        en_fecha = True
        driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, "//a[contains(text(), 'Exportar')]"))
        log(f"   📥 Descargando {nombre}...")
        time.sleep(20 if nombre == "VALE AMIGO PERU" else 45)
        archivo = mover_archivo_descargado(prefijo, carpeta, log)
    else:
        log(f"   ⚠️ La página está en {f_pagina}, no en el corte de hoy ({fecha_hoy}); no se descargó.")

    # Logout
    driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(@class, 'user-menu')]/a"))))
    time.sleep(2)
    driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/logout')]"))))
    time.sleep(2)
    return archivo, en_fecha


def proceso_vale_amigo(driver, wait, fecha_hoy, log=print):
    return _proceso_nv(driver, wait, fecha_hoy,
                       "https://valeamigo-prod.caprepaprojects.com/login",
                       USUARIO_VALE, PASS_VALE,
                       f"Cartera_Base_Dias_ValeAmigo_{fecha_hoy}.csv",
                       CARPETAS_DESTINO["VALE_AMIGO"], "VALE AMIGO", log)


def proceso_vale_amigo_peru(driver, wait, fecha_hoy, log=print):
    # Prefijo con guion bajo al final para diferenciarlo (igual que el original)
    return _proceso_nv(driver, wait, fecha_hoy,
                       "https://valeamigo-peru.caprepaprojects.com/login",
                       USUARIO_PERU, PASS_PERU,
                       f"Cartera_Base_Dias_ValeAmigo_{fecha_hoy}_",
                       CARPETAS_DESTINO["VALE_AMIGO_PERU"], "VALE AMIGO PERU", log)


def proceso_viva_vale(driver, wait, fecha_hoy, log=print):
    return _proceso_nv(driver, wait, fecha_hoy,
                       "http://system.vivavale.mx/login",
                       USUARIO_VALE, PASS_VALE,
                       f"CarteraBaseDias_VivaVale_{fecha_hoy}",
                       CARPETAS_DESTINO["VIVA_VALE"], "VIVA VALE", log)


def proceso_navegador(marcas=None, log=print):
    """Corre el proceso del navegador para las marcas elegidas (todas por defecto).

    Regresa una lista de dicts: Marca | Estado | Archivo — para el seguimiento
    en la página o en consola.
    """
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    marcas = [m for m in MARCAS_NAVEGADOR if (marcas is None or m in marcas)]
    resumen = []

    with crear_driver() as driver:
        wait = WebDriverWait(driver, 30)
        for marca in marcas:
            try:
                if marca == "RAPIVALE":
                    archivo = proceso_rapivale(driver, wait, fecha_hoy, log)
                    en_fecha = True
                elif marca == "VALE AMIGO":
                    archivo, en_fecha = proceso_vale_amigo(driver, wait, fecha_hoy, log)
                elif marca == "VALE AMIGO PERU":
                    archivo, en_fecha = proceso_vale_amigo_peru(driver, wait, fecha_hoy, log)
                else:
                    archivo, en_fecha = proceso_viva_vale(driver, wait, fecha_hoy, log)

                if archivo:
                    estado = "✅ Descargado y movido a su carpeta"
                elif en_fecha:
                    estado = "⚠️ Descargó pero no se encontró el archivo en Descargas"
                else:
                    estado = "⚠️ La página no está en el corte de hoy (no se descargó)"
                resumen.append({"Marca": marca, "Estado": estado, "Archivo": archivo or ""})
            except Exception as e:
                log(f"❌ Error en {marca}: {e}")
                resumen.append({"Marca": marca, "Estado": f"❌ {e}", "Archivo": ""})

    log("*** PROCESO DEL NAVEGADOR COMPLETADO Y ARCHIVOS DISTRIBUIDOS ***")
    return resumen


if __name__ == "__main__":
    proceso_navegador()
