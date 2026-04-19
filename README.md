# 📈 Simulador de Portafolio de Inversión v1.0

### **Universidad — Materia: Estructura de Datos / Finanzas Computacionales**

Este es un simulador avanzado de gestión de portafolios de inversión desarrollado en Python. Permite a los usuarios gestionar activos de renta variable (Acciones) y renta fija (CDTs), utilizando datos reales del mercado financiero a través de la API de Yahoo Finance.

---

## 🚀 Características Principales

*   **📊 Datos Reales:** Integración con `yfinance` para obtener precios de cierre, mínimos y máximos en tiempo real.
*   **💼 Gestión de Acciones:** Compra y venta de activos con cálculo automático de comisiones de broker y precio promedio ponderado.
*   **🏦 Renta Fija (CDTs):** Simulación de certificados de depósito que generan intereses diarios y se liquidan al vencimiento.
*   **💰 Dividendos:** Consulta y cobro automático de dividendos con aplicación de retenciones de ley.
*   **📈 Gráficos Avanzados:** Generación de visualizaciones con `matplotlib`:
    *   Evolución histórica del valor total.
    *   Composición del portafolio (Efectivo vs Acciones vs CDTs).
    *   Historial de precios por activo.
    *   Rentabilidad neta por acción.
*   **💾 Persistencia:** Guardado y carga automática del estado del portafolio en formato JSON.

---

## 🛠️ Tecnologías Utilizadas

*   **Python 3.x**
*   **Libraries:**
    *   `yfinance`: Datos del mercado financiero.
    *   `pandas`: Manejo de series de tiempo y estructuras de datos.
    *   `matplotlib`: Generación de reportes visuales.
    *   `json`: Almacenamiento de datos.

---

## 📋 Estructura de Datos

El núcleo del programa utiliza una organización orientada a objetos para gestionar la complejidad del mercado financiero:
*   **Clase Portafolio:** Centraliza el capital, el diccionario de posiciones (Hash Maps para búsqueda rápida O(1)) y listas de transacciones.
*   **Gestión de Historial:** Implementa un registro cronológico de operaciones para el análisis de rendimiento temporal.

---

## 🔧 Instalación y Uso

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/yechavarria17-commits/Inversionistas-so-adores.git
   ```

2. **Instalar dependencias:**
   ```bash
   pip install yfinance pandas matplotlib
   ```

3. **Ejecutar el simulador:**
   ```bash
   python simulador.py
   ```

---

## 📖 Instrucciones de Operación

1. Al iniciar por primera vez, ingresa tu **capital inicial** en USD.
2. Utiliza el **Menú Principal** para navegar entre las opciones (compra, resumen, gráficas, etc.).
3. El sistema guarda automáticamente tus cambios al salir (**Opción 0**).

---

## 👥 Autores
Desarrollado para la facultad de ingeniería/economía.
**Usuario:** yechavarria17

---
*Este proyecto tiene fines académicos para el aprendizaje de estructuras de datos y lógica financiera.*
