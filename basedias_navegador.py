# -*- coding: utf-8 -*-
"""
BASE DÍAS — Proceso por PÁGINA (navegador) — se corre LOCAL en la computadora.

Es el script de movimiento: entra a las páginas de Rapivale, Vale Amigo,
Vale Amigo Perú y Viva Vale, descarga la cartera base días del DÍA DE HOY y
mueve cada archivo de Descargas a su carpeta de OneDrive.

Requisitos (solo local, NO van en requirements.txt de la página):
    pip install selenium webdriver-manager

Para correrlo:  python basedias_navegador.py

Nota: la alternativa a nivel BASE DE DATOS (eligiendo el día) está en la
página del proyecto (app.py -> pestaña BASE DÍAS), que usa datos_basedias.py
y procesos_basedias.py.
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

# ------------------ CONFIGURACIÓN DE FECHAS Y RUTAS ------------------
FECHA_HOY = datetime.now().strftime("%Y-%m-%d")

# Ruta de origen (Descargas) y base de destino en OneDrive
downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
ruta_base_destinos = r'C:\Users\progr\OneDrive\Documentos\Ivan\OneDrive\Nidya\Base dias'

# Definición de carpetas por marca
carpetas_destino = {
    "RAPIVALE": os.path.join(ruta_base_destinos, "RAPI VALE"),
    "VALE_AMIGO": os.path.join(ruta_base_destinos, "VALE AMIGO"),
    "VIVA_VALE": os.path.join(ruta_base_destinos, "VIVA VALE"),
    "VALE_AMIGO_PERU": os.path.join(ruta_base_destinos, "VALE AMIGO PERU")
}

# Credenciales
USUARIO_VALE = "jorgeitl"
PASS_VALE = "Trejo907654"
USUARIO_RAPI = "Nidyarh"
PASS_RAPI = "Nidyarh2234"
USUARIO_PERU = "Nidyarh"
PASS_PERU = "Hernandez315"

# ------------------ FUNCIÓN PARA MOVER ARCHIVOS ------------------
def mover_archivo_descargado(prefijo, carpeta_destino):
    """Busca el archivo recién descargado y lo mueve a su carpeta correspondiente."""
    # Asegurar que la carpeta de destino existe
    if not os.path.exists(carpeta_destino):
        os.makedirs(carpeta_destino)
        
    archivo_movido = False
    for archivo in os.listdir(downloads_folder):
        if archivo.startswith(prefijo):
            ruta_origen = os.path.join(downloads_folder, archivo)
            ruta_destino = os.path.join(carpeta_destino, archivo)
            try:
                shutil.move(ruta_origen, ruta_destino)
                print(f"    ✅ Movido a {os.path.basename(carpeta_destino)}: {archivo}")
                archivo_movido = True
                break # Sale del ciclo una vez que encuentra y mueve el archivo
            except Exception as e:
                print(f"    ⚠️ Error al mover {archivo}: {e}")
                
    if not archivo_movido:
        print(f"    ⚠️ No se encontró ningún archivo con el prefijo '{prefijo}' en Descargas.")

# ------------------ CONFIGURACIÓN DEL NAVEGADOR ------------------
options = Options()
options.add_argument("--start-maximized")
prefs = {
    "download.default_directory": downloads_folder,
    "download.prompt_for_download": False,
    "directory_upgrade": True,
    "safebrowsing.enabled": True
}
options.add_experimental_option("prefs", prefs)

service = Service(ChromeDriverManager().install())

with webdriver.Chrome(service=service, options=options) as driver:
    wait = WebDriverWait(driver, 30)

    # =========================================================================
    # 1. RAPIVALE (Descarga Directa)
    # =========================================================================
    print("\n>>> INICIANDO RAPIVALE")
    driver.get("https://system.rapivale.mx/#/auth/login")
    try:
        wait.until(EC.visibility_of_element_located((By.XPATH, "//input[@formcontrolname='username']"))).send_keys(USUARIO_RAPI)
        driver.find_element(By.XPATH, "//input[@formcontrolname='password']").send_keys(PASS_RAPI)
        driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, "//button[@type='submit']"))
        time.sleep(10)

        driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Reportes')]"))))
        time.sleep(3)
        driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'report/wallet')]"))))
        time.sleep(3)

        btn_gen = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'float-end')]")))
        print("   📥 Descargando Rapivale...")
        driver.execute_script("arguments[0].click();", btn_gen)
        time.sleep(30) # Tiempo de descarga
        
        # MOVER ARCHIVO INMEDIATAMENTE
        mover_archivo_descargado(f"base_dias_{FECHA_HOY}", carpetas_destino["RAPIVALE"])

        # Logout Rapivale
        driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@class, 'nav-user')]"))))
        time.sleep(2)
        driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Cerrar sesión')]"))))
        time.sleep(2)
    except Exception as e: print(f"❌ Error en Rapivale: {e}")

    # =========================================================================
    # 2. VALE AMIGO (Validación de Fecha)
    # =========================================================================
    print("\n>>> INICIANDO VALE AMIGO")
    driver.get("https://valeamigo-prod.caprepaprojects.com/login")
    try:
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(USUARIO_VALE)
        driver.find_element(By.NAME, "password").send_keys(PASS_VALE)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "submit"))
        time.sleep(10)

        driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Reportes']/.."))))
        time.sleep(3)
        driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Cartera base días')]"))))
        time.sleep(3)

        f_vale = wait.until(EC.presence_of_element_located((By.ID, "date"))).get_attribute("value")
        if f_vale == FECHA_HOY:
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, "//a[contains(text(), 'Exportar')]"))
            print("   📥 Descargando Vale Amigo...")
            time.sleep(45)
            
            # MOVER ARCHIVO INMEDIATAMENTE
            mover_archivo_descargado(f"Cartera_Base_Dias_ValeAmigo_{FECHA_HOY}.csv", carpetas_destino["VALE_AMIGO"])
        
        # Logout Vale Amigo
        driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(@class, 'user-menu')]/a"))))
        time.sleep(2)
        driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/logout')]"))))
        time.sleep(2)
    except Exception as e: print(f"❌ Error en Vale Amigo: {e}")

    # =========================================================================
    # 3. VALE AMIGO PERU (Validación de Fecha)
    # =========================================================================
    print("\n>>> INICIANDO VALE AMIGO PERU") # Corregido el print para que diga PERU
    driver.get("https://valeamigo-peru.caprepaprojects.com/login")
    try:
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(USUARIO_PERU)
        driver.find_element(By.NAME, "password").send_keys(PASS_PERU)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "submit"))
        time.sleep(10)

        driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Reportes']/.."))))
        time.sleep(3)
        driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Cartera base días')]"))))
        time.sleep(3)

        f_vale = wait.until(EC.presence_of_element_located((By.ID, "date"))).get_attribute("value")
        if f_vale == FECHA_HOY:
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, "//a[contains(text(), 'Exportar')]"))
            print("   📥 Descargando Vale Amigo Peru...")
            time.sleep(20)
            
            # MOVER ARCHIVO INMEDIATAMENTE (Usando la lógica del guion bajo para diferenciarlo)
            mover_archivo_descargado(f"Cartera_Base_Dias_ValeAmigo_{FECHA_HOY}_", carpetas_destino["VALE_AMIGO_PERU"])
        
        # Logout Vale Amigo Peru
        driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(@class, 'user-menu')]/a"))))
        time.sleep(2)
        driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/logout')]"))))
        time.sleep(2)
    except Exception as e: print(f"❌ Error en Vale Amigo Peru: {e}")


    # =========================================================================
    # 4. VIVA VALE (Validación de Fecha)
    # =========================================================================
    print("\n>>> INICIANDO VIVA VALE")
    driver.get("http://system.vivavale.mx/login")
    try:
        wait.until(EC.presence_of_element_located((By.NAME, "username"))).send_keys(USUARIO_VALE)
        driver.find_element(By.NAME, "password").send_keys(PASS_VALE)
        driver.execute_script("arguments[0].click();", driver.find_element(By.ID, "submit"))
        time.sleep(10)

        driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Reportes']/.."))))
        time.sleep(3)
        driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Cartera base días')]"))))
        time.sleep(3)

        f_viva = wait.until(EC.presence_of_element_located((By.ID, "date"))).get_attribute("value")
        if f_viva == FECHA_HOY:
            driver.execute_script("arguments[0].click();", driver.find_element(By.XPATH, "//a[contains(text(), 'Exportar')]"))
            print("   📥 Descargando Viva Vale...")
            time.sleep(45)
            
            # MOVER ARCHIVO INMEDIATAMENTE
            mover_archivo_descargado(f"CarteraBaseDias_VivaVale_{FECHA_HOY}", carpetas_destino["VIVA_VALE"])

        # Logout Viva Vale
        driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//li[contains(@class, 'user-menu')]/a"))))
        time.sleep(2)
        driver.execute_script("arguments[0].click();", wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, '/logout')]"))))
        time.sleep(2)
    except Exception as e: print(f"❌ Error en Viva Vale: {e}")

print("\n*** PROCESO COMPLETADO Y ARCHIVOS DISTRIBUIDOS ***")