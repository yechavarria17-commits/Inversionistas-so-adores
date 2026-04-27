# Diagrama UML - Simulador de Portafolio de Inversión

## Diagrama de Clases (Mermaid)

```mermaid
classDiagram
    %% ==================== CLASE PRINCIPAL ====================
    class Portafolio {
        +float capital
        +dict acciones
        +list cdts
        +list historial_transacciones
        +list historial_valor
        +float dividendos_recibidos
        +float comisiones_pagadas
        +__init__(capital_inicial: float)
        +to_dict() dict
        +from_dict(datos: dict) Portafolio$
    }

    %% ==================== ESTRUCTURAS DE DATOS ====================
    class EstructuraAccion {
        +int cantidad
        +float precio_promedio
    }

    class EstructuraCDT {
        +int id
        +float monto_inicial
        +float tasa_anual
        +int dias_plazo
        +string fecha_inicio
        +string fecha_vencimiento
        +float interes_diario
        +float intereses_acumulados
        +int dias_transcurridos
        +bool activo
    }

    class EstructuraTransaccion {
        +string tipo
        +string ticker
        +int cantidad
        +float precio
        +float comision
        +float total
        +string fecha
        +float capital_restante
        +float ganancia
    }

    %% ==================== SERVICIOS ====================
    class ServicioDatosMercado {
        +obtener_precio_accion(ticker: str) dict$
        +obtener_historial_precios(ticker: str, dias: int) Series$
        +obtener_dividendos(ticker: str, dias: int) float$
    }

    class ServicioTransacciones {
        +comprar_accion(portafolio, ticker, cantidad) bool$
        +vender_accion(portafolio, ticker, cantidad) bool$
    }

    class ServicioRentaFija {
        +agregar_cdt(portafolio, monto, tasa_anual, dias_plazo) bool$
        +liquidar_intereses_cdts(portafolio) void$
        +cobrar_dividendos(portafolio) void$
    }

    class ServicioReportes {
        +calcular_valor_portafolio(portafolio) dict$
        +mostrar_resumen(portafolio, capital_inicial) dict$
    }

    class ServicioGraficos {
        +graficar_evolucion_portafolio(portafolio) void$
        +graficar_composicion_portafolio(portafolio) void$
        +graficar_precios_acciones(portafolio, dias) void$
        +graficar_rentabilidad_acciones(portafolio) void$
    }

    class ServicioPersistencia {
        +guardar_portafolio(portafolio, capital_inicial) void$
        +cargar_portafolio() tuple$
    }

    class Principal {
        +mostrar_menu() void$
        +main() void$
    }

    %% ==================== CONSTANTES ====================
    class Constantes {
        +COMISION_BROKER: 0.001$
        +IMPUESTO_DIVIDENDO: 0.10$
        +ARCHIVO_DATOS: "portafolio_datos.json"$
        +ACCIONES_DISPONIBLES: dict$
    }

    %% ==================== RELACIONES ====================
    Portafolio --> "*" EstructuraAccion : contiene
    Portafolio --> "*" EstructuraCDT : contiene
    Portafolio --> "*" EstructuraTransaccion : registra

    ServicioTransacciones ..> Portafolio : opera sobre
    ServicioTransacciones ..> ServicioDatosMercado : utiliza

    ServicioRentaFija ..> Portafolio : opera sobre
    ServicioRentaFija ..> ServicioDatosMercado : utiliza

    ServicioReportes ..> Portafolio : consulta
    ServicioReportes ..> ServicioDatosMercado : utiliza

    ServicioGraficos ..> Portafolio : visualiza
    ServicioGraficos ..> ServicioReportes : utiliza
    ServicioGraficos ..> ServicioDatosMercado : utiliza

    ServicioPersistencia ..> Portafolio : guarda/carga

    Principal ..> Portafolio : crea/usa
    Principal ..> ServicioTransacciones : usa
    Principal ..> ServicioRentaFija : usa
    Principal ..> ServicioReportes : usa
    Principal ..> ServicioGraficos : usa
    Principal ..> ServicioPersistencia : usa
    Principal ..> Constantes : accede
```

---

## Diagrama de Flujo del Sistema

