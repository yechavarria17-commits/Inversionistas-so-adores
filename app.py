"""
SERVIDOR WEB - Simulador de Portafolio POKECELL
Expone el simulador como una API REST para la interfaz web.
"""

from flask import Flask, jsonify, request, send_from_directory
import json, os
from datetime import datetime, timedelta
from simulador import (
    Portafolio, ACCIONES_DISPONIBLES, ARCHIVO_DATOS,
    obtener_precio_accion, obtener_historial_precios,
    comprar_accion, vender_accion,
    agregar_cdt, liquidar_intereses_cdts, cobrar_dividendos,
    calcular_valor_portafolio
)
import yfinance as yf
import pandas as pd


app = Flask(__name__, static_folder='static', static_url_path='/static')

# ─── Persistencia ────────────────────────────────────────────────────────────

def guardar(p: Portafolio):
    with open(ARCHIVO_DATOS, 'w') as f:
        json.dump(p.to_dict(), f, indent=2)

def cargar() -> Portafolio:
    if os.path.exists(ARCHIVO_DATOS):
        with open(ARCHIVO_DATOS) as f:
            return Portafolio.from_dict(json.load(f))
    return None

# ─── Rutas API ────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/portafolio', methods=['GET'])
def get_portafolio():
    p = cargar()
    if not p:
        return jsonify({'error': 'No hay portafolio. Crea uno primero.'}), 404
    val = calcular_valor_portafolio(p)
    guardar(p)
    return jsonify({
        'capital':                p.capital,
        'dividendos_recibidos':   p.dividendos_recibidos,
        'comisiones_pagadas':     p.comisiones_pagadas,
        'cdts':                   p.cdts,
        'historial_valor':        p.historial_valor,
        'historial_transacciones': p.historial_transacciones[-50:],
        **val
    })

@app.route('/api/crear', methods=['POST'])
def crear_portafolio():
    data = request.json
    capital = float(data.get('capital', 10000))
    p = Portafolio(capital)
    p.historial_valor.append({
        'fecha': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'valor': capital
    })
    guardar(p)
    return jsonify({'ok': True, 'capital': capital})

@app.route('/api/acciones', methods=['GET'])
def get_acciones():
    return jsonify(ACCIONES_DISPONIBLES)

@app.route('/api/precio/<ticker>', methods=['GET'])
def get_precio(ticker):
    datos = obtener_precio_accion(ticker.upper())
    if datos:
        return jsonify(datos)
    return jsonify({'error': f'No se pudo obtener precio de {ticker}'}), 400

@app.route('/api/historial/<ticker>', methods=['GET'])
def get_historial(ticker):
    dias = int(request.args.get('dias', 30))
    serie = obtener_historial_precios(ticker.upper(), dias)
    if serie is None or serie.empty:
        return jsonify({'error': 'Sin datos'}), 400
    return jsonify({
        'fechas':  [str(d.date()) for d in serie.index],
        'precios': [round(float(v), 2) for v in serie.values]
    })

@app.route('/api/comprar', methods=['POST'])
def api_comprar():
    data = request.json
    p = cargar()
    if not p:
        return jsonify({'error': 'Crea un portafolio primero'}), 404
    ticker   = data['ticker'].upper()
    cantidad = int(data['cantidad'])
    ok = comprar_accion(p, ticker, cantidad)
    if ok:
        _registrar_valor(p)
        guardar(p)
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'Operacion fallida (revisa capital o ticker)'}), 400

@app.route('/api/vender', methods=['POST'])
def api_vender():
    data = request.json
    p = cargar()
    if not p:
        return jsonify({'error': 'Crea un portafolio primero'}), 404
    ticker   = data['ticker'].upper()
    cantidad = int(data['cantidad'])
    ok = vender_accion(p, ticker, cantidad)
    if ok:
        _registrar_valor(p)
        guardar(p)
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'Operacion fallida'}), 400

@app.route('/api/cdt', methods=['POST'])
def api_cdt():
    data = request.json
    p = cargar()
    if not p:
        return jsonify({'error': 'Crea un portafolio primero'}), 404
    ok = agregar_cdt(p, float(data['monto']), float(data['tasa']), int(data['dias']))
    if ok:
        guardar(p)
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'Capital insuficiente'}), 400

@app.route('/api/capital', methods=['POST'])
def api_capital():
    data = request.json
    p = cargar()
    if not p:
        return jsonify({'error': 'Crea un portafolio primero'}), 404
    p.capital = float(data['capital'])
    guardar(p)
    return jsonify({'ok': True, 'capital': p.capital})

@app.route('/api/cerrar-dia', methods=['POST'])
def api_cerrar_dia():
    p = cargar()
    if not p:
        return jsonify({'error': 'Crea un portafolio primero'}), 404
    liquidar_intereses_cdts(p)
    cobrar_dividendos(p)
    _registrar_valor(p)
    guardar(p)
    return jsonify({'ok': True})

@app.route('/api/maquina', methods=['POST'])
def api_maquina():
    data = request.json
    ticker = data['ticker'].upper()
    inversion = float(data['inversion'])
    anios = int(data['anios'])
    
    try:
        accion = yf.Ticker(ticker)
        fecha_pasado = datetime.now() - timedelta(days=anios*365)
        historial = accion.history(start=fecha_pasado - timedelta(days=5), end=fecha_pasado + timedelta(days=5))
        
        if historial.empty:
            return jsonify({'error': 'No hay datos históricos para esa fecha.'}), 400
        
        precio_pasado = float(historial.iloc[0]["Close"])
        cantidad = inversion / precio_pasado
        
        precio_actual_dict = obtener_precio_accion(ticker)
        if not precio_actual_dict: 
            return jsonify({'error': 'Error obteniendo precio actual.'}), 400
        precio_actual = precio_actual_dict["cierre"]
        
        divs = accion.dividends
        divs_periodo = divs[divs.index > pd.Timestamp(fecha_pasado, tz='America/New_York')] if not divs.empty else pd.Series(dtype=float)
        total_dividendos_por_accion = float(divs_periodo.sum()) if not divs_periodo.empty else 0.0
        dividendos_ganados = total_dividendos_por_accion * cantidad
        
        valor_actual = cantidad * precio_actual
        ganancia_total = (valor_actual + dividendos_ganados) - inversion
        retorno_pct = (ganancia_total / inversion) * 100
        
        return jsonify({
            'ok': True,
            'ticker': ticker,
            'precio_pasado': precio_pasado,
            'cantidad': cantidad,
            'precio_actual': precio_actual,
            'valor_actual': valor_actual,
            'dividendos_ganados': dividendos_ganados,
            'ganancia_total': ganancia_total,
            'retorno_pct': retorno_pct
        })
    except Exception as e:
        return jsonify({'error': f'Error en máquina del tiempo: {str(e)}'}), 400

def _registrar_valor(p: Portafolio):
    val = calcular_valor_portafolio(p)
    p.historial_valor.append({
        'fecha': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'valor': val['valor_total']
    })

if __name__ == '__main__':
    print('\n Servidor web del Simulador de Portafolio')
    print('  Abre tu navegador en: http://localhost:5000\n')
    app.run(debug=False, port=5000)
