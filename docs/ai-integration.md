# Integración con IA, Arquitectura Fail-Safe y Políticas de Safety

Este documento describe la arquitectura técnica, las salvaguardas de tolerancia a fallos (*fail-safe*) y las políticas de seguridad pedagógica (*safety*) implementadas en **CapacityAR** para la interacción con Modelos de Lenguaje de Gran Escala (LLM).

Este diseño responde a los requerimientos de calidad de la norma **ISO/IEC 25010:2023** (específicamente en las características de *Fiabilidad*, *Tolerancia a Fallos* y *Disponibilidad*) y formaliza el cierre de la **Brecha B4.7 ("Safety de IA no tratado")**.

---

## 1. Visión General y Principio de Diseño Híbrido

CapacityAR no realiza entrenamiento propio ni *fine-tuning* de modelos base. Se utilizan modelos de lenguaje pre-entrenados de última generación accedidos a través de APIs de inferencia en la nube (Groq con Llama 3.3 70B y Google con Gemini).

Para garantizar predictibilidad pedagógica y evitar comportamientos erráticos, el sistema implementa una **arquitectura híbrida**:
- **Estructura y Reglas de Negocio Determinísticas (Código Python):** El motor de análisis de brechas (`gap_analysis`), la selección y ponderación de habilidades a entrenar, el número de unidades por módulo, los tiempos pedagógicos estimados (10, 15 y 30 minutos) y la corrección de respuestas con cálculo de maestría (`mastery >= 0.80`) son ejecutados exclusivamente por código determinístico en el backend.
- **Generación Textual Adaptativa (LLM):** La IA interviene únicamente en la redacción de contenidos pedagógicos contextualizados a los intereses del estudiante, la generación de consignas y opciones para ejercicios de práctica, la sugerencia de recursos y la elaboración de retroalimentación empática ante fallas.

```
┌────────────────────────────────────────────────────────┐
│      Motor Determinístico (FastAPI + SQLAlchemy)       │
│  - Cálculo de Brecha (Gap Analysis)                    │
│  - Estructura de Fases 5P (Pasión, Play, Práctica)     │
│  - Evaluación de Respuestas y Cálculo de Maestría      │
└───────────────────────────┬────────────────────────────┘
                            │ Orquesta parámetros
                            ▼
┌────────────────────────────────────────────────────────┐
│     Capa de Inferencia LLM (Groq / Google Gemini)      │
│  - Contenido personalizado según intereses             │
│  - Ejercicios prácticos contextualizados               │
│  - Feedback empático (Paciencia - 4° P)                │
└───────────────────────────┬────────────────────────────┘
                            │ Fallback automático ante error
                            ▼
┌────────────────────────────────────────────────────────┐
│        Salvaguarda Fail-Safe (Mock Determinístico)     │
│  - MockPlanGenerator / _mock_resources / Static Text   │
│  - Disponibilidad garantizada (Zero-Downtime)          │
└────────────────────────────────────────────────────────┘
```

---

## 2. Dónde se Utiliza el LLM y Matriz de Responsabilidades

| Componente | Archivo Backend | Responsabilidad del LLM | Salvaguarda / Fallback |
| :--- | :--- | :--- | :--- |
| **Generación de Unidades del Plan** | `app/modules/learning_paths/plan_generator/_base_llm.py` | Redacción de `title`, `content` y 5 ejercicios interactivos adaptados al estudiante. | Si falla, fallback inmediato a `MockPlanGenerator` (`generator_used: "mock"`). |
| **Sugerencia de Recursos de Estudio** | `app/modules/resources/suggester.py` | Recomendación de videos, lecturas y sandboxes clasificados por fase pedagógica. | Guardrail anti-alucinación de enlaces. Si falla, fallback a `_mock_resources()` o lista vacía `[]`. |
| **Feedback Empático ante Fallos** | `app/modules/attempts/feedback.py` | Mensaje motivacional en español rioplatense (Fase Paciencia) sin revelar la respuesta correcta. | Fallback a mensaje estático de aliento (`_STATIC_FAILURE_MESSAGE`). |

### Matriz de Decisión: Código vs. LLM