```mermaid
flowchart TD
    A[Inicio] --> B{Portafolio\nexistente?}
    B -->|Sí| C[Cargar desde JSON]
    B -->|No| D[Solicitar Capital Inicial]
    D --> E[Crear Nuevo Portafolio]
    C --> F[Mostrar Menú Principal]
    E --> F

    F --> G{Opción}

    G -->|1| H[Comprar Acciones]
    G -->|2| I[Vender Acciones]
    G -->|3| J[Crear CDT]
    G -->|4| K[Liquidar Intereses]
    G -->|5| L[Cobrar Dividendos]
    G -->|6| M[Mostrar Resumen]
    G -->|7| N[Ver Acciones Disponibles]
    G -->|8| O[Graficar Evolución]
    G -->|9| P[Graficar Composición]
    G -->|10| Q[Graficar Precios]
    G -->|11| R[Graficar Rentabilidad]
    G -->|12| S[Guardar Portafolio]
    G -->|0| T[Guardar y Salir]

    H --> U[Consultar Precio\nYahoo Finance]
    I --> U
    L --> V[Consultar Dividendos\nYahoo Finance]

    U --> W[Validar Capital]
    W -->|Suficiente| X[Ejecutar Operación]
    W -->|Insuficiente| Y[Error: Sin fondos]

    X --> Z[Actualizar Portafolio]
    Y --> F
    Z --> F
    J --> F
    K --> F
    V --> F
    M --> F
    N --> F
    O --> F
    P --> F
    Q --> F
    R --> F
    S --> F
```

---

## Diagrama de Secuencia - Compra de Acción

```mermaid
sequenceDiagram
    actor Usuario
    participant Principal
    participant ServicioTransacciones
    participant ServicioDatosMercado
    participant YahooFinance
    participant Portafolio

    Usuario->>Principal: Seleccionar "Comprar Acciones"
    Principal->>Usuario: Solicitar ticker y cantidad
    Usuario->>Principal: ticker="NVDA", cantidad=20

    Principal->>ServicioTransacciones: comprar_accion(portafolio, "NVDA", 20)

    ServicioTransacciones->>ServicioDatosMercado: obtener_precio_accion("NVDA")
    ServicioDatosMercado->>YahooFinance: Petición API
    YahooFinance-->>ServicioDatosMercado: precio=201.68
    ServicioDatosMercado-->>ServicioTransacciones: datos mercado

    ServicioTransacciones->>ServicioTransacciones: Validar rango precio
    ServicioTransacciones->>ServicioTransacciones: Calcular comisión (0.1%)
    ServicioTransacciones->>Portafolio: Verificar capital >= costo_total
    Portafolio-->>ServicioTransacciones: OK

    ServicioTransacciones->>Portafolio: capital -= costo_total
    ServicioTransacciones->>Portafolio: comisiones_pagadas += comision
    ServicioTransacciones->>Portafolio: Actualizar/Agregar acciones
    ServicioTransacciones->>Portafolio: Registrar transacción

    ServicioTransacciones-->>Principal: True (éxito)
    Principal-->>Usuario: Confirmación compra
```

---

## Estructura de Datos del Portafolio (JSON)

```mermaid
erDiagram
    PORTAFOLIO ||--|| CAPITAL : contiene
    PORTAFOLIO ||--o{ ACCIONES : posee
    PORTAFOLIO ||--o{ CDTS : mantiene
    PORTAFOLIO ||--o{ TRANSACCIONES : registra
    PORTAFOLIO ||--o{ HISTORIAL_VALOR : almacena
    PORTAFOLIO ||--|| DIVIDENDOS : acumula
    PORTAFOLIO ||--|| COMISIONES : registra

    PORTAFOLIO {
        float capital
        float capital_inicial
    }

    ACCIONES {
        string ticker PK
        int cantidad
        float precio_promedio
    }

    CDTS {
        int id PK
        float monto_inicial
        float tasa_anual
        int dias_plazo
        date fecha_inicio
        date fecha_vencimiento
        float interes_diario
        float intereses_acumulados
        int dias_transcurridos
        boolean activo
    }

    TRANSACCIONES {
        string tipo
        string ticker
        int cantidad
        float precio
        float comision
        float total
        datetime fecha
        float capital_restante
        float ganancia
    }

    HISTORIAL_VALOR {
        datetime fecha
        float valor_total
    }
```
