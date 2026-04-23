"""
SIMULADOR DE PORTAFOLIO DE INVERSIÓN
=====================================
Este programa permite gestionar un portafolio con acciones (renta variable)
y CDTs/bonos (renta fija). Usa yfinance para obtener precios reales del mercado.

Cómo funciona en resumen:
1. Se crea un portafolio con un capital inicial
2. Se pueden comprar y vender acciones con precios reales de Yahoo Finance
3. Se pueden agregar CDTs que generan intereses diarios
4. Se calcula la rentabilidad neta considerando dividendos y comisiones
5. Se grafican resultados históricos
"""

import sys
import io

# Configurar la salida estándar para usar UTF-8 y evitar errores de codificación en Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

import yfinance as yf           # Para obtener precios de acciones
import pandas as pd             # Para manejar tablas de datos
import matplotlib.pyplot as plt # Para hacer gráficas
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import json                     # Para guardar y cargar datos
import os                       # Para verificar si existen archivos

# ============================================================
# CONSTANTES GLOBALES
# Estos valores se usan en todo el programa
# ============================================================

COMISION_BROKER = 0.002   # Subimos al 0.2% por operación
IMPUESTO_DIVIDENDO = 0.08  # Bajamos la retención al 8%
ARCHIVO_DATOS = "portafolio_datos.json"  # Archivo donde se guarda el portafolio

# Lista de 10 acciones disponibles para invertir (universo de acciones)
ACCIONES_DISPONIBLES = {
    "AAPL":  "Apple Inc.",
    "MSFT":  "Microsoft Corp.",
    "GOOGL": "Alphabet (Google)",
    "AMZN":  "Amazon.com Inc.",
    "TSLA":  "Tesla Inc.",
    "NVDA":  "NVIDIA Corp.",
    "META":  "Meta Platforms",
    "BRK-B": "Berkshire Hathaway",
    "JPM":   "JPMorgan Chase",
    "V":     "Visa Inc.",
    "NFLX":  "Netflix Inc.",
    "COST":  "Costco Wholesale",
    "BTC-USD": "Bitcoin (Yahoo Finance)",
    "WMT":   "Walmart Inc.",
    "JNJ":   "Johnson & Johnson",
    "PG":    "Procter & Gamble",
    "XOM":   "Exxon Mobil Corp.",
    "DIS":   "The Walt Disney Co.",
    "KO":    "Coca-Cola Company"
}


# ============================================================
# CLASE PORTAFOLIO
# Aquí se guarda toda la información del portafolio:
# capital disponible, acciones compradas, CDTs, historial
# ============================================================

class Portafolio:
    def __init__(self, capital_inicial: float):
        """
        Crea un nuevo portafolio.
        capital_inicial: dinero en USD con el que empezamos
        """
        self.capital = capital_inicial          # Dinero disponible en caja
        self.acciones = {}                      # Diccionario: ticker -> {cantidad, precio_promedio}
        self.cdts = []                          # Lista de CDTs activos
        self.historial_transacciones = []       # Registro de todas las compras/ventas
        self.historial_valor = []               # Registro del valor total del portafolio día a día
        self.dividendos_recibidos = 0.0         # Total de dividendos cobrados
        self.comisiones_pagadas = 0.0           # Total de comisiones pagadas al broker

    def to_dict(self):
        """Convierte el portafolio a un diccionario para guardarlo en JSON."""
        return {
            "capital": self.capital,
            "acciones": self.acciones,
            "cdts": self.cdts,
            "historial_transacciones": self.historial_transacciones,
            "historial_valor": self.historial_valor,
            "dividendos_recibidos": self.dividendos_recibidos,
            "comisiones_pagadas": self.comisiones_pagadas
        }

    @classmethod
    def from_dict(cls, datos: dict):
        """Reconstruye un portafolio desde un diccionario cargado de JSON."""
        p = cls(datos["capital"])
        p.acciones = datos["acciones"]
        p.cdts = datos["cdts"]
        p.historial_transacciones = datos["historial_transacciones"]
        p.historial_valor = datos["historial_valor"]
        p.dividendos_recibidos = datos["dividendos_recibidos"]
        p.comisiones_pagadas = datos["comisiones_pagadas"]
        return p


# ============================================================
# FUNCIONES DE DATOS DE MERCADO (yfinance)
# ============================================================