| Decisión del Sistema | Responsable | Mecanismo de Control |
| :--- | :---: | :--- |
| Habilidades que ingresan al plan, orden y prioridad | **Código** | `gap_report.skills` ordenado por prioridad (`HIGH`, `MEDIUM`, `LOW`). |
| Cantidad de unidades por módulo (3) y fases pedagógicas | **Código** | Tupla fija `(PASION, PLAY, PRACTICA)`. |
| Tiempos pedagógicos de cada fase (10, 15 y 30 min) | **Código** | Diccionario `_PHASE_MINUTES` en `_base_llm.py`. |
| Corrección de la respuesta del estudiante | **Código** | Comparación determinística en `attempts/service.py` (`_evaluate`). |
| Cálculo de dominio acumulado (`skill_mastery`) | **Código** | Proporción de aciertos sobre total de intentos en base de datos. |
| Redacción de títulos, explicaciones y preguntas | **LLM** | Prompt engineering con schema estricto (`UNIT_RESPONSE_SCHEMA`). |
| Enlaces y sugerencias formativas | **LLM** | Filtrado con lista blanca `_KNOWN_DOC_DOMAINS` y búsquedas parametrizadas. |
| Mensaje de contención ante errores | **LLM** | Prompt de Paciencia (4° P) con límite de 60 palabras. |

---

## 3. Proveedores Soportados y Configuración

El sistema soporta dos proveedores de LLM en la nube, seleccionables mediante la variable de entorno `PLAN_GENERATOR`:

| Parámetro | Groq (Proveedor Principal) | Google Gemini (Proveedor Secundario) |
| :--- | :--- | :--- |
| **Variable `PLAN_GENERATOR`** | `groq` | `gemini` |
| **Modelo por defecto** | `llama-3.3-70b-versatile` | `gemini-2.5-flash-lite` |
| **Latencia promedio por llamada** | 1 – 3 segundos | 3 – 7 segundos |
| **Límite de solicitudes (Free Tier)** | 14.400 RPD | 1.500 RPD |
| **Modo de salida estructurada** | `response_format={"type": "json_object"}` | `generation_config={"response_mime_type": "application/json"}` |
| **Gestor de claves de API** | `GROQ_API_KEY` | `GEMINI_API_KEY` |

> [!NOTE]
> Para entornos de pruebas unitarias, integración local o entornos desconectados de red, se configura `PLAN_GENERATOR=mock`, lo que desactiva por completo las llamadas a APIs externas sin requerir claves de API.

---

## 4. Arquitectura de Resiliencia y Comportamiento Fail-Safe

La resiliencia del sistema ante fallos de red, caídas de servicio del proveedor de IA, agotamiento de cuotas (HTTP 429) o respuestas malformadas se sustenta en tres niveles de aislamiento:

### 4.1 Fallback Transparente en Planes: `_PlanGeneratorWithMockFallback`
En `app/modules/learning_paths/plan_generator/factory.py`, toda instancia de generador basado en LLM se envuelve obligatoriamente en la clase decoradora `_PlanGeneratorWithMockFallback`:

```python
class _PlanGeneratorWithMockFallback:
    def __init__(self, primary: PlanGenerator, fallback: PlanGenerator) -> None:
        self._primary = primary
        self._fallback = fallback

    def generate(self, gap_report: GapReport) -> GeneratedPlan:
        try:
            return self._primary.generate(gap_report)
        except Exception:
            logger.exception(
                "Primary plan generator failed; falling back to MockPlanGenerator."
            )
            return self._fallback.generate(gap_report)
```

**Propiedades del mecanismo:**
1. **Captura Total de Excepciones:** Atrapa cualquier error (`TimeoutError`, `APIConnectionError`, `RateLimitError` 429, `LlmResponseError` o errores de validación de Pydantic).
2. **Invocación Inmediata al Mock:** Dispara de forma síncrona `MockPlanGenerator.generate(gap_report)`, generando un plan estructurado pedagógicamente válido en milisegundos.
3. **Registro de Auditoría (Logging):** Registra el *traceback* completo mediante `logger.exception()` para permitir trazabilidad y cálculo de métricas de confiabilidad (MTTR/MTBF).
4. **Persistencia Transparente:** La API nunca retorna un error HTTP 500 al cliente. El plan resultante se almacena en la base de datos identificando su procedencia en el campo `generator_used = "mock"`.

### 4.2 Validación Estricta de Esquemas (Pydantic y `UNIT_RESPONSE_SCHEMA`)
En `app/modules/learning_paths/plan_generator/_base_llm.py`, cada unidad generada por el LLM se valida contra el modelo de datos `GeneratedUnit` de Pydantic:
- Si el LLM omite campos obligatorios (`phase`, `title`, `content`, `exercises`) o devuelve estructuras corruptas, `GeneratedUnit.model_validate(raw)` lanza una `ValidationError`.
- Esta excepción no se silencia de forma silenciosa ni produce datos incompletos en la base de datos: es capturada por `_PlanGeneratorWithMockFallback`, activando el reemplazo integral del plan por la versión Mock certificada.

