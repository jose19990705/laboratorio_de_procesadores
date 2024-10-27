import subprocess
import os
import shutil
from multiprocessing import Pool  # Importar para procesamiento en paralelo

# Combinaciones de parámetros específicas
combinaciones_parametros = [
    {"int_alu": 2, "mem_write": 2, "mem_read": 2},
    {"int_alu": 2, "mem_write": 2, "mem_read": 3},
    {"int_alu": 2, "mem_write": 2, "mem_read": 4},
    {"int_alu": 2, "mem_write": 3, "mem_read": 2},
    {"int_alu": 2, "mem_write": 3, "mem_read": 3},
    {"int_alu": 2, "mem_write": 3, "mem_read": 4},
    {"int_alu": 3, "mem_write": 2, "mem_read": 2},
    {"int_alu": 3, "mem_write": 2, "mem_read": 3},
    {"int_alu": 3, "mem_write": 3, "mem_read": 4},
    {"int_alu": 4, "mem_write": 4, "mem_read": 4},
]

# Ruta base donde están los programas a simular
RUTA_BASE_PROGRAMAS = os.path.expanduser("~/mySimTools/workloads")
NOMBRE_PROGRAMA = "mp3_dec"

# Ruta del simulador y script
GEM5PATH = os.path.expanduser("~/mySimTools/gem5/build/ARM")
SCRIPTDIR = os.path.join(os.path.dirname(__file__), "../../scripts/CortexA76_scripts_gem5")

# Generar un nombre de archivo único basado en la configuración
def generar_nombre_archivo(config, simulacion):
    return f"{RUTA_BASE_PROGRAMAS}/{NOMBRE_PROGRAMA}/{config['mem_read']}_{config['mem_write']}_{config['int_alu']}/s:{simulacion}:Alu:{config['int_alu']}:" \
           f"write:{config['mem_write']}:" \
           f"read:{config['mem_read']}.txt"

# Leer el archivo de resultados y extraer estadísticas
def leer_estadisticas(archivo):
    estadisticas = {}
    try:
        with open(archivo, 'r') as f:
            for linea in f:
                if "system.cpu.numCycles" in linea:
                    estadisticas["num_ciclos"] = int(linea.split()[1])
                elif "simInsts" in linea:
                    estadisticas["num_instrucciones"] = int(linea.split()[1])
    except FileNotFoundError:
        print(f"Archivo no encontrado: {archivo}")
    return estadisticas

# Calcular CPI
def calcular_cpi(num_ciclos, num_instrucciones):
    if num_instrucciones == 0:
        return float('inf')  # Evita la división por cero
    return num_ciclos / num_instrucciones

# Ejecutar la simulación
def ejecutar_simulacion(config, simulacion):
    carpeta_m5out = os.path.join(RUTA_BASE_PROGRAMAS, NOMBRE_PROGRAMA, f"{config['mem_read']}_{config['mem_write']}_{config['int_alu']}")
    os.makedirs(carpeta_m5out, exist_ok=True)

    nombre_archivo_resultados = generar_nombre_archivo(config, simulacion)

    command = [
        os.path.join(GEM5PATH, "gem5.fast"),
        f"--outdir={carpeta_m5out}",
        os.path.join(SCRIPTDIR, "CortexA76.py"),
        f"--num_fu_intALU={config['int_alu']}",
        f"--num_fu_write={config['mem_write']}",
        f"--num_fu_read={config['mem_read']}",
        "--cmd=mp3_dec",
        "--options=-w mp3dec_outfile.wav mp3dec_testfile.mp3"
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Error al ejecutar gem5:")
        print(result.stderr)
        return None

    archivo_wav = os.path.join(carpeta_m5out, "mp3dec_outfile.wav")
    archivo_estadisticas_gem5 = os.path.join(carpeta_m5out, "stats.txt")

    if os.path.exists(archivo_wav):
        print(f"Archivo de salida encontrado: {archivo_wav}")
    else:
        print("Error: Archivo de salida no encontrado.")

    if os.path.exists(archivo_estadisticas_gem5):
        shutil.copy(archivo_estadisticas_gem5, nombre_archivo_resultados)
        print(f"Resultados guardados en: {nombre_archivo_resultados}")
    else:
        print("Error: Archivo de estadísticas no encontrado.")

    return nombre_archivo_resultados

# Evaluar la configuración
def evaluar_configuracion(config, simulacion):
    nombre_archivo_resultados = ejecutar_simulacion(config, simulacion)
    if nombre_archivo_resultados is None:
        return float('inf')

    estadisticas = leer_estadisticas(nombre_archivo_resultados)
    if "num_ciclos" in estadisticas and "num_instrucciones" in estadisticas:
        cpi = calcular_cpi(estadisticas["num_ciclos"], estadisticas["num_instrucciones"])
        return cpi
    return float('inf')

# Algoritmo Genético para ejecutar simulaciones
def algoritmo_genetico(combinaciones_parametros, simulaciones):
    poblacion = combinaciones_parametros

    with Pool(processes=2) as pool:
        for simulacion in range(simulaciones):
            print(f"Ejecutando simulación {simulacion + 1}...")
            resultados = pool.starmap(evaluar_configuracion, [(config, simulacion + 1) for config in poblacion])
            for config, cpi in zip(poblacion, resultados):
                print(f"Configuración: {config} - CPI: {cpi}")

    mejor_configuracion = min(poblacion, key=lambda config: evaluar_configuracion(config, simulaciones))
    return mejor_configuracion

# Parámetros del algoritmo
TAMANO_POBLACION = len(combinaciones_parametros)  # Usar todas las combinaciones
SIMULACIONES = 3  # Aumentado para aprovechar los núcleos disponibles 

# Ejecutar el algoritmo genético
mejor_configuracion = algoritmo_genetico(combinaciones_parametros, SIMULACIONES)
print(f"La mejor configuración encontrada: {mejor_configuracion}")