def obtener_precio_accion(ticker: str):
    """
    Descarga el precio de cierre más reciente y el rango del día (min/max)
    para una acción usando yfinance.

    Retorna un diccionario con: cierre, minimo, maximo
    O None si hubo un error (ej: ticker inválido, sin internet)
    """
    try:
        accion = yf.Ticker(ticker)
        # Descargamos los últimos 5 días para asegurarnos de tener datos
        historial = accion.history(period="5d")

        if historial.empty:
            print(f"  [!] No se encontraron datos para {ticker}")
            return None

        # Tomamos la última fila (día más reciente)
        ultimo_dia = historial.iloc[-1]
        return {
            "cierre":  round(float(ultimo_dia["Close"]), 2),
            "minimo":  round(float(ultimo_dia["Low"]),   2),
            "maximo":  round(float(ultimo_dia["High"]),  2),
            "fecha":   str(historial.index[-1].date())
        }
    except Exception as e:
        print(f"  [!] Error obteniendo precio de {ticker}: {e}")
        return None


def obtener_historial_precios(ticker: str, dias: int = 30):
    """
    Descarga el historial de precios de cierre para graficar.
    dias: cuántos días hacia atrás queremos
    """
    try:
        accion = yf.Ticker(ticker)
        historial = accion.history(period=f"{dias}d")
        return historial["Close"]
    except Exception as e:
        print(f"  [!] Error en historial de {ticker}: {e}")
        return None


def obtener_dividendos(ticker: str, dias: int = 90):
    """
    Consulta si una acción pagó dividendos recientemente.
    Retorna el total de dividendos por acción en el período.
    """
    try:
        accion = yf.Ticker(ticker)
        dividendos = accion.dividends  # Serie con fechas y montos de dividendos
        if dividendos.empty:
            return 0.0
        # Filtrar dividendos de los últimos 'dias' días
        fecha_inicio = datetime.now() - timedelta(days=dias)
        dividendos_recientes = dividendos[dividendos.index > pd.Timestamp(fecha_inicio, tz='America/New_York')]
        return round(float(dividendos_recientes.sum()), 4)
    except:
        return 0.0


# ============================================================
# FUNCIONES DE TRANSACCIONES
# ============================================================

def comprar_accion(portafolio: Portafolio, ticker: str, cantidad: int):
    """
    Compra una cantidad de acciones de un ticker.

    Pasos:
    1. Obtiene el precio actual del mercado
    2. Valida que el precio de compra esté dentro del rango del día (min-max)
    3. Calcula el costo total incluyendo la comisión del broker
    4. Verifica que haya suficiente capital
    5. Actualiza el portafolio
    """
    print(f"\n  Consultando precio de {ticker}...")
    datos = obtener_precio_accion(ticker)

    if datos is None:
        print(f"  [X] No se pudo obtener precio de {ticker}. Operación cancelada.")
        return False

    precio_cierre = datos["cierre"]
    precio_min    = datos["minimo"]
    precio_max    = datos["maximo"]

    print(f"  Precio cierre: ${precio_cierre} | Rango del día: ${precio_min} - ${precio_max}")

    # Validación: usamos el precio de cierre que debe estar dentro del rango
    # (esto siempre es verdad con datos reales, pero lo validamos como medida de seguridad)
    if not (precio_min <= precio_cierre <= precio_max):
        print(f"  [X] El precio de cierre ${precio_cierre} está fuera del rango del día.")
        return False

    # Cálculo de costos
    costo_acciones = precio_cierre * cantidad
    comision       = round(costo_acciones * COMISION_BROKER, 4)
    costo_total    = costo_acciones + comision

    print(f"  Costo acciones: ${costo_acciones:.2f} | Comisión: ${comision:.4f} | Total: ${costo_total:.2f}")

    # Verificar si hay suficiente capital
    if portafolio.capital < costo_total:
        print(f"  [X] Capital insuficiente. Disponible: ${portafolio.capital:.2f}, Necesario: ${costo_total:.2f}")
        return False

    # Ejecutar la compra: descontar capital
    portafolio.capital -= costo_total
    portafolio.comisiones_pagadas += comision

    # Actualizar posición en acciones (precio promedio ponderado)
    if ticker in portafolio.acciones:
        pos = portafolio.acciones[ticker]
        total_cantidad = pos["cantidad"] + cantidad
        total_costo    = (pos["cantidad"] * pos["precio_promedio"]) + (cantidad * precio_cierre)
        portafolio.acciones[ticker] = {
            "cantidad":        total_cantidad,
            "precio_promedio": round(total_costo / total_cantidad, 4)
        }
    else:
        portafolio.acciones[ticker] = {
            "cantidad":        cantidad,
            "precio_promedio": precio_cierre
        }

    # Registrar en el historial
    portafolio.historial_transacciones.append({
        "tipo":      "COMPRA",
        "ticker":    ticker,
        "cantidad":  cantidad,
        "precio":    precio_cierre,
        "comision":  comision,
        "total":     costo_total,
        "fecha":     datetime.now().strftime("%Y-%m-%d %H:%M"),
        "capital_restante": round(portafolio.capital, 2)
    })

    print(f"  [OK] Compra exitosa: {cantidad} acciones de {ticker} a ${precio_cierre}")
    print(f"  Capital restante: ${portafolio.capital:.2f}")
    return True