### 4.3 Guardrails Anti-Alucinación de Enlaces (`suggester.py`)
Uno de los riesgos principales en la recomendación formativa mediante IA es la alucinación de hipervínculos (enlaces a páginas 404 o videos inexistentes). En `app/modules/resources/suggester.py`, la función `_resolve_url()` aplica guardrails estrictos:

1. **Lista Blanca Estricta para Documentación (`_KNOWN_DOC_DOMAINS`):**  
   Solo se aceptan URLs canónicas directas si su dominio pertenece a fuentes oficiales auditadas:
   `developer.mozilla.org`, `docs.python.org`, `git-scm.com`, `react.dev`, `nodejs.org`, `freecodecamp.org`, `w3schools.com`, `tailwindcss.com`, `djangoproject.com`, `fastapi.tiangolo.com`, `kotlinlang.org`, `developer.android.com`, `aws.amazon.com`, `azure.microsoft.com`, `cloud.google.com`.
2. **Prohibición de URLs Fijas en YouTube:**  
   Se prohíbe explícitamente en el prompt del sistema que el LLM invente identificadores de videos de YouTube (`watch?v=...`). Toda recomendación audiovisual se transforma forzosamente en una búsqueda parametrizada segura:
   ```
   https://www.youtube.com/results?search_query={skill_name}+{terminos_busqueda}
   ```
3. **Redirección de Contenido General a Búsqueda Segura:**  
   Si una URL no coincide con la lista blanca o no ofrece certeza de estabilidad, se convierte automáticamente en una búsqueda en Google con términos curados.
4. **Fallback Determinístico en Recursos:**  
   Si la llamada a la API del LLM falla, el sistema invoca `_mock_resources(skill_name, phase)` para entregar recursos estándar probados, o retorna una lista vacía `[]`, asegurando que la carga de la unidad nunca se bloquee.

### 4.4 Manejo de Feedback Empático (4° P: Paciencia en `feedback.py`)
Cuando un estudiante falla un ejercicio de práctica, entra en acción la **Fase de Paciencia**:
- **Desacoplamiento de la Corrección:** La decisión de si la respuesta es correcta o errónea la toma el backend (`is_correct: bool`). El LLM no califica ni juzga la respuesta.
- **Instrucción de Anti-Revelación:** El prompt prohíbe de forma terminante revelar la respuesta correcta o dar la solución explícita. El modelo debe actuar como coach empático en español rioplatense, normalizar el tropiezo y ofrecer una pista conceptual.
- **Fallback Estático Fail-Safe:** Si el LLM no responde o lanza error, la función `_failure_feedback` retorna de inmediato el mensaje estático predefinido:
  > *"No te preocupes, equivocarte es parte de aprender. Repasá el concepto y volvé a intentarlo. La mayoría de los desarrolladores necesitó más de un intento en este tipo de ejercicios."*

---

## 5. Safety de IA y Límites de las Recomendaciones (Cierre Brecha B4.7)

En cumplimiento de los principios de **Safety y Responsabilidad en Sistemas Autónomos y Adaptativos** (ISO/IEC 25010 / Brecha B4.7), se establecen los siguientes límites y directrices operativas:

### 5.1 Naturaleza Orientativa y No Vinculante
- **Alcance Educativo:** Los planes de capacitación generados, sus diagnósticos de brecha y las evaluaciones asociadas constituyen **herramientas de orientación pedagógica y nivelación formativa**.
- **Inexistencia de Certificación Laboral Vinculante:** Ninguna recomendación o puntaje generado por el sistema constituye una certificación técnica oficial, título habilitante ni dictamen psicotécnico sobre la empleabilidad del estudiante frente a las empresas demandantes.

### 5.2 Modelo con Supervisión Humana (Human-in-the-Loop)
- La IA actúa exclusivamente como **asistente del proceso de tutoría**, nunca como decisor autónomo aislado.
- Los tutores humanos asignados (`role: tutor`) tienen acceso al panel de supervisión para:
  1. Visualizar los planes generados y el historial de intentos del estudiante.
  2. Identificar bloqueos en habilidades específicas donde el estudiante no alcance el umbral de maestría (`mastery < 0.80`).
  3. Modificar o reasignar rutas pedagógicas si observan recomendaciones inadecuadas al contexto del postulante.

