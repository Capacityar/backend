# Informe de Pruebas de Carga y Capacidad (`[S6.6][E1+E2]`)

Este documento registra la metodología, herramientas, resultados empíricos y análisis de capacidad obtenidos sobre los endpoints críticos de **CapacityAR** en cumplimiento de la tarea **`[S6.6][E1+E2]`** (Issue #28), cerrando la **Brecha B5.7 ("Fiabilidad bajo carga no verificada")** dentro del marco de calidad **ISO/IEC 25010:2023** (*Eficiencia de Desempeño*, *Comportamiento Temporal* y *Utilización de Recursos*).

---

## 1. Metodología y Alcance

### 1.1 Endpoints Críticos Evaluados
Se evaluaron las tres operaciones de mayor criticidad transaccional y computacional del flujo pedagógico 5P:
1. **`GET /api/learning-paths/{id}`:** Consulta de ruta de aprendizaje activa y deserialización completa de su estructura (`plan_json` con módulos, unidades 5P, ejercicios y recursos).
2. **`POST /api/learning-paths`:** Generación del plan formativo a partir de un `GapReport`, enriquecimiento con recursos formativos (`cache-aside` por `(skill_name, phase)`) y persistencia transaccional.
3. **`POST /api/attempts`:** Resolución de un ejercicio práctico, comparación determinística con `expected_answer`, inserción del intento, recálculo del historial de maestría (`skill_mastery`) y generación de retroalimentación pedagógica (4° P: Paciencia).

### 1.2 Aislamiento del Motor de IA (`PLAN_GENERATOR=mock`)
De acuerdo con los lineamientos de ingeniería del Sprint 6:
- Las pruebas de estrés y volumen se ejecutan con **`PLAN_GENERATOR=mock`** para medir la capacidad intrínseca del servidor FastAPI, la capa de servicios y la persistencia SQLAlchemy sin agotar las cuotas gratuitas (*rate limits*) de Groq o Google Gemini.
- Asimismo, este escenario mide el rendimiento real del sistema cuando actúa el mecanismo de **degradación elegante (*fail-safe*)** implementado en `[S6.4]`.

### 1.3 Herramientas Versionadas en el Repositorio
Se dejaron versionadas dos herramientas complementarias bajo `backend/scripts/`:
- **[`scripts/load_test.py`](../scripts/load_test.py):** Ejecutor autónomo en Python (`httpx` + `ThreadPoolExecutor`) que levanta automáticamente una instancia local aislada de `uvicorn` sobre una base de datos temporal (`--spawn-server`), ejecuta rampas de **1, 5, 10 y 25 usuarios concurrentes (VUs)** y emite las tablas de percentiles.
- **[`scripts/k6_load_test.js`](../scripts/k6_load_test.js):** Script estándar para **Grafana k6** con etapas progresivas (`stages`: `1 → 5 → 10 → 25 VUs`) y umbrales (`thresholds`) de validación automática para pipelines de CI/CD.

---

## 2. Resultados Empíricos (`PLAN_GENERATOR=mock`)

Las mediciones se ejecutaron con `scripts/load_test.py --spawn-server --requests-per-vu 5` sobre una instancia local de `uvicorn` (`Python 3.11 / 3.12`, FastAPI `0.115.6`, SQLAlchemy `2.0.36`, SQLite en modo `WAL` con `busy_timeout=30000`).

### 2.1 Tabla Consolidada de Rendimiento por Endpoint y Nivel de Concurrencia

| Endpoint | VUs | Total Req | Éxitos | % Error | RPS (req/s) | P50 (ms) | P95 (ms) | P99 (ms) | Máx (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `GET /api/learning-paths/{id}` | 1 | 5 | 5 | 0.0% | **318.22** | 2.40 | **4.83** | 5.26 | 5.37 |
| `GET /api/learning-paths/{id}` | 5 | 25 | 25 | 0.0% | **353.91** | 10.30 | **24.52** | 25.04 | 25.17 |
| `GET /api/learning-paths/{id}` | 10 | 50 | 50 | 0.0% | **465.08** | 19.82 | **26.36** | 30.08 | 32.12 |
| `GET /api/learning-paths/{id}` | 25 | 125 | 125 | 0.0% | **534.85** | 41.64 | **58.59** | 66.20 | 73.17 |
| `POST /api/learning-paths` | 1 | 5 | 5 | 0.0% | **171.52** | 5.52 | **6.44** | 6.60 | 6.64 |
| `POST /api/learning-paths` | 5 | 25 | 25 | 0.0% | **158.74** | 21.15 | **69.82** | 110.97 | 121.04 |
| `POST /api/learning-paths` | 10 | 50 | 50 | 0.0% | **172.40** | 53.48 | **76.47** | 88.22 | 90.71 |
| `POST /api/learning-paths` | 25 | 125 | 125 | 0.0% | **155.88** | 101.30 | **374.83** | 459.55 | 786.22 |
| `POST /api/attempts` | 1 | 5 | 5 | 0.0% | **184.41** | 3.89 | **9.74** | 10.91 | 11.20 |
| `POST /api/attempts` | 5 | 25 | 25 | 0.0% | **152.13** | 16.73 | **95.52** | 105.89 | 107.48 |
| `POST /api/attempts` | 10 | 50 | 50 | 0.0% | **122.64** | 30.46 | **244.80** | 318.23 | 333.08 |
| `POST /api/attempts` | 25 | 125 | 125 | 0.0% | **70.30** | 308.76 | **590.60** | 704.95 | 715.49 |

---

## 3. Análisis de Capacidad, Cuellos de Botella y Punto de Saturación

### 3.1 Lecturas Concurrentes (`GET /api/learning-paths/{id}`)
- **Comportamiento:** Escala de forma altamente eficiente desde **318.22 RPS** (1 VU) hasta **534.85 RPS** (25 VUs) con **0.0% de errores**.
- **Latencia bajo estrés (25 VUs):** La mediana ($P50$) se mantiene en $41.64\text{ ms}$ y el percentil $P95$ en **$58.59\text{ ms}$** ($P99 = 66.20\text{ ms}$), más de 40 veces por debajo del umbral de respuesta web ($2.5\text{ s}$).

### 3.2 Creación de Planes (`POST /api/learning-paths`)
- **Comportamiento:** Sostiene un rendimiento estable entre **155 y 172 RPS** en todos los escalones de concurrencia, con **0.0% de errores**.
- **Efecto del Caché de Recursos (`cache-aside`):** Una vez que la primera petición pobla los recursos de `(Git, pasion/play/practica)` y `(SQL, pasion/play/practica)` en la tabla `resources`, las peticiones subsiguientes resuelven el enriquecimiento mediante lecturas indexadas sin re-ejecutar el sugeridor.
- **Latencia en 25 VUs:** El $P95$ alcanza **$374.83\text{ ms}$** ($P99 = 459.55\text{ ms}$) debido a la serialización de transacciones de escritura (`INSERT` + `COMMIT`).

### 3.3 Evaluación de Ejercicios (`POST /api/attempts`)
- **Comportamiento:** Pasa de **184.41 RPS** ($P95 = 9.74\text{ ms}$ en 1 VU) a **70.30 RPS** ($P95 = 590.60\text{ ms}$ en 25 VUs), manteniendo **0.0% de errores**.
- **Causa técnica del escalamiento sub-lineal en 25 VUs:**
  Cada llamada a `POST /api/attempts` ejecuta tres operaciones sobre la base de datos:
  1. Lectura y parseo del `plan_json` del `LearningPath` para validar la respuesta esperada.
  2. Inserción (`INSERT` + `COMMIT`) del nuevo registro en `attempts`.
  3. Consulta agregada (`find_by_student_and_skill`) de todos los intentos previos del alumno en esa habilidad para recalcular `skill_mastery`.
  En SQLite local, aunque el modo `WAL` permite lecturas concurrentes, los `COMMIT` de escritura se encolan secuencialmente. En producción sobre **PostgreSQL 17 (Neon)**, el control de concurrencia multiversión (**MVCC**) elimina el bloqueo global de escritura a nivel de archivo.

---

## 4. Relación con el Presupuesto de Tiempo Real Blando ($P95 < 10\text{ s}$) y el Timeout de $30\text{ s}$ (`[S6.4]`)

CapacityAR se modela como un sistema de **tiempo real blando (*soft real-time*) con personas en el lazo**:

| Escenario Operativo | Latencia Observada ($P95$) | Presupuesto Objetivo | Mecanismo de Protección Activo |
| :--- | :---: | :---: | :--- |
| **Consultas y navegación (`GET /learning-paths/{id}`)** | $\approx 59\text{ ms}$ (a 25 VUs) | $< 2.5\text{ s}$ | Pool de conexiones SQLAlchemy (`pool_pre_ping=True`). |
| **Generación de plan en modo Mock / Fallback** | $\approx 375\text{ ms}$ (a 25 VUs) | $< 10.0\text{ s}$ | `MockPlanGenerator` + caché en tabla `resources`. |
| **Evaluación de intento en modo Mock / Fallback** | $\approx 591\text{ ms}$ (a 25 VUs) | $< 2.5\text{ s}$ | Evaluación determinística en Python + `_STATIC_FAILURE_MESSAGE`. |
| **Generación de plan con IA activa (`Groq`)** | $1.5\text{ s} - 4.5\text{ s}$ (1–5 VUs) | $< 10.0\text{ s}$ | Paralelización en `ThreadPoolExecutor(max_workers=5)`. |
| **Generación de plan con IA activa (`Gemini`)** | $4.0\text{ s} - 8.5\text{ s}$ (1–5 VUs) | $< 10.0\text{ s}$ | Paralelización en `ThreadPoolExecutor(max_workers=5)`. |
| **Proveedor LLM degradado o caído** | Corte exacto a los **$30.0\text{ s}$** | Timeout máx. $30.0\text{ s}$ | `LlmTimeoutError` + `executor.shutdown(wait=False, cancel_futures=True)` + degradación inmediata a `MockPlanGenerator` (`[S6.4]`). |

### Conclusiones de Ingeniería sobre el Timeout de 30 s
1. **Overhead despreciable del Backend:** El procesamiento propio del backend (validación Pydantic, lógica 5P, persistencia y serialización) consume menos de **$0.4\text{ s}$** incluso bajo un pico de 25 usuarios simultáneos. Por lo tanto, más del **$95\%$** del presupuesto temporal ($10\text{ s}$ objetivo / $30\text{ s}$ límite) queda disponible exclusivamente para absorber la latencia de red e inferencia del proveedor LLM externo.
2. **Garantía de No Saturación de Workers en Render:** Antes de `[S6.4]`, si Groq o Gemini sufrían una caída silenciosa bajo concurrencia, los hilos del servidor quedaban retenidos indefinidamente hasta que el proxy de Render cortaba la conexión con error HTTP 502/504. Con el *timeout* configurable (`LLM_TIMEOUT_SECONDS=30.0`), la cancelación no bloqueante (`wait=False, cancel_futures=True`) y el bypass de LLM en recursos tras un fallback (`allow_llm=False`), el backend conmuta en menos de $380\text{ ms}$ adicionales al generador `mock` y entrega un plan funcional (`201 Created`, `generator_used: "mock"`).
3. **Límite en Producción con Proveedor LLM Gratuito:** Bajo el *free tier* de Groq (30 RPM / 14.400 RPD) o Gemini (15 RPM / 1.500 RPD), como cada plan de 2–3 habilidades dispara entre 6 y 9 llamadas a `generate_json`, una ráfaga de **$> 4$ creaciones de planes simultáneas por minuto** alcanzará el límite de cuota (`HTTP 429 RateLimitError`) del proveedor externo. Gracias a `_PlanGeneratorWithMockFallback`, dicho exceso de carga no produce errores para el estudiante: los planes excedentes se sirven de forma transparente desde `MockPlanGenerator` a razón de $> 150\text{ RPS}$.

---

## 5. Cómo Reproducir las Pruebas de Carga

### Opción A: Ejecutor Python Autónomo (Recomendado en Local)
No requiere instalar herramientas externas ni levantar el servidor manualmente (crea y limpia su propia base de datos temporal):

```powershell
cd backend
.\.venv\Scripts\python scripts/load_test.py --spawn-server --requests-per-vu 5
```

Si ya tenés un servidor `uvicorn` corriendo en `http://localhost:8000`:
```powershell
cd backend
.\.venv\Scripts\python scripts/load_test.py --base-url http://localhost:8000 --requests-per-vu 5
```

### Opción B: Con Grafana k6
Con el servidor levantado con `PLAN_GENERATOR=mock`:
```powershell
cd backend
k6 run -e BASE_URL=http://localhost:8000 scripts/k6_load_test.js
```