def vender_accion(portafolio: Portafolio, ticker: str, cantidad: int):
    """
    Vende una cantidad de acciones.

    Pasos:
    1. Verifica que el portafolio tenga suficientes acciones
    2. Obtiene el precio actual
    3. Calcula ganancia/pérdida y comisión
    4. Actualiza el portafolio
    """
    # Verificar que tengamos las acciones
    if ticker not in portafolio.acciones:
        print(f"  [X] No tienes acciones de {ticker} en el portafolio.")
        return False

    pos = portafolio.acciones[ticker]
    if pos["cantidad"] < cantidad:
        print(f"  [X] Solo tienes {pos['cantidad']} acciones de {ticker}, no puedes vender {cantidad}.")
        return False

    print(f"\n  Consultando precio de {ticker}...")
    datos = obtener_precio_accion(ticker)

    if datos is None:
        print(f"  [X] No se pudo obtener precio de {ticker}. Operación cancelada.")
        return False

    precio_cierre = datos["cierre"]
    precio_min    = datos["minimo"]
    precio_max    = datos["maximo"]

    print(f"  Precio cierre: ${precio_cierre} | Rango del día: ${precio_min} - ${precio_max}")

    # Validación de coherencia del precio
    if not (precio_min <= precio_cierre <= precio_max):
        print(f"  [X] Precio de cierre fuera del rango del día.")
        return False

    # Cálculo
    ingreso_bruto = precio_cierre * cantidad
    comision      = round(ingreso_bruto * COMISION_BROKER, 4)
    ingreso_neto  = ingreso_bruto - comision

    # Ganancia o pérdida respecto al precio de compra promedio
    ganancia = round((precio_cierre - pos["precio_promedio"]) * cantidad - comision, 4)

    print(f"  Ingreso bruto: ${ingreso_bruto:.2f} | Comisión: ${comision:.4f} | Ingreso neto: ${ingreso_neto:.2f}")
    print(f"  {'[OK] Ganancia' if ganancia >= 0 else '[X] Pérdida'}: ${ganancia:.2f}")

    # Actualizar portafolio
    portafolio.capital += ingreso_neto
    portafolio.comisiones_pagadas += comision

    nueva_cantidad = pos["cantidad"] - cantidad
    if nueva_cantidad == 0:
        del portafolio.acciones[ticker]  # Si vendemos todo, eliminamos la posición
    else:
        portafolio.acciones[ticker]["cantidad"] = nueva_cantidad

    # Registrar transacción
    portafolio.historial_transacciones.append({
        "tipo":      "VENTA",
        "ticker":    ticker,
        "cantidad":  cantidad,
        "precio":    precio_cierre,
        "ganancia":  ganancia,
        "comision":  comision,
        "total":     ingreso_neto,
        "fecha":     datetime.now().strftime("%Y-%m-%d %H:%M"),
        "capital_restante": round(portafolio.capital, 2)
    })

    print(f"  [OK] Venta exitosa: {cantidad} acciones de {ticker} a ${precio_cierre}")
    print(f"  Capital disponible: ${portafolio.capital:.2f}")
    return True


# ============================================================
# FUNCIONES DE RENTA FIJA (CDTs)
# ============================================================

