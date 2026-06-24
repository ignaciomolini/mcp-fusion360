> **Nota:** Ver [`README.md`](./README.md) para el estado actual del proyecto. Este documento es la especificación original y se preserva como referencia histórica.

# Product Requirements Document (PRD): Fusion 360 MCP Server

## 1. Contexto y Objetivo
Desarrollar un servidor Model Context Protocol (MCP) para Autodesk Fusion 360. El objetivo es permitir que un agente de IA (vía CLI o Claude Desktop) interactúe con el entorno de Fusion 360 usando lenguaje natural para leer parámetros del modelo, calcular métricas (como cinemática o tolerancias de materiales) y generar o modificar geometría, facilitando la automatización en diseños de hardware y mobiliario.

## 2. Arquitectura del Sistema
Debido a que Fusion 360 ejecuta sus scripts y Add-ins dentro de su propio intérprete de Python embebido y requiere que la manipulación de la API ocurra en el hilo principal, la arquitectura debe constar de dos partes:

* **Componente A (Fusion 360 Add-in - Python):** Un Add-in nativo escrito en Python que se ejecuta dentro de Fusion 360. Este componente levanta un servidor local (WebSocket o HTTP en `localhost`) en un hilo secundario y delega las operaciones de la API al hilo principal utilizando `adsk.core.Application.get().fireCustomEvent()`.
* **Componente B (MCP Wrapper - Python o Node.js):** Un servidor MCP estándar que se comunica con el cliente (agente) a través de `stdio`. Traduce las "Tool Calls" del LLM en peticiones de red hacia el Componente A y devuelve los resultados.

## 3. Core Tools (Herramientas expuestas al LLM - MVP)
El agente debe tener acceso a las siguientes herramientas iniciales para validar el flujo de diseño paramétrico y ensamblaje:

### 3.1. Herramientas de Lectura y Análisis
* **`get_active_design_parameters`**:
    * *Descripción:* Devuelve un JSON con todos los User Parameters del diseño activo (nombre, expresión, valor evaluado en milímetros/grados).
* **`measure_clearance`**:
    * *Parámetros:* `body1_name` (string), `body2_name` (string).
    * *Descripción:* Calcula la distancia mínima o interferencia entre dos cuerpos sólidos (ej. para verificar que un mecanismo de elevación de una tapa de madera no colisione con un marco de acero fijo al abrirse).

### 3.2. Herramientas de Modificación y Modelado
* **`update_user_parameter`**:
    * *Parámetros:* `parameter_name` (string), `new_expression` (string).
    * *Descripción:* Modifica el valor de un parámetro existente (ej. cambiar el grosor de los caños de acero estructural) y fuerza un recalculo del modelo (`design.computeAll()`).
* **`create_hardware_cutout`**:
    * *Parámetros:* `target_body` (string), `face_index` (integer), `diameter_mm` (number), `depth_mm` (number).
    * *Descripción:* Crea un boceto (sketch) en la cara especificada y ejecuta una extrusión de corte (Cut Feature). Ideal para automatizar la integración minimalista de hardware, como orificios precisos para botones de encendido o puertos USB directamente en la estructura.

## 4. Requisitos No Funcionales y Manejo de Errores
* **Aislamiento de la API de Fusion:** El Componente B NUNCA debe importar el módulo `adsk`. Todo el código dependiente de la API de Fusion debe vivir exclusivamente en el Componente A.
* **Manejo de Errores Geométricos:** Si una herramienta (como `update_user_parameter`) causa un error en la línea de tiempo de Fusion (ej. se rompe un *fillet* o un boceto queda sobre-restringido), el Componente A debe capturar la excepción y devolver el mensaje de error de la API al agente para que pueda intentar corregirlo.
* **Unidades de Medida:** Fusion 360 internamente maneja todas las longitudes en centímetros. El Add-in (Componente A) debe encargarse de la conversión si el agente asume o envía los datos en milímetros.

## 5. Esquemas de Datos (Ejemplo de Comunicación)
Respuesta esperada de `get_active_design_parameters`:

~~~json
{
  "parameters": [
    {
      "name": "SteelTubeWidth",
      "expression": "40 mm",
      "value_cm": 4.0
    },
    {
      "name": "WoodLidThickness",
      "expression": "25 mm",
      "value_cm": 2.5
    },
    {
      "name": "HingeAngle",
      "expression": "90 deg",
      "value_deg": 90.0
    }
  ]
}
~~~

## 6. Instrucciones de Ejecución para el Agente de Código
1. **Fase 1:** Crea la estructura del proyecto. Genera el archivo manifiesto (`.manifest`) y el script principal en Python para el Add-in de Fusion 360 (Componente A).
2. **Fase 2:** Implementa la lógica de eventos personalizados (`adsk.core.CustomEvent`) en el Add-in para permitir la ejecución segura de comandos de la API desde un hilo secundario (servidor local HTTP/WebSocket).
3. **Fase 3:** Desarrolla el Componente B usando el SDK oficial de MCP. Define las herramientas descritas en la sección 3 e implementa las llamadas al servidor local.
4. **Fase 4:** Realiza un caso de prueba documentado modificando un parámetro geométrico y creando un orificio de corte, verificando que la actualización se refleje en la interfaz gráfica de Fusion 360.