### 5.3 Bordes Seguros de Contenido y Prevención de Sesgos
- **Restricción de Temperatura:** Las llamadas al LLM operan en rangos de temperatura controlada ($0.6$ a $0.8$), reduciendo la variabilidad y evitando alucinaciones o derivaciones temáticas.
- **Esquema Cerrado:** El uso obligatorio de *JSON Schemas* previene la inyección de textos no estructurados o contenidos ajenos a la consigna académica.
- **Tono Pedagógico Inclusivo:** Los *system prompts* instruyen explícitamente el uso de lenguaje accesible, cercano y libre de sesgos socioeconómicos, adaptado a jóvenes de contextos vulnerables en Argentina.

---

## 6. Contrato de Señalización Frontend / Backend (E1 ↔ E3)

Para que el equipo de Frontend (`E3`) exponga de forma transparente el origen del contenido al usuario final, se definen los siguientes contratos de interfaz:

### 6.1 Trazabilidad del Plan (`generator_used`)
El esquema `GeneratedPlan` expone el campo `generator_used: str`:

| Valor de `generator_used` | Significado Técnico | Comportamiento Esperado en UI (Frontend E3) |
| :--- | :--- | :--- |
| `"groq"` o `"gemini"` | Plan generado dinámicamente mediante LLM. | Mostrar en la cabecera del plan un badge informativo:  <br>`[ ✨ Plan Personalizado con IA ]` acompañado de un tooltip: *"Contenido generado de forma adaptativa según tu perfil. Revisado bajo el modelo pedagógico 5P."* |
| `"mock"` | Plan provisto por el generador determinístico de respaldo (*fail-safe*). | Mostrar badge discreto: <br>`[ 📋 Plan de Respaldo Estándar ]` con tooltip: *"Generado mediante la guía pedagógica base para garantizar disponibilidad inmediata."* |

### 6.2 Señalización en Enlaces de Recursos
En cada recurso dentro de `GeneratedUnit.resources`:
- Si la URL apunta a un dominio de `_KNOWN_DOC_DOMAINS`: La interfaz puede mostrar el icono de *"Documentación Oficial Verificada"*.
- Si la URL contiene `youtube.com/results` o `google.com/search`: La interfaz debe indicar *"Búsqueda recomendada en [YouTube / Google]"*, evitando inducir al alumno a creer que se trata de un video o enlace directo cerrado.

### 6.3 Interfaz de Desescalamiento ante Dudas
En las tarjetas de evaluación y módulos formativos, el frontend debe incluir siempre un botón de acción secundario:
- **`[ 💬 Consultar con mi Tutor ]`:** Permite al estudiante canalizar dudas conceptuales directamente con su tutor humano ante cualquier respuesta de la IA que resulte confusa o insuficiente.

---

## 7. Verificación del Comportamiento Fail-Safe

El comportamiento de degradación elegante y salvaguardas ante fallos se verifica mediante la suite automatizada de pruebas en memoria:

```bash
# Ejecutar suite de integración en el entorno de backend
cd backend
.venv\Scripts\python -m pytest tests/test_integration_api.py
```

### Casos de Prueba Críticos
1. **Fallback de Plan:** `test_learning_path_generation_with_mock` verifica que ante `PLAN_GENERATOR=mock` el endpoint `/api/learning-paths` responde con código HTTP 200, genera los módulos 5P y persiste `generator_used: "mock"`.
2. **Evaluación y Feedback Determinístico:** `test_create_attempt_and_mastery` valida que la corrección del ejercicio y la persistencia de `AttemptResponse` devuelva el mensaje pedagógico sin interrupciones.

---

## 8. Reglas de Mantenimiento para Desarrolladores (DoD)

1. **Inviolabilidad del Fallback a Mock:** Prohibido remover o puentear la clase `_PlanGeneratorWithMockFallback` en `factory.py`.
2. **Preservación de la Lista Blanca:** No agregar dominios a `_KNOWN_DOC_DOMAINS` en `suggester.py` sin previa verificación de que se trata de portales estables con documentación técnica oficial de libre acceso.
3. **No Mover Reglas al Prompt:** La lógica de ponderación, cálculo de notas y umbrales de avance deben permanecer en código Python auditable. El prompt solo da estilo, formato y redacción pedagógica.
4. **Política de Git Local:** Commits y merges se realizan exclusivamente en local. **PROHIBIDO ejecutar git push** al repositorio remoto.