def agregar_cdt(portafolio: Portafolio, monto: float, tasa_anual: float, dias_plazo: int):
    """
    Agrega un CDT (Certificado de Depósito a Término) al portafolio.

    El CDT genera intereses diarios calculados con interés simple:
    interes_diario = monto * (tasa_anual / 365)

    monto:       dinero a invertir en el CDT
    tasa_anual:  tasa de interés anual en decimal (ej: 0.12 para 12%)
    dias_plazo:  número de días que dura el CDT
    """
    if portafolio.capital < monto:
        print(f"  [X] Capital insuficiente. Disponible: ${portafolio.capital:.2f}")
        return False

    # Descontar el monto del capital disponible
    portafolio.capital -= monto

    fecha_inicio = datetime.now().strftime("%Y-%m-%d")
    fecha_vencimiento = (datetime.now() + timedelta(days=dias_plazo)).strftime("%Y-%m-%d")
    interes_diario = round(monto * (tasa_anual / 360), 4)

    cdt = {
        "id":               len(portafolio.cdts) + 1,
        "monto_inicial":    monto,
        "tasa_anual":       tasa_anual,
        "dias_plazo":       dias_plazo,
        "fecha_inicio":     fecha_inicio,
        "fecha_vencimiento": fecha_vencimiento,
        "interes_diario":   interes_diario,
        "intereses_acumulados": 0.0,
        "dias_transcurridos":   0,
        "activo":           True
    }

    portafolio.cdts.append(cdt)
    print(f"  [OK] CDT #{cdt['id']} creado: ${monto:.2f} al {tasa_anual*100:.1f}% anual por {dias_plazo} días")
    print(f"  Interés diario: ${interes_diario:.4f} | Vencimiento: {fecha_vencimiento}")
    return True


def liquidar_intereses_cdts(portafolio: Portafolio):
    """
    Aplica un día de intereses a todos los CDTs activos.
    Esto simula el cierre de jornada para los instrumentos de renta fija.
    """
    total_intereses = 0.0
    for cdt in portafolio.cdts:
        if not cdt["activo"]:
            continue
        cdt["dias_transcurridos"] += 1
        cdt["intereses_acumulados"] = round(
            cdt["intereses_acumulados"] + cdt["interes_diario"], 4
        )
        total_intereses += cdt["interes_diario"]

        # Si el CDT venció, lo marcamos como inactivo y devolvemos el capital + intereses
        if cdt["dias_transcurridos"] >= cdt["dias_plazo"]:
            cdt["activo"] = False
            devolucion = cdt["monto_inicial"] + cdt["intereses_acumulados"]
            portafolio.capital += devolucion
            print(f"  [OK] CDT #{cdt['id']} VENCIDO. Devuelto: ${devolucion:.2f} "
                  f"(capital + ${cdt['intereses_acumulados']:.2f} en intereses)")

    if total_intereses > 0:
        print(f"  Intereses del día en CDTs: ${total_intereses:.4f}")


def cobrar_dividendos(portafolio: Portafolio):
    """
    Consulta y cobra dividendos para todas las acciones en portafolio.
    Aplica retención de impuestos sobre los dividendos.
    """
    print("\n  Verificando dividendos...")
    dividendos_totales = 0.0

    for ticker, pos in portafolio.acciones.items():
        div_por_accion = obtener_dividendos(ticker)
        if div_por_accion > 0:
            div_bruto = div_por_accion * pos["cantidad"]
            retencion = round(div_bruto * IMPUESTO_DIVIDENDO, 4)
            div_neto  = div_bruto - retencion

            portafolio.capital += div_neto
            portafolio.dividendos_recibidos += div_neto
            dividendos_totales += div_neto

            print(f"  {ticker}: ${div_bruto:.4f} bruto → retención ${retencion:.4f} → neto ${div_neto:.4f}")

    if dividendos_totales == 0:
        print("  Sin dividendos recientes para cobrar.")
    else:
        print(f"  Total dividendos netos cobrados: ${dividendos_totales:.4f}")


# ============================================================
# FUNCIONES DE VALORACIÓN Y REPORTES
# ============================================================

def calcular_valor_portafolio(portafolio: Portafolio):
    """
    Calcula el valor total actual del portafolio:
    = capital en caja + valor de mercado de acciones + valor de CDTs

    Retorna un diccionario con el desglose completo.
    """
    valor_acciones = 0.0
    detalle_acciones = []

    for ticker, pos in portafolio.acciones.items():
        datos = obtener_precio_accion(ticker)
        if datos:
            precio_actual = datos["cierre"]
            valor         = precio_actual * pos["cantidad"]
            ganancia_loss = (precio_actual - pos["precio_promedio"]) * pos["cantidad"]
            valor_acciones += valor
            detalle_acciones.append({
                "ticker":           ticker,
                "cantidad":         pos["cantidad"],
                "precio_promedio":  pos["precio_promedio"],
                "precio_actual":    precio_actual,
                "valor_actual":     round(valor, 2),
                "ganancia_perdida": round(ganancia_loss, 2)
            })

    # Valor de CDTs: capital inicial + intereses acumulados
    valor_cdts = sum(
        cdt["monto_inicial"] + cdt["intereses_acumulados"]
        for cdt in portafolio.cdts if cdt["activo"]
    )

    valor_total = portafolio.capital + valor_acciones + valor_cdts

    return {
        "capital_caja":    round(portafolio.capital, 2),
        "valor_acciones":  round(valor_acciones, 2),
        "valor_cdts":      round(valor_cdts, 2),
        "valor_total":     round(valor_total, 2),
        "detalle_acciones": detalle_acciones
    }


def mostrar_resumen(portafolio: Portafolio, capital_inicial: float):
    """
    Imprime un resumen detallado del estado actual del portafolio.
    """
    print("\n" + "="*60)
    print("       RESUMEN DEL PORTAFOLIO DE INVERSIÓN")
    print("="*60)

    print("\nObteniendo precios actuales del mercado...")
    valoracion = calcular_valor_portafolio(portafolio)

    # Rentabilidad neta
    rentabilidad = valoracion["valor_total"] - capital_inicial
    pct = (rentabilidad / capital_inicial) * 100 if capital_inicial > 0 else 0

    print(f"\n{'─'*40}")
    print(f"  Capital en caja:      ${valoracion['capital_caja']:>12,.2f}")
    print(f"  Valor en acciones:    ${valoracion['valor_acciones']:>12,.2f}")
    print(f"  Valor en CDTs:        ${valoracion['valor_cdts']:>12,.2f}")
    print(f"{'-'*40}")
    print(f"  VALOR TOTAL:          ${valoracion['valor_total']:>12,.2f}")
    print(f"  Capital inicial:      ${capital_inicial:>12,.2f}")
    print(f"  Rentabilidad neta:    ${rentabilidad:>+12,.2f}  ({pct:+.2f}%)")
    print(f"{'-'*40}")
    print(f"  Dividendos cobrados:  ${portafolio.dividendos_recibidos:>12,.4f}")
    print(f"  Comisiones pagadas:   ${portafolio.comisiones_pagadas:>12,.4f}")

    if valoracion["detalle_acciones"]:
        print(f"\n  ACCIONES EN PORTAFOLIO:")
        print(f"  {'Ticker':<8} {'Cant':>5} {'P.Compra':>10} {'P.Actual':>10} {'Valor':>12} {'G/P':>10}")
        print(f"  {'─'*8} {'─'*5} {'─'*10} {'─'*10} {'─'*12} {'─'*10}")
        for d in valoracion["detalle_acciones"]:
            signo = "[+]" if d["ganancia_perdida"] >= 0 else "[-]"
            print(f"  {d['ticker']:<8} {d['cantidad']:>5} "
                  f"${d['precio_promedio']:>9.2f} "
                  f"${d['precio_actual']:>9.2f} "
                  f"${d['valor_actual']:>11,.2f} "
                  f"{signo}${abs(d['ganancia_perdida']):>9.2f}")

    if portafolio.cdts:
        print(f"\n  CDTs ACTIVOS:")
        for cdt in portafolio.cdts:
            if cdt["activo"]:
                print(f"  CDT #{cdt['id']}: ${cdt['monto_inicial']:.2f} al "
                      f"{cdt['tasa_anual']*100:.1f}% | "
                      f"Día {cdt['dias_transcurridos']}/{cdt['dias_plazo']} | "
                      f"Intereses: ${cdt['intereses_acumulados']:.4f}")

    print("="*60)

    # Registrar el valor del portafolio en el historial
    portafolio.historial_valor.append({
        "fecha":       datetime.now().strftime("%Y-%m-%d %H:%M"),
        "valor_total": valoracion["valor_total"]
    })

    return valoracion


# ============================================================
# FUNCIONES DE GRÁFICAS
# ============================================================

def graficar_evolucion_portafolio(portafolio: Portafolio):
    """
    Gráfica 1: Evolución del valor total del portafolio en el tiempo.
    Usa el historial_valor que se guarda cada vez que se hace un resumen.
    """
    if len(portafolio.historial_valor) < 2:
        print("  [!] Se necesitan al menos 2 registros para graficar la evolución.")
        print("    Haz más operaciones y consulta el resumen varias veces.")
        return

    fechas = [h["fecha"] for h in portafolio.historial_valor]
    valores = [h["valor_total"] for h in portafolio.historial_valor]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(fechas, valores, marker='s', linewidth=3, color='darkgreen', label='Patrimonio Total')
    ax.fill_between(range(len(valores)), valores, alpha=0.15, color='steelblue')

    ax.set_title("Evolución del Valor del Portafolio", fontsize=14, fontweight='bold')
    ax.set_xlabel("Fecha/Hora")
    ax.set_ylabel("Valor (USD)")
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True, alpha=0.3)
    ax.legend()

    plt.tight_layout()
    plt.savefig("evolucion_portafolio.png", dpi=120)
    plt.show()
    print("  [OK] Gráfica guardada: evolucion_portafolio.png")


def graficar_composicion_portafolio(portafolio: Portafolio):
    """
    Gráfica 2: Composición del portafolio en gráfico de torta (pie chart).
    Muestra qué porcentaje está en efectivo, acciones y CDTs.
    """
    valoracion = calcular_valor_portafolio(portafolio)

    etiquetas = []
    valores   = []

    if valoracion["capital_caja"] > 0:
        etiquetas.append("Efectivo")
        valores.append(valoracion["capital_caja"])

    for d in valoracion["detalle_acciones"]:
        etiquetas.append(d["ticker"])
        valores.append(d["valor_actual"])

    if valoracion["valor_cdts"] > 0:
        etiquetas.append("CDTs")
        valores.append(valoracion["valor_cdts"])

    if not valores:
        print("  [!] El portafolio está vacío.")
        return

    colores = plt.cm.tab20c.colors[:len(etiquetas)]

    fig, ax = plt.subplots(figsize=(8, 8))
    wedges, texts, autotexts = ax.pie(
        valores,
        labels=etiquetas,
        autopct='%1.1f%%',
        colors=colores,
        startangle=140
    )
    ax.set_title("Composición del Portafolio", fontsize=14, fontweight='bold')
    plt.tight_layout()
    plt.savefig("composicion_portafolio.png", dpi=120)
    plt.show()
    print("  [OK] Gráfica guardada: composicion_portafolio.png")


def graficar_precios_acciones(portafolio: Portafolio, dias: int = 30):
    """
    Gráfica 3: Histórico de precios de todas las acciones en portafolio.
    Muestra la evolución de cada acción en los últimos 'dias' días.
    """
    if not portafolio.acciones:
        print("  [!] No tienes acciones en el portafolio.")
        return

    tickers = list(portafolio.acciones.keys())
    fig, axes = plt.subplots(
        nrows=len(tickers), ncols=1,
        figsize=(12, 4 * len(tickers)),
        sharex=False
    )

    # Si solo hay una acción, axes no es lista
    if len(tickers) == 1:
        axes = [axes]

    for ax, ticker in zip(axes, tickers):
        print(f"  Descargando historial de {ticker}...")
        historial = obtener_historial_precios(ticker, dias)
        if historial is not None and not historial.empty:
            ax.plot(historial.index, historial.values,
                    linewidth=2, color='darkorange')
            ax.set_title(f"{ticker} — {ACCIONES_DISPONIBLES.get(ticker, ticker)}", fontsize=12)
            ax.set_ylabel("Precio (USD)")
            ax.grid(True, alpha=0.3)
            ax.tick_params(axis='x', rotation=45)
        else:
            ax.text(0.5, 0.5, "Sin datos", ha='center', va='center',
                    transform=ax.transAxes)

    plt.suptitle(f"Historial de Precios — Últimos {dias} días",
                 fontsize=14, fontweight='bold', y=1.01)
    plt.tight_layout()
    plt.savefig("historial_precios.png", dpi=120, bbox_inches='tight')
    plt.show()
    print("  [OK] Gráfica guardada: historial_precios.png")


def graficar_rentabilidad_acciones(portafolio: Portafolio):
    """
    Gráfica 4: Barras con ganancia/pérdida por cada acción.
    Verde = ganancia, Rojo = pérdida.
    """
    valoracion = calcular_valor_portafolio(portafolio)
    detalle    = valoracion["detalle_acciones"]

    if not detalle:
        print("  [!] No hay acciones para graficar.")
        return

    tickers   = [d["ticker"] for d in detalle]
    ganancias = [d["ganancia_perdida"] for d in detalle]
    colores   = ["green" if g >= 0 else "red" for g in ganancias]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(tickers, ganancias, color=colores, edgecolor='white', linewidth=0.8)

    # Etiquetas encima/abajo de cada barra
    for bar, g in zip(bars, ganancias):
        ypos = bar.get_height() + (0.5 if g >= 0 else -1.5)
        ax.text(bar.get_x() + bar.get_width()/2, ypos,
                f"${g:+.2f}", ha='center', va='bottom', fontsize=10)

    ax.axhline(0, color='black', linewidth=0.8, linestyle='--')
    ax.set_title("Rentabilidad por Acción (USD)", fontsize=14, fontweight='bold')
    ax.set_ylabel("Ganancia / Pérdida (USD)")
    ax.set_xlabel("Ticker")
    ax.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig("rentabilidad_acciones.png", dpi=120)
    plt.show()
    print("  [OK] Gráfica guardada: rentabilidad_acciones.png")


# ============================================================
# PERSISTENCIA: GUARDAR Y CARGAR
# ============================================================

def guardar_portafolio(portafolio: Portafolio, capital_inicial: float):
    """Guarda el estado completo del portafolio en un archivo JSON."""
    datos = portafolio.to_dict()
    datos["capital_inicial"] = capital_inicial
    with open(ARCHIVO_DATOS, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
    print(f"  [OK] Portafolio guardado en '{ARCHIVO_DATOS}'")


def cargar_portafolio():
    """
    Carga un portafolio guardado anteriormente.
    Retorna (portafolio, capital_inicial) o (None, None) si no hay archivo.
    """
    if not os.path.exists(ARCHIVO_DATOS):
        return None, None
    try:
        with open(ARCHIVO_DATOS, "r", encoding="utf-8") as f:
            datos = json.load(f)
        capital_inicial = datos.pop("capital_inicial")
        portafolio = Portafolio.from_dict(datos)
        return portafolio, capital_inicial
    except Exception as e:
        print(f"  [!] Error cargando portafolio: {e}")
        return None, None


# ============================================================
# MENÚ PRINCIPAL
# ============================================================

def mostrar_menu():
    """Imprime el menú de opciones del simulador."""
    print("\n" + "-"*50)
    print("  SIMULADOR DE PORTAFOLIO — MENÚ PRINCIPAL")
    print("-"*50)
    print("  [1] Comprar acciones")
    print("  [2] Vender acciones")
    print("  [3] Agregar CDT (renta fija)")
    print("  [4] Liquidar intereses CDTs (cierre de jornada)")
    print("  [5] Cobrar dividendos")
    print("  [6] Ver resumen del portafolio")
    print("  [7] Ver acciones disponibles")
    print("  [8] Graficar evolución del portafolio")
    print("  [9] Graficar composición del portafolio")
    print(" [10] Graficar historial de precios")
    print(" [11] Graficar rentabilidad por acción")
    print(" [12] Guardar portafolio")
    print("  [0] Salir")
    print("-"*50)


def main():
    """
    Función principal que controla el flujo del programa.
    Aquí arranca todo: carga o crea el portafolio y muestra el menú.
    """
    print("\n" + "#"*50)
    print("   SIMULADOR DE PORTAFOLIO DE INVERSIÓN v1.0")
    print("   Universidad — Estructura de Dactos")
    print("#"*50)

    # Intentar cargar portafolio existente
    portafolio, capital_inicial = cargar_portafolio()

    if portafolio is not None:
        print(f"\n  Portafolio cargado. Capital inicial: ${capital_inicial:,.2f}")
        print(f"  Capital disponible: ${portafolio.capital:,.2f}")
    else:
        # Crear nuevo portafolio
        print("\n  No se encontró portafolio guardado. Creando uno nuevo...")
        while True:
            try:
                capital_inicial = float(input("  Ingresa el capital inicial en USD: $"))
                if capital_inicial <= 0:
                    print("  El capital debe ser mayor a 0.")
                    continue
                break
            except ValueError:
                print("  Ingresa un número válido.")

        portafolio = Portafolio(capital_inicial)
        print(f"\n  [OK] Portafolio creado con ${capital_inicial:,.2f}")

    # Bucle principal del menú
    while True:
        mostrar_menu()
        opcion = input("\n  Elige una opción: ").strip()

        if opcion == "1":
            # Comprar acciones
            print("\n  Acciones disponibles:")
            for t, n in ACCIONES_DISPONIBLES.items():
                en_portafolio = "[OK]" if t in portafolio.acciones else " "
                print(f"  [{en_portafolio}] {t:<8} — {n}")
            ticker = input("\n  Ticker a comprar (ej: AAPL): ").strip().upper()
            if ticker not in ACCIONES_DISPONIBLES:
                print(f"  [!] '{ticker}' no está en la lista. Verifica el ticker.")
            else:
                try:
                    cant = int(input("  Cantidad de acciones: "))
                    if cant > 0:
                        comprar_accion(portafolio, ticker, cant)
                    else:
                        print("  La cantidad debe ser mayor a 0.")
                except ValueError:
                    print("  Ingresa un número entero válido.")

        elif opcion == "2":
            # Vender acciones
            if not portafolio.acciones:
                print("  No tienes acciones en el portafolio.")
            else:
                print("\n  Tus acciones:")
                for t, pos in portafolio.acciones.items():
                    print(f"  {t}: {pos['cantidad']} acciones | P.promedio: ${pos['precio_promedio']:.2f}")
                ticker = input("\n  Ticker a vender: ").strip().upper()
                try:
                    cant = int(input("  Cantidad a vender: "))
                    if cant > 0:
                        vender_accion(portafolio, ticker, cant)
                    else:
                        print("  La cantidad debe ser mayor a 0.")
                except ValueError:
                    print("  Ingresa un número entero válido.")

        elif opcion == "3":
            # Agregar CDT
            print(f"\n  Capital disponible: ${portafolio.capital:,.2f}")
            try:
                monto = float(input("  Monto a invertir en CDT ($): "))
                tasa  = float(input("  Tasa de interés anual (%, ej: 12 para 12%): ")) / 100
                dias  = int(input("  Plazo en días (ej: 90, 180, 360): "))
                agregar_cdt(portafolio, monto, tasa, dias)
            except ValueError:
                print("  Valores inválidos.")

        elif opcion == "4":
            # Liquidar intereses
            print("\n  Liquidando intereses del día...")
            liquidar_intereses_cdts(portafolio)

        elif opcion == "5":
            # Cobrar dividendos
            cobrar_dividendos(portafolio)

        elif opcion == "6":
            # Resumen
            mostrar_resumen(portafolio, capital_inicial)

        elif opcion == "7":
            # Mostrar acciones disponibles
            print("\n  ACCIONES DISPONIBLES PARA INVERTIR:")
            for t, n in ACCIONES_DISPONIBLES.items():
                print(f"  {t:<8} — {n}")

        elif opcion == "8":
            graficar_evolucion_portafolio(portafolio)

        elif opcion == "9":
            graficar_composicion_portafolio(portafolio)

        elif opcion == "10":
            try:
                dias = int(input("  ¿Cuántos días de historial? (ej: 30): "))
                graficar_precios_acciones(portafolio, dias)
            except ValueError:
                graficar_precios_acciones(portafolio, 30)

        elif opcion == "11":
            graficar_rentabilidad_acciones(portafolio)

        elif opcion == "12":
            guardar_portafolio(portafolio, capital_inicial)

        elif opcion == "0":
            guardar_portafolio(portafolio, capital_inicial)
            print("\n  ¡Hasta luego! Tu portafolio ha sido guardado.")
            break

        else:
            print("  Opción no válida. Elige un número del 0 al 12.")


# Punto de entrada del programa
if __name__ == "__main__":
    main()
